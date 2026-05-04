# readme_for_extracted

由 `tools/extract_courses_pdf.py` 输出.

| 文件 | 作用 |
|------|------|
| `<pdfname>.csv` | 该 PDF 提取出的课程行 (含表头) |
| `unparseable_pages.txt` | 未能识别表格的页码清单 — 用户参考此清单走手 OCR 流程 |

注意: 现有两份 PDF 的后段课程页大量使用合并单元格与跨页表格, pdfplumber `extract_tables()`
对其识别率不稳定, 实际灌库的真实数据以 `manual_md/` 通道为准.
