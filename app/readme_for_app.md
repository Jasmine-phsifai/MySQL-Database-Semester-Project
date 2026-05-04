# readme_for_app

应用代码包根目录.

| 文件 | 作用 | 被谁调用 | 调用谁 |
|------|------|----------|--------|
| `__init__.py` | 暴露 `__version__` | 包导入时 | — |
| `__main__.py` | 入口: 启动自检 → 登录 → 主窗口 | `start.bat` (`python -m app`) | `app.config`, `app.backend.db`, `app.backend.security.credentials`, `app.ui.login_dialog`, `app.ui.main_window` |
| `config.py` | 解析 `config.toml` 为冻结 dataclass | 几乎所有后端模块 | `tomllib` 标准库 |

子包: `backend/` (数据 + 安全 + 审计), `ui/` (PyQt6 视图), `domain/` (M2 用 dataclass), `resources/` (qss / icons).
