# 学生成绩数据库系统

复旦《数据库及实现》课程项目 (题目四). MySQL 8 + Python 3.12 + PyQt6 桌面应用.

满足 3NF; 含完整性约束 (实体 / 参照 / CHECK); JSON 操作日志; bcrypt+HMAC 凭据;
ER 图独立弹窗; 18 业务表 + 1 元数据表全部可浏览/编辑/导入导出.

**M2 已实现**:
- 表格双击编辑 + 黄色脏单元格 + 撤销/恢复 (Ctrl+Z/Y)
- 「保存 Ctrl+S」一次事务批量提交; 失败全部回滚
- 切页/退出前未保存改动弹窗
- 新增 (按 ColSpec 渲染表单含 FK 下拉) / 删除 (软删 status=0)
- CSV/XLSX 导入向导 (字段映射 + 预检 + 事务提交) / 导出
- 自定义 SQL 控制台 (Ctrl+L); admin 全权 / editor 禁 DROP+TRUNCATE / viewer 仅 SELECT
- 操作日志查询页 (按 actor/table/action/时间窗筛选)
- 真实课程数据导入: `tools/import_md_table.py` 解析 PDF→识别 md, 灌入 641 课程 / 1378 开课 / 729 教师 / 48 院系

## 一键启动

1. 确认 MySQL 8 服务已运行 (`net start MySQL`)
2. 在本目录双击 `start.bat`
3. 登录: `admin / admin123` (或 `editor / demo123` / `viewer / demo123`)

`start.bat` 会按以下顺序选择 Python 解释器:
1. `runtime\python.exe` (打包用 embeddable, M3 阶段填充)
2. `D:\Anaconda\envs\py312\python.exe` (开发期 fallback)
3. PATH 中的 `python`

## 系统要求

- Windows 10+
- MySQL 8.0+ (本机 127.0.0.1:3306, root 用户; 见 `config.toml`)
- Python 3.12+ 含: PyQt6, PyMySQL, bcrypt, pandas, openpyxl, Faker, qdarktheme, pdfplumber

## 首次部署

```cmd
:: 1. 应用 schema
mysql -u root < sql\ddl\001_schema.sql

:: 2. 灌样例数据 (18 张表全部填齐, 共 ~36000 行)
"D:\Anaconda\envs\py312\python.exe" tools\gen_fixtures.py

:: 3. (可选) 提取 PDF 课程数据
"D:\Anaconda\envs\py312\python.exe" tools\extract_courses_pdf.py

:: 4. 启动
start.bat
```

## 目录结构

```
.\
├── start.bat                  一键启动
├── config.toml                MySQL 连接 + HMAC 盐 + UI 设置
├── README.md                  本文件
├── DESIGN.md                  设计文档 (评分对齐 6 项)
├── runtime\                   内置 embeddable Python (打包用, 开发期空)
├── app\                       应用代码包
│   ├── __main__.py
│   ├── config.py
│   ├── backend\               连接池 / 仓储 / 安全 / 审计
│   └── ui\                    PyQt6 主窗口 / 对话框 / 控件
├── sql\
│   ├── ddl\                   建表 SQL (按编号迁移)
│   ├── seed\                  生成器输出
│   └── views\                 GPA 等报表视图
├── tools\                     生成器 / 提取器 / 烟雾测试
├── data\                      PDF 提取与导入用数据
├── logs\                      JSON 操作日志 (按日轮转 .jsonl)
├── backups\                   mysqldump 输出
└── docs\
    └── er\                    ER 图源 + 渲染产物 + 润色指南
```

每个子目录有 `readme_for_<dirname>.md` 详细说明每个文件的作用与调用关系.

## 常见问题

| 现象 | 排查 |
|------|------|
| `Can't connect to MySQL server (10061)` | MySQL 服务未启动: `net start MySQL` |
| `Access denied for user 'root'` | 修改 `config.toml` 中 `[mysql] password` |
| 启动后表是空的 | 跑 `python tools\gen_fixtures.py` 填样例数据 |
| ER 图弹窗显示"未找到" | 渲染 mermaid: `mmdc -i docs\er\schema.mmd -o docs\er\schema.png` |
| 中文显示成 ?? | 确认数据库 `CHARACTER SET utf8mb4` |

## 故障排查工具

```cmd
"D:\Anaconda\envs\py312\python.exe" tools\smoke_test.py     :: 后端健康检查
"D:\Anaconda\envs\py312\python.exe" tools\gui_smoke_test.py :: GUI 离屏启动检查
```

## 许可

课程项目, 仅供学习参考. 严禁商用或代码抄袭.
