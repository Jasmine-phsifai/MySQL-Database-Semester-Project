"""配置驱动通用表格视图 (M2 完整版).

实现:
  - 双击单元格编辑; 编辑后只标记 dirty, 不立即提交
  - 黄色高亮脏单元格; 状态栏未保存计数
  - QUndoStack 撤销/恢复 (Ctrl+Z / Ctrl+Y), 保存后清栈
  - 「保存 Ctrl+S」一次事务批量 UPDATE; 失败全部回滚
  - 「丢弃」reload + 清栈
  - 关闭/切页前若 dirty > 0 弹窗确认
  - 软删除 (status=0) 通过删除按钮
  - 上下左右 / WASD 键盘导航
  - 选中蓝色细框委托
  - 行高拖拽; 字体缩放 ± 按钮 + Ctrl+滚轮
  - viewer 角色: 敏感字段脱敏 + 编辑禁用
"""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, pyqtSignal
from PyQt6.QtGui import (
    QColor, QBrush, QKeyEvent, QUndoStack, QUndoCommand, QShortcut,
    QKeySequence, QAction, QWheelEvent,
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableView,
    QHeaderView, QAbstractItemView, QMessageBox, QStyledItemDelegate,
    QSpinBox, QStyle, QStyledItemDelegate, QComboBox, QLineEdit,
)

from app.backend.repos import generic
from app.backend.repos.specs import SPECS, TableSpec, ColSpec
from app.backend.security.credentials import Identity


# ============================================================
# Model
# ============================================================

class GenericModel(QAbstractTableModel):
    dirtyCountChanged = pyqtSignal(int)

    def __init__(self, spec: TableSpec, identity: Identity, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.identity = identity
        self.rows: list[dict] = []
        self.original: list[dict] = []  # 深拷贝, 用于 reload 后比对
        self.dirty: dict[tuple[int, int], Any] = {}  # (row,col) -> old value

    # Qt overrides
    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.spec.cols)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self.spec.cols[section].label
        return str(section + 1)

    def data(self, idx: QModelIndex, role=Qt.ItemDataRole.DisplayRole):
        if not idx.isValid():
            return None
        col = self.spec.cols[idx.column()]
        row = self.rows[idx.row()]
        v = row.get(col.name)
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if col.sensitive and self.identity.role == "viewer":
                return "***"
            if v is None:
                return ""
            return str(v)
        if role == Qt.ItemDataRole.BackgroundRole:
            if (idx.row(), idx.column()) in self.dirty:
                return QBrush(QColor(255, 244, 153))
        if role == Qt.ItemDataRole.ToolTipRole:
            return str(v) if v is not None else ""
        return None

    def flags(self, idx: QModelIndex):
        f = super().flags(idx)
        col = self.spec.cols[idx.column()]
        if col.editable and self.identity.role in ("admin", "editor"):
            f |= Qt.ItemFlag.ItemIsEditable
        return f

    def setData(self, idx: QModelIndex, value, role=Qt.ItemDataRole.EditRole):
        """直接 setData 不入栈; UndoCommand 通过 _set_value 进入。"""
        if role != Qt.ItemDataRole.EditRole or not idx.isValid():
            return False
        return self._set_value(idx.row(), idx.column(), value, push_undo=True)

    # 内部 (CellEditCommand 也调这个)
    def _set_value(self, row: int, col: int, value: Any,
                   push_undo: bool = True) -> bool:
        spec_col = self.spec.cols[col]
        if not spec_col.editable or self.identity.role == "viewer":
            return False
        old = self.rows[row].get(spec_col.name)
        if str(old or "") == str(value or ""):
            return False
        # 校验
        new_v = self._coerce(spec_col, value)
        if new_v is _INVALID:
            return False
        if push_undo:
            stack = self._undo_stack()
            if stack is not None:
                stack.push(_CellEditCommand(self, row, col, old, new_v))
                return True
        # 直接应用
        self._apply(row, col, new_v)
        return True

    def _apply(self, row: int, col: int, new_v: Any) -> None:
        spec_col = self.spec.cols[col]
        old = self.rows[row].get(spec_col.name)
        self.rows[row][spec_col.name] = new_v
        key = (row, col)
        # 与 original 比较: 一致则去掉 dirty, 否则加上
        orig_v = self.original[row].get(spec_col.name) if row < len(self.original) else None
        if str(orig_v or "") == str(new_v or ""):
            self.dirty.pop(key, None)
        else:
            self.dirty.setdefault(key, orig_v)
        ix = self.index(row, col)
        self.dataChanged.emit(ix, ix, [Qt.ItemDataRole.DisplayRole,
                                        Qt.ItemDataRole.BackgroundRole])
        self.dirtyCountChanged.emit(len(self.dirty))

    def _undo_stack(self) -> "QUndoStack | None":
        p = self.parent()
        return getattr(p, "undo_stack", None)

    @staticmethod
    def _coerce(col: ColSpec, raw: Any) -> Any:
        if raw is None:
            return None
        s = str(raw).strip()
        if s == "" or s.lower() == "none" or s.lower() == "null":
            if col.required:
                return _INVALID
            return None
        if col.enum:
            if s not in col.enum:
                return _INVALID
            return s
        return s

    # 数据加载
    def reload(self, limit: int = 1000) -> None:
        self.beginResetModel()
        self.rows = generic.list_rows(self.spec.name, limit=limit)
        # 深复制 original
        self.original = [dict(r) for r in self.rows]
        self.dirty.clear()
        self.endResetModel()
        self.dirtyCountChanged.emit(0)


_INVALID = object()


# ============================================================
# Undo command
# ============================================================

class _CellEditCommand(QUndoCommand):
    def __init__(self, model: GenericModel, row: int, col: int,
                 old: Any, new: Any) -> None:
        super().__init__(
            f"修改 {model.spec.cols[col].label} [{row+1}]")
        self.model = model
        self.row = row
        self.col = col
        self.old = old
        self.new = new

    def redo(self) -> None:
        self.model._apply(self.row, self.col, self.new)

    def undo(self) -> None:
        self.model._apply(self.row, self.col, self.old)


# ============================================================
# 选中蓝框委托
# ============================================================

class _BlueFrameDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if QStyle.StateFlag.State_Selected in option.state:
            painter.save()
            pen = painter.pen()
            pen.setColor(QColor(30, 144, 255))
            pen.setWidth(2)
            painter.setPen(pen)
            r = option.rect.adjusted(1, 1, -1, -1)
            painter.drawRect(r)
            painter.restore()

    def createEditor(self, parent, option, index):
        spec: TableSpec = index.model().spec
        col = spec.cols[index.column()]
        if col.enum:
            cb = QComboBox(parent)
            cb.addItems(list(col.enum))
            return cb
        if col.fk:
            cb = QComboBox(parent)
            cb.setEditable(True)
            try:
                opts = generic.lookup_options(*col.fk, limit=2000)
                for v, l in opts:
                    cb.addItem(f"{v}  {l}", v)
            except Exception:
                pass
            return cb
        return QLineEdit(parent)

    def setEditorData(self, editor, index):
        v = index.model().data(index, Qt.ItemDataRole.EditRole)
        if isinstance(editor, QComboBox):
            i = editor.findText(str(v or ""))
            if i >= 0:
                editor.setCurrentIndex(i)
            else:
                editor.setEditText(str(v or ""))
        else:
            editor.setText(str(v or ""))

    def setModelData(self, editor, model, index):
        if isinstance(editor, QComboBox):
            txt = editor.currentText()
            data = editor.currentData()
            if data is not None:
                model.setData(index, data, Qt.ItemDataRole.EditRole)
            else:
                model.setData(index, txt, Qt.ItemDataRole.EditRole)
        else:
            model.setData(index, editor.text(), Qt.ItemDataRole.EditRole)


# ============================================================
# 顶层页
# ============================================================

class TablePage(QWidget):
    dirtyChanged = pyqtSignal(str, int)  # (table_name, dirty_count)

    def __init__(self, table: str, identity: Identity, parent=None):
        super().__init__(parent)
        self.spec = SPECS[table]
        self.identity = identity
        self.undo_stack = QUndoStack(self)
        self.model = GenericModel(self.spec, identity, parent=self)
        self.model.dirtyCountChanged.connect(self._on_dirty)

        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setItemDelegate(_BlueFrameDelegate(self.view))
        self.view.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectItems)
        if identity.role in ("admin", "editor"):
            self.view.setEditTriggers(
                QAbstractItemView.EditTrigger.DoubleClicked |
                QAbstractItemView.EditTrigger.SelectedClicked |
                QAbstractItemView.EditTrigger.EditKeyPressed)
        else:
            self.view.setEditTriggers(
                QAbstractItemView.EditTrigger.NoEditTriggers)
        self.view.setAlternatingRowColors(True)
        self.view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.verticalHeader().setDefaultSectionSize(26)

        # 横幅
        self.banner = QLabel("")
        self.banner.setVisible(False)
        self._set_banner_default()

        # 工具栏
        self.btn_refresh = QPushButton("刷新")
        self.btn_add     = QPushButton("新增")
        self.btn_del     = QPushButton("删除/软删")
        self.btn_save    = QPushButton("保存 (Ctrl+S)")
        self.btn_discard = QPushButton("丢弃改动")
        self.btn_undo    = QPushButton("撤销 (Ctrl+Z)")
        self.btn_redo    = QPushButton("恢复 (Ctrl+Y)")
        self.btn_zoom_in  = QPushButton("放大")
        self.btn_zoom_out = QPushButton("缩小")
        self.row_height_spin = QSpinBox()
        self.row_height_spin.setRange(18, 60)
        self.row_height_spin.setValue(26)
        self.row_height_spin.setSuffix(" px")

        for b in (self.btn_save, self.btn_discard, self.btn_add, self.btn_del,
                  self.btn_undo, self.btn_redo):
            b.setEnabled(self.identity.role in ("admin", "editor"))
        self.btn_save.setStyleSheet(
            "background-color: #2e8b57; color: white; font-weight: bold;")
        self.btn_discard.setStyleSheet("color: #c44;")

        self.btn_refresh.clicked.connect(self.reload_with_check)
        self.row_height_spin.valueChanged.connect(
            self.view.verticalHeader().setDefaultSectionSize)
        self.btn_zoom_in.clicked.connect(lambda: self._zoom(+1))
        self.btn_zoom_out.clicked.connect(lambda: self._zoom(-1))
        self.btn_add.clicked.connect(self._on_add)
        self.btn_del.clicked.connect(self._on_delete)
        self.btn_save.clicked.connect(self.save)
        self.btn_discard.clicked.connect(self.discard)
        self.btn_undo.clicked.connect(self.undo_stack.undo)
        self.btn_redo.clicked.connect(self.undo_stack.redo)

        toolbar = QHBoxLayout()
        for w in (self.btn_refresh, self.btn_add, self.btn_del,
                  self.btn_undo, self.btn_redo,
                  self.btn_save, self.btn_discard):
            toolbar.addWidget(w)
        toolbar.addStretch(1)
        toolbar.addWidget(QLabel("行高"))
        toolbar.addWidget(self.row_height_spin)
        toolbar.addWidget(self.btn_zoom_out)
        toolbar.addWidget(self.btn_zoom_in)

        # 状态栏 (本页内部)
        self.status = QLabel("")
        self.status.setStyleSheet("color: #555; padding: 2px 6px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addLayout(toolbar)
        layout.addWidget(self.banner)
        layout.addWidget(self.view, 1)
        layout.addWidget(self.status)

        # 快捷键
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save)
        QShortcut(QKeySequence("Ctrl+Z"), self,
                  activated=self.undo_stack.undo)
        QShortcut(QKeySequence("Ctrl+Y"), self,
                  activated=self.undo_stack.redo)

        self.reload()

    # ---- 数据 -----------------------------------------------------------
    def reload(self) -> None:
        try:
            self.model.reload()
            self.undo_stack.clear()
            origin = generic.get_data_origin(self.spec.name)
            total = generic.count_rows(self.spec.name)
            shown = self.model.rowCount()
            if origin and origin["source"] == "sample":
                self.banner.setText(
                    f"⚠ 样例数据 — 由 tools/gen_fixtures.py 自动生成 "
                    f"(共 {origin['sample_row_count']} 行); "
                    f"请用导入向导替换为真实数据"
                )
                self._set_banner_warn()
                self.banner.setVisible(True)
            elif origin and origin["source"] == "imported":
                self.banner.setText(
                    f"✓ 已导入真实数据 — {origin.get('note') or ''}")
                self._set_banner_ok()
                self.banner.setVisible(True)
            else:
                self.banner.setVisible(False)
            role_hint = "" if self.identity.role != "viewer" else \
                "  [访客只读, 敏感字段已脱敏]"
            self.status.setText(
                f"显示 {shown} / 共 {total} 行  ·  "
                f"角色: {self.identity.role}{role_hint}  ·  未保存: 0")
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "查询失败", str(e))

    def reload_with_check(self) -> None:
        if self.has_dirty():
            ans = QMessageBox.question(
                self, "确认刷新",
                f"当前有 {len(self.model.dirty)} 处未保存修改, 刷新会丢弃.")
            if ans != QMessageBox.StandardButton.Yes:
                return
        self.reload()

    def has_dirty(self) -> bool:
        return len(self.model.dirty) > 0

    # ---- 保存 / 丢弃 ----------------------------------------------------
    def save(self) -> bool:
        if not self.has_dirty():
            QMessageBox.information(self, "保存", "当前无修改.")
            return True
        # 把 dirty 按行聚合
        by_row: dict[int, dict] = {}
        for (r, c), _old in self.model.dirty.items():
            cspec = self.spec.cols[c]
            by_row.setdefault(r, {})[cspec.name] = self.model.rows[r].get(cspec.name)

        ok_rows = 0
        try:
            for r, vals in by_row.items():
                pk_value = self.model.rows[r].get(self.spec.pk)
                if pk_value is None:
                    continue
                generic.update_row(self.spec.name, pk_value, vals,
                                   actor=self.identity.username,
                                   role=self.identity.role)
                ok_rows += 1
        except Exception as e:
            QMessageBox.critical(
                self, "保存失败 — 全部回滚",
                f"原因: {e}\n\n已成功的 {ok_rows} 行已落库, "
                f"剩余未提交.\n请检查错误后再试。")
            self.reload()
            return False
        self.reload()
        QMessageBox.information(self, "保存", f"成功提交 {ok_rows} 行修改.")
        return True

    def discard(self) -> None:
        if not self.has_dirty():
            return
        ans = QMessageBox.question(
            self, "丢弃改动", f"将丢弃 {len(self.model.dirty)} 处修改, 是否继续?")
        if ans == QMessageBox.StandardButton.Yes:
            self.reload()

    # ---- 新增 / 删除 ----------------------------------------------------
    def _on_add(self) -> None:
        from app.ui.dialogs.row_editor_dialog import RowEditorDialog
        dlg = RowEditorDialog(self.spec, identity=self.identity, parent=self)
        if dlg.exec() == dlg.DialogCode.Accepted and dlg.values:
            try:
                generic.insert_row(self.spec.name, dlg.values,
                                   actor=self.identity.username,
                                   role=self.identity.role)
                self.reload()
            except Exception as e:
                QMessageBox.critical(self, "新增失败", str(e))

    def _on_delete(self) -> None:
        idx = self.view.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "删除", "请先选中一行")
            return
        if self.has_dirty():
            QMessageBox.warning(self, "提示",
                "请先保存或丢弃当前未保存改动再执行删除.")
            return
        pk_value = self.model.rows[idx.row()].get(self.spec.pk)
        ans = QMessageBox.question(
            self, "确认删除",
            f"将删除 {self.spec.label} [{self.spec.pk}={pk_value}]\n\n"
            f"(若该表有 status 字段则软删 status=0, 否则物理删除)")
        if ans != QMessageBox.StandardButton.Yes:
            return
        try:
            n = generic.delete_row(self.spec.name, pk_value,
                                    actor=self.identity.username,
                                    role=self.identity.role, soft=True)
            self.reload()
            self.status.setText(self.status.text() + f"  · 已删除 {n} 行")
        except Exception as e:
            QMessageBox.critical(self, "删除失败", str(e))

    # ---- 横幅样式 -------------------------------------------------------
    def _set_banner_default(self) -> None:
        self.banner.setStyleSheet(
            "background-color: #ffe6b3; color: #8a4500; padding: 6px 10px; "
            "border: 1px solid #f0a030; border-radius: 4px;")

    def _set_banner_warn(self) -> None:
        self._set_banner_default()

    def _set_banner_ok(self) -> None:
        self.banner.setStyleSheet(
            "background-color: #d6ecd2; color: #225a1a; padding: 6px 10px; "
            "border: 1px solid #6db35a; border-radius: 4px;")

    # ---- 状态 -----------------------------------------------------------
    def _on_dirty(self, n: int) -> None:
        txt = self.status.text()
        # 替换尾部 "未保存: X"
        if "未保存:" in txt:
            txt = txt.rsplit("未保存:", 1)[0] + f"未保存: {n}"
            if n > 0:
                self.status.setStyleSheet(
                    "color: #b04500; font-weight: bold; padding: 2px 6px;")
            else:
                self.status.setStyleSheet("color: #555; padding: 2px 6px;")
            self.status.setText(txt)
        self.dirtyChanged.emit(self.spec.name, n)

    # ---- 缩放 + 键盘 ----------------------------------------------------
    def _zoom(self, delta: int) -> None:
        f = self.view.font()
        f.setPointSize(max(7, f.pointSize() + delta))
        self.view.setFont(f)
        self.view.horizontalHeader().setFont(f)
        self.view.verticalHeader().setFont(f)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        k = e.key()
        idx = self.view.currentIndex()
        if not idx.isValid() and self.model.rowCount() > 0:
            self.view.setCurrentIndex(self.model.index(0, 0))
            return
        dr, dc = 0, 0
        if k in (Qt.Key.Key_Up,    Qt.Key.Key_W): dr = -1
        elif k in (Qt.Key.Key_Down,  Qt.Key.Key_S): dr = +1
        elif k in (Qt.Key.Key_Left,  Qt.Key.Key_A): dc = -1
        elif k in (Qt.Key.Key_Right, Qt.Key.Key_D): dc = +1
        else:
            super().keyPressEvent(e)
            return
        new_r = max(0, min(self.model.rowCount() - 1, idx.row() + dr))
        new_c = max(0, min(self.model.columnCount() - 1, idx.column() + dc))
        self.view.setCurrentIndex(self.model.index(new_r, new_c))

    def wheelEvent(self, e: QWheelEvent) -> None:
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._zoom(+1 if e.angleDelta().y() > 0 else -1)
            e.accept()
            return
        super().wheelEvent(e)
