"""把 OCR / 识别出的课程表 markdown 灌入数据库.

输入: 数据库PJ 根目录下的 *_识别.md (两份), 或 data/manual_md/*.md
表头(13 列):
    | 选课序号 | 课程名称 | 学分 | 教师 | 职称 | 时间 | 教室 | 人数 |
    | 备注 | 考试时间 | 考试类型 | 含A+ | 开课院系 |

行示例:
    | PTSS110082.01 | 毛泽东思想... | 3 | 陈琳 | 副教授 | 三11-13[1-15] | 邯郸校区 | 95 | 思政A | 考试日期:... | 开卷 |  | 马克思主义学院 |

落库:
    department  按 dept_name 反查/创建
    teacher     按 name+dept_id 反查; 不存在则建 (工号 T_AUTO_xxxxx)
    course      按 course_code (= 选课序号去除 .班号) 反查/创建
    course_offering  (course_id, semester_id, section_no) UNIQUE; 同 key 跳过
    offering_teacher 关联

semester 由文件名推断:
    "2025-2026 学年第一学期" → 2025-2026-1
    "25-26第二学期课程表"     → 2025-2026-2
也支持 --semester 参数显式指定.

每张被影响表写 data_origin='imported'.
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.backend.db import get_pool   # noqa: E402
from app.backend.repos import generic # noqa: E402
from app.backend import audit         # noqa: E402


HEADER_KEYS = ("选课序号", "课程名称", "学分", "教师", "开课院系")
SEM_FROM_FILE = {
    "2025-2026 学年第一学期": "2025-2026-1",
    "2025-2026 学年第一学期_识别": "2025-2026-1",
    "25-26第二学期课程表": "2025-2026-2",
    "25-26第二学期课程表_识别": "2025-2026-2",
}


# ------------------------------------------------------------------
# Markdown table parser
# ------------------------------------------------------------------

_PIPE_ROW = re.compile(r"^\|.*\|\s*$")
_SEP_ROW  = re.compile(r"^\|[\s:-]+\|[\s:-]+(?:\|[\s:-]*)+\|?\s*$")


def _split_row(line: str) -> list[str]:
    cells = line.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def iter_course_rows(md_path: Path) -> list[dict]:
    """遍历 md 中所有带 13 列且表头匹配的表, 返回字典列表."""
    out: list[dict] = []
    in_table = False
    header: list[str] | None = None
    with md_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not _PIPE_ROW.match(line):
                in_table = False
                header = None
                continue
            if _SEP_ROW.match(line):
                continue
            cells = _split_row(line)
            if header is None:
                if "选课序号" in line and "课程名称" in line:
                    header = cells
                    in_table = True
                continue
            if in_table:
                if len(cells) != len(header):
                    continue
                if not cells[0] or not re.match(r"^[A-Z0-9]+\.[0-9]+$", cells[0]):
                    continue
                out.append(dict(zip(header, cells)))
    return out


# ------------------------------------------------------------------
# 反查 / 自动建表辅助
# ------------------------------------------------------------------

class Cache:
    def __init__(self) -> None:
        self.dept: dict[str, int] = {}
        self.teacher: dict[tuple[str, int], int] = {}  # (name, dept_id) -> id
        self.course: dict[str, int] = {}                # course_code -> id
        self.semester: dict[str, int] = {}              # name -> id
        self.dept_seq = 0
        self.teacher_seq = 0

    def warmup(self) -> None:
        with get_pool().read() as cur:
            cur.execute("SELECT dept_id, dept_code, dept_name FROM department")
            for r in cur.fetchall():
                self.dept[r["dept_name"]] = r["dept_id"]
            cur.execute("SELECT teacher_id, name, dept_id, staff_no FROM teacher")
            for r in cur.fetchall():
                self.teacher[(r["name"], r["dept_id"])] = r["teacher_id"]
                m = re.match(r"T_AUTO_(\d+)", r["staff_no"] or "")
                if m:
                    self.teacher_seq = max(self.teacher_seq, int(m.group(1)))
                m2 = re.match(r"T(\d+)", r["staff_no"] or "")
                if m2 and len(r["staff_no"]) <= 6:
                    self.teacher_seq = max(self.teacher_seq, int(m2.group(1)))
            cur.execute("SELECT course_id, course_code FROM course")
            for r in cur.fetchall():
                self.course[r["course_code"]] = r["course_id"]
            cur.execute("SELECT semester_id, name FROM semester")
            for r in cur.fetchall():
                self.semester[r["name"]] = r["semester_id"]
            cur.execute("SELECT dept_code FROM department "
                        "WHERE dept_code LIKE 'D_AUTO_%' "
                        "ORDER BY dept_code DESC LIMIT 1")
            r = cur.fetchone()
            if r:
                m = re.match(r"D_AUTO_(\d+)", r["dept_code"])
                if m:
                    self.dept_seq = int(m.group(1))

    def get_or_create_dept(self, name: str, actor: str) -> int:
        if name in self.dept:
            return self.dept[name]
        self.dept_seq += 1
        code = f"D_AUTO_{self.dept_seq:03d}"
        try:
            new_id = generic.insert_row(
                "department",
                {"dept_code": code, "dept_name": name, "status": 1},
                actor=actor, role="admin",
            )
        except Exception:
            # collation 把 visually similar 的名字视作相同; 反查取 id
            with get_pool().read() as cur:
                cur.execute(
                    "SELECT dept_id, dept_name FROM department "
                    "WHERE dept_name=%s LIMIT 1", (name,))
                r = cur.fetchone()
                if not r:
                    raise
                new_id = r["dept_id"]
                # 把数据库里的 canonical name 也存入 cache
                self.dept[r["dept_name"]] = new_id
        self.dept[name] = new_id
        return new_id

    def get_or_create_teacher(self, name: str, dept_id: int, title: str,
                              actor: str) -> int:
        key = (name, dept_id)
        if key in self.teacher:
            return self.teacher[key]
        self.teacher_seq += 1
        staff = f"T_AUTO_{self.teacher_seq:05d}"
        try:
            new_id = generic.insert_row(
                "teacher",
                {"staff_no": staff, "name": name[:50], "dept_id": dept_id,
                 "title": (title or None) and title[:30], "status": 1},
                actor=actor, role="admin",
            )
        except Exception:
            # staff_no 撞了, 重抛新序号
            self.teacher_seq += 100
            staff = f"T_AUTO_{self.teacher_seq:05d}"
            new_id = generic.insert_row(
                "teacher",
                {"staff_no": staff, "name": name[:50], "dept_id": dept_id,
                 "title": (title or None) and title[:30], "status": 1},
                actor=actor, role="admin",
            )
        self.teacher[key] = new_id
        return new_id

    def get_or_create_course(self, code: str, name: str, credits: float,
                             dept_id: int, description: str,
                             is_honor: int, actor: str) -> int:
        if code in self.course:
            return self.course[code]
        try:
            new_id = generic.insert_row(
                "course",
                {"course_code": code, "course_name": name[:100],
                 "description": (description[:500] if description else None),
                 "class_hours": max(1, int(round(credits * 16))),
                 "credits": credits or 0.5, "degree_level": "本科",
                 "dept_id": dept_id, "is_honor": is_honor,
                 "allow_pnp": 0, "grade_mode": "PERCENT", "status": 1},
                actor=actor, role="admin",
            )
        except Exception:
            with get_pool().read() as cur:
                cur.execute("SELECT course_id FROM course WHERE course_code=%s",
                            (code,))
                r = cur.fetchone()
                if not r:
                    raise
                new_id = r["course_id"]
        self.course[code] = new_id
        return new_id

    def ensure_semester(self, sem_name: str) -> int:
        if sem_name in self.semester:
            return self.semester[sem_name]
        # 新增学期 (按 sem_name 推断起止日期)
        if sem_name.endswith("-1"):
            start = datetime(int(sem_name[:4]), 9, 1)
            end   = start + timedelta(days=130)
        else:
            year = int(sem_name[:4]) + 1
            start = datetime(year, 2, 22)
            end   = start + timedelta(days=130)
        new_id = generic.insert_row(
            "semester",
            {"name": sem_name, "start_date": start.date(), "end_date": end.date()},
            actor="md-import", role="admin",
        )
        self.semester[sem_name] = new_id
        return new_id


# ------------------------------------------------------------------
# 字段解析
# ------------------------------------------------------------------

def parse_credits(s: str) -> float:
    s = (s or "").strip()
    m = re.search(r"\d+(?:\.\d+)?", s)
    return float(m.group()) if m else 0.0


def parse_capacity(s: str) -> int:
    s = (s or "").strip()
    m = re.search(r"\d+", s)
    n = int(m.group()) if m else 100
    return max(1, n)  # CHECK 约束: capacity > 0


def split_serial(serial: str) -> tuple[str, str]:
    """PTSS110082.01 → ('PTSS110082', '01')."""
    code, _, sec = serial.partition(".")
    return code, sec or "01"


def is_honor(remark: str, name: str) -> int:
    txt = (remark or "") + (name or "")
    return 1 if any(k in txt for k in ("荣誉", "(荣誉)", "(H)")) else 0


# ------------------------------------------------------------------
# 主流程
# ------------------------------------------------------------------

def process_file(md_path: Path, sem_name: str | None,
                 cache: Cache, actor: str) -> dict:
    rows = iter_course_rows(md_path)
    if not rows:
        return {"file": str(md_path), "rows": 0, "warning": "未找到课程表"}

    sem = sem_name or SEM_FROM_FILE.get(md_path.stem) \
                  or SEM_FROM_FILE.get(md_path.stem.replace("_识别", ""))
    if not sem:
        raise ValueError(
            f"无法从文件名推断 semester: {md_path.name}; 请用 --semester 指定"
        )
    sem_id = cache.ensure_semester(sem)

    affected = {"course": 0, "teacher": 0, "department": 0,
                 "course_offering": 0, "offering_teacher": 0,
                 "skipped_existing_offering": 0}

    pool = get_pool()
    # 预读 (course_id, semester_id, section_no) UNIQUE 已存在的开课
    existing_off: set[tuple[int, int, str]] = set()
    with pool.read() as cur:
        cur.execute("SELECT course_id, semester_id, section_no "
                    "FROM course_offering WHERE semester_id=%s", (sem_id,))
        for r in cur.fetchall():
            existing_off.add((r["course_id"], r["semester_id"], r["section_no"]))

    for r in rows:
        serial   = r.get("选课序号", "")
        cname    = r.get("课程名称", "")
        credits  = parse_credits(r.get("学分", ""))
        tname    = r.get("教师", "").strip()
        title    = r.get("职称", "").strip()
        capacity = parse_capacity(r.get("人数", ""))
        remark   = r.get("备注", "").strip()
        dept_name = r.get("开课院系", "").strip()

        if not serial or not cname or not dept_name:
            continue

        ccode, section = split_serial(serial)

        before_dept_count    = len(cache.dept)
        before_teacher_count = len(cache.teacher)
        before_course_count  = len(cache.course)

        dept_id = cache.get_or_create_dept(dept_name, actor=actor)
        if len(cache.dept) > before_dept_count:
            affected["department"] += 1

        course_id = cache.get_or_create_course(
            ccode, cname, credits, dept_id, remark,
            is_honor(remark, cname), actor=actor,
        )
        if len(cache.course) > before_course_count:
            affected["course"] += 1

        teacher_id = None
        if tname:
            teacher_id = cache.get_or_create_teacher(tname, dept_id, title,
                                                       actor=actor)
            if len(cache.teacher) > before_teacher_count:
                affected["teacher"] += 1

        # 开课实例
        key = (course_id, sem_id, section)
        if key in existing_off:
            affected["skipped_existing_offering"] += 1
            offering_id = None
            with pool.read() as cur:
                cur.execute("SELECT offering_id FROM course_offering "
                            "WHERE course_id=%s AND semester_id=%s "
                            "AND section_no=%s",
                            (course_id, sem_id, section))
                row = cur.fetchone()
                if row:
                    offering_id = row["offering_id"]
        else:
            with pool.read() as cur:
                cur.execute("SELECT start_date, end_date FROM semester "
                            "WHERE semester_id=%s", (sem_id,))
                sem_row = cur.fetchone()
            sem_start = datetime.combine(sem_row["start_date"], datetime.min.time())
            sem_end   = datetime.combine(sem_row["end_date"],   datetime.min.time())
            try:
                offering_id = generic.insert_row(
                    "course_offering",
                    {"course_id": course_id, "semester_id": sem_id,
                     "section_no": section[:10], "capacity": max(1, capacity),
                     "free_period_start":   sem_start,
                     "free_period_end":     sem_start + timedelta(days=14),
                     "withdrawal_deadline": sem_start + timedelta(days=70),
                     "pass_threshold": 60.00, "grade_mode": "PERCENT",
                     "status": 1},
                    actor=actor, role="admin",
                )
            except Exception as e:
                print(f"  warn: offering insert {ccode}.{section}: {e}")
                continue
            existing_off.add(key)
            affected["course_offering"] += 1

        # 关联教师
        if offering_id and teacher_id:
            with pool.read() as cur:
                cur.execute("SELECT 1 FROM offering_teacher "
                            "WHERE offering_id=%s AND teacher_id=%s",
                            (offering_id, teacher_id))
                if not cur.fetchone():
                    try:
                        generic.insert_row(
                            "offering_teacher",
                            {"offering_id": offering_id,
                             "teacher_id":  teacher_id, "role": "主讲"},
                            actor=actor, role="admin",
                        )
                        affected["offering_teacher"] += 1
                    except Exception as e:  # 已存在等
                        print(f"  warn: offering_teacher insert: {e}")

    return {"file": md_path.name, "semester": sem,
            "input_rows": len(rows), **affected}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", action="append",
                    help="markdown 文件路径; 不指定则扫 数据库PJ 根 + data/manual_md/")
    ap.add_argument("--semester", default=None,
                    help="覆盖 semester 名 (例 2025-2026-1)")
    ap.add_argument("--actor", default="md-import")
    args = ap.parse_args()

    paths: list[Path] = []
    if args.md:
        paths = [Path(p) for p in args.md]
    else:
        paths.extend(sorted(PROJECT_ROOT.glob("*_识别.md")))
        paths.extend(sorted((PROJECT_ROOT / "data" / "manual_md").glob("*.md")))
    paths = [p for p in paths if p.is_file()
              and not p.name.startswith("readme_")]

    if not paths:
        print("[md] 未找到可导入的 markdown.")
        return 0

    cache = Cache()
    cache.warmup()

    summary: list[dict] = []
    for p in paths:
        print(f"\n==== {p.relative_to(PROJECT_ROOT)} ====")
        result = process_file(p, args.semester, cache, args.actor)
        for k, v in result.items():
            print(f"  {k}: {v}")
        summary.append(result)

    # 标 data_origin
    for tab in ("department", "teacher", "course",
                "course_offering", "offering_teacher", "semester"):
        n = generic.count_rows(tab)
        generic.set_data_origin(tab, "imported", n,
                                 note="merged from PDF-recognized markdown")

    audit.write(args.actor, "admin", "(import-md)", "IMPORT",
                affected_rows=sum(r.get("course_offering", 0) for r in summary),
                extra={"files": [r["file"] for r in summary]})

    print("\nOK — md import done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
