# readme_for_backend

后端: 数据访问 + 业务规则 + 安全 + 审计. **不依赖 PyQt**, 可单独跑测试.

| 文件 | 作用 | 被谁调用 | 调用谁 |
|------|------|----------|--------|
| `__init__.py` | 包标记 | — | — |
| `db.py` | `DBPool` 连接池 + `tx()` / `read()` 上下文 | `repos/generic.py`, `security/credentials.py`, `audit.py`, `tools/gen_fixtures.py` | `pymysql`, `app.config` |
| `audit.py` | JSON 操作日志切面 (写 `logs/*.jsonl` + `audit_log_index` 索引行) | `repos/generic.py`, `ui/login_dialog.py` | `db.py`, `app.config` |

子目录: `security/` (bcrypt + HMAC), `repos/` (仓储 + TableSpec).
