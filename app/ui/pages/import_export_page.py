"""CSV / XLSX 导入导出向导.

导入: 选文件 → 自动字段映射 (列名相同自动) → 预检 (CHECK / FK) → 事务批量提交.
导出: 选表 + 格式 → 保存到磁盘.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QFileDialog, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QPlainTextEdit,
)

from app.backend.repos import generic
from app.backend.repos.specs import SPECS, NAV_ORDER
from app.backend.security.credentials import Identity


def _read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path, dtype=str)
    return pd.read_csv(path, dtype=str, encoding_errors="replace")


class ImportExportPage(QWidget):
    def __init__(self, identity: Identity, parent=None) -> None:
        super().__init__(parent)
        self.identity = identity

        self.table_combo = QComboBox()
        for t in NAV_ORDER:
            self.table_combo.addItem(f"{SPECS[t].label}  ({t})", t)

        self.btn_import = QPushButton("导入 CSV/XLSX...")
        self.btn_export_csv  = QPushButton("导出当前表为 CSV")
        self.btn_export_xlsx = QPushButton("导出当前表为 XLSX")
        if identity.role == "viewer":
            self.btn_import.setEnabled(False)
            self.btn_import.setToolTip("访客无导入权限")

        self.btn_import.clicked.connect(self._do_import)
        self.btn_export_csv.clicked.connect(lambda: self._do_export("csv"))
        self.btn_export_xlsx.clicked.connect(lambda: self._do_export("xlsx"))

        bar = QHBoxLayout()
        bar.addWidget(QLabel("目标表"))
        bar.addWidget(self.table_combo)
        bar.addWidget(self.btn_import)
        bar.addWidget(self.btn_export_csv)
        bar.addWidget(self.btn_export_xlsx)
        bar.addStretch(1)

        # 预检表
        self.preview = QTableWidget()
        self.preview.setAlternatingRowColors(True)
        self.preview.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(160)
        self.log.setPlaceholderText("操作日志输出区...")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addLayout(bar)
        layout.addWidget(QLabel("预览 (前 200 行):"))
        layout.addWidget(self.preview, 1)
        layout.addWidget(QLabel("操作日志:"))
        layout.addWidget(self.log)

    # ------------------------------------------------------------------
    def _current_table(self) -> str:
        return self.table_combo.currentData()

    def _do_import(self) -> None:
        table = self._current_table()
        spec = SPECS[table]
        fn, _ = QFileDialog.getOpenFileName(
            self, "选择要导入的文件", "",
            "数据 (*.csv *.xlsx *.xls);;CSV (*.csv);;Excel (*.xlsx *.xls)")
        if not fn:
            return
        path = Path(fn)
        try:
            df = _read_table(path)
        except Exception as e:
            QMessageBox.critical(self, "读取失败", str(e))
            return

        # 字段映射 (按列名直接匹配; 不匹配的列丢弃)
        valid_cols = {c.name for c in spec.cols}
        keep_cols = [c for c in df.columns if c in valid_cols]
        skipped = [c for c in df.columns if c not in valid_cols]
        df = df[keep_cols].copy()
        # NaN → None
        df = df.where(pd.notna(df), None)

        # 预检显示
        self._fill_preview(df, head=200)
        self.log.appendPlainText(
            f"\n[load] {path.name}  原 {len(df)} 行 / {len(df.columns)} 列")
        if skipped:
            self.log.appendPlainText(
                f"[map] 丢弃未识别列: {', '.join(skipped)}")
        self.log.appendPlainText(
            f"[map] 灌入列: {', '.join(keep_cols)}")

        # 必填校验
        missing_required = [c.name for c in spec.cols
                            if c.required and c.name not in keep_cols]
        if missing_required:
            QMessageBox.warning(
                self, "字段缺失",
                f"目标表必填列未在源文件中: {', '.join(missing_required)}")
            return

        ans = QMessageBox.question(
            self, "确认导入",
            f"将向 {spec.label} ({table}) 插入 {len(df)} 行.\n继续?")
        if ans != QMessageBox.StandardButton.Yes:
            return

        rows = df.to_dict(orient="records")
        try:
            n = generic.batch_insert(table, rows,
                                      actor=self.identity.username,
                                      role=self.identity.role)
            generic.set_data_origin(
                table, "imported", generic.count_rows(table),
                note=f"imported from {path.name}")
            self.log.appendPlainText(f"[ok]  插入 {n} 行")
            QMessageBox.information(self, "完成", f"成功导入 {n} 行")
        except Exception as e:
            self.log.appendPlainText(f"[fail] {e}")
            QMessageBox.critical(self, "导入失败 — 全部回滚", str(e))

    def _do_export(self, fmt: str) -> None:
        table = self._current_table()
        spec = SPECS[table]
        ext = {"csv": "csv", "xlsx": "xlsx"}[fmt]
        fn, _ = QFileDialog.getSaveFileName(
            self, "导出到...", f"{table}.{ext}",
            f"{ext.upper()} (*.{ext})")
        if not fn:
            return
        try:
            rows = generic.list_rows(table, limit=1_000_000)
            df = pd.DataFrame(rows, columns=[c.name for c in spec.cols])
            if fmt == "csv":
                df.to_csv(fn, index=False, encoding="utf-8-sig")
            else:
                df.to_excel(fn, index=False)
            self.log.appendPlainText(
                f"[export] {table}: {len(df)} 行 → {fn}")
            QMessageBox.information(self, "完成",
                f"已导出 {len(df)} 行 → {fn}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))

    def _fill_preview(self, df: "pd.DataFrame", head: int = 200) -> None:
        self.preview.clear()
        cols = list(df.columns)
        self.preview.setColumnCount(len(cols))
        self.preview.setHorizontalHeaderLabels(cols)
        n = min(head, len(df))
        self.preview.setRowCount(n)
        for i in range(n):
            for j, c in enumerate(cols):
                v = df.iat[i, j]
                self.preview.setItem(i, j,
                    QTableWidgetItem("" if v is None else str(v)))
