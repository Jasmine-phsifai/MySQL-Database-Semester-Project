# readme_for_ddl

建表脚本.

| 文件 | 作用 | 被谁调用 | 调用谁 |
|------|------|----------|--------|
| `001_schema.sql` | 创建 `student_grading` 库 + 18 业务表 + 1 元数据表 + 默认 admin 占位行 | 部署: `mysql -u root < sql\ddl\001_schema.sql`; 也由 `tools/smoke_test.py` 间接验证 | MySQL 服务 |

约束摘要:
- 实体完整性: 全部 PK + 业务唯一键
- 参照完整性: 全部 FK `ON DELETE RESTRICT ON UPDATE CASCADE`
- 检查完整性: `chk_grade_score`, `chk_grade_mode`, `chk_course_credits`, `chk_offering_periods` 等

后续迁移按 `002_*.sql` 编号追加.
