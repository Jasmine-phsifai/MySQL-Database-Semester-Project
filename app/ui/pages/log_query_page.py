"""操作日志查询页. 按 actor / table / action / 时间窗筛选."""
from __future__ import annotations

from datetime import datetime, timedelta

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QSpinBox,
    QMessageBox, QDateTimeEdit,
)
from PyQt6.QtCore import QDateTime

from app.backend import audit
from app.backend.security.credentials import Identity


class LogQueryPage(QWidget):
    def __init__(self, identity: Identity, parent=None) -> None:
        super().__init__(parent)
        self.identity = identity

        self.actor_edit = QLineEdit()
        self.actor_edit.setPlaceholderText("操作者用户名 (留空=全部)")

        self.table_combo = QComboBox()
        self.table_combo.addItem("(全部表)", "")
        for t in ("department", "major", "degree_requirement", "student",
                  "teacher", "course", "course_alias", "department_change_note",
                  "semester", "course_offering", "offering_teacher",
                  "enrollment", "enrollment_action", "grade_band", "grade",
                  "app_user", "auth_session", "(login)", "(custom-sql)",
                  "(import-md)"):
            self.table_combo.addItem(t, t)

        self.action_combo = QComboBox()
        self.action_combo.addItem("(全部动作)", "")
        for a in ("INSERT", "UPDATE", "DELETE", "LOGIN", "LOGOUT",
                   "SQL", "EXPORT", "IMPORT", "BACKUP", "RESTORE"):
            self.action_combo.addItem(a, a)

        self.since_edit = QDateTimeEdit()
        self.since_edit.setCalendarPopup(True)
        self.since_edit.setDateTime(
            QDateTime.currentDateTime().addDays(-7))
        self.since_edit.setDisplayFormat("yyyy-MM-dd HH:mm")

        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(10, 5000)
        self.limit_spin.setValue(200)

        self.btn = QPushButton("查询")
        self.btn.clicked.connect(self.do_query)
        self.btn.setStyleSheet(
            "background-color: #2e8b57; color: white; font-weight: bold;")

        bar = QHBoxLayout()
        bar.addWidget(QLabel("操作者")); bar.addWidget(self.actor_edit)
        bar.addWidget(QLabel("表"));    bar.addWidget(self.table_combo)
        bar.addWidget(QLabel("动作"));  bar.addWidget(self.action_combo)
        bar.addWidget(QLabel("起始"));  bar.addWidget(self.since_edit)
        bar.addWidget(QLabel("最多"));  bar.addWidget(self.limit_spin)
        bar.addWidget(self.btn)
        bar.addStretch(1)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.summary = QLabel("点击「查询」加载日志")
        self.summary.setStyleSheet("color: #555; padding: 4px;")

        # 权限提示
        if self.identity.role != "admin":
            self.actor_edit.setText(self.identity.username)
            self.actor_edit.setReadOnly(True)
            self.actor_edit.setToolTip("非管理员仅能查看自己的日志")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addLayout(bar)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.summary)

    def do_query(self) -> None:
        try:
            rows = audit.query(
                actor=self.actor_edit.text().strip() or None,
                table_name=self.table_combo.currentData() or None,
                action=self.action_combo.currentData() or None,
                since=self.since_edit.dateTime().toPyDateTime(),
                limit=self.limit_spin.value(),
            )
        except Exception as e:
            QMessageBox.critical(self, "查询失败", str(e))
            return
        cols = ["log_id", "ts", "actor", "role", "table_name", "action",
                "target_pk", "affected_rows", "log_file", "file_offset"]
        self.table.clear()
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, c in enumerate(cols):
                v = r.get(c)
                self.table.setItem(i, j,
                    QTableWidgetItem("" if v is None else str(v)))
        self.summary.setText(
            f"返回 {len(rows)} 行  ·  按 ts 倒序  ·  "
            f"详细 JSON 见 logs/<日期>.jsonl")
