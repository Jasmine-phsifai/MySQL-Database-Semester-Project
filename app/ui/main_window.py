"""主窗口: 左导航 (19 表 + 日志页 + 导入导出页) + 中央 stacked + 菜单 (SQL/ER)."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QMainWindow, QListWidget, QStackedWidget, QSplitter, QListWidgetItem,
    QStatusBar, QMessageBox,
)

from app.backend.repos.specs import SPECS, NAV_ORDER
from app.backend.security.credentials import Identity, logout
from app.ui.widgets.editable_table import TablePage
from app.ui.dialogs.er_diagram_dialog import ErDiagramDialog
from app.ui.dialogs.sql_console_dialog import SqlConsoleDialog
from app.ui.pages.log_query_page import LogQueryPage
from app.ui.pages.import_export_page import ImportExportPage


# 特殊功能页 (key=唯一槽 id, label=导航显示, factory=构造函数)
SPECIAL_PAGES = [
    ("__import_export__", "📥 导入导出"),
    ("__log_query__",     "🪵 操作日志查询"),
]


class MainWindow(QMainWindow):
    def __init__(self, identity: Identity) -> None:
        super().__init__()
        self.identity = identity
        self.setWindowTitle(
            f"学生成绩数据库  ·  用户: {identity.username} ({identity.role})")
        self.resize(1480, 900)

        self.nav = QListWidget()
        self.nav.setMinimumWidth(200)
        self.stack = QStackedWidget()
        self._pages: dict[str, object] = {}
        self._row_keys: list[str] = []

        # 业务表 19 张
        for name in NAV_ORDER:
            spec = SPECS[name]
            it = QListWidgetItem(spec.label)
            it.setData(Qt.ItemDataRole.UserRole, name)
            self.nav.addItem(it)
            page = TablePage(name, identity)
            self._pages[name] = page
            self.stack.addWidget(page)
            self._row_keys.append(name)

        # 分隔
        sep = QListWidgetItem("──── 功能 ────")
        sep.setFlags(Qt.ItemFlag.NoItemFlags)
        self.nav.addItem(sep)
        self._row_keys.append("__sep__")
        self.stack.addWidget(TablePage("data_origin", identity))  # placeholder for sep index
        # 上面 placeholder 的 stack 不会被使用因为 sep row 不可选

        # 特殊页
        for key, label in SPECIAL_PAGES:
            it = QListWidgetItem(label)
            it.setData(Qt.ItemDataRole.UserRole, key)
            self.nav.addItem(it)
            if key == "__log_query__":
                p = LogQueryPage(identity)
            elif key == "__import_export__":
                p = ImportExportPage(identity)
            self._pages[key] = p
            self.stack.addWidget(p)
            self._row_keys.append(key)

        # 先 setCurrentRow (无 signal 时), 再初始化 _prev_row, 再 connect
        default_row = NAV_ORDER.index("student")
        self._prev_row = default_row
        self.nav.blockSignals(True)
        self.nav.setCurrentRow(default_row)
        self.nav.blockSignals(False)
        self.nav.currentRowChanged.connect(self._on_nav_changed)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.nav)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([220, 1260])
        self.setCentralWidget(splitter)

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

        tool_menu = mb.addMenu("工具(&T)")
        act_sql = QAction("自定义 SQL 控制台...", self)
        act_sql.setShortcut(QKeySequence("Ctrl+L"))
        act_sql.triggered.connect(self._open_sql)
        tool_menu.addAction(act_sql)

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
        self._sql_dialog: SqlConsoleDialog | None = None

    # ---- 切页 dirty 拦截 -----------------------------------------------
    def _on_nav_changed(self, row: int) -> None:
        if row < 0 or row >= len(self._row_keys):
            return
        key = self._row_keys[row]
        if key == "__sep__":
            self.nav.setCurrentRow(self._prev_row)
            return
        # 检查上一页 dirty
        prev_key = self._row_keys[self._prev_row] if 0 <= self._prev_row < len(self._row_keys) else None
        prev = self._pages.get(prev_key) if prev_key else None
        if isinstance(prev, TablePage) and prev.has_dirty():
            ans = QMessageBox.question(
                self, "未保存改动",
                f"「{prev.spec.label}」还有 {len(prev.model.dirty)} 处未保存修改.\n"
                f"切换页面将丢弃这些改动 (建议先保存 Ctrl+S 或丢弃).",
                QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel
                | QMessageBox.StandardButton.Save)
            if ans == QMessageBox.StandardButton.Save:
                if not prev.save():
                    self.nav.blockSignals(True)
                    self.nav.setCurrentRow(self._prev_row)
                    self.nav.blockSignals(False)
                    return
            elif ans == QMessageBox.StandardButton.Cancel:
                self.nav.blockSignals(True)
                self.nav.setCurrentRow(self._prev_row)
                self.nav.blockSignals(False)
                return
            else:
                prev.reload()
        # 实际切换
        self.stack.setCurrentIndex(row)
        self._prev_row = row

    # ---- 动作 -----------------------------------------------------------
    def _open_er(self) -> None:
        if self._er_dialog is None:
            self._er_dialog = ErDiagramDialog(self)
        self._er_dialog.show()
        self._er_dialog.raise_()
        self._er_dialog.activateWindow()

    def _open_sql(self) -> None:
        if self._sql_dialog is None:
            self._sql_dialog = SqlConsoleDialog(self.identity, self)
        self._sql_dialog.show()
        self._sql_dialog.raise_()
        self._sql_dialog.activateWindow()

    def _refresh_current(self) -> None:
        page = self.stack.currentWidget()
        if isinstance(page, TablePage):
            page.reload_with_check()
        elif hasattr(page, "do_query"):
            page.do_query()

    def _logout(self) -> None:
        if not self._confirm_close_with_dirty():
            return
        logout(self.identity.token)
        self.close()

    def _about(self) -> None:
        QMessageBox.about(
            self, "关于",
            "学生成绩数据库系统  v0.2 (M2)\n\n"
            "MySQL 8 + PyQt6 + PyMySQL + bcrypt + HMAC\n"
            "满足 3NF, 19 张表, 三角色权限, JSON 操作日志.\n"
            "支持手动保存编辑 / 撤销 / CSV-XLSX 导入导出 / 自定义 SQL.\n\n"
            "详见 README.md / DESIGN.md."
        )

    # ---- 关闭拦截 -------------------------------------------------------
    def _confirm_close_with_dirty(self) -> bool:
        dirty_pages = [(k, p) for k, p in self._pages.items()
                       if isinstance(p, TablePage) and p.has_dirty()]
        if not dirty_pages:
            return True
        names = ", ".join(p.spec.label for _, p in dirty_pages)
        ans = QMessageBox.question(
            self, "退出前确认",
            f"以下页面有未保存改动:\n  {names}\n\n直接退出会丢弃!",
            QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel)
        return ans == QMessageBox.StandardButton.Discard

    def closeEvent(self, e) -> None:
        if not self._confirm_close_with_dirty():
            e.ignore()
            return
        try:
            logout(self.identity.token)
        except Exception:
            pass
        super().closeEvent(e)
