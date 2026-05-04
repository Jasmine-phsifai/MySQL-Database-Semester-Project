"""通用 CRUD 仓储 — 由 TableSpec 驱动。

为 17+1 张表共用; 不为每张表写独立类。
所有写操作通过审计装饰器记录 JSON 日志。
"""
from __future__ import annotations

from typing import Any

from app.backend.db import get_pool
from app.backend.repos.specs import SPECS, TableSpec
from app.backend import audit


# ---- 列名安全 (防 SQL 注入) -------------------------------------------------

def _validate_cols(spec: TableSpec, cols: list[str]) -> None:
    valid = {c.name for c in spec.cols}
    for c in cols:
        if c not in valid:
            raise ValueError(f"非法列名: {c}")


def _spec(table: str) -> TableSpec:
    if table not in SPECS:
        raise KeyError(f"未知业务表: {table}")
    return SPECS[table]


# ---- 查询 -----------------------------------------------------------------

def list_rows(table: str, *, limit: int = 500, offset: int = 0,
              where: str = "", params: tuple = ()) -> list[dict]:
    s = _spec(table)
    cols = ", ".join(c.name for c in s.cols)
    order = f"ORDER BY {s.order_by}" if s.order_by else ""
    w = f"WHERE {where}" if where else ""
    sql = f"SELECT {cols} FROM {s.name} {w} {order} LIMIT %s OFFSET %s"
    with get_pool().read() as cur:
        cur.execute(sql, (*params, limit, offset))
        return list(cur.fetchall())


def count_rows(table: str, where: str = "", params: tuple = ()) -> int:
    s = _spec(table)
    w = f"WHERE {where}" if where else ""
    with get_pool().read() as cur:
        cur.execute(f"SELECT COUNT(*) AS n FROM {s.name} {w}", params)
        return int(cur.fetchone()["n"])


def get_row(table: str, pk_value: Any) -> dict | None:
    s = _spec(table)
    cols = ", ".join(c.name for c in s.cols)
    with get_pool().read() as cur:
        cur.execute(f"SELECT {cols} FROM {s.name} WHERE {s.pk}=%s", (pk_value,))
        return cur.fetchone()


def lookup_options(fk_table: str, value_col: str, label_col: str,
                   limit: int = 1000) -> list[tuple[Any, str]]:
    """外键下拉用 — 返回 (value, label) 列表。"""
    if fk_table not in SPECS:
        return []
    with get_pool().read() as cur:
        cur.execute(
            f"SELECT {value_col} AS v, {label_col} AS l "
            f"FROM {fk_table} ORDER BY {label_col} LIMIT %s", (limit,)
        )
        return [(r["v"], str(r["l"])) for r in cur.fetchall()]


# ---- 写入 -----------------------------------------------------------------

def insert_row(table: str, values: dict, *, actor: str, role: str) -> Any:
    s = _spec(table)
    cols = [c for c in values.keys() if s.by_name(c) is not None]
    _validate_cols(s, cols)
    placeholders = ", ".join(["%s"] * len(cols))
    sql = f"INSERT INTO {s.name} ({', '.join(cols)}) VALUES ({placeholders})"
    with get_pool().tx() as cur:
        cur.execute(sql, tuple(values[c] for c in cols))
        new_id = cur.lastrowid or values.get(s.pk)
    audit.write(actor, role, table, "INSERT",
                target_pk=new_id, affected_rows=1, after=values)
    return new_id


def update_row(table: str, pk_value: Any, values: dict,
               *, actor: str, role: str) -> int:
    s = _spec(table)
    cols = [c for c in values.keys() if s.by_name(c) is not None and c != s.pk]
    _validate_cols(s, cols)
    if not cols:
        return 0
    set_clause = ", ".join(f"{c}=%s" for c in cols)
    before = get_row(table, pk_value)
    with get_pool().tx() as cur:
        cur.execute(f"UPDATE {s.name} SET {set_clause} WHERE {s.pk}=%s",
                    (*[values[c] for c in cols], pk_value))
        affected = cur.rowcount
    audit.write(actor, role, table, "UPDATE",
                target_pk=pk_value, affected_rows=affected,
                before=before, after=values)
    return affected


def delete_row(table: str, pk_value: Any, *, actor: str, role: str,
               soft: bool = True) -> int:
    """优先软删 (status=0); 仅在表无 status 字段时才物理删除。"""
    s = _spec(table)
    has_status = s.by_name("status") is not None
    before = get_row(table, pk_value)
    with get_pool().tx() as cur:
        if soft and has_status:
            cur.execute(f"UPDATE {s.name} SET status=0 WHERE {s.pk}=%s", (pk_value,))
        else:
            cur.execute(f"DELETE FROM {s.name} WHERE {s.pk}=%s", (pk_value,))
        affected = cur.rowcount
    audit.write(actor, role, table,
                "DELETE" if not (soft and has_status) else "UPDATE",
                target_pk=pk_value, affected_rows=affected, before=before)
    return affected


def batch_insert(table: str, rows: list[dict], *, actor: str, role: str) -> int:
    """事务内批量插入; 由生成器/导入向导使用。"""
    if not rows:
        return 0
    s = _spec(table)
    cols = [c.name for c in s.cols if any(c.name in r for r in rows)]
    _validate_cols(s, cols)
    placeholders = ", ".join(["%s"] * len(cols))
    sql = f"INSERT INTO {s.name} ({', '.join(cols)}) VALUES ({placeholders})"
    with get_pool().tx() as cur:
        for r in rows:
            cur.execute(sql, tuple(r.get(c) for c in cols))
        affected = len(rows)
    audit.write(actor, role, table, "INSERT",
                affected_rows=affected, extra={"batch": True})
    return affected


# ---- 数据来源标注 ---------------------------------------------------------

def get_data_origin(table: str) -> dict | None:
    with get_pool().read() as cur:
        cur.execute("SELECT * FROM data_origin WHERE table_name=%s", (table,))
        return cur.fetchone()


def set_data_origin(table: str, source: str, count: int = 0,
                    note: str = "") -> None:
    with get_pool().tx() as cur:
        cur.execute(
            "INSERT INTO data_origin(table_name, source, sample_row_count, note) "
            "VALUES (%s,%s,%s,%s) "
            "ON DUPLICATE KEY UPDATE source=VALUES(source), "
            "sample_row_count=VALUES(sample_row_count), "
            "generated_at=CURRENT_TIMESTAMP, note=VALUES(note)",
            (table, source, count, note[:255]),
        )


# ---- 自定义 SQL (admin 全权; viewer 只读 SELECT) -------------------------

_FORBIDDEN_FOR_VIEWER = ("INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE",
                          "ALTER", "CREATE", "GRANT", "REVOKE", "SET", "CALL")


def run_sql(sql: str, *, actor: str, role: str) -> dict:
    """前端自定义 SQL 入口。viewer 只允许 SELECT。"""
    head = sql.lstrip().split(None, 1)[0].upper() if sql.strip() else ""
    if role == "viewer":
        if head != "SELECT":
            raise PermissionError("访客只能执行 SELECT")
    elif role == "editor":
        if head in {"DROP", "TRUNCATE", "GRANT", "REVOKE"}:
            raise PermissionError(f"录入员不能执行 {head}")
    with get_pool().conn() as c:
        cur = c.cursor()
        try:
            cur.execute(sql)
            if cur.description:
                rows = list(cur.fetchall())
                cols = [d[0] for d in cur.description]
                c.commit()
                audit.write(actor, role, "(custom-sql)", "SQL",
                            affected_rows=len(rows),
                            extra={"sql": sql[:500]})
                return {"columns": cols, "rows": rows, "affected": len(rows)}
            else:
                affected = cur.rowcount
                c.commit()
                audit.write(actor, role, "(custom-sql)", "SQL",
                            affected_rows=affected,
                            extra={"sql": sql[:500]})
                return {"columns": [], "rows": [], "affected": affected}
        except Exception:
            c.rollback()
            raise
        finally:
            cur.close()
