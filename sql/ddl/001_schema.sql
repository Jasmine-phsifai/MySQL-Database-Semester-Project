-- ============================================================================
-- 学生成绩数据库 - 全表 Schema (3NF, MySQL 8.0+)
-- 满足: 实体完整性 / 参照完整性 / 用户自定义检查完整性
-- 字符集: utf8mb4_0900_ai_ci   引擎: InnoDB   主键: BIGINT UNSIGNED
-- 业务表 18 张 + 元数据表 1 张 = 19 张
-- ============================================================================

CREATE DATABASE IF NOT EXISTS student_grading
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;
USE student_grading;

SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------------------------------------------------------
-- 1. department  院系
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS department;
CREATE TABLE department (
    dept_id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    dept_code        VARCHAR(20)  NOT NULL,
    dept_name        VARCHAR(100) NOT NULL,
    office_location  VARCHAR(255),
    phone            VARCHAR(20),
    status           TINYINT      NOT NULL DEFAULT 1
                     COMMENT '1=有效, 0=关闭, 2=合并停用',
    created_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                  ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (dept_id),
    UNIQUE KEY uk_department_code (dept_code),
    UNIQUE KEY uk_department_name (dept_name),
    CONSTRAINT chk_department_status CHECK (status IN (0,1,2))
) ENGINE=InnoDB COMMENT='院系';

-- ---------------------------------------------------------------------------
-- 2. major  专业
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS major;
CREATE TABLE major (
    major_id     BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    major_code   VARCHAR(20)  NOT NULL,
    major_name   VARCHAR(100) NOT NULL,
    dept_id      BIGINT UNSIGNED NOT NULL,
    status       TINYINT      NOT NULL DEFAULT 1,
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                              ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (major_id),
    UNIQUE KEY uk_major_code (major_code),
    KEY idx_major_dept (dept_id),
    CONSTRAINT fk_major_dept FOREIGN KEY (dept_id)
        REFERENCES department(dept_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_major_status CHECK (status IN (0,1,2))
) ENGINE=InnoDB COMMENT='专业';

-- ---------------------------------------------------------------------------
-- 3. degree_requirement  专业学位等级学分要求（拆分以满足 3NF）
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS degree_requirement;
CREATE TABLE degree_requirement (
    major_id          BIGINT UNSIGNED NOT NULL,
    degree_level      ENUM('本科','硕士','博士') NOT NULL,
    required_credits  DECIMAL(5,1) NOT NULL,
    created_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                   ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (major_id, degree_level),
    CONSTRAINT fk_degree_req_major FOREIGN KEY (major_id)
        REFERENCES major(major_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_degree_req_credits CHECK (required_credits > 0)
) ENGINE=InnoDB COMMENT='专业-学位等级-要求学分(3NF 拆分)';

-- ---------------------------------------------------------------------------
-- 4. student  学生
-- 注: 当前主修院系由 major.dept_id 推导, 不在此表重复存储, 避免传递依赖
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS student;
CREATE TABLE student (
    student_id     BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    student_no     VARCHAR(20)  NOT NULL COMMENT '学号',
    name           VARCHAR(50)  NOT NULL,
    id_card        VARCHAR(18)  NOT NULL,
    dorm           VARCHAR(50),
    address        VARCHAR(255),
    phone          VARCHAR(20),
    birth_date     DATE,
    gender         ENUM('M','F','U') NOT NULL DEFAULT 'U',
    grade_year     SMALLINT     NOT NULL,
    major_id       BIGINT UNSIGNED NOT NULL,
    minor_dept_id  BIGINT UNSIGNED NULL COMMENT '辅修院系, 可空',
    degree_level   ENUM('本科','硕士','博士') NOT NULL DEFAULT '本科',
    status         TINYINT      NOT NULL DEFAULT 1
                                COMMENT '1=在读, 0=休学, 2=毕业, 3=退学',
    created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (student_id),
    UNIQUE KEY uk_student_no (student_no),
    UNIQUE KEY uk_student_idcard (id_card),
    KEY idx_student_major (major_id),
    KEY idx_student_minor (minor_dept_id),
    CONSTRAINT fk_student_major FOREIGN KEY (major_id)
        REFERENCES major(major_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_student_minor_dept FOREIGN KEY (minor_dept_id)
        REFERENCES department(dept_id) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_student_grade_year CHECK (grade_year BETWEEN 1900 AND 2200),
    CONSTRAINT chk_student_status     CHECK (status IN (0,1,2,3))
) ENGINE=InnoDB COMMENT='学生';

-- ---------------------------------------------------------------------------
-- 5. teacher  教师
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS teacher;
CREATE TABLE teacher (
    teacher_id   BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    staff_no     VARCHAR(20)  NOT NULL COMMENT '工号',
    name         VARCHAR(50)  NOT NULL,
    dept_id      BIGINT UNSIGNED NOT NULL,
    title        VARCHAR(30)              COMMENT '教授/副教授/讲师等',
    status       TINYINT      NOT NULL DEFAULT 1,
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                              ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (teacher_id),
    UNIQUE KEY uk_teacher_staff_no (staff_no),
    KEY idx_teacher_dept (dept_id),
    CONSTRAINT fk_teacher_dept FOREIGN KEY (dept_id)
        REFERENCES department(dept_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_teacher_status CHECK (status IN (0,1,2))
) ENGINE=InnoDB COMMENT='教师';

-- ---------------------------------------------------------------------------
-- 6. course  课程
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS course;
CREATE TABLE course (
    course_id     BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    course_code   VARCHAR(30)  NOT NULL COMMENT '当前课程代码',
    course_name   VARCHAR(100) NOT NULL,
    description   TEXT,
    class_hours   SMALLINT     NOT NULL,
    credits       DECIMAL(3,1) NOT NULL,
    degree_level  ENUM('本科','硕士','博士') NOT NULL DEFAULT '本科',
    dept_id       BIGINT UNSIGNED NOT NULL COMMENT '开课院系',
    is_honor      TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '是否荣誉课',
    allow_pnp     TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '是否开放 PNP',
    grade_mode    ENUM('PERCENT','PNP','BOTH') NOT NULL DEFAULT 'PERCENT',
    status        TINYINT      NOT NULL DEFAULT 1,
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                               ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (course_id),
    UNIQUE KEY uk_course_code (course_code),
    KEY idx_course_dept (dept_id),
    CONSTRAINT fk_course_dept FOREIGN KEY (dept_id)
        REFERENCES department(dept_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_course_credits CHECK (credits > 0 AND credits <= 20),
    CONSTRAINT chk_course_hours   CHECK (class_hours > 0),
    CONSTRAINT chk_course_status  CHECK (status IN (0,1,2))
) ENGINE=InnoDB COMMENT='课程';

-- ---------------------------------------------------------------------------
-- 7. course_alias  课程旧代码别名
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS course_alias;
CREATE TABLE course_alias (
    alias_id    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    course_id   BIGINT UNSIGNED NOT NULL,
    old_code    VARCHAR(30)  NOT NULL,
    note        VARCHAR(255),
    created_at  TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (alias_id),
    UNIQUE KEY uk_course_alias_old (old_code),
    KEY idx_course_alias_course (course_id),
    CONSTRAINT fk_course_alias_course FOREIGN KEY (course_id)
        REFERENCES course(course_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='课程旧代码别名';

-- ---------------------------------------------------------------------------
-- 8. department_change_note  院系变动摘要
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS department_change_note;
CREATE TABLE department_change_note (
    note_id      BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    change_type  ENUM('合并','拆分','更名','关闭','新建') NOT NULL,
    summary      VARCHAR(500) NOT NULL,
    change_date  DATE         NOT NULL,
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (note_id),
    KEY idx_dept_change_date (change_date)
) ENGINE=InnoDB COMMENT='院系变动摘要(只记摘要, 不做自动迁移)';

-- ---------------------------------------------------------------------------
-- 9. semester  学期
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS semester;
CREATE TABLE semester (
    semester_id  BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    name         VARCHAR(50)  NOT NULL COMMENT '如 2025-2026-1',
    start_date   DATE         NOT NULL,
    end_date     DATE         NOT NULL,
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (semester_id),
    UNIQUE KEY uk_semester_name (name),
    CONSTRAINT chk_semester_dates CHECK (end_date > start_date)
) ENGINE=InnoDB COMMENT='学期';

-- ---------------------------------------------------------------------------
-- 10. course_offering  开课实例
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS course_offering;
CREATE TABLE course_offering (
    offering_id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    course_id            BIGINT UNSIGNED NOT NULL,
    semester_id          BIGINT UNSIGNED NOT NULL,
    section_no           VARCHAR(10)  NOT NULL DEFAULT '01' COMMENT '班号',
    capacity             SMALLINT     NOT NULL DEFAULT 100,
    free_period_start    DATETIME     NOT NULL,
    free_period_end      DATETIME     NOT NULL,
    withdrawal_deadline  DATETIME     NOT NULL COMMENT '期中退课截止时间',
    pass_threshold       DECIMAL(5,2) NOT NULL DEFAULT 60.00 COMMENT '及格线, 不锁死 60',
    grade_mode           ENUM('PERCENT','PNP') NOT NULL DEFAULT 'PERCENT',
    status               TINYINT      NOT NULL DEFAULT 1
                                       COMMENT '1=开放, 0=取消, 2=已结课',
    created_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                       ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (offering_id),
    UNIQUE KEY uk_offering_course_sem_section (course_id, semester_id, section_no),
    KEY idx_offering_semester (semester_id, course_id),
    CONSTRAINT fk_offering_course FOREIGN KEY (course_id)
        REFERENCES course(course_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_offering_semester FOREIGN KEY (semester_id)
        REFERENCES semester(semester_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_offering_capacity  CHECK (capacity > 0),
    CONSTRAINT chk_offering_threshold CHECK (pass_threshold BETWEEN 0 AND 100),
    CONSTRAINT chk_offering_periods   CHECK (free_period_end >  free_period_start
                                         AND withdrawal_deadline >= free_period_end)
) ENGINE=InnoDB COMMENT='开课实例';

-- ---------------------------------------------------------------------------
-- 11. offering_teacher  开课-教师 (m:n)
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS offering_teacher;
CREATE TABLE offering_teacher (
    offering_id  BIGINT UNSIGNED NOT NULL,
    teacher_id   BIGINT UNSIGNED NOT NULL,
    role         ENUM('主讲','合讲','助教') NOT NULL DEFAULT '主讲',
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (offering_id, teacher_id),
    KEY idx_off_teacher_t (teacher_id),
    CONSTRAINT fk_off_teacher_off FOREIGN KEY (offering_id)
        REFERENCES course_offering(offering_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_off_teacher_t FOREIGN KEY (teacher_id)
        REFERENCES teacher(teacher_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='开课-教师 (m:n)';

-- ---------------------------------------------------------------------------
-- 12. enrollment  当前有效选课
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS enrollment;
CREATE TABLE enrollment (
    enrollment_id    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    student_id       BIGINT UNSIGNED NOT NULL,
    offering_id      BIGINT UNSIGNED NOT NULL,
    enroll_status    ENUM('FREE','LOCKED','WITHDRAWN_MID','COMPLETED','CANCELLED')
                                  NOT NULL DEFAULT 'FREE',
    enroll_mode      ENUM('PERCENT','PNP') NOT NULL DEFAULT 'PERCENT',
    last_select_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    locked_at        DATETIME     NULL,
    withdrawn_at     DATETIME     NULL,
    created_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                  ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (enrollment_id),
    UNIQUE KEY uk_enrollment_student_off (student_id, offering_id),
    KEY idx_enrollment_offering (offering_id),
    CONSTRAINT fk_enrollment_student FOREIGN KEY (student_id)
        REFERENCES student(student_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_enrollment_offering FOREIGN KEY (offering_id)
        REFERENCES course_offering(offering_id) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='学生当前有效选课';

-- ---------------------------------------------------------------------------
-- 13. enrollment_action  前两周自由选课操作日志
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS enrollment_action;
CREATE TABLE enrollment_action (
    action_id     BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    student_id    BIGINT UNSIGNED NOT NULL,
    offering_id   BIGINT UNSIGNED NOT NULL,
    action_type   ENUM('ADD','DROP') NOT NULL,
    operator      VARCHAR(50)  NOT NULL DEFAULT 'student',
    created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (action_id),
    KEY idx_enroll_action_student (student_id, created_at),
    KEY idx_enroll_action_offering (offering_id, created_at),
    CONSTRAINT fk_enroll_action_student FOREIGN KEY (student_id)
        REFERENCES student(student_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_enroll_action_offering FOREIGN KEY (offering_id)
        REFERENCES course_offering(offering_id) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB COMMENT='前两周自由选课/退课操作过程日志';

-- ---------------------------------------------------------------------------
-- 14. grade_band  开课等第区间(由任课老师设置)
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS grade_band;
CREATE TABLE grade_band (
    offering_id  BIGINT UNSIGNED NOT NULL,
    letter       ENUM('A+','A','A-','B+','B','B-','C+','C','C-','D','F') NOT NULL,
    score_min    DECIMAL(5,2) NOT NULL,
    score_max    DECIMAL(5,2) NOT NULL,
    gpa_min      DECIMAL(4,3) NOT NULL,
    gpa_max      DECIMAL(4,3) NOT NULL,
    created_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                              ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (offering_id, letter),
    CONSTRAINT fk_band_offering FOREIGN KEY (offering_id)
        REFERENCES course_offering(offering_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_band_score CHECK (score_max >= score_min
                                  AND score_min >= 0 AND score_max <= 100),
    CONSTRAINT chk_band_gpa   CHECK (gpa_max   >= gpa_min
                                  AND gpa_min  >= 0 AND gpa_max  <= 4)
) ENGINE=InnoDB COMMENT='开课等第区间(分数段→等第→绩点区间)';

-- ---------------------------------------------------------------------------
-- 15. grade  当前有效成绩
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS grade;
CREATE TABLE grade (
    grade_id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    enrollment_id     BIGINT UNSIGNED NOT NULL,
    grade_mode        ENUM('PERCENT','PNP') NOT NULL,
    score             DECIMAL(5,2) NULL  COMMENT '百分制原始分',
    pnp_result        ENUM('P','NP') NULL,
    letter_grade      ENUM('A+','A','A-','B+','B','B-','C+','C','C-','D','F','P','NP') NULL,
    gpa               DECIMAL(4,3) NULL,
    rank_in_offering  INT          NULL,
    grade_status      ENUM('VALID','INVALID','RESIT_COVERED') NOT NULL DEFAULT 'VALID',
    counts_credit     TINYINT(1)   NOT NULL DEFAULT 1,
    counts_gpa        TINYINT(1)   NOT NULL DEFAULT 1,
    is_resit          TINYINT(1)   NOT NULL DEFAULT 0,
    recorded_at       TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                   ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (grade_id),
    UNIQUE KEY uk_grade_enrollment (enrollment_id),
    KEY idx_grade_score (score),
    CONSTRAINT fk_grade_enrollment FOREIGN KEY (enrollment_id)
        REFERENCES enrollment(enrollment_id) ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT chk_grade_score   CHECK (score IS NULL OR (score BETWEEN 0 AND 100)),
    CONSTRAINT chk_grade_gpa     CHECK (gpa   IS NULL OR (gpa   BETWEEN 0 AND 4)),
    CONSTRAINT chk_grade_mode    CHECK (
        (grade_mode = 'PERCENT' AND score IS NOT NULL AND pnp_result IS NULL) OR
        (grade_mode = 'PNP'     AND pnp_result IS NOT NULL AND score IS NULL)
    ),
    CONSTRAINT chk_grade_pnp_gpa CHECK (
        NOT (grade_mode = 'PNP' AND counts_gpa = 1)
    )
) ENGINE=InnoDB COMMENT='当前有效成绩(每个 enrollment 至多一条)';

-- ---------------------------------------------------------------------------
-- 16. app_user  系统账户
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS app_user;
CREATE TABLE app_user (
    user_id        BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    username       VARCHAR(50)  NOT NULL,
    password_hash  VARCHAR(255) NOT NULL COMMENT 'bcrypt',
    role           ENUM('admin','editor','viewer') NOT NULL DEFAULT 'viewer',
    guest_type     VARCHAR(50)  NULL COMMENT '访客可见类型, role=viewer 时使用',
    is_active      TINYINT(1)   NOT NULL DEFAULT 1,
    signature      VARCHAR(64)  NOT NULL COMMENT 'HMAC-SHA256 行签名',
    last_login_at  DATETIME     NULL,
    created_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    UNIQUE KEY uk_app_user_name (username)
) ENGINE=InnoDB COMMENT='账户(bcrypt 密码 + HMAC 行签)';

-- ---------------------------------------------------------------------------
-- 17. auth_session  会话
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS auth_session;
CREATE TABLE auth_session (
    session_id   BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id      BIGINT UNSIGNED NOT NULL,
    token_hash   CHAR(64)     NOT NULL COMMENT 'sha256(token)',
    issued_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at   DATETIME     NOT NULL,
    revoked_at   DATETIME     NULL,
    client_info  VARCHAR(255),
    PRIMARY KEY (session_id),
    UNIQUE KEY uk_session_token (token_hash),
    KEY idx_session_user (user_id),
    CONSTRAINT fk_session_user FOREIGN KEY (user_id)
        REFERENCES app_user(user_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT chk_session_expiry CHECK (expires_at > issued_at)
) ENGINE=InnoDB COMMENT='登录会话';

-- ---------------------------------------------------------------------------
-- 18. audit_log_index  审计索引(JSON 详细落 jsonl 文件, 此表只索引)
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS audit_log_index;
CREATE TABLE audit_log_index (
    log_id        BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    actor         VARCHAR(50)  NOT NULL,
    role          VARCHAR(20)  NOT NULL,
    table_name    VARCHAR(50)  NOT NULL,
    action        ENUM('INSERT','UPDATE','DELETE','LOGIN','LOGOUT','SQL','EXPORT','IMPORT','BACKUP','RESTORE') NOT NULL,
    target_pk     VARCHAR(50),
    affected_rows INT          NOT NULL DEFAULT 0,
    log_file      VARCHAR(50)  NOT NULL COMMENT 'jsonl 文件名 YYYY-MM-DD',
    file_offset   BIGINT       NOT NULL COMMENT 'jsonl 行偏移',
    ts            TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (log_id),
    KEY idx_audit_ts (ts),
    KEY idx_audit_actor_ts (actor, ts),
    KEY idx_audit_table_ts (table_name, ts)
) ENGINE=InnoDB COMMENT='操作日志索引(全文落 logs/*.jsonl)';

-- ---------------------------------------------------------------------------
-- 19. data_origin  元数据: 标注每张业务表数据来源
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS data_origin;
CREATE TABLE data_origin (
    table_name        VARCHAR(50)  NOT NULL,
    source            ENUM('real','sample','imported') NOT NULL,
    generated_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sample_row_count  INT          NOT NULL DEFAULT 0,
    note              VARCHAR(255),
    PRIMARY KEY (table_name)
) ENGINE=InnoDB COMMENT='每张业务表的数据来源标注(real/sample/imported)';

SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------------
-- 默认管理员账户(密码 admin123 的 bcrypt, signature 由后端首次启动重写)
-- ---------------------------------------------------------------------------
INSERT INTO app_user (username, password_hash, role, is_active, signature)
VALUES ('admin',
        '$2b$12$BOOTSTRAP.PLACEHOLDER.WILL.BE.REPLACED.BY.BACKEND/security',
        'admin', 1, 'BOOTSTRAP')
ON DUPLICATE KEY UPDATE username = username;
