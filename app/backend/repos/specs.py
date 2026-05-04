"""所有业务表的列规格 — 由 GenericRepo 与 GenericTableView 共用。

每个 ColSpec:
  name        SQL 列名
  label       中文显示名 (前端表头)
  width       默认列宽 (px), 0 表示自适应
  editable    在前端是否可编辑 (主键/审计列 False)
  sensitive   敏感字段 (viewer 角色脱敏成 ***)
  fk          (table, value_col, label_col) — 若是外键, 前端展示下拉
  enum        枚举可选值 (前端下拉)
  required    NOT NULL 必填
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ColSpec:
    name: str
    label: str
    width: int = 120
    editable: bool = True
    sensitive: bool = False
    fk: tuple[str, str, str] | None = None
    enum: tuple[str, ...] | None = None
    required: bool = False
    is_pk: bool = False


@dataclass(frozen=True)
class TableSpec:
    name: str          # SQL 表名
    label: str         # 中文显示名 (导航栏)
    pk: str            # 主键列
    cols: list[ColSpec] = field(default_factory=list)
    order_by: str = ""

    def col_names(self) -> list[str]:
        return [c.name for c in self.cols]

    def by_name(self, n: str) -> ColSpec | None:
        for c in self.cols:
            if c.name == n:
                return c
        return None


# ---------------------------------------------------------------------------
# 表清单 (与 sql/ddl/001_schema.sql 一一对应)
# ---------------------------------------------------------------------------

SPECS: dict[str, TableSpec] = {}


def _add(spec: TableSpec) -> None:
    SPECS[spec.name] = spec


_AUDIT_COLS = [
    ColSpec("created_at", "创建时间", 150, editable=False),
    ColSpec("updated_at", "更新时间", 150, editable=False),
]

_STATUS_BUSINESS = ColSpec(
    "status", "状态", 80, enum=("0", "1", "2", "3"),
)


_add(TableSpec(
    name="department", label="院系", pk="dept_id", order_by="dept_code",
    cols=[
        ColSpec("dept_id",         "ID",       60,  editable=False, is_pk=True),
        ColSpec("dept_code",       "院系代码", 90,  required=True),
        ColSpec("dept_name",       "院系名称", 180, required=True),
        ColSpec("office_location", "办公地点", 180),
        ColSpec("phone",           "电话",     120),
        _STATUS_BUSINESS,
        *_AUDIT_COLS,
    ],
))

_add(TableSpec(
    name="major", label="专业", pk="major_id", order_by="major_code",
    cols=[
        ColSpec("major_id",   "ID",       60,  editable=False, is_pk=True),
        ColSpec("major_code", "专业代码", 90,  required=True),
        ColSpec("major_name", "专业名称", 180, required=True),
        ColSpec("dept_id",    "所属院系", 140, required=True,
                fk=("department", "dept_id", "dept_name")),
        _STATUS_BUSINESS,
        *_AUDIT_COLS,
    ],
))

_add(TableSpec(
    name="degree_requirement", label="学位学分要求", pk="major_id",
    order_by="major_id, degree_level",
    cols=[
        ColSpec("major_id", "专业", 140, required=True, is_pk=True,
                fk=("major", "major_id", "major_name")),
        ColSpec("degree_level",     "学位等级", 80,  required=True, is_pk=True,
                enum=("本科", "硕士", "博士")),
        ColSpec("required_credits", "要求学分", 100, required=True),
        *_AUDIT_COLS,
    ],
))

_add(TableSpec(
    name="student", label="学生", pk="student_id", order_by="student_no",
    cols=[
        ColSpec("student_id",    "ID",       60,  editable=False, is_pk=True),
        ColSpec("student_no",    "学号",     110, required=True),
        ColSpec("name",          "姓名",     90,  required=True),
        ColSpec("id_card",       "身份证号", 170, required=True, sensitive=True),
        ColSpec("dorm",          "宿舍",     100),
        ColSpec("address",       "家庭地址", 200, sensitive=True),
        ColSpec("phone",         "电话",     120, sensitive=True),
        ColSpec("birth_date",    "出生日期", 110),
        ColSpec("gender",        "性别",     70,  enum=("M", "F", "U")),
        ColSpec("grade_year",    "年级",     70,  required=True),
        ColSpec("major_id",      "当前专业", 140, required=True,
                fk=("major", "major_id", "major_name")),
        ColSpec("minor_dept_id", "辅修院系", 140,
                fk=("department", "dept_id", "dept_name")),
        ColSpec("degree_level",  "学位等级", 80,
                enum=("本科", "硕士", "博士"), required=True),
        ColSpec("status",        "状态",     70,  enum=("0", "1", "2", "3")),
        *_AUDIT_COLS,
    ],
))

_add(TableSpec(
    name="teacher", label="教师", pk="teacher_id", order_by="staff_no",
    cols=[
        ColSpec("teacher_id", "ID",       60,  editable=False, is_pk=True),
        ColSpec("staff_no",   "工号",     90,  required=True),
        ColSpec("name",       "姓名",     90,  required=True),
        ColSpec("dept_id",    "所属院系", 140, required=True,
                fk=("department", "dept_id", "dept_name")),
        ColSpec("title",      "职称",     90),
        _STATUS_BUSINESS,
        *_AUDIT_COLS,
    ],
))

_add(TableSpec(
    name="course", label="课程", pk="course_id", order_by="course_code",
    cols=[
        ColSpec("course_id",    "ID",       60,  editable=False, is_pk=True),
        ColSpec("course_code",  "课程代码", 100, required=True),
        ColSpec("course_name",  "课程名称", 180, required=True),
        ColSpec("description",  "课程说明", 240),
        ColSpec("class_hours",  "学时",     70,  required=True),
        ColSpec("credits",      "学分",     70,  required=True),
        ColSpec("degree_level", "学位等级", 80,
                enum=("本科", "硕士", "博士"), required=True),
        ColSpec("dept_id",      "开课院系", 140, required=True,
                fk=("department", "dept_id", "dept_name")),
        ColSpec("is_honor",     "荣誉课",   70,  enum=("0", "1")),
        ColSpec("allow_pnp",    "开放PNP",  80,  enum=("0", "1")),
        ColSpec("grade_mode",   "成绩模式", 90,
                enum=("PERCENT", "PNP", "BOTH"), required=True),
        _STATUS_BUSINESS,
        *_AUDIT_COLS,
    ],
))

_add(TableSpec(
    name="course_alias", label="课程别名", pk="alias_id", order_by="course_id",
    cols=[
        ColSpec("alias_id",  "ID",       60, editable=False, is_pk=True),
        ColSpec("course_id", "当前课程", 140, required=True,
                fk=("course", "course_id", "course_name")),
        ColSpec("old_code",  "旧课程代码", 110, required=True),
        ColSpec("note",      "说明",     220),
        ColSpec("created_at", "创建时间", 150, editable=False),
    ],
))

_add(TableSpec(
    name="department_change_note", label="院系变动", pk="note_id",
    order_by="change_date DESC",
    cols=[
        ColSpec("note_id",     "ID",     60,  editable=False, is_pk=True),
        ColSpec("change_type", "变动类型", 90, required=True,
                enum=("合并", "拆分", "更名", "关闭", "新建")),
        ColSpec("summary",     "摘要",   320, required=True),
        ColSpec("change_date", "变动日期", 110, required=True),
        ColSpec("created_at",  "创建时间", 150, editable=False),
    ],
))

_add(TableSpec(
    name="semester", label="学期", pk="semester_id", order_by="start_date DESC",
    cols=[
        ColSpec("semester_id", "ID",     60,  editable=False, is_pk=True),
        ColSpec("name",        "学期名", 130, required=True),
        ColSpec("start_date",  "开始日期", 110, required=True),
        ColSpec("end_date",    "结束日期", 110, required=True),
        ColSpec("created_at",  "创建时间", 150, editable=False),
    ],
))

_add(TableSpec(
    name="course_offering", label="开课", pk="offering_id",
    order_by="semester_id DESC, course_id",
    cols=[
        ColSpec("offering_id",  "ID",     60,  editable=False, is_pk=True),
        ColSpec("course_id",    "课程",   180, required=True,
                fk=("course", "course_id", "course_name")),
        ColSpec("semester_id",  "学期",   120, required=True,
                fk=("semester", "semester_id", "name")),
        ColSpec("section_no",   "班号",   70,  required=True),
        ColSpec("capacity",     "容量",   70,  required=True),
        ColSpec("free_period_start",   "选课开始", 150, required=True),
        ColSpec("free_period_end",     "选课结束", 150, required=True),
        ColSpec("withdrawal_deadline", "退课截止", 150, required=True),
        ColSpec("pass_threshold", "及格线", 80,  required=True),
        ColSpec("grade_mode",   "成绩模式", 90, enum=("PERCENT", "PNP")),
        _STATUS_BUSINESS,
        *_AUDIT_COLS,
    ],
))

_add(TableSpec(
    name="offering_teacher", label="开课-教师", pk="offering_id",
    order_by="offering_id, teacher_id",
    cols=[
        ColSpec("offering_id", "开课", 140, required=True, is_pk=True,
                fk=("course_offering", "offering_id", "offering_id")),
        ColSpec("teacher_id",  "教师", 140, required=True, is_pk=True,
                fk=("teacher", "teacher_id", "name")),
        ColSpec("role",        "角色", 90,
                enum=("主讲", "合讲", "助教")),
        ColSpec("created_at",  "创建时间", 150, editable=False),
    ],
))

_add(TableSpec(
    name="enrollment", label="选课", pk="enrollment_id",
    order_by="enrollment_id DESC",
    cols=[
        ColSpec("enrollment_id", "ID",   60,  editable=False, is_pk=True),
        ColSpec("student_id",   "学生", 140, required=True,
                fk=("student", "student_id", "name")),
        ColSpec("offering_id",  "开课", 140, required=True,
                fk=("course_offering", "offering_id", "offering_id")),
        ColSpec("enroll_status", "状态", 110, required=True,
                enum=("FREE", "LOCKED", "WITHDRAWN_MID", "COMPLETED", "CANCELLED")),
        ColSpec("enroll_mode",  "模式", 80,  enum=("PERCENT", "PNP")),
        ColSpec("last_select_at", "最后选择", 150),
        ColSpec("locked_at",    "锁定时间", 150),
        ColSpec("withdrawn_at", "退课时间", 150),
        *_AUDIT_COLS,
    ],
))

_add(TableSpec(
    name="enrollment_action", label="选课操作日志", pk="action_id",
    order_by="created_at DESC",
    cols=[
        ColSpec("action_id",   "ID",     60,  editable=False, is_pk=True),
        ColSpec("student_id",  "学生", 140, required=True,
                fk=("student", "student_id", "name")),
        ColSpec("offering_id", "开课", 140, required=True,
                fk=("course_offering", "offering_id", "offering_id")),
        ColSpec("action_type", "类型",  80, required=True, enum=("ADD", "DROP")),
        ColSpec("operator",    "操作者", 100),
        ColSpec("created_at",  "时间",  150, editable=False),
    ],
))

_add(TableSpec(
    name="grade_band", label="等第区间", pk="offering_id",
    order_by="offering_id, score_min DESC",
    cols=[
        ColSpec("offering_id", "开课", 140, required=True, is_pk=True,
                fk=("course_offering", "offering_id", "offering_id")),
        ColSpec("letter",      "等第", 70,  required=True, is_pk=True,
                enum=("A+","A","A-","B+","B","B-","C+","C","C-","D","F")),
        ColSpec("score_min",   "分数下限", 80,  required=True),
        ColSpec("score_max",   "分数上限", 80,  required=True),
        ColSpec("gpa_min",     "绩点下限", 80,  required=True),
        ColSpec("gpa_max",     "绩点上限", 80,  required=True),
        *_AUDIT_COLS,
    ],
))

_add(TableSpec(
    name="grade", label="成绩", pk="grade_id", order_by="grade_id DESC",
    cols=[
        ColSpec("grade_id",     "ID",     60,  editable=False, is_pk=True),
        ColSpec("enrollment_id","选课", 100, required=True),
        ColSpec("grade_mode",   "模式", 80,  required=True, enum=("PERCENT", "PNP")),
        ColSpec("score",        "百分制", 70),
        ColSpec("pnp_result",   "PNP",  60,  enum=("P", "NP")),
        ColSpec("letter_grade", "等第", 70,
                enum=("A+","A","A-","B+","B","B-","C+","C","C-","D","F","P","NP")),
        ColSpec("gpa",          "绩点", 70),
        ColSpec("rank_in_offering", "排名", 70),
        ColSpec("grade_status", "状态", 100, required=True,
                enum=("VALID", "INVALID", "RESIT_COVERED")),
        ColSpec("counts_credit", "计学分", 70, enum=("0", "1")),
        ColSpec("counts_gpa",    "计GPA",  70, enum=("0", "1")),
        ColSpec("is_resit",      "重修",   60, enum=("0", "1")),
        ColSpec("recorded_at",   "录入时间", 150, editable=False),
        ColSpec("updated_at",    "更新时间", 150, editable=False),
    ],
))

_add(TableSpec(
    name="app_user", label="账户", pk="user_id", order_by="user_id",
    cols=[
        ColSpec("user_id",       "ID",     60,  editable=False, is_pk=True),
        ColSpec("username",      "用户名", 130, required=True),
        ColSpec("password_hash", "密码哈希", 240, editable=False, sensitive=True),
        ColSpec("role",          "角色",   90,  required=True,
                enum=("admin", "editor", "viewer")),
        ColSpec("guest_type",    "访客类型", 110),
        ColSpec("is_active",     "启用",   60,  enum=("0", "1")),
        ColSpec("signature",     "行签",   100, editable=False, sensitive=True),
        ColSpec("last_login_at", "上次登录", 150, editable=False),
        *_AUDIT_COLS,
    ],
))

_add(TableSpec(
    name="auth_session", label="会话", pk="session_id",
    order_by="session_id DESC",
    cols=[
        ColSpec("session_id",  "ID",   60,  editable=False, is_pk=True),
        ColSpec("user_id",     "用户", 80,  fk=("app_user", "user_id", "username")),
        ColSpec("token_hash",  "Token哈希", 200, editable=False, sensitive=True),
        ColSpec("issued_at",   "签发", 150, editable=False),
        ColSpec("expires_at",  "过期", 150),
        ColSpec("revoked_at",  "撤销", 150),
        ColSpec("client_info", "客户端", 200),
    ],
))

_add(TableSpec(
    name="audit_log_index", label="审计索引", pk="log_id",
    order_by="log_id DESC",
    cols=[
        ColSpec("log_id",        "ID",    60, editable=False, is_pk=True),
        ColSpec("actor",         "操作者", 100, editable=False),
        ColSpec("role",          "角色",  80,  editable=False),
        ColSpec("table_name",    "表",    120, editable=False),
        ColSpec("action",        "动作",  90,  editable=False),
        ColSpec("target_pk",     "目标PK", 90,  editable=False),
        ColSpec("affected_rows", "影响行", 80,  editable=False),
        ColSpec("log_file",      "日志文件", 130, editable=False),
        ColSpec("file_offset",   "偏移量", 90,  editable=False),
        ColSpec("ts",            "时间",  150, editable=False),
    ],
))


# 元数据表 (前端只读, 不在导航栏直接呈现, 通过样例横幅查询)
_add(TableSpec(
    name="data_origin", label="数据来源", pk="table_name", order_by="table_name",
    cols=[
        ColSpec("table_name",       "表名",     140, editable=False, is_pk=True),
        ColSpec("source",           "来源",     90,  enum=("real", "sample", "imported")),
        ColSpec("generated_at",     "生成时间", 150, editable=False),
        ColSpec("sample_row_count", "样例行数", 100),
        ColSpec("note",             "说明",     240),
    ],
))


# 导航栏顺序 — 18 张业务表 + 1 张元数据
NAV_ORDER: list[str] = [
    "department", "major", "degree_requirement",
    "student", "teacher",
    "course", "course_alias", "department_change_note",
    "semester", "course_offering", "offering_teacher",
    "enrollment", "enrollment_action",
    "grade_band", "grade",
    "app_user", "auth_session", "audit_log_index",
    "data_origin",
]
