"""自定义 SQL 控制台.

权限:
  admin   全部 SQL
  editor  禁 DROP / TRUNCATE / GRANT / REVOKE
  viewer  仅 SELECT
后端 generic.run_sql 内做最终校验, 前端只是友好提示.
"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView, QSplitter,
    QWidget,
)

from app.backend.repos import generic
from app.backend.security.credentials import Identity


_ROLE_HINT = {
    "admin":  "管理员: 全部 SQL 可执行 (危险操作请谨慎)",
    "editor": "录入员: 禁止 DROP / TRUNCATE / GRANT / REVOKE",
    "viewer": "访客: 仅允许 SELECT (其他将被后端拒绝)",
}


class SqlConsoleDialog(QDialog):
    def __init__(self, identity: Identity, parent=None) -> None:
        super().__init__(parent)
        self.identity = identity
        self.setWindowTitle(f"自定义 SQL — {identity.username} ({identity.role})")
        self.resize(900, 640)
        self.setModal(False)

        self.editor = QPlainTextEdit()
        f = QFont("Consolas")
        f.setPointSize(11)
        self.editor.setFont(f)
        self.editor.setPlaceholderText(
            "SELECT s.student_no, s.name, m.major_name\n"
            "  FROM student s JOIN major m USING(major_id)\n"
            " LIMIT 50;\n\n"
            "F5 / Ctrl+Enter 执行")

        self.role_lbl = QLabel(_ROLE_HINT.get(identity.role, ""))
        self.role_lbl.setStyleSheet("color: #555; padding: 4px;")

        self.btn_run = QPushButton("执行 (F5)")
        self.btn_run.setStyleSheet(
            "background-color: #2e8b57; color: white; font-weight: bold;")
        self.btn_clear = QPushButton("清空")
        self.btn_run.clicked.connect(self._run)
        self.btn_clear.clicked.connect(self.editor.clear)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.btn_run)
        toolbar.addWidget(self.btn_clear)
        toolbar.addStretch(1)
        toolbar.addWidget(self.role_lbl)

        # 结果表
        self.result = QTableWidget()
        self.result.setAlternatingRowColors(True)
        self.result.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive)
        self.result.horizontalHeader().setStretchLastSection(True)
        self.summary = QLabel("")
        self.summary.setStyleSheet("color: #444; padding: 4px;")

        editor_box = QWidget()
        eb = QVBoxLayout(editor_box)
        eb.setContentsMargins(0, 0, 0, 0)
        eb.addLayout(toolbar)
        eb.addWidget(self.editor, 1)

        result_box = QWidget()
        rb = QVBoxLayout(result_box)
        rb.setContentsMargins(0, 0, 0, 0)
        rb.addWidget(self.result, 1)
        rb.addWidget(self.summary)

        sp = QSplitter(Qt.Orientation.Vertical)
        sp.addWidget(editor_box)
        sp.addWidget(result_box)
        sp.setSizes([220, 420])

        layout = QVBoxLayout(self)
        layout.addWidget(sp)

        QShortcut(QKeySequence("F5"), self, activated=self._run)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._run)
        QShortcut(QKeySequence("Ctrl+Enter"),  self, activated=self._run)

    def _run(self) -> None:
        sql = self.editor.toPlainText().strip()
        if not sql:
            return
        try:
            r = generic.run_sql(sql, actor=self.identity.username,
                                 role=self.identity.role)
        except PermissionError as e:
            QMessageBox.warning(self, "权限拒绝", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "执行失败", str(e))
            self.summary.setText(f"错误: {e}")
            return

        cols = r["columns"]
        rows = r["rows"]
        self.result.clear()
        self.result.setColumnCount(len(cols))
        self.result.setHorizontalHeaderLabels(cols)
        self.result.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, c in enumerate(cols):
                v = row.get(c)
                self.result.setItem(i, j,
                    QTableWidgetItem("" if v is None else str(v)))
        self.summary.setText(
            f"返回 {len(rows)} 行 / {len(cols)} 列  ·  影响 {r['affected']} 行")
