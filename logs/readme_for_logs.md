# readme_for_logs

JSON 操作日志.

| 文件 | 作用 | 被谁写 | 被谁读 |
|------|------|--------|--------|
| `YYYY-MM-DD.jsonl` | 当日全部写操作 / 登录 / 自定义 SQL 等审计行 (一行一 JSON) | `app.backend.audit.write()` | 前端日志查询 (M2) + `app.backend.audit.query()` |
| `autosave/<table>.json` | 前端崩溃保护用 dirty 缓存 (M2) | `app.ui.widgets.editable_table` 周期 dump | 启动时 `MainWindow` 检测并提示恢复 |

权限: 录入员 / 访客**不能删除** jsonl 文件 — 后端不暴露删除 API; 文件系统级请用操作系统配置只追加.
