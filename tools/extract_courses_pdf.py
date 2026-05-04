"""从课程表 PDF 提取课程数据 → CSV。

用法:
    python tools/extract_courses_pdf.py
    python tools/extract_courses_pdf.py --pdf "<file>" --skip-pages 16

策略:
  1. 跳过开头校历页 (默认 16 页)
  2. 用 pdfplumber.extract_table() 抓表格行
  3. 不识别的页 (返回空表) 写入 unparseable_pages.txt, 由用户走手 OCR

输出:
  data/extracted/<pdfname>.csv  字段尽量对齐 todo:
    选课序号 / 课程名称 / 学分 / 教师 / 上课时间 / 教室 / 考试类型 / 含A+ / 院系
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import pdfplumber


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PDFS = [
    PROJECT_ROOT / "2025-2026 学年第一学期.pdf",
    PROJECT_ROOT / "25-26第二学期课程表.pdf",
]
OUT_DIR = PROJECT_ROOT / "data" / "extracted"
UNPARSED = OUT_DIR / "unparseable_pages.txt"


WANTED_HEADERS = ("序号", "课程", "学分", "教师", "时间", "教室", "考试", "院系")


def looks_like_header(row: list) -> bool:
    cell_join = "|".join(str(c or "") for c in row)
    return any(h in cell_join for h in WANTED_HEADERS)


def extract_one(pdf_path: Path, skip_pages: int) -> tuple[list[list[str]], list[int]]:
    rows: list[list[str]] = []
    unparsed: list[int] = []
    header: list[str] | None = None
    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages):
            page_no = i + 1
            if i < skip_pages:
                continue
            tables = page.extract_tables() or []
            page_rows = 0
            for tbl in tables:
                for r in tbl:
                    if header is None and looks_like_header(r):
                        header = [str(c or "").strip() for c in r]
                        continue
                    if not any((c or "").strip() for c in r):
                        continue
                    rows.append([str(c or "").strip() for c in r])
                    page_rows += 1
            if page_rows == 0 and not tables:
                unparsed.append(page_no)
    return ([header] if header else []) + rows, unparsed


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", action="append")
    ap.add_argument("--skip-pages", type=int, default=16)
    args = ap.parse_args()

    pdfs = [Path(p) for p in args.pdf] if args.pdf else DEFAULT_PDFS
    all_unparsed: dict[str, list[int]] = {}
    total = 0

    for p in pdfs:
        if not p.exists():
            print(f"[skip] not found: {p}")
            continue
        print(f"[parse] {p.name} (skip first {args.skip_pages} pages)")
        rows, unparsed = extract_one(p, args.skip_pages)
        out = OUT_DIR / (p.stem + ".csv")
        with out.open("w", encoding="utf-8-sig", newline="") as f:
            csv.writer(f).writerows(rows)
        course_rows = max(0, len(rows) - 1)  # exclude header
        print(f"  -> {out.name}: {course_rows} rows, "
              f"{len(unparsed)} pages with no table")
        total += course_rows
        if unparsed:
            all_unparsed[p.name] = unparsed

    UNPARSED.write_text(
        "# 以下页未能识别表格. 请人工 OCR 转 markdown 表格放在\n"
        "# data/manual_md/<pdfname>_page<n>.md 然后用 import_md_table.py 灌入\n\n"
        + "\n".join(f"{name}: {pages}" for name, pages in all_unparsed.items()),
        encoding="utf-8",
    )
    print(f"\nTotal extracted course rows: {total}")
    print(f"Unparseable pages report: {UNPARSED}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
