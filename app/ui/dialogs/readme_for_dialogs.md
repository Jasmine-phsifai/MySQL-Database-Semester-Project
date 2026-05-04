# readme_for_dialogs

独立弹窗 (非主窗口 stacked 槽位的功能).

| 文件 | 作用 | 被谁调用 | 调用谁 |
|------|------|----------|--------|
| `__init__.py` | 包标记 | — | — |
| `er_diagram_dialog.py` | `ErDiagramDialog` 非模态 ER 图弹窗 (缩放 / 适应 / 另存) | `ui/main_window.py` (Ctrl+E / 视图菜单) | `app.config.load_config()`, 文件系统读 `docs/er/*.png|svg` |

加载顺序: `schema_polished.png` → `schema.svg` → `schema.png` → 占位提示.
