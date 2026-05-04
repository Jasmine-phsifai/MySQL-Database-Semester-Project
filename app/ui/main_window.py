"""主窗口: 左侧导航 + 中央 stacked 表格 + 菜单栏 (ER 图 / 关于 / 退出)。"""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QMainWindow, QListWidget, QStackedWidget, QSplitter, QListWidgetItem,
    QStatusBar, QWidget, QVBoxLayout, QLabel,
)

from app.backend.repos.specs import SPECS, NAV_ORDER
from app.backend.security.credentials import Identity, logout
from app.ui.widgets.editable_table import TablePage
from app.ui.dialogs.er_diagram_dialog import ErDiagramDialog


class MainWindow(QMainWindow):
    def __init__(self, identity: Identity) -> None:
        super().__init__()
        self.identity = identity
        self.setWindowTitle(
            f"学生成绩数据库  ·  用户: {identity.username} ({identity.role})")
        self.resize(1400, 880)

        self.nav = QListWidget()
        self.nav.setMinimumWidth(180)
        self.stack = QStackedWidget()
        self._pages: dict[str, TablePage] = {}

        for name in NAV_ORDER:
            spec = SPECS[name]
            it = QListWidgetItem(spec.label)
            it.setData(Qt.ItemDataRole.UserRole, name)
            self.nav.addItem(it)
            page = TablePage(name, identity)
            self._pages[name] = page
            self.stack.addWidget(page)

        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(NAV_ORDER.index("student"))

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.nav)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([200, 1200])
        self.setCentralWidget(splitter)

        # 状态栏
        sb = QStatusBar()
        sb.showMessage(f"已登录: {identity.username}  ·  角色: {identity.role}")
        self.setStatusBar(sb)

        self._build_menus()

    # ---- 菜单 -----------------------------------------------------------
    def _build_menus(self) -> None:
        mb = self.menuBar()
        view_menu = mb.addMenu("视图(&V)")
        act_er = QAction("ER 图...", self)
        act_er.setShortcut(QKeySequence("Ctrl+E"))
        act_er.triggered.connect(self._open_er)
        view_menu.addAction(act_er)

        act_refresh = QAction("刷新当前表(&R)", self)
        act_refresh.setShortcut(QKeySequence("F5"))
        act_refresh.triggered.connect(self._refresh_current)
        view_menu.addAction(act_refresh)

        file_menu = mb.addMenu("文件(&F)")
        act_logout = QAction("注销", self)
        act_logout.triggered.connect(self._logout)
        file_menu.addAction(act_logout)
        act_quit = QAction("退出", self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        help_menu = mb.addMenu("帮助(&H)")
        act_about = QAction("关于", self)
        act_about.triggered.connect(self._about)
        help_menu.addAction(act_about)

        self._er_dialog: ErDiagramDialog | None = None

    # ---- 动作 -----------------------------------------------------------
    def _open_er(self) -> None:
        if self._er_dialog is None:
            self._er_dialog = ErDiagramDialog(self)
        self._er_dialog.show()
        self._er_dialog.raise_()
        self._er_dialog.activateWindow()

    def _refresh_current(self) -> None:
        page = self.stack.currentWidget()
        if isinstance(page, TablePage):
            page.reload()

    def _logout(self) -> None:
        logout(self.identity.token)
        self.close()

    def _about(self) -> None:
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.about(
            self, "关于",
            "学生成绩数据库系统  v0.1\n\n"
            "MySQL 8 + PyQt6 + PyMySQL\n"
            "满足 3NF; 含完整性约束、JSON 操作日志、bcrypt+HMAC 凭据。\n"
            "详见 README.md / DESIGN.md。"
        )

    def closeEvent(self, e) -> None:
        try:
            logout(self.identity.token)
        except Exception:
            pass
        super().closeEvent(e)
