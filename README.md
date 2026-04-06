# PCCES MCP Server

台灣公共工程經費電腦估價系統（PCCES）的 MCP (Model Context Protocol) 伺服器。

讓 Claude Desktop 等 AI 助理能直接查詢 PCCES 資料庫，包含專案工項、標準資源代碼（L/E 人力機具）、工項代碼解碼等功能。

---

## 系統需求

| 項目 | 需求 |
|------|------|
| 作業系統 | Windows 10 / 11（64位元） |
| Python | 3.10 以上（含 pip） |
| PCCES 軟體 | 已安裝並建立資料庫（含 `Pcces` 標準庫） |
| SQL Server | SQL Server Express（PCCES 安裝時自動附帶） |
| AI 客戶端 | Claude Desktop（或其他支援 MCP 的客戶端） |

> **重要**：本工具僅適用於已安裝 PCCES 軟體的 Windows 電腦，需能存取 PCCES 的 SQL Server 資料庫。

---

## 安裝步驟

### 1. 下載專案

```bash
git clone https://github.com/manosaki/pcces-mcp-server.git
```

或直接下載 ZIP 並解壓縮到任意目錄（建議 `C:\pcces-mcp-server`）。

### 2. 執行安裝程式（建議）

進入專案目錄，**雙擊執行** `install.bat`。

安裝程式會自動：
- 偵測電腦上正確的 Python 版本（處理多版本共存問題）
- 安裝必要套件（`mcp`、`pyodbc`）
- 驗證 PCCES 資料庫連線
- 顯示 Claude Desktop 設定內容（直接複製貼上即可）

### 3. 設定 Claude Desktop

開啟設定檔（按 `Win + R`，輸入 `%APPDATA%\Claude`，用記事本開啟 `claude_desktop_config.json`）。

將 `install.bat` 輸出的設定內容貼入存檔，例如：

```json
{
  "mcpServers": {
    "pcces": {
      "command": "C:\\Users\\USER\\AppData\\Local\\Programs\\Python\\Python312\\python.exe",
      "args": ["C:\\pcces-mcp-server\\server.py"]
    }
  }
}
```

> **注意**：`command` 必須使用 `install.bat` 輸出的完整 Python 路徑，不可直接填 `python`（多版本環境下會指到錯誤的版本）。

### 4. 重新啟動 Claude Desktop

關閉並重新開啟 Claude Desktop，在工具清單中確認出現 `pcces` 相關工具即完成設定。

---

## 手動安裝（進階）

若不使用 `install.bat`，請手動執行：

```bash
# 確認 Python 版本（需 3.10+）
python --version

# 若系統有多個 Python，使用 py 啟動器指定版本
py -3.12 -m pip install -r requirements.txt

# 查詢實際 Python 路徑（貼入 claude_desktop_config.json）
py -3.12 -c "import sys; print(sys.executable)"
```

---

## 進階設定

### 環境變數

| 環境變數 | 說明 | 預設值 |
|---------|------|--------|
| `PCCES_SQL_SERVER` | SQL Server 伺服器\\執行個體名稱 | `.\\SQLEXPRESS` |
| `PCCES_SQL_DRIVER` | ODBC 驅動程式名稱 | `SQL Server` |

在 `claude_desktop_config.json` 中設定環境變數：

```json
{
  "mcpServers": {
    "pcces": {
      "command": "C:\\Users\\USER\\AppData\\Local\\Programs\\Python\\Python312\\python.exe",
      "args": ["C:\\pcces-mcp-server\\server.py"],
      "env": {
        "PCCES_SQL_SERVER": ".\\SQLEXPRESS2019"
      }
    }
  }
}
```

---

## 提供工具清單

| 工具名稱 | 說明 |
|---------|------|
| `list_databases` | 列出所有可用 PCCES 資料庫及統計 |
| `list_projects` | 列出資料庫中的所有專案 |
| `get_project_summary` | 取得專案摘要（總金額、章節小計） |
| `get_project_items` | 取得專案完整工項明細清單 |
| `search_item_by_name` | 依名稱關鍵字搜尋工項 |
| `get_item_by_pcces_code` | 依 PCCES 編碼查詢工項 |
| `search_resource` | 在專案資源庫搜尋材料/人力/機具 |
| `get_unit_price_analysis` | 查詢工項單價分析（費率與子工項明細） |
| `decode_work_item_code` | 解碼 10 碼 PCCES 工項代碼 |
| `decode_resource_code` | 解碼 13 碼 PCCES 資源代碼（L=人力、E=機具） |
| `search_standard_codes` | 在全國標準資源庫搜尋資源代碼（支援所有 L/E 代碼） |

---

## 使用範例

安裝完成後，可在 Claude Desktop 直接用中文提問：

- 「列出所有可用的 PCCES 資料庫」
- 「幫我找 AR 資料庫中含有混凝土的工項」
- 「解碼工項代碼 0225340004 是什麼意思」
- 「建築師的人力資源代碼是什麼？單位為月」
- 「找出救險吊車，3噸的機具代碼」

---

## 常見問題

**Q：執行 `install.bat` 顯示找不到 Python**

請先安裝 Python 3.10+：前往 https://www.python.org/downloads/ 下載，安裝時勾選「Add Python to PATH」及「pip」。

**Q：連線失敗，找不到資料庫**

1. 確認 PCCES 軟體已正常安裝
2. 確認 SQL Server Express 服務正在執行（工作管理員→服務→`MSSQL$SQLEXPRESS`）
3. 若執行個體名稱不同，在 `claude_desktop_config.json` 加入 `"env": {"PCCES_SQL_SERVER": ".\\你的執行個體名稱"}`

**Q：Claude Desktop 看不到 pcces 工具**

1. 確認 `claude_desktop_config.json` 的 Python 路徑正確（使用 `install.bat` 輸出的完整路徑）
2. 完整關閉並重新開啟 Claude Desktop

---

## 授權

MIT License
