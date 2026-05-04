"""GUI 烟雾测试: offscreen 模式启动主窗口, 2 秒后自动退出。

验证全部 import / 构造 / 表加载没崩。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from app.backend.security.credentials import login, ensure_default_admin
from app.ui.main_window import MainWindow
from app.ui.dialogs.er_diagram_dialog import ErDiagramDialog


def main() -> int:
    app = QApplication(sys.argv)
    ensure_default_admin()
    ident = login("admin", "admin123", client_info="gui-smoke")
    assert ident, "admin login failed"

    win = MainWindow(ident)
    win.show()

    # 也实例化 ER 图弹窗 (不显示)
    er = ErDiagramDialog(win)

    # 1.5 秒后退出
    QTimer.singleShot(1500, app.quit)
    code = app.exec()
    print(f"GUI smoke OK, exit code = {code}, "
          f"main window visible = {win.isVisible()}, "
          f"pages = {win.stack.count()}, "
          f"er widgets ready = {er.label is not None}")
    return code


if __name__ == "__main__":
    sys.exit(main())
