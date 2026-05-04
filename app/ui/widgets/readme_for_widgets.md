# readme_for_widgets

可复用控件.

| 文件 | 作用 | 被谁调用 | 调用谁 |
|------|------|----------|--------|
| `__init__.py` | 包标记 | — | — |
| `editable_table.py` | `GenericModel` (QAbstractTableModel) + `_BlueFrameDelegate` (选中蓝框) + `TablePage` (工具栏 + 横幅 + 表格 + 状态条 + 键盘导航) | `ui/main_window.py` (一表一页 ×19) | `backend.repos.generic`, `backend.repos.specs.SPECS`, `backend.security.credentials.Identity` |

M1 范围: 只读 + 横幅 + 缩放 + 键盘 (上下左右 / WASD).
M2 范围: 双击编辑 + 黄色脏单元格 + QUndoStack + 保存按钮提交事务.
