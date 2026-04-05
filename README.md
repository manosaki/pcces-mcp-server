# PCCES MCP Server

台灣公共工程經費電腦估價系統（PCCES）的 MCP (Model Context Protocol) 伺服器。

讓 Claude Desktop 等 AI 助理能直接查詢 PCCES 資料庫，包含專案工項、標準資源代碼（L/E 人力機具）、工項代碼解碼等功能。

---

## 系統需求

| 項目 | 需求 |
|------|------|
| 作業系統 | Windows 10 / 11（64位元） |
| Python | 3.10 以上 |
| PCCES 軟體 | 已安裝並建立資料庫（含 `Pcces` 標準庫） |
| SQL Server | SQL Server Express（PCCES 安裝時自動附帶） |
| ODBC 驅動程式 | `SQL Server`（Windows 內建，通常已存在） |
| AI 客戶端 | Claude Desktop（或其他支援 MCP 的客戶端） |

> **重要**：本工具僅適用於已安裝 PCCES 軟體的 Windows 電腦，需能存取 PCCES 的 SQL Server 資料庫。

---

## 安裝步驟

### 1. 下載專案

```bash
git clone https://github.com/YOUR_USERNAME/pcces-mcp-server.git
cd pcces-mcp-server
```

或直接下載 ZIP 並解壓縮到任意目錄（例如 `C:\pcces-mcp-server`）。

### 2. 安裝 Python 套件

```bash
pip install -r requirements.txt
```

### 3. 確認 SQL Server 連線

預設會連線到本機的 `.\SQLEXPRESS`（PCCES 標準安裝位置）。

如果您的 SQL Server 執行個體名稱不同，請設定環境變數：

```bash
# 範例：若執行個體名稱為 SQLEXPRESS2019
set PCCES_SQL_SERVER=.\SQLEXPRESS2019
```

可在命令提示字元執行以下指令確認連線是否正常：

```bash
python -c "from tools.db_tools import list_databases; print(list_databases())"
```

若回傳資料庫清單（如 `[{'db': 'Pcces', ...}, {'db': 'AR', ...}]`），表示連線成功。

### 4. 設定 Claude Desktop

開啟 Claude Desktop 的設定檔：

**Windows 路徑：**
```
%APPDATA%\Claude\claude_desktop_config.json
```

加入以下設定（請將路徑改為您實際的安裝位置）：

```json
{
  "mcpServers": {
    "pcces": {
      "command": "python",
      "args": ["C:\\pcces-mcp-server\\server.py"]
    }
  }
}
```

> **注意**：`command` 中的 `python` 需能在系統 PATH 中找到。若有多個 Python 版本，建議改用完整路徑，例如 `C:\\Python312\\python.exe`。

### 5. 重新啟動 Claude Desktop

關閉並重新開啟 Claude Desktop，在工具清單中確認出現 `pcces` 相關工具即完成設定。

---

## 進階設定

### 環境變數

| 環境變數 | 說明 | 預設值 |
|---------|------|--------|
| `PCCES_SQL_SERVER` | SQL Server 伺服器\\執行個體名稱 | `.\\SQLEXPRESS` |
| `PCCES_SQL_DRIVER` | ODBC 驅動程式名稱 | `SQL Server` |

在 Claude Desktop 設定中傳入環境變數的方式：

```json
{
  "mcpServers": {
    "pcces": {
      "command": "python",
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

**Q：連線失敗，找不到資料庫**

請確認：
1. PCCES 軟體已正常安裝
2. SQL Server Express 服務正在執行（可在工作管理員→服務中查看 `MSSQL$SQLEXPRESS`）
3. 執行個體名稱正確（可設定環境變數 `PCCES_SQL_SERVER`）

**Q：Python 找不到 `mcp` 套件**

請執行 `pip install mcp pyodbc` 確認已安裝。

**Q：ODBC 連線錯誤**

請確認已安裝 SQL Server ODBC 驅動程式。Windows 10/11 通常內建，若缺少可從 Microsoft 官網下載 `ODBC Driver for SQL Server`，並將 `PCCES_SQL_DRIVER` 設為 `ODBC Driver 17 for SQL Server`。

---

## 授權

MIT License
