# readme_for_views

报表视图 (M3 填充).

预留:
- `student_gpa.sql` — `CREATE VIEW vw_student_gpa AS SELECT student_id, SUM(g.gpa * c.credits) / SUM(c.credits) FROM grade g JOIN enrollment e USING(enrollment_id) JOIN course_offering co USING(offering_id) JOIN course c USING(course_id) WHERE g.counts_gpa = 1 GROUP BY student_id;`
- `offering_grade_dist.sql` — 每个开课的分数分布 (用于评估 A/A+ 30% 上限)

调用方: 前端 GPA 查询页; 自定义 SQL 控制台.
