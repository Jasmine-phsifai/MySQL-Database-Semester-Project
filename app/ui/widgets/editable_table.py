"""配置驱动通用表格视图.

M1 范围:
  - 显示数据
  - 样例数据橙色横幅
  - 工具栏 [刷新] [新增] [删除] [保存] [丢弃] (按钮存在但保存/编辑后续 M2 启用)
  - 选中蓝色细框, 行高可调
  - 上下左右键移动, WASD 兼容
M2 范围:
  - 双击编辑、脏单元格高亮、QUndoStack、乐观锁
"""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt6.QtGui import QColor, QBrush, QKeyEvent
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableView,
    QHeaderView, QAbstractItemView, QMessageBox, QStyledItemDelegate,
    QSpinBox, QStyle,
)

from app.backend.repos import generic
from app.backend.repos.specs import SPECS, TableSpec
from app.backend.security.credentials import Identity


# ---- 模型 -----------------------------------------------------------------

class GenericModel(QAbstractTableModel):
    def __init__(self, spec: TableSpec, identity: Identity, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.identity = identity
        self.rows: list[dict] = []
        self.dirty: dict[tuple[int, int], Any] = {}  # (row, col) -> old value

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
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
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

    # 数据加载
    def reload(self, limit: int = 1000) -> None:
        self.beginResetModel()
        self.rows = generic.list_rows(self.spec.name, limit=limit)
        self.dirty.clear()
        self.endResetModel()


# ---- 选中蓝框委托 ---------------------------------------------------------

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


# ---- 顶层 widget ----------------------------------------------------------

class TablePage(QWidget):
    def __init__(self, table: str, identity: Identity, parent=None):
        super().__init__(parent)
        self.spec = SPECS[table]
        self.identity = identity
        self.model = GenericModel(self.spec, identity, parent=self)
        self.view = QTableView()
        self.view.setModel(self.model)
        self.view.setItemDelegate(_BlueFrameDelegate(self.view))
        self.view.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectItems)
        self.view.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers  # M1 只读, M2 改成 DoubleClicked
        )
        self.view.setAlternatingRowColors(True)
        self.view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.verticalHeader().setDefaultSectionSize(26)

        # 横幅
        self.banner = QLabel("")
        self.banner.setStyleSheet(
            "background-color: #ffe6b3; color: #8a4500; "
            "padding: 6px 10px; border: 1px solid #f0a030; border-radius: 4px;")
        self.banner.setVisible(False)

        # 工具栏
        self.btn_refresh = QPushButton("刷新")
        self.btn_add     = QPushButton("新增")
        self.btn_del     = QPushButton("删除")
        self.btn_save    = QPushButton("保存 (Ctrl+S)")
        self.btn_discard = QPushButton("丢弃改动")
        self.btn_zoom_in  = QPushButton("放大")
        self.btn_zoom_out = QPushButton("缩小")
        self.row_height_spin = QSpinBox()
        self.row_height_spin.setRange(18, 60)
        self.row_height_spin.setValue(26)
        self.row_height_spin.setSuffix(" px")

        for b in (self.btn_save, self.btn_discard, self.btn_add, self.btn_del):
            b.setEnabled(self.identity.role in ("admin", "editor"))

        self.btn_refresh.clicked.connect(self.reload)
        self.row_height_spin.valueChanged.connect(
            self.view.verticalHeader().setDefaultSectionSize)
        self.btn_zoom_in.clicked.connect(lambda: self._zoom(+1))
        self.btn_zoom_out.clicked.connect(lambda: self._zoom(-1))
        self.btn_add.clicked.connect(self._stub_add)
        self.btn_del.clicked.connect(self._stub_del)
        self.btn_save.clicked.connect(self._stub_save)
        self.btn_discard.clicked.connect(self._stub_discard)

        toolbar = QHBoxLayout()
        for w in (self.btn_refresh, self.btn_add, self.btn_del,
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

        self.reload()

    # ---- 数据 -----------------------------------------------------------
    def reload(self) -> None:
        try:
            self.model.reload()
            origin = generic.get_data_origin(self.spec.name)
            total = generic.count_rows(self.spec.name)
            shown = self.model.rowCount()
            if origin and origin["source"] == "sample":
                self.banner.setText(
                    f"⚠ 本表为样例数据 — 由 tools/gen_fixtures.py 自动生成 "
                    f"(共 {origin['sample_row_count']} 行); "
                    f"请通过『导入』替换为真实数据"
                )
                self.banner.setVisible(True)
            elif origin and origin["source"] == "imported":
                self.banner.setText(
                    f"✓ 本表数据已通过导入更新 — {origin.get('note') or ''}")
                self.banner.setStyleSheet(
                    "background-color: #d6ecd2; color: #225a1a; "
                    "padding: 6px 10px; border: 1px solid #6db35a; border-radius: 4px;")
                self.banner.setVisible(True)
            else:
                self.banner.setVisible(False)
            role_hint = "" if self.identity.role != "viewer" else "  [访客只读, 敏感字段已脱敏]"
            self.status.setText(f"显示 {shown} / 共 {total} 行  ·  当前角色: {self.identity.role}{role_hint}")
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "查询失败", str(e))

    # ---- 工具按钮 stub (M2 完整实现) -------------------------------------
    def _stub_add(self) -> None:
        QMessageBox.information(self, "新增", "M2 阶段实现 — 行内编辑 + 保存按钮。")

    def _stub_del(self) -> None:
        idx = self.view.currentIndex()
        if not idx.isValid():
            QMessageBox.information(self, "删除", "请先选中一行")
            return
        QMessageBox.information(self, "删除", "M2 阶段实现 — 选中行软删 + 撤销。")

    def _stub_save(self) -> None:
        QMessageBox.information(self, "保存", "当前为只读模式。M2 阶段开放编辑后, 此按钮提交所有黄色单元格。")

    def _stub_discard(self) -> None:
        self.reload()

    # ---- 缩放 -----------------------------------------------------------
    def _zoom(self, delta: int) -> None:
        f = self.view.font()
        f.setPointSize(max(7, f.pointSize() + delta))
        self.view.setFont(f)
        self.view.horizontalHeader().setFont(f)
        self.view.verticalHeader().setFont(f)

    # ---- 键盘导航 (上下左右 / WASD) ------------------------------------
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
