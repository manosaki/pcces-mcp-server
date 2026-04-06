@echo off
chcp 65001 >nul 2>&1
echo ================================================
echo   PCCES MCP Server - 安裝程式
echo ================================================
echo.

:: ── 1. 尋找有 pip 的 Python ──────────────────────
set PYTHON_EXE=

:: 先嘗試 py 啟動器（Windows 標準方式，依版本由新到舊）
for %%v in (3.13 3.12 3.11 3.10) do (
    if not defined PYTHON_EXE (
        py -%%v -m pip --version >nul 2>&1
        if not errorlevel 1 (
            for /f "tokens=*" %%i in ('py -%%v -c "import sys; print(sys.executable)"') do (
                set PYTHON_EXE=%%i
            )
        )
    )
)

:: 再嘗試直接 python 指令
if not defined PYTHON_EXE (
    python -m pip --version >nul 2>&1
    if not errorlevel 1 (
        for /f "tokens=*" %%i in ('python -c "import sys; print(sys.executable)"') do (
            set PYTHON_EXE=%%i
        )
    )
)

if not defined PYTHON_EXE (
    echo [錯誤] 找不到含有 pip 的 Python 安裝。
    echo.
    echo 請先安裝 Python 3.10 以上版本：
    echo   https://www.python.org/downloads/
    echo 安裝時請勾選 "Add Python to PATH" 與 "pip"
    echo.
    pause
    exit /b 1
)

echo [OK] 使用 Python: %PYTHON_EXE%
echo.

:: ── 2. 安裝必要套件 ──────────────────────────────
echo 正在安裝必要套件 (mcp, pyodbc)...
"%PYTHON_EXE%" -m pip install -r "%~dp0requirements.txt" --quiet
if errorlevel 1 (
    echo [錯誤] 套件安裝失敗，請確認網路連線後重試。
    pause
    exit /b 1
)
echo [OK] 套件安裝完成
echo.

:: ── 3. 驗證資料庫連線 ────────────────────────────
echo 正在驗證 PCCES 資料庫連線...
"%PYTHON_EXE%" -c "from tools.db_tools import list_databases; dbs=list_databases(); print('[OK] 找到資料庫:', [d['db'] for d in dbs]) if dbs else print('[警告] 找不到資料庫，請確認 PCCES 已安裝且 SQL Server 正在執行')" 2>nul
if errorlevel 1 (
    echo [警告] 無法連線到 PCCES 資料庫
    echo   請確認：
    echo   1. PCCES 軟體已完整安裝
    echo   2. SQL Server Express 服務正在執行
    echo   3. 若 SQL Server 執行個體不是 .\SQLEXPRESS，請設定環境變數 PCCES_SQL_SERVER
)
echo.

:: ── 4. 輸出 claude_desktop_config.json 設定 ─────
set SERVER_PY=%~dp0server.py
:: 將路徑中的 \ 轉為 \\（JSON 格式需要）
set PYTHON_JSON=%PYTHON_EXE:\=\\%
set SERVER_JSON=%SERVER_PY:\=\\%
:: 移除結尾的 \
if "%SERVER_JSON:~-2%"=="\\" set SERVER_JSON=%SERVER_JSON:~0,-2%

echo ================================================
echo   Claude Desktop 設定
echo ================================================
echo.
echo 請用記事本開啟以下路徑的設定檔：
echo   %APPDATA%\Claude\claude_desktop_config.json
echo.
echo 將內容替換（或合併）為：
echo.
echo {
echo   "mcpServers": {
echo     "pcces": {
echo       "command": "%PYTHON_JSON%",
echo       "args": ["%SERVER_JSON%"]
echo     }
echo   }
echo }
echo.
echo 儲存後重新啟動 Claude Desktop 即完成設定。
echo ================================================
echo.
pause
