# 设计文档 — 学生成绩数据库系统

> 本文按评分细则 6 项展开:
> 1. 介绍题目  2. 需求分析  3. 数据库设计  4. 模型图  5. 功能设计  6. 模块划分

---

## 1. 介绍题目

来源: 《数据库案例设计以及实现要求-2026》第四题 **学生成绩数据库**.
目标: 设计并实现一个用于管理学生成绩的数据库系统, 涵盖学生、院系、专业、课程、教师、成绩等信息的存储、管理、查询.

我方在保留官方 6 个核心实体的基础上, 按 todo 详细需求扩展为 18 张业务表 + 1 张元数据表,
覆盖以下不在原始题面但在 todo 中要求的能力:

- 选课 / 退课 / 期中退课 / 重修 / PNP 业务规则
- 前两周自由选课操作日志
- bcrypt + HMAC 三角色账户系统
- JSON 操作日志, 后端写入, 前端可查
- 课程旧代码别名 / 院系变动摘要
- 等第区间 (per-offering) 与原始百分制双轨并存
- 数据来源元数据 (real / sample / imported)

不增加额外历史快照表 — 当前数据准确为主, 与课程 3NF 教学保持一致.

## 2. 需求分析

### 2.1 实体与属性

| 实体 (官方 6) | 关键属性 |
|---------------|----------|
| 学生 Student | 学号 / 姓名 / 身份证号 / 宿舍 / 家庭地址 / 电话 / 出生日期 / 性别 / 年级 / 当前专业 / 辅修院系 / 学位等级 / 状态 |
| 院系 Department | 代码 / 名称 / 办公地点 / 电话 / 状态 |
| 专业 Major | 代码 / 名称 / 所属院系 / 状态 (学位学分要求拆出独立表) |
| 课程 Course | 代码 / 名称 / 说明 / 学时 / 学分 / 学位等级 / 开课院系 / 是否荣誉 / 是否开放 PNP / 成绩模式 / 状态 |
| 教师 Teacher | 工号 / 姓名 / 所属院系 / 职称 / 状态 |
| 成绩 Grade | 选课 / 成绩模式 / 百分制 / PNP / 等第 / 绩点 / 排名 / 状态 / 是否计学分 / 是否计 GPA / 是否重修 |

### 2.2 扩展实体 (12 张)

| 表 | 用途 |
|----|------|
| degree_requirement   | 专业 × 学位等级 → 要求学分 (从 major 拆出, 满足 3NF) |
| course_alias         | 课程旧代码别名 (代码变更后旧查询仍可用) |
| department_change_note | 院系合并/拆分/关闭事件摘要 |
| semester             | 学期主表 (开始 / 结束日期) |
| course_offering      | 课程在某学期的具体开课实例 |
| offering_teacher     | 开课-教师 m:n 关系 |
| enrollment           | 学生当前有效选课 (UNIQUE student_id+offering_id) |
| enrollment_action    | 前两周选退操作过程日志 |
| grade_band           | 任课老师设置的分数段→等第→绩点区间 |
| app_user             | 账户 (bcrypt + HMAC 行签名) |
| auth_session         | 登录会话 (token sha256) |
| audit_log_index      | 操作日志索引 (jsonl 在 logs/ 目录) |
| data_origin (元数据) | 每张业务表的数据来源标注 |

### 2.3 实体间关系

| 关系 | 类型 | 落点 |
|------|------|------|
| 院系-专业        | 1:n | major.dept_id |
| 院系-教师        | 1:n | teacher.dept_id |
| 院系-课程        | 1:n | course.dept_id |
| 院系-学生(辅修)  | 1:n | student.minor_dept_id |
| 专业-学生(主修)  | 1:n | student.major_id |
| 课程-开课实例    | 1:n | course_offering.course_id |
| 学期-开课实例    | 1:n | course_offering.semester_id |
| 教师-开课        | m:n | offering_teacher (复合 PK) |
| 学生-开课        | m:n | enrollment (复合 UK) |
| 选课-成绩        | 1:1 | grade.enrollment_id UNIQUE |

### 2.4 业务流程 (用户可执行的功能)

```
登录(三角色) → 主窗口
  ├── 18 张表浏览 (左导航)
  │     ├── 学生 / 教师 / 院系 / 专业 / 课程 / 学期 / 开课 / 选课 / 成绩 / ...
  │     └── 工具栏: 刷新/新增/删除/保存/丢弃/缩放
  ├── ER 图弹窗 (Ctrl+E)
  ├── 自定义 SQL (M2)
  ├── 操作日志查询 (M2)
  ├── CSV/XLSX 导入导出 (M2)
  ├── 备份还原 (M3)
  └── 注销
```

## 3. 数据库设计

### 3.1 范式

所有 18 张业务表满足 **3NF**:

- 每个非主属性直接依赖候选键
- 没有传递依赖 (例: student.major_id 决定主修院系, 故不在 student 表重复存 dept_id)
- 多值属性 (各学位学分要求) 拆为 degree_requirement 独立表

### 3.2 主键 / 外键 / 唯一键 (评分硬指标)

- 主键: 全部 `BIGINT UNSIGNED AUTO_INCREMENT`, 复合 PK 用于纯关系表 (offering_teacher, degree_requirement, grade_band)
- 业务唯一: dept_code / major_code / student_no / id_card / staff_no / course_code / old_code / semester.name 全部 `UNIQUE`
- 外键: 全部 `ON DELETE RESTRICT ON UPDATE CASCADE`; 软删走 status 字段, 不物理删

### 3.3 完整性约束 (评分硬指标)

| 类别 | 实现 |
|------|------|
| 实体完整性 | PK 非空 + AUTO_INCREMENT, 业务编号 UNIQUE |
| 参照完整性 | 全部 FK 显式声明, RESTRICT 阻止悬空 |
| 检查完整性 | `chk_grade_score CHECK (score BETWEEN 0 AND 100)`, `chk_grade_mode CHECK (...互斥...)`, `chk_course_credits CHECK (credits > 0)` 等 |
| 用户自定义 | `gender ENUM('M','F','U')`, `degree_level ENUM('本科','硕士','博士')`, `enroll_status ENUM(...)`, 跨表规则 (PNP 16 学分上限 / A+ 30% 上限) 在后端服务层 |

### 3.4 索引

- 学号 / 课程代码 / 教师工号 / 院系代码: `UNIQUE`
- 选课查询: `enrollment(student_id, offering_id)` UNIQUE + `(offering_id)`
- 成绩查询: `grade(offering_id, score)`
- 日志查询: `audit_log_index(actor, ts) / (table_name, ts)`
- 学期-课程: `course_offering(semester_id, course_id)` 复合

### 3.5 字符集 / 引擎 / 类型规约 (来自课程 notes)

- 字符集 `utf8mb4_0900_ai_ci`, 引擎 `InnoDB`
- 学分 / 分数 / 绩点 全部 `DECIMAL` (避免 FLOAT 漂移)
- 性别 `ENUM` (避免 SET 违 1NF)
- 出生日期存 `DATE` (不存 age, 避免每年漂)
- 时间列 `TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP`

## 4. 模型图

详见 `docs/er/schema.mmd` (mermaid 源) + `docs/er/schema.png` (base 渲染).
润色版 `docs/er/schema_polished.png` 存在时, 前端 ER 图弹窗自动优先加载.

渲染指南: `docs/er/POLISH_GUIDE.md`.

## 5. 功能设计

### 5.1 已实现 (M1)

- 三角色登录 (admin / editor / viewer); bcrypt + HMAC 行签
- 主窗口左侧导航 19 个表, 中央 stacked 视图
- 配置驱动通用表格 (`GenericTableView`):
  - 列宽可拖、行高可调、表格内容缩放按钮 + Ctrl+滚轮
  - 上下左右键 / WASD 单元格切换
  - 选中蓝色细框
  - 样例数据橙色横幅 / 已导入数据绿色横幅
- ER 图独立弹窗 (Ctrl+E), 缩放 / 适应 / 另存
- JSON 操作日志切面 (logs/YYYY-MM-DD.jsonl + audit_log_index 索引表)
- 数据来源元数据机制 (real / sample / imported)
- 键盘快捷键: Ctrl+E ER 图; F5 刷新当前表; Ctrl+Q 退出
- 启动自检: MySQL 端口 ping; admin 账户首次自动初始化

### 5.2 已实现 (M2)

- 表格双击编辑 + 黄色脏单元格 + QUndoStack 撤销/恢复 (Ctrl+Z/Y)
- 「保存 Ctrl+S」按钮 = 一次事务批量提交; 提交后清栈
- 切页/关闭前若 dirty>0 弹窗 (保存/丢弃/取消)
- 新增按钮: ColSpec 驱动表单 (enum→QComboBox, fk→下拉加载选项, 日期→QDateEdit)
- 删除按钮: 软删 (status=0); 无 status 字段则物理删
- CSV / XLSX 导入向导 (列名匹配 + 必填校验 + 事务批量); 导出双向
- 自定义 SQL 控制台 Ctrl+L: admin 全权, editor 禁 DROP/TRUNCATE/GRANT/REVOKE, viewer 仅 SELECT
- 操作日志查询页: 按 actor/table/action/时间窗 + admin 可查全部 / 其他仅自己
- ER 图润色版自动回灌 (`schema_polished.png` 存在则优先加载)
- 真实课程数据导入器 `tools/import_md_table.py`: 解析"_识别.md", 自动建 dept/teacher/course/offering/offering_teacher 并标 `data_origin='imported'`

### 5.3 计划 (M3)

- mysqldump 一键备份 / 一键回退
- `SHOW PROCESSLIST` 监控 + KILL 僵死连接
- 慢 SQL 进度条
- GPA 视图 (`sql/views/student_gpa.sql`)
- 打包 zip + 内置 embeddable Python

## 6. 模块划分

```
app/
├── config.py             读 config.toml; 单例; 全局路径
├── backend/
│   ├── db.py             PyMySQL 连接池 + 事务/读上下文
│   ├── audit.py          JSON 日志切面 (写 jsonl + 索引行)
│   ├── security/
│   │   └── credentials.py  bcrypt + HMAC + 会话 token
│   └── repos/
│       ├── specs.py      18+1 表的 ColSpec/TableSpec 配置
│       └── generic.py    通用 CRUD (用 specs 驱动)
└── ui/
    ├── login_dialog.py
    ├── main_window.py    QMainWindow + 左导航 + 中央 stacked + 菜单
    ├── widgets/
    │   └── editable_table.py    GenericModel + TablePage (横幅/工具栏/键盘)
    └── dialogs/
        └── er_diagram_dialog.py 独立 QDialog + QPixmap 缩放
```

调用关系:

```
app.__main__ ─→ app.config (load_config)
              ─→ app.backend.db (DBPool)
              ─→ app.backend.security.credentials (login/admin init)
              ─→ app.ui.login_dialog → app.ui.main_window
                  ↓
                  app.ui.widgets.editable_table → app.backend.repos.generic → backend.db
                                                                            → backend.audit
                  app.ui.dialogs.er_diagram_dialog (读 docs/er/*.png)
```

每个子目录 `readme_for_<dirname>.md` 列出该目录每文件的作用 / 被谁调用 / 调用谁.

## 附: 设计取舍

| 取舍 | 选择 | 理由 |
|------|------|------|
| 是否引 ORM | 否 (dataclass + 手写 SQL) | 评分要求展示 SQL 能力; ORM 遮蔽; 学期级业务规则纯 Python 服务层更直观 |
| 是否走 FastAPI | 否 (库形式直调) | 单机桌面零部署; 少 JSON 序列化层 |
| 撤销 vs 自动提交 | 手动保存 + QUndoStack | 用户明确要求; 撤销栈语义干净 (保存后 clear) |
| ER 图渲染 | mermaid base + 用户 AI 润色 | todo 要求"不用 python 直接绘制保存", 由外部工具生成符合精神 |
| 历史表 | 不做完整版本表 | 只记 course_alias / department_change_note 摘要; 与课程 3NF 教学一致, 避免双写一致性问题 |
| PDF 提取失败 | 生成器兜底 + OCR md 通道 | PDF 多为非标准表格, 手 OCR 转 markdown 后由 import_md_table.py 灌入 |
