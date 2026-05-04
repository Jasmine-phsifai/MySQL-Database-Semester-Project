# readme_for_sql

SQL 文件目录. 全部 utf8mb4 / InnoDB / MySQL 8.

| 子目录 | 用途 |
|--------|------|
| `ddl/` | 建表 / 改表 SQL (按编号迁移 001_*.sql, 002_*.sql) |
| `seed/` | 生成器输出的 INSERT 语句 (M2 选用; 当前生成器走 PyMySQL 直 INSERT) |
| `views/` | 报表视图 (M3: GPA、按学期均分等) |

部署方式:
```cmd
mysql -u root < sql\ddl\001_schema.sql
```
