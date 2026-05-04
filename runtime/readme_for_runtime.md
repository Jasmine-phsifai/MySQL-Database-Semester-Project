# readme_for_runtime

内置 embeddable Python (M3 阶段填充).

打包步骤 (M3):

1. 下载 `python-3.12.x-embed-amd64.zip` (https://www.python.org/downloads/windows/)
2. 解压到本目录, 应得 `runtime\python.exe`, `runtime\python312.zip` 等
3. 在 `runtime\python312._pth` 取消 `import site` 注释
4. 装 pip:
   ```cmd
   curl -O https://bootstrap.pypa.io/get-pip.py
   runtime\python.exe get-pip.py
   ```
5. 装项目依赖:
   ```cmd
   runtime\python.exe -m pip install PyQt6 pymysql bcrypt pandas openpyxl Faker pyqtdarktheme pdfplumber
   ```

之后 `start.bat` 会自动优先使用 `runtime\python.exe`, 整个仓库可拷贝到任何 Windows 机器开箱即用.

M1 / M2 开发期: 不需要 runtime\, `start.bat` 自动 fallback 到 `D:\Anaconda\envs\py312\python.exe`.
