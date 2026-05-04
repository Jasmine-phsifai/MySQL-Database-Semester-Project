"""MySQL 连接池 + 事务上下文管理。

PyMySQL 本身没有官方连接池; 这里用 queue.Queue 做最小封装,
适合单机桌面应用 (并发数 <= 8) 的场景。
"""
from __future__ import annotations

import queue
import threading
from contextlib import contextmanager
from typing import Iterator

import pymysql
from pymysql.cursors import DictCursor

from app.config import MysqlCfg, load_config


class DBPool:
    """简易连接池。线程安全, 上下文管理自动归还。"""

    _instance: "DBPool | None" = None
    _lock = threading.Lock()

    def __init__(self, cfg: MysqlCfg) -> None:
        self.cfg = cfg
        self._pool: queue.Queue = queue.Queue(maxsize=cfg.pool_size)
        for _ in range(cfg.pool_size):
            self._pool.put(self._new_conn())

    def _new_conn(self) -> pymysql.connections.Connection:
        return pymysql.connect(
            host=self.cfg.host,
            port=self.cfg.port,
            user=self.cfg.user,
            password=self.cfg.password,
            database=self.cfg.database,
            charset=self.cfg.charset,
            connect_timeout=self.cfg.connect_timeout_sec,
            read_timeout=self.cfg.query_timeout_sec,
            write_timeout=self.cfg.query_timeout_sec,
            autocommit=False,
            cursorclass=DictCursor,
        )

    @classmethod
    def instance(cls) -> "DBPool":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(load_config().mysql)
        return cls._instance

    @contextmanager
    def conn(self) -> Iterator[pymysql.connections.Connection]:
        c = self._pool.get()
        try:
            try:
                c.ping(reconnect=True)
            except Exception:
                try:
                    c.close()
                except Exception:
                    pass
                c = self._new_conn()
            yield c
        finally:
            self._pool.put(c)

    @contextmanager
    def tx(self):
        """事务上下文: 提交/回滚 + 返回 cursor。"""
        with self.conn() as c:
            cur = c.cursor()
            try:
                yield cur
                c.commit()
            except Exception:
                c.rollback()
                raise
            finally:
                cur.close()

    @contextmanager
    def read(self):
        """只读 cursor。

        退出时 commit 释放 InnoDB REPEATABLE READ 隐式快照,
        否则连接复用会在下次读时仍看见旧版本数据 (生成器/导入器场景常见)。
        """
        with self.conn() as c:
            cur = c.cursor()
            try:
                yield cur
            finally:
                cur.close()
                try:
                    c.commit()
                except Exception:
                    pass


def get_pool() -> DBPool:
    return DBPool.instance()
