"""登录窗。"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QPushButton, QHBoxLayout,
    QVBoxLayout, QLabel, QMessageBox,
)

from app.backend.security.credentials import login, Identity
from app.backend import audit


class LoginDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("登录 — 学生成绩数据库")
        self.setMinimumWidth(360)
        self.identity: Identity | None = None

        title = QLabel("学生成绩数据库系统")
        title.setStyleSheet("font-size: 18px; font-weight: bold; padding: 12px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("admin / editor / viewer")
        self.pwd_edit = QLineEdit()
        self.pwd_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd_edit.setPlaceholderText("默认密码: admin / demo")

        form = QFormLayout()
        form.addRow("用户名", self.user_edit)
        form.addRow("密码", self.pwd_edit)

        ok = QPushButton("登录")
        ok.setDefault(True)
        cancel = QPushButton("取消")
        ok.clicked.connect(self._on_login)
        cancel.clicked.connect(self.reject)
        btns = QHBoxLayout()
        btns.addStretch(1)
        btns.addWidget(cancel)
        btns.addWidget(ok)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addLayout(form)
        layout.addLayout(btns)

        self.user_edit.setFocus()

    def _on_login(self) -> None:
        u = self.user_edit.text().strip()
        p = self.pwd_edit.text()
        if not u or not p:
            QMessageBox.warning(self, "提示", "请输入用户名与密码")
            return
        ident = login(u, p, client_info="desktop")
        if ident is None:
            QMessageBox.critical(self, "登录失败",
                                  "用户名或密码错误, 或账户被禁用")
            audit.write(u, "?", "(login)", "LOGIN", affected_rows=0,
                        extra={"result": "fail"})
            return
        self.identity = ident
        audit.write(ident.username, ident.role, "(login)", "LOGIN",
                    affected_rows=1, extra={"result": "ok"})
        self.accept()
