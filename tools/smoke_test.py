"""快速烟雾测试 — 不启动 GUI, 只验证后端模块能 import 与基本功能。

用法:
    python tools/smoke_test.py
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    print("[1/6] import 后端模块 ...")
    from app.config import load_config
    from app.backend.db import get_pool
    from app.backend.repos import generic
    from app.backend.repos.specs import SPECS
    from app.backend.security.credentials import (
        ensure_default_admin, login, logout
    )
    from app.backend import audit

    print("[2/6] load_config ...")
    cfg = load_config()
    print(f"      mysql={cfg.mysql.host}:{cfg.mysql.port}/{cfg.mysql.database}")

    print("[3/6] DB ping ...")
    with get_pool().read() as cur:
        cur.execute("SELECT 1 AS ok")
        assert cur.fetchone()["ok"] == 1

    print("[4/6] ensure_default_admin ...")
    ensure_default_admin()

    print("[5/6] 登录 admin/admin123 ...")
    ident = login("admin", "admin123", client_info="smoke-test")
    assert ident is not None, "admin 登录失败"
    print(f"      ok, role={ident.role}, token len={len(ident.token)}")

    print("[6/6] 表与计数:")
    for t in SPECS:
        n = generic.count_rows(t)
        origin = generic.get_data_origin(t)
        src = origin["source"] if origin else "-"
        print(f"      {t:30s}  rows={n:6d}  origin={src}")

    audit.write(ident.username, ident.role, "(smoke-test)", "LOGIN",
                affected_rows=1, extra={"phase": "smoke"})
    logout(ident.token)
    print("\nOK — backend smoke test passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
