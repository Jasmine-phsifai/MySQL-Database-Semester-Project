# ER 图润色指南

## 当前状态

`docs/er/schema.mmd` 是用 mermaid `erDiagram` 写的关系骨架。
直接用 mermaid CLI 或在线渲染器生成的 PNG/SVG 结构正确, 但视觉粗糙
(直角箭头 / 单色卡片 / 默认字体)。

前端 ER 图弹窗 (`app/ui/dialogs/er_diagram_dialog.py`) 的加载顺序:

```
1. docs/er/schema_polished.png      润色版 (优先)
2. docs/er/schema.svg               base SVG
3. docs/er/schema.png               base PNG
4. (无图占位提示)
```

只要把润色版命名为 `schema_polished.png` 放在 `docs/er/` 下, 前端会自动加载。

## 推荐润色流程 (任一即可)

### A. ChatGPT-4 / GPT-4o (推荐, 最便宜)

1. 上传 `docs/er/schema.png` (base 渲染) 给模型
2. 提示词模板:

```
请基于这张数据库 ER 图重新绘制一张视觉优化的版本, 严格保留:
- 所有实体的中文标签 (DEPARTMENT 院系 / STUDENT 学生 / ...)
- 实体之间所有关系线和基数 (1:1 / 1:n / m:n)
- 所有主外键标注

视觉要求:
- 实体框使用圆角矩形, 浅色填充 + 深色边框
- 关系线使用平滑曲线代替直线, 箭头使用细羽形
- 颜色按业务域分组: 蓝(基础) / 绿(开课选课) / 橙(成绩) / 灰(账户审计)
- 字体: 中文用思源黑体或微软雅黑; 英文用 Inter 或 Helvetica
- 整体留白充足, 不要拥挤
- 输出 PNG, 1920x1200, 透明背景
```

3. 下载图片, 重命名为 `schema_polished.png`, 放入 `docs/er/`

### B. Midjourney / Stable Diffusion

不推荐 — 这两类模型对"严格保留中文标签 + 关系线"非常差, 会出现错字。

### C. draw.io / dbdiagram.io

人工手绘最可控:
- draw.io 导入 schema.mmd 不直接支持, 需要先 mermaid 渲染 PNG, 再用 draw.io 描线
- dbdiagram.io 改用 DBML 重写一遍 (粘贴 sql/ddl/001_schema.sql)

## 如何渲染 base 版 (开发期一次即可)

### Node.js + mermaid-cli

```cmd
npm i -g @mermaid-js/mermaid-cli
cd 数据库PJ\docs\er
mmdc -i schema.mmd -o schema.png -w 2400 -H 1600 -t default --backgroundColor white
mmdc -i schema.mmd -o schema.svg -t default --backgroundColor white
```

### 在线渲染 (最省事)

打开 https://mermaid.live, 粘贴 schema.mmd 内容, 右上角 `Actions → PNG/SVG`。

## 验证清单

润色版交付前请检查:

- [ ] 19 个实体框全部存在 (含 data_origin)
- [ ] 所有箭头基数标注清晰可读
- [ ] 中文字符无乱码 / 不被截断
- [ ] PNG 分辨率 ≥ 1600x1000 (前端展示清晰)
- [ ] 文件大小 ≤ 5MB (避免加载卡顿)
