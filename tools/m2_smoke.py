"""M2 端到端烟雾测试.

不启 GUI; 直接走仓储:
  1. 用 admin 登录
  2. 选一名学生, 修改 dorm, 保存, 验证落库
  3. 用 generic.run_sql(SELECT) 测自定义 SQL
  4. 用 generic.run_sql(DROP TABLE) 期望被 admin 允许 (但跳过实际 DROP) -> 改为 viewer 测拒绝
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.backend.db import get_pool
from app.backend.repos import generic
from app.backend.security.credentials import login, ensure_default_admin
from app.backend import audit


def main() -> int:
    ensure_default_admin()
    ident = login("admin", "admin123", client_info="m2-smoke")
    assert ident, "admin login failed"
    print(f"[1] admin login ok, role={ident.role}")

    # 取一名学生
    rows = generic.list_rows("student", limit=1)
    assert rows, "no student row"
    sid = rows[0]["student_id"]
    old_dorm = rows[0].get("dorm")
    new_dorm = (old_dorm or "") + "★"
    print(f"[2] target student_id={sid}, old dorm={old_dorm}")

    n = generic.update_row("student", sid, {"dorm": new_dorm},
                           actor=ident.username, role=ident.role)
    print(f"    UPDATE affected={n}")
    after = generic.get_row("student", sid)
    assert after["dorm"] == new_dorm, f"update not visible: {after['dorm']}"
    print(f"    verified: dorm now = {after['dorm']}")

    # 还原
    generic.update_row("student", sid, {"dorm": old_dorm},
                       actor=ident.username, role=ident.role)
    print(f"[3] reverted dorm to {old_dorm}")

    # 自定义 SQL
    r = generic.run_sql(
        "SELECT s.student_no, s.name, m.major_name "
        "FROM student s JOIN major m USING(major_id) LIMIT 3",
        actor=ident.username, role="admin")
    print(f"[4] custom SQL returned {len(r['rows'])} rows / {len(r['columns'])} cols")
    for row in r["rows"]:
        print(f"      {row}")

    # viewer 试 DROP, 应被拒
    try:
        generic.run_sql("DROP TABLE student",
                         actor="viewer", role="viewer")
        print("[5] FAIL — viewer DROP 应被拒")
        return 1
    except PermissionError as e:
        print(f"[5] viewer DROP 被拒 ✓ ({e})")

    # editor 试 TRUNCATE, 也应被拒
    try:
        generic.run_sql("TRUNCATE TABLE student",
                         actor="editor", role="editor")
        print("[6] FAIL — editor TRUNCATE 应被拒")
        return 1
    except PermissionError as e:
        print(f"[6] editor TRUNCATE 被拒 ✓ ({e})")

    # 审计日志查询
    logs = audit.query(actor="admin", limit=5)
    print(f"[7] 最近 admin 操作 {len(logs)} 条")
    for r in logs[:3]:
        print(f"      {r['ts']} {r['action']:8s} {r['table_name']:18s} pk={r['target_pk']}")

    print("\nM2 smoke OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
