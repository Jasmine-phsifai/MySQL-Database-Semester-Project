"""桌面应用入口 — `python -m app` 调起。"""
from __future__ import annotations

import sys
import traceback

from PyQt6.QtWidgets import QApplication, QMessageBox

from app.config import load_config
from app.backend.db import get_pool
from app.backend.security.credentials import ensure_default_admin
from app.ui.main_window import MainWindow
from app.ui.login_dialog import LoginDialog


def _preflight() -> str | None:
    """启动前自检; 返回错误文本 (None 表示 OK)。"""
    try:
        cfg = load_config()
    except SystemExit as e:
        return str(e)
    try:
        with get_pool().read() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    except Exception as e:  # noqa: BLE001
        return (f"无法连接 MySQL ({cfg.mysql.host}:{cfg.mysql.port}).\n\n"
                f"请确认:\n"
                f"  1. MySQL 服务正在运行\n"
                f"  2. config.toml 中 user/password 正确\n"
                f"  3. 数据库 {cfg.mysql.database} 已创建\n\n"
                f"原始错误:\n{e}")
    try:
        ensure_default_admin()
    except Exception as e:  # noqa: BLE001
        return f"初始化 admin 账户失败:\n{e}"
    return None


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("学生成绩数据库")

    # 主题 (容错: qdarktheme 缺失或 API 改动不致死)
    try:
        import qdarktheme
        qdarktheme.setup_theme(load_config().ui.theme)
    except Exception:
        pass

    err = _preflight()
    if err:
        QMessageBox.critical(None, "启动失败", err)
        return 1

    login = LoginDialog()
    if login.exec() != login.DialogCode.Accepted or not login.identity:
        return 0

    win = MainWindow(login.identity)
    win.show()
    return app.exec()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        QMessageBox.critical(None, "未捕获错误", traceback.format_exc())
        sys.exit(1)
