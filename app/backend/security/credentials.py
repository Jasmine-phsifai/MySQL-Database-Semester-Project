"""账户与登录态。

- 密码使用 bcrypt(cost=12) 存储
- 每行 app_user 带 HMAC-SHA256 行签 (defense-in-depth, 防止直接 UPDATE 注入)
- 登录返回 token, sha256(token) 落 auth_session
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

import bcrypt

from app.config import load_config
from app.backend.db import get_pool


_BCRYPT_COST = 12


@dataclass(frozen=True)
class Identity:
    user_id: int
    username: str
    role: str          # admin | editor | viewer
    guest_type: str | None
    token: str         # 明文 token, 仅在登录响应中返回, 不入库


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(_BCRYPT_COST)).decode()


def verify_password(plain: str, stored: str) -> bool:
    if not stored or stored.startswith("$2b$12$BOOTSTRAP"):
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), stored.encode("utf-8"))
    except ValueError:
        return False


def _row_signature(user_id: int, username: str, role: str,
                   password_hash: str, is_active: int) -> str:
    salt = load_config().security.hmac_salt.encode("utf-8")
    msg = f"{user_id}|{username}|{role}|{password_hash}|{is_active}".encode()
    return hmac.new(salt, msg, hashlib.sha256).hexdigest()


def _verify_row_signature(row: dict) -> bool:
    expected = _row_signature(
        row["user_id"], row["username"], row["role"],
        row["password_hash"], int(row["is_active"]),
    )
    return hmac.compare_digest(expected, row["signature"])


def ensure_default_admin() -> None:
    """启动时调用: 若 admin 行还是 BOOTSTRAP 占位, 用 config 中默认密码重置。"""
    cfg = load_config().security
    pool = get_pool()
    with pool.tx() as cur:
        cur.execute("SELECT * FROM app_user WHERE username=%s", (cfg.default_admin_username,))
        row = cur.fetchone()
        if row and not row["password_hash"].startswith("$2b$12$BOOTSTRAP"):
            return
        ph = hash_password(cfg.default_admin_password)
        if row:
            sig = _row_signature(row["user_id"], row["username"], row["role"], ph, 1)
            cur.execute(
                "UPDATE app_user SET password_hash=%s, signature=%s, is_active=1 "
                "WHERE user_id=%s",
                (ph, sig, row["user_id"]),
            )
        else:
            cur.execute(
                "INSERT INTO app_user(username,password_hash,role,is_active,signature) "
                "VALUES(%s,%s,'admin',1,'TEMP')",
                (cfg.default_admin_username, ph),
            )
            cur.execute("SELECT user_id FROM app_user WHERE username=%s",
                        (cfg.default_admin_username,))
            uid = cur.fetchone()["user_id"]
            sig = _row_signature(uid, cfg.default_admin_username, "admin", ph, 1)
            cur.execute("UPDATE app_user SET signature=%s WHERE user_id=%s", (sig, uid))


def login(username: str, password: str, client_info: str = "") -> Identity | None:
    pool = get_pool()
    with pool.tx() as cur:
        cur.execute("SELECT * FROM app_user WHERE username=%s", (username,))
        row = cur.fetchone()
        if not row or not row["is_active"]:
            return None
        if not _verify_row_signature(row):
            # 行签不一致 — 数据被绕过 ORM 直改, 拒绝登录
            return None
        if not verify_password(password, row["password_hash"]):
            return None

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        ttl = load_config().security.session_ttl_hours
        cur.execute(
            "INSERT INTO auth_session(user_id, token_hash, expires_at, client_info) "
            "VALUES (%s,%s,%s,%s)",
            (row["user_id"], token_hash,
             datetime.now() + timedelta(hours=ttl), client_info[:255]),
        )
        cur.execute("UPDATE app_user SET last_login_at=NOW() WHERE user_id=%s",
                    (row["user_id"],))
        return Identity(
            user_id=row["user_id"],
            username=row["username"],
            role=row["role"],
            guest_type=row["guest_type"],
            token=token,
        )


def logout(token: str) -> None:
    th = hashlib.sha256(token.encode()).hexdigest()
    with get_pool().tx() as cur:
        cur.execute("UPDATE auth_session SET revoked_at=NOW() "
                    "WHERE token_hash=%s AND revoked_at IS NULL", (th,))


def reset_password(actor_role: str, target_user_id: int, new_password: str) -> bool:
    if actor_role != "admin":
        return False
    ph = hash_password(new_password)
    with get_pool().tx() as cur:
        cur.execute("SELECT * FROM app_user WHERE user_id=%s", (target_user_id,))
        row = cur.fetchone()
        if not row:
            return False
        sig = _row_signature(row["user_id"], row["username"], row["role"],
                             ph, int(row["is_active"]))
        cur.execute("UPDATE app_user SET password_hash=%s, signature=%s "
                    "WHERE user_id=%s", (ph, sig, target_user_id))
    return True
