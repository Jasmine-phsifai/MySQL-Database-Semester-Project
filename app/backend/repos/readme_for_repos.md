# readme_for_repos

仓储层. 18 + 1 张表共用配置驱动方案, 不为每张表写独立类.

| 文件 | 作用 | 被谁调用 | 调用谁 |
|------|------|----------|--------|
| `__init__.py` | 包标记 | — | — |
| `specs.py` | 所有表的 `ColSpec` / `TableSpec` 配置 + `NAV_ORDER` 导航顺序 | `generic.py`, `ui/main_window.py`, `ui/widgets/editable_table.py` | — |
| `generic.py` | 通用 CRUD: `list_rows / get_row / insert_row / update_row / delete_row / batch_insert / lookup_options / get_data_origin / set_data_origin / run_sql` | `ui/widgets/editable_table.py`, `tools/gen_fixtures.py`, `tools/import_md_table.py` (M2) | `backend.db`, `backend.audit`, `specs` |

`generic.run_sql()` 给前端"自定义 SQL"窗使用, 对 viewer 强制只允许 SELECT.
