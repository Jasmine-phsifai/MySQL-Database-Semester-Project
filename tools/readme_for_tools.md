# readme_for_tools

命令行工具. 全部用 `D:\Anaconda\envs\py312\python.exe -X utf8 tools\<script>.py` 调起.

| 文件 | 作用 | 被谁调用 | 调用谁 |
|------|------|----------|--------|
| `extract_courses_pdf.py` | pdfplumber 抓两份 PDF 后段课程页 → CSV; 识别失败页清单 → `data/extracted/unparseable_pages.txt` | 用户手动跑 (一次性) | `pdfplumber`, `pathlib`, `csv` |
| `gen_fixtures.py` | 扫描 18 张表, 凡空表自动用 Faker 灌样例数据并标 `data_origin='sample'` | 用户手动跑; 也可 `--force-table <name>` 强制重建 | `Faker`, `app.backend.db`, `app.backend.repos.generic`, `app.backend.security.credentials` |
| `import_md_table.py` (M2) | 解析 `data/manual_md/*.md` 管道表 → 灌 `course / course_offering / offering_teacher / teacher / department` | 用户手动跑 | `re`, `app.backend.repos.generic` |
| `smoke_test.py` | 后端健康检查: import / DB ping / 登录 / 各表行数 | 调试期 | 全部 backend 模块 |
| `gui_smoke_test.py` | offscreen 模式 GUI 启动 1.5 秒自退, 验证 19 页与 ER 弹窗都能构造 | 调试期 | `PyQt6`, 全部 ui 模块 |
