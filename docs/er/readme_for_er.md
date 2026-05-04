# readme_for_er

ER 图相关.

| 文件 | 作用 | 被谁调用 | 调用谁 |
|------|------|----------|--------|
| `schema.mmd` | mermaid `erDiagram` 源, 19 个实体 + 全部关系 + 主外键标注 | mermaid CLI (`mmdc`) 或 https://mermaid.live | — |
| `schema.png` / `schema.svg` | mermaid 渲染 base 版 (M1 后人工跑 mmdc 生成) | `app/ui/dialogs/er_diagram_dialog.py` 加载顺序 #2/#3 | — |
| `schema_polished.png` | AI 文生图润色版 (用户用 ChatGPT/Midjourney 生成后回放) | `app/ui/dialogs/er_diagram_dialog.py` 加载顺序 #1 | — |
| `POLISH_GUIDE.md` | 润色 prompt 模板 + 渲染步骤 | 用户阅读 | — |

加载顺序: `schema_polished.png` → `schema.svg` → `schema.png` → 占位提示.
