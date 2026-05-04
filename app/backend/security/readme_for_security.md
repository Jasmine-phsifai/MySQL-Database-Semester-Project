# readme_for_security

账户与登录态.

| 文件 | 作用 | 被谁调用 | 调用谁 |
|------|------|----------|--------|
| `__init__.py` | 包标记 | — | — |
| `credentials.py` | bcrypt 密码哈希 / HMAC 行签 / `login()` / `logout()` / `reset_password()` / `ensure_default_admin()` | `app.__main__`, `ui/login_dialog.py`, `tools/gen_fixtures.py` (创建 demo 账户) | `bcrypt`, `hmac`, `hashlib`, `secrets`, `backend.db`, `app.config` |

行签 = `HMAC-SHA256(salt, "user_id|username|role|password_hash|is_active")`.
绕过 ORM 直 UPDATE app_user 会导致行签不匹配, `login()` 拒绝认证.
