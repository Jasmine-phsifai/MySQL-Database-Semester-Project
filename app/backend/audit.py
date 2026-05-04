"""JSON 操作日志切面。

每次写入会:
  1. 在 logs/YYYY-MM-DD.jsonl append 一行 JSON (事务外, 异步)
  2. 在 audit_log_index 写一条索引行 (用于按用户/表/时间快速查询)

录入员/访客无法删除 jsonl 文件 (todo 3.5.4); 通过设置文件只追加 + 后端不暴露删除 API 实现。
"""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import load_config
from app.backend.db import get_pool


_lock = threading.Lock()


def _log_path(now: datetime) -> Path:
    p = load_config().paths.logs_dir / f"{now:%Y-%m-%d}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def write(actor: str, role: str, table_name: str, action: str,
          target_pk: Any = None, affected_rows: int = 0,
          before: Any = None, after: Any = None,
          extra: dict | None = None) -> None:
    now = datetime.now()
    path = _log_path(now)
    entry = {
        "ts":            now.isoformat(timespec="seconds"),
        "actor":         actor,
        "role":          role,
        "table_name":    table_name,
        "action":        action,
        "target_pk":     target_pk,
        "affected_rows": affected_rows,
        "before":        before,
        "after":         after,
    }
    if extra:
        entry.update(extra)
    line = json.dumps(entry, ensure_ascii=False, default=str)

    with _lock:
        offset = path.stat().st_size if path.exists() else 0
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    # 索引行写库 (失败不影响业务, swallow)
    try:
        with get_pool().tx() as cur:
            cur.execute(
                "INSERT INTO audit_log_index(actor,role,table_name,action,"
                "target_pk,affected_rows,log_file,file_offset,ts) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (actor, role, table_name, action,
                 None if target_pk is None else str(target_pk)[:50],
                 affected_rows, path.name, offset, now),
            )
    except Exception as e:  # noqa: BLE001
        print(f"[audit] index write failed: {e}")


def query(actor: str | None = None, table_name: str | None = None,
          action: str | None = None, since: datetime | None = None,
          limit: int = 200) -> list[dict]:
    sql = ["SELECT * FROM audit_log_index WHERE 1=1"]
    params: list = []
    if actor:
        sql.append("AND actor=%s"); params.append(actor)
    if table_name:
        sql.append("AND table_name=%s"); params.append(table_name)
    if action:
        sql.append("AND action=%s"); params.append(action)
    if since:
        sql.append("AND ts>=%s"); params.append(since)
    sql.append("ORDER BY log_id DESC LIMIT %s"); params.append(limit)
    with get_pool().read() as cur:
        cur.execute(" ".join(sql), tuple(params))
        return list(cur.fetchall())
