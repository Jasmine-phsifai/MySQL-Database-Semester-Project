# readme_for_backups

mysqldump 输出. M3 一键备份 / 一键回退.

文件命名: `student_grading_YYYY-MM-DD_HHMMSS.sql.gz`.

预定义命令 (M3 由前端按钮触发):
```cmd
mysqldump -u root --single-transaction --triggers --routines student_grading | gzip > backups\student_grading_<ts>.sql.gz
gunzip -c backups\<file>.sql.gz | mysql -u root student_grading   :: 回退
```

被前端"备份/还原"页调用; 也可手动跑.
