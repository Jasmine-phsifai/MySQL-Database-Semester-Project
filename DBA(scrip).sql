CREATE DATABASE IF NOT EXISTS StudentGradingSystem;
USE StudentGradingSystem;

-- 院系表
CREATE TABLE Department (
    dept_id INT PRIMARY KEY AUTO_INCREMENT,
    dept_name VARCHAR(100) NOT NULL UNIQUE,
    office_location VARCHAR(255),
    phone VARCHAR(20)
);

-- 专业表
CREATE TABLE Major (
    major_id INT PRIMARY KEY AUTO_INCREMENT,
    major_name VARCHAR(100) NOT NULL,
    dept_id INT,
    required_credits_bachelor INT,
    required_credits_master INT,
    FOREIGN KEY (dept_id) REFERENCES Department(dept_id) ON DELETE SET NULL
);

-- 学生表
CREATE TABLE Student (
    student_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    id_card VARCHAR(18) UNIQUE NOT NULL,
    dormitory VARCHAR(50),
    address VARCHAR(255),
    phone VARCHAR(20),
    birthday DATE,
    gender ENUM('Male', 'Female'),
    grade_year INT,
    major_id INT,
    major_dept_id INT,
    minor_dept_id INT,
    degree_level VARCHAR(20),
    earned_credits INT DEFAULT 0,
    password VARCHAR(128) NOT NULL, -- 为组员 B 预留的密码字段
    FOREIGN KEY (major_id) REFERENCES Major(major_id),
    FOREIGN KEY (major_dept_id) REFERENCES Department(dept_id),
    FOREIGN KEY (minor_dept_id) REFERENCES Department(dept_id)
);

-- 教师表
CREATE TABLE Teacher (
    teacher_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    dept_id INT,
    FOREIGN KEY (dept_id) REFERENCES Department(dept_id)
);

-- 课程表
CREATE TABLE Course (
    course_id VARCHAR(20) PRIMARY KEY,
    course_name VARCHAR(100) NOT NULL,
    description TEXT,
    hours INT,
    credits INT,
    degree_level VARCHAR(20),
    dept_id INT,
    FOREIGN KEY (dept_id) REFERENCES Department(dept_id)
);

-- 教师-课程中间表 (多对多关系)
CREATE TABLE Teacher_Course (
    teacher_id VARCHAR(20),
    course_id VARCHAR(20),
    PRIMARY KEY (teacher_id, course_id),
    FOREIGN KEY (teacher_id) REFERENCES Teacher(teacher_id),
    FOREIGN KEY (course_id) REFERENCES Course(course_id)
);

-- 成绩表 (学生-课程多对多关系)
CREATE TABLE Grade (
    student_id VARCHAR(20),
    course_id VARCHAR(20),
    semester VARCHAR(20),
    score DECIMAL(5,2),
    PRIMARY KEY (student_id, course_id, semester),
    FOREIGN KEY (student_id) REFERENCES Student(student_id),
    FOREIGN KEY (course_id) REFERENCES Course(course_id)
);



-- 修改成绩表，增加分数范围验证（0-100分）
ALTER TABLE Grade 
ADD CONSTRAINT chk_score CHECK (score >= 0 AND score <= 100);

-- 修改学生表，确保性别输入只能是 'Male' 或 'Female'
ALTER TABLE Student 
MODIFY COLUMN gender ENUM('Male', 'Female') NOT NULL;

-- 确保学分不能为负数
ALTER TABLE Course 
ADD CONSTRAINT chk_credits CHECK (credits >= 0);






