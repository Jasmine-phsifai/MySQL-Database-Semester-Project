"""新增 / 编辑单行的弹窗 (ColSpec 驱动控件渲染)."""
from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QDateEdit, QHBoxLayout, QPushButton, QMessageBox, QVBoxLayout,
)

from app.backend.repos import generic
from app.backend.repos.specs import TableSpec, ColSpec
from app.backend.security.credentials import Identity


class RowEditorDialog(QDialog):
    def __init__(self, spec: TableSpec, identity: Identity,
                 initial: dict | None = None, parent=None) -> None:
        super().__init__(parent)
        self.spec = spec
        self.identity = identity
        self.initial = initial or {}
        self.values: dict[str, Any] = {}
        self.setWindowTitle(f"新增 — {spec.label}" if not initial
                              else f"编辑 — {spec.label}")
        self.setMinimumWidth(480)

        self._editors: dict[str, Any] = {}
        form = QFormLayout()
        for col in spec.cols:
            if not col.editable:
                continue
            if col.name in ("created_at", "updated_at"):
                continue
            w = self._make_editor(col)
            self._editors[col.name] = w
            label = col.label + (" *" if col.required else "")
            form.addRow(label, w)

        ok = QPushButton("确定")
        ok.setDefault(True)
        cancel = QPushButton("取消")
        ok.clicked.connect(self._accept)
        cancel.clicked.connect(self.reject)
        bl = QHBoxLayout()
        bl.addStretch(1); bl.addWidget(cancel); bl.addWidget(ok)

        v = QVBoxLayout(self)
        v.addLayout(form)
        v.addLayout(bl)

    def _make_editor(self, col: ColSpec):
        v = self.initial.get(col.name)
        if col.enum:
            cb = QComboBox()
            if not col.required:
                cb.addItem("", None)
            for o in col.enum:
                cb.addItem(o, o)
            if v is not None:
                i = cb.findText(str(v))
                if i >= 0:
                    cb.setCurrentIndex(i)
            return cb
        if col.fk:
            cb = QComboBox()
            cb.setEditable(False)
            if not col.required:
                cb.addItem("(空)", None)
            try:
                opts = generic.lookup_options(*col.fk, limit=2000)
                for val, label in opts:
                    cb.addItem(f"{val} — {label}", val)
            except Exception:
                pass
            if v is not None:
                for i in range(cb.count()):
                    if cb.itemData(i) == v:
                        cb.setCurrentIndex(i); break
            return cb
        if col.name in ("birth_date", "start_date", "end_date", "change_date"):
            de = QDateEdit()
            de.setCalendarPopup(True)
            de.setDisplayFormat("yyyy-MM-dd")
            if v:
                try:
                    y, m, d = str(v).split("-")[:3]
                    de.setDate(QDate(int(y), int(m), int(d[:2])))
                except Exception:
                    de.setDate(QDate.currentDate())
            else:
                de.setDate(QDate.currentDate())
            return de
        if col.name in ("credits",):
            sp = QDoubleSpinBox()
            sp.setRange(0.0, 99.9)
            sp.setSingleStep(0.5)
            sp.setValue(float(v or 0))
            return sp
        if col.name in ("class_hours", "capacity", "grade_year",
                          "rank_in_offering", "sample_row_count"):
            sp = QSpinBox()
            sp.setRange(0, 1_000_000)
            sp.setValue(int(v) if v not in (None, "") else 0)
            return sp
        le = QLineEdit()
        if v is not None:
            le.setText(str(v))
        return le

    def _accept(self) -> None:
        out: dict[str, Any] = {}
        for name, w in self._editors.items():
            col = self.spec.by_name(name)
            if col is None:
                continue
            if isinstance(w, QComboBox):
                v = w.currentData() if w.itemData(w.currentIndex()) is not None \
                    else (w.currentText() or None)
                if v == "":
                    v = None
            elif isinstance(w, QDateEdit):
                v = w.date().toString("yyyy-MM-dd")
            elif isinstance(w, (QSpinBox, QDoubleSpinBox)):
                v = w.value()
            else:
                v = w.text().strip() or None
            if col.required and (v is None or v == ""):
                QMessageBox.warning(self, "校验失败", f"{col.label} 为必填")
                return
            out[name] = v
        self.values = out
        self.accept()
