# readme_for_ui

PyQt6 前端. 严格不直连 MySQL, 一律走 `app.backend.repos.generic`.

| 文件 | 作用 | 被谁调用 | 调用谁 |
|------|------|----------|--------|
| `__init__.py` | 包标记 | — | — |
| `login_dialog.py` | `LoginDialog` 登录窗 | `app.__main__` | `backend.security.credentials.login()`, `backend.audit.write()` |
| `main_window.py` | `MainWindow` 主窗口 (左导航 + 中央 stacked + 菜单 + 状态栏 + ER 图弹窗触发) | `app.__main__` | `backend.security.credentials.logout()`, `widgets.editable_table.TablePage`, `dialogs.er_diagram_dialog.ErDiagramDialog`, `backend.repos.specs.SPECS / NAV_ORDER` |

子目录: `widgets/` (可复用控件), `dialogs/` (独立弹窗).
