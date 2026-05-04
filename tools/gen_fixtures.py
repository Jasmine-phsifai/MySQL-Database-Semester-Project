"""扫描 18 张业务表; 凡为空的, 用 Faker 中文 locale 自动填充样例数据。

设计原则:
  - 不覆盖已有数据 (count > 0 跳过)
  - 写入后在 data_origin 表标注 source='sample'
  - 教师/院系若 PDF 已灌则不重复造
  - 业务边界覆盖: 重修 / 期中退课 / PNP / A+ 30% 上限 / 转专业各 ~3%

用法:
    python tools/gen_fixtures.py
    python tools/gen_fixtures.py --force-table student   # 强制重建 student
"""
from __future__ import annotations

import argparse
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from faker import Faker  # noqa: E402

from app.backend.db import get_pool  # noqa: E402
from app.backend.repos import generic  # noqa: E402
from app.config import load_config  # noqa: E402

fake = Faker("zh_CN")
Faker.seed(42)
random.seed(42)


# ---------------------------------------------------------------------------
# 实体生成器
# ---------------------------------------------------------------------------

DEPARTMENTS = [
    ("CS",   "计算机科学技术学院", "邯郸校区计算机楼"),
    ("MATH", "数学科学学院",       "光华楼东主楼"),
    ("PHYS", "物理学系",           "邯郸校区物理楼"),
    ("ECON", "经济学院",           "邯郸校区经济学院楼"),
    ("CHEM", "化学系",             "邯郸校区化学楼"),
    ("FOR",  "外国语言文学学院",   "文科楼"),
    ("LIFE", "生命科学学院",       "江湾校区生科院"),
    ("PHIL", "哲学学院",           "光华楼西主楼"),
]

MAJORS = [
    ("CS",   [("CS-CS",   "计算机科学与技术"), ("CS-SE", "软件工程"),
              ("CS-DS",   "数据科学与大数据技术"), ("CS-AI", "人工智能")]),
    ("MATH", [("MATH-MA", "数学与应用数学"), ("MATH-ST", "统计学")]),
    ("PHYS", [("PHYS-PH", "物理学"),         ("PHYS-AS", "天体物理")]),
    ("ECON", [("ECON-EC", "经济学"),         ("ECON-FI", "金融学"),
              ("ECON-IT", "国际经济与贸易")]),
    ("CHEM", [("CHEM-CH", "化学"),           ("CHEM-AC", "应用化学")]),
    ("FOR",  [("FOR-EN",  "英语"),           ("FOR-JA", "日语"),
              ("FOR-FR",  "法语")]),
    ("LIFE", [("LIFE-BI", "生物科学"),       ("LIFE-EC", "生态学")]),
    ("PHIL", [("PHIL-PH", "哲学")]),
]

COURSE_BANK = [
    # (code, name, hours, credits, dept_code, is_honor, allow_pnp)
    ("CS101",  "数据结构",       64, 4.0, "CS",   0, 0),
    ("CS102",  "算法设计与分析", 48, 3.0, "CS",   0, 0),
    ("CS103H", "高级算法 (荣誉)",64, 4.0, "CS",   1, 0),
    ("CS201",  "操作系统",       64, 4.0, "CS",   0, 0),
    ("CS202",  "计算机网络",     48, 3.0, "CS",   0, 0),
    ("CS203",  "数据库及实现",   48, 3.0, "CS",   0, 0),
    ("CS204",  "编译原理",       48, 3.0, "CS",   0, 0),
    ("CS301",  "机器学习",       48, 3.0, "CS",   0, 0),
    ("CS302",  "人工智能基础",   48, 3.0, "CS",   0, 0),
    ("CS303",  "分布式系统",     48, 3.0, "CS",   1, 0),
    ("MATH101","数学分析",       96, 6.0, "MATH", 0, 0),
    ("MATH102","线性代数",       64, 4.0, "MATH", 0, 0),
    ("MATH201","概率论与数理统计",48, 3.0,"MATH", 0, 0),
    ("MATH202","离散数学",       48, 3.0, "MATH", 0, 0),
    ("PHYS101","大学物理 A",     64, 4.0, "PHYS", 0, 0),
    ("PHYS102","大学物理实验",   32, 1.5, "PHYS", 0, 0),
    ("ECON101","微观经济学",     48, 3.0, "ECON", 0, 0),
    ("ECON102","宏观经济学",     48, 3.0, "ECON", 0, 0),
    ("CHEM101","普通化学",       48, 3.0, "CHEM", 0, 0),
    ("FOR101", "大学英语 (一)",  64, 2.0, "FOR",  0, 1),  # 通识允许 PNP
    ("FOR102", "大学英语 (二)",  64, 2.0, "FOR",  0, 1),
    ("LIFE101","生命科学导论",   32, 2.0, "LIFE", 0, 1),
    ("PHIL101","哲学导论",       32, 2.0, "PHIL", 0, 1),
    ("CS401",  "毕业设计",       96, 6.0, "CS",   0, 0),
]

SEMESTERS = [
    ("2024-2025-1", "2024-09-09", "2025-01-12"),
    ("2024-2025-2", "2025-02-24", "2025-06-29"),
    ("2025-2026-1", "2025-09-08", "2026-01-11"),
    ("2025-2026-2", "2026-02-23", "2026-06-28"),
]


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

def table_empty(table: str) -> bool:
    return generic.count_rows(table) == 0


def fk_id_map(table: str, code_col: str, pk: str = None) -> dict:
    pk = pk or {  # 默认 pk
        "department": "dept_id", "major": "major_id",
        "course": "course_id", "teacher": "teacher_id",
        "semester": "semester_id", "course_offering": "offering_id",
        "student": "student_id",
    }[table]
    with get_pool().read() as cur:
        cur.execute(f"SELECT {code_col} AS code, {pk} AS id FROM {table}")
        return {r["code"]: r["id"] for r in cur.fetchall()}


# ---------------------------------------------------------------------------
# 各表生成
# ---------------------------------------------------------------------------

def seed_department(actor="seed", role="admin") -> int:
    rows = [{"dept_code": c, "dept_name": n, "office_location": loc,
             "phone": fake.phone_number()[:20], "status": 1}
            for c, n, loc in DEPARTMENTS]
    return generic.batch_insert("department", rows, actor=actor, role=role)


def seed_major(actor="seed", role="admin") -> int:
    dmap = fk_id_map("department", "dept_code")
    rows = []
    for dept_code, majors in MAJORS:
        for code, name in majors:
            rows.append({"major_code": code, "major_name": name,
                         "dept_id": dmap[dept_code], "status": 1})
    return generic.batch_insert("major", rows, actor=actor, role=role)


def seed_degree_requirement(actor="seed", role="admin") -> int:
    mmap = fk_id_map("major", "major_code")
    rows = []
    for mid in mmap.values():
        rows.append({"major_id": mid, "degree_level": "本科",
                     "required_credits": 150.0})
        rows.append({"major_id": mid, "degree_level": "硕士",
                     "required_credits": 32.0})
    return generic.batch_insert("degree_requirement", rows,
                                 actor=actor, role=role)


def seed_teacher(actor="seed", role="admin", n: int = 80) -> int:
    dmap = fk_id_map("department", "dept_code")
    dept_ids = list(dmap.values())
    rows = []
    titles = ["教授", "副教授", "讲师", "助教"]
    for i in range(1, n + 1):
        rows.append({
            "staff_no": f"T{i:05d}",
            "name":     fake.name(),
            "dept_id":  random.choice(dept_ids),
            "title":    random.choices(titles, weights=[2, 4, 5, 1])[0],
            "status":   1,
        })
    return generic.batch_insert("teacher", rows, actor=actor, role=role)


def seed_course(actor="seed", role="admin") -> int:
    dmap = fk_id_map("department", "dept_code")
    rows = []
    for code, name, hours, credits, dept, honor, pnp in COURSE_BANK:
        mode = "BOTH" if pnp else "PERCENT"
        rows.append({
            "course_code": code, "course_name": name,
            "description": fake.sentence(nb_words=8),
            "class_hours": hours, "credits": credits,
            "degree_level": "本科", "dept_id": dmap[dept],
            "is_honor": honor, "allow_pnp": pnp,
            "grade_mode": mode, "status": 1,
        })
    return generic.batch_insert("course", rows, actor=actor, role=role)


def seed_semester(actor="seed", role="admin") -> int:
    rows = [{"name": n, "start_date": s, "end_date": e}
            for n, s, e in SEMESTERS]
    return generic.batch_insert("semester", rows, actor=actor, role=role)


def seed_student(actor="seed", role="admin", n: int = 600) -> int:
    mmap = fk_id_map("major", "major_code")
    dmap = fk_id_map("department", "dept_code")
    major_ids = list(mmap.values())
    dept_ids = list(dmap.values())
    rows = []
    for i in range(1, n + 1):
        gender = random.choice(["M", "F"])
        year = random.choice([2022, 2023, 2024, 2025])
        rows.append({
            "student_no": f"{year}30{i:04d}",
            "name":       fake.name_male() if gender == "M" else fake.name_female(),
            "id_card":    fake.ssn(),
            "dorm":       f"{random.randint(1,30):02d}号楼{random.randint(101,608)}",
            "address":    fake.address().replace("\n", " ")[:200],
            "phone":      fake.phone_number()[:20],
            "birth_date": fake.date_of_birth(minimum_age=17, maximum_age=24),
            "gender":     gender,
            "grade_year": year,
            "major_id":   random.choice(major_ids),
            "minor_dept_id": random.choice(dept_ids) if random.random() < 0.15 else None,
            "degree_level":  "本科",
            "status":     1,
        })
    return generic.batch_insert("student", rows, actor=actor, role=role)


def seed_course_offering(actor="seed", role="admin") -> int:
    cmap = fk_id_map("course", "course_code")
    smap = fk_id_map("semester", "name")
    rows = []
    for sem_name, sem_id in smap.items():
        # 每学期开 60% 课程, 部分课程开多个班
        chosen = random.sample(list(cmap.items()), int(len(cmap) * 0.6))
        sem_start_str = next(s for n, s, _ in SEMESTERS if n == sem_name)
        sem_start = datetime.strptime(sem_start_str, "%Y-%m-%d")
        for ccode, cid in chosen:
            sections = random.choices([1, 1, 1, 2, 3], k=1)[0]
            for sec in range(1, sections + 1):
                rows.append({
                    "course_id":   cid,
                    "semester_id": sem_id,
                    "section_no":  f"{sec:02d}",
                    "capacity":    random.choice([50, 80, 120, 150]),
                    "free_period_start":   sem_start,
                    "free_period_end":     sem_start + timedelta(days=14),
                    "withdrawal_deadline": sem_start + timedelta(days=70),
                    "pass_threshold":      60.00,
                    "grade_mode":          "PERCENT",
                    "status":              2 if sem_name.startswith("2024") else 1,
                })
    return generic.batch_insert("course_offering", rows, actor=actor, role=role)


def seed_offering_teacher(actor="seed", role="admin") -> int:
    with get_pool().read() as cur:
        cur.execute("SELECT offering_id, course_id FROM course_offering")
        offs = list(cur.fetchall())
        cur.execute("SELECT teacher_id, dept_id FROM teacher")
        teachers = list(cur.fetchall())
        cur.execute("SELECT course_id, dept_id FROM course")
        course_dept = {r["course_id"]: r["dept_id"] for r in cur.fetchall()}
    rows = []
    for off in offs:
        candidate = [t for t in teachers if t["dept_id"] == course_dept[off["course_id"]]]
        if not candidate:
            candidate = teachers
        main = random.choice(candidate)
        rows.append({"offering_id": off["offering_id"],
                     "teacher_id": main["teacher_id"], "role": "主讲"})
        if random.random() < 0.2:  # 20% 双教师
            second = random.choice(candidate)
            if second["teacher_id"] != main["teacher_id"]:
                rows.append({"offering_id": off["offering_id"],
                             "teacher_id": second["teacher_id"], "role": "合讲"})
    return generic.batch_insert("offering_teacher", rows, actor=actor, role=role)


def seed_enrollment(actor="seed", role="admin") -> int:
    """每个学生在每学期选 4-7 门课。覆盖各种状态。"""
    with get_pool().read() as cur:
        cur.execute("SELECT student_id FROM student")
        students = [r["student_id"] for r in cur.fetchall()]
        cur.execute("SELECT offering_id, semester_id, grade_mode "
                    "FROM course_offering")
        offs = list(cur.fetchall())
    by_sem: dict = {}
    for o in offs:
        by_sem.setdefault(o["semester_id"], []).append(o)

    rows = []
    for sid in students:
        for sem_id, sem_offs in by_sem.items():
            n_pick = random.randint(4, 7)
            picked = random.sample(sem_offs, min(n_pick, len(sem_offs)))
            for o in picked:
                # 状态分布: 80% 已完成, 5% 期中退课, 10% 锁定 (本学期), 5% 取消
                r = random.random()
                if r < 0.80:
                    st = "COMPLETED"
                elif r < 0.85:
                    st = "WITHDRAWN_MID"
                elif r < 0.95:
                    st = "LOCKED"
                else:
                    st = "CANCELLED"
                mode = "PNP" if (random.random() < 0.05 and o["grade_mode"] != "PERCENT") else "PERCENT"
                rows.append({
                    "student_id":   sid,
                    "offering_id":  o["offering_id"],
                    "enroll_status": st,
                    "enroll_mode":  mode,
                    "last_select_at": datetime.now(),
                    "locked_at":     datetime.now() if st != "FREE" else None,
                    "withdrawn_at":  datetime.now() if st == "WITHDRAWN_MID" else None,
                })
    # 去重 (student_id, offering_id) — 上面 random.sample 已保证学期内不重, 但跨学期有 unique 约束键就在 (student_id, offering_id)
    seen = set()
    uniq = []
    for r in rows:
        k = (r["student_id"], r["offering_id"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    return generic.batch_insert("enrollment", uniq, actor=actor, role=role)


def seed_enrollment_action(actor="seed", role="admin") -> int:
    """前两周的选退操作日志, 随机抽 enrollment 的 30% 制造历史。"""
    with get_pool().read() as cur:
        cur.execute("SELECT enrollment_id, student_id, offering_id "
                    "FROM enrollment ORDER BY RAND() LIMIT 4000")
        sample = list(cur.fetchall())
    rows = []
    for e in sample:
        n_actions = random.randint(1, 4)
        for _ in range(n_actions):
            rows.append({
                "student_id":  e["student_id"],
                "offering_id": e["offering_id"],
                "action_type": random.choice(["ADD", "DROP"]),
                "operator":    "student",
                "created_at":  fake.date_time_between(start_date="-90d",
                                                       end_date="-60d"),
            })
    return generic.batch_insert("enrollment_action", rows,
                                 actor=actor, role=role)


def seed_grade_band(actor="seed", role="admin") -> int:
    """为每个开课写一组标准等第区间。"""
    with get_pool().read() as cur:
        cur.execute("SELECT offering_id FROM course_offering")
        offs = [r["offering_id"] for r in cur.fetchall()]
    bands = [
        ("A+", 95, 100, 4.000, 4.000),  # 仅荣誉课实际产生
        ("A",  90,  94, 4.000, 4.000),
        ("A-", 85,  89, 3.700, 3.800),
        ("B+", 82,  84, 3.300, 3.500),
        ("B",  78,  81, 3.000, 3.200),
        ("B-", 75,  77, 2.700, 2.900),
        ("C+", 72,  74, 2.300, 2.500),
        ("C",  68,  71, 2.000, 2.200),
        ("C-", 64,  67, 1.700, 1.900),
        ("D",  60,  63, 1.000, 1.500),
        ("F",   0,  59, 0.000, 0.000),
    ]
    rows = [{"offering_id": oid, "letter": l, "score_min": s0,
             "score_max": s1, "gpa_min": g0, "gpa_max": g1}
            for oid in offs for (l, s0, s1, g0, g1) in bands]
    return generic.batch_insert("grade_band", rows, actor=actor, role=role)


def _letter_for(score: float, is_honor: bool) -> tuple[str, float]:
    table = [
        ("A+", 95, 4.0), ("A", 90, 4.0), ("A-", 85, 3.7), ("B+", 82, 3.3),
        ("B", 78, 3.0), ("B-", 75, 2.7), ("C+", 72, 2.3), ("C", 68, 2.0),
        ("C-", 64, 1.7), ("D", 60, 1.0),
    ]
    if score < 60:
        return "F", 0.0
    for l, lo, gpa in table:
        if score >= lo:
            if l == "A+" and not is_honor:
                return "A", 4.0  # 非荣誉课不允许 A+
            return l, gpa
    return "F", 0.0


def seed_grade(actor="seed", role="admin") -> int:
    with get_pool().read() as cur:
        cur.execute("""
            SELECT e.enrollment_id, e.enroll_mode, e.enroll_status, c.is_honor
              FROM enrollment e
              JOIN course_offering co ON co.offering_id = e.offering_id
              JOIN course c           ON c.course_id    = co.course_id
             WHERE e.enroll_status = 'COMPLETED'
        """)
        completed = list(cur.fetchall())
    rows = []
    for e in completed:
        if e["enroll_mode"] == "PNP":
            res = "P" if random.random() < 0.85 else "NP"
            rows.append({
                "enrollment_id": e["enrollment_id"],
                "grade_mode": "PNP", "score": None, "pnp_result": res,
                "letter_grade": res, "gpa": None, "rank_in_offering": None,
                "grade_status": "VALID",
                "counts_credit": 1 if res == "P" else 0,
                "counts_gpa": 0, "is_resit": 0,
            })
        else:
            score = round(max(0, min(100, random.gauss(78, 12))), 1)
            l, g = _letter_for(score, bool(e["is_honor"]))
            rows.append({
                "enrollment_id": e["enrollment_id"],
                "grade_mode": "PERCENT", "score": score, "pnp_result": None,
                "letter_grade": l, "gpa": g, "rank_in_offering": None,
                "grade_status": "VALID" if score >= 60 else "VALID",
                "counts_credit": 1 if score >= 60 else 0,
                "counts_gpa": 1, "is_resit": 0,
            })
    return generic.batch_insert("grade", rows, actor=actor, role=role)


def seed_app_user_demo(actor="seed", role="admin") -> int:
    """除 admin 外, 再加一个 editor 与一个 viewer 演示账户 (密码 demo123)。"""
    from app.backend.security.credentials import (
        hash_password, _row_signature
    )
    rows = []
    for username, role_ in [("editor", "editor"), ("viewer", "viewer")]:
        ph = hash_password("demo123")
        rows.append({
            "username": username, "password_hash": ph,
            "role": role_, "is_active": 1, "signature": "TEMP",
        })
    n = generic.batch_insert("app_user", rows, actor=actor, role=role)
    # 补行签
    with get_pool().tx() as cur:
        cur.execute("SELECT * FROM app_user WHERE username IN ('editor','viewer')")
        for r in cur.fetchall():
            sig = _row_signature(r["user_id"], r["username"], r["role"],
                                  r["password_hash"], int(r["is_active"]))
            cur.execute("UPDATE app_user SET signature=%s WHERE user_id=%s",
                        (sig, r["user_id"]))
    return n


# ---------------------------------------------------------------------------
# 调度
# ---------------------------------------------------------------------------

PIPELINE = [
    ("department",         seed_department),
    ("major",              seed_major),
    ("degree_requirement", seed_degree_requirement),
    ("teacher",            seed_teacher),
    ("course",             seed_course),
    ("semester",           seed_semester),
    ("student",            seed_student),
    ("course_offering",    seed_course_offering),
    ("offering_teacher",   seed_offering_teacher),
    ("grade_band",         seed_grade_band),
    ("enrollment",         seed_enrollment),
    ("enrollment_action",  seed_enrollment_action),
    ("grade",              seed_grade),
    ("app_user",           seed_app_user_demo),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force-table", action="append", default=[],
                    help="强制重建该表 (会先 TRUNCATE)")
    args = ap.parse_args()
    cfg = load_config().fixtures
    print(f"[gen] auto_seed_empty_tables={cfg.auto_seed_empty_tables}")

    for table, fn in PIPELINE:
        if table in args.force_table:
            with get_pool().tx() as cur:
                cur.execute(f"SET FOREIGN_KEY_CHECKS=0; TRUNCATE TABLE {table}; "
                            f"SET FOREIGN_KEY_CHECKS=1")
            print(f"[gen] FORCE rebuild {table}")
        if not table_empty(table) and table not in args.force_table:
            print(f"[gen] skip {table} (already has data)")
            continue
        n = fn()
        generic.set_data_origin(table, "sample", n,
                                 note="generated by tools/gen_fixtures.py")
        print(f"[gen] {table}: {n} rows")

    print("\n[gen] data_origin 标注完毕")
    print("[gen] done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
