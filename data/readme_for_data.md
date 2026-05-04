# readme_for_data

数据导入用工作目录 (代码不直读, 仅由 tools/ 写入与读出).

| 子目录 | 用途 |
|--------|------|
| `extracted/` | `tools/extract_courses_pdf.py` 输出的 CSV (PDF 自动提取) + `unparseable_pages.txt` (识别失败页清单) |
| `manual_md/` | 用户对识别失败页手 OCR 转的 markdown 表格, 由 `tools/import_md_table.py` (M2) 灌入 |

CSV 编码: UTF-8 BOM, 字段对齐 todo 字段:
选课序号 / 课程名称 / 学分 / 教师 / 上课时间 / 教室 / 考试类型 / 含A+ / 院系
