"""读取并校验 config.toml; 全局只解析一次。"""
from __future__ import annotations

import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class MysqlCfg:
    host: str
    port: int
    user: str
    password: str
    database: str
    charset: str
    pool_size: int
    connect_timeout_sec: int
    query_timeout_sec: int


@dataclass(frozen=True)
class SecurityCfg:
    hmac_salt: str
    session_ttl_hours: int
    default_admin_username: str
    default_admin_password: str


@dataclass(frozen=True)
class PathsCfg:
    logs_dir: Path
    backups_dir: Path
    data_dir: Path
    docs_dir: Path
    runtime_dir: Path


@dataclass(frozen=True)
class UiCfg:
    theme: str
    font_size: int
    table_row_height: int


@dataclass(frozen=True)
class FixturesCfg:
    auto_seed_empty_tables: bool
    sample_students: int
    sample_teachers: int
    sample_courses: int
    sample_semesters: int


@dataclass(frozen=True)
class AppConfig:
    mysql: MysqlCfg
    security: SecurityCfg
    paths: PathsCfg
    ui: UiCfg
    fixtures: FixturesCfg


@lru_cache(maxsize=1)
def load_config(path: Path | None = None) -> AppConfig:
    p = path or (PROJECT_ROOT / "config.toml")
    if not p.exists():
        sys.exit(f"配置文件缺失: {p}")
    raw = tomllib.loads(p.read_text(encoding="utf-8"))

    paths = raw["paths"]
    return AppConfig(
        mysql=MysqlCfg(**raw["mysql"]),
        security=SecurityCfg(**raw["security"]),
        paths=PathsCfg(
            logs_dir   =PROJECT_ROOT / paths["logs_dir"],
            backups_dir=PROJECT_ROOT / paths["backups_dir"],
            data_dir   =PROJECT_ROOT / paths["data_dir"],
            docs_dir   =PROJECT_ROOT / paths["docs_dir"],
            runtime_dir=PROJECT_ROOT / paths["runtime_dir"],
        ),
        ui=UiCfg(**raw["ui"]),
        fixtures=FixturesCfg(**raw["fixtures"]),
    )
