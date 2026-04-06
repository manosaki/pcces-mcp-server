import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
from tools.db_tools import (
    list_databases,
    list_projects,
    get_project_items,
    get_project_summary,
    search_item_by_name,
    get_item_by_pcces_code,
    search_resource,
    get_unit_price_analysis,
    decode_standard_resource_code,
    search_standard_codes,
    decode_work_item_code,
    search_work_item_codes,
)

app = Server("pcces")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="list_databases",
            description="列出所有可用的 PCCES 資料庫及其專案數量與資源庫數量",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="list_projects",
            description="列出指定 PCCES 資料庫中的所有專案",
            inputSchema={
                "type": "object",
                "properties": {
                    "db": {
                        "type": "string",
                        "description": "資料庫名稱，可選: Pcces, AR, B379110000G, B383110000G",
                        "default": "AR",
                    }
                },
            },
        ),
        types.Tool(
            name="get_project_summary",
            description="取得指定專案的摘要資訊，包含總金額與各章節小計",
            inputSchema={
                "type": "object",
                "required": ["project_code"],
                "properties": {
                    "project_code": {"type": "string", "description": "專案代碼"},
                    "db": {"type": "string", "description": "資料庫名稱", "default": "AR"},
                },
            },
        ),
        types.Tool(
            name="get_project_items",
            description="取得指定專案的完整工項明細清單（含編號、名稱、單位、單價、數量、複價）",
            inputSchema={
                "type": "object",
                "required": ["project_code"],
                "properties": {
                    "project_code": {"type": "string", "description": "專案代碼"},
                    "db": {"type": "string", "description": "資料庫名稱", "default": "AR"},
                },
            },
        ),
        types.Tool(
            name="search_item_by_name",
            description="依中文名稱關鍵字搜尋工項，可跨整個資料庫查詢",
            inputSchema={
                "type": "object",
                "required": ["keyword"],
                "properties": {
                    "keyword": {"type": "string", "description": "搜尋關鍵字，例如: 混凝土、鋼筋、模板"},
                    "db": {"type": "string", "description": "資料庫名稱", "default": "AR"},
                },
            },
        ),
        types.Tool(
            name="get_item_by_pcces_code",
            description="依 PCCES 標準編碼查詢工項",
            inputSchema={
                "type": "object",
                "required": ["pcces_code"],
                "properties": {
                    "pcces_code": {"type": "string", "description": "PCCES 標準編碼，例如: 0225340004"},
                    "db": {"type": "string", "description": "資料庫名稱", "default": "AR"},
                },
            },
        ),
        types.Tool(
            name="search_resource",
            description="搜尋資源庫（材料/人力/機具），可依名稱與類型篩選",
            inputSchema={
                "type": "object",
                "required": ["keyword"],
                "properties": {
                    "keyword": {"type": "string", "description": "搜尋關鍵字"},
                    "db": {"type": "string", "description": "資料庫名稱", "default": "AR"},
                    "res_type": {
                        "type": "string",
                        "description": "資源類型篩選: L=人力, E=機具, M=材料，不填則全部",
                    },
                },
            },
        ),
        types.Tool(
            name="get_unit_price_analysis",
            description="查詢指定專案內符合關鍵字的工項單價分析，回傳費率（人工/機具/材料）與詳細子工項（名稱、單位、數量、單價、複價、PCCES編碼）",
            inputSchema={
                "type": "object",
                "required": ["project_code", "keyword"],
                "properties": {
                    "project_code": {"type": "string", "description": "專案代碼"},
                    "keyword": {"type": "string", "description": "工項名稱關鍵字，例如: 模板、混凝土、鋼筋"},
                    "db": {"type": "string", "description": "資料庫名稱，可選: Pcces, AR, B379110000G, B383110000G", "default": "AR"},
                },
            },
        ),
        types.Tool(
            name="decode_work_item_code",
            description=(
                "解碼 PCCES 10碼工項標準代碼，回傳章節名稱、完整工項名稱與單位。"
                "例如: 0225340004 → 建築物及構造物之保護，修護　式。"
                "優先使用最新的 AutoNumA/AutoNumB 命名，若演算法失敗則查 mrsBaseA 備援。"
            ),
            inputSchema={
                "type": "object",
                "required": ["code10"],
                "properties": {
                    "code10": {
                        "type": "string",
                        "description": "PCCES 10碼工項代碼，例如: 0225340004, 0152310004",
                    },
                    "db": {
                        "type": "string",
                        "description": "規則庫所在資料庫 (預設 Pcces)",
                        "default": "Pcces",
                    },
                },
            },
        ),
        types.Tool(
            name="search_standard_codes",
            description=(
                "在 PCCES 標準資源代碼庫中以名稱關鍵字搜尋資源，回傳 pccesCode、名稱、單位、費用與類型。"
                "與 search_resource 不同：此工具搜尋全國標準資源庫，不限於特定專案。"
                "res_type 可指定 L=人力、E=機具、M=材料、W=其他。"
            ),
            inputSchema={
                "type": "object",
                "required": ["keyword"],
                "properties": {
                    "keyword": {"type": "string", "description": "搜尋關鍵字，例如: 混凝土泵、裝料機、技術工"},
                    "res_type": {
                        "type": "string",
                        "description": "資源類型: L=人力, E=機具, M=材料, W=其他，不填則全部",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "最多回傳筆數 (預設50，最大200)",
                        "default": 50,
                    },
                    "db": {
                        "type": "string",
                        "description": "標準庫資料庫 (預設 Pcces)",
                        "default": "Pcces",
                    },
                },
            },
        ),
        types.Tool(
            name="search_work_item_codes",
            description=(
                "在 PCCES 標準工項代碼庫（AutoNumB）中依名稱關鍵字搜尋工項代碼。"
                "與 search_item_by_name 不同：此工具直接查詢全國標準定義，不依賴專案資料，"
                "任何安裝了 PCCES 的電腦均可使用。"
                "回傳 pccesCode（10碼）、工項名稱、單位。"
            ),
            inputSchema={
                "type": "object",
                "required": ["keyword"],
                "properties": {
                    "keyword": {
                        "type": "string",
                        "description": "工項名稱關鍵字，例如: 矽酸鈣板、混凝土、鋼筋、天花板",
                    },
                    "unit": {
                        "type": "string",
                        "description": "單位過濾，例如: M2, 式, 個, T（可選）",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "最多回傳筆數（預設50，最大200）",
                        "default": 50,
                    },
                },
            },
        ),
        types.Tool(
            name="decode_resource_code",
            description=(
                "解碼 PCCES 標準資源代碼，回傳該代碼對應的中文名稱與單位。"
                "支援 L 開頭 (人力) 和 E 開頭 (機具) 的13碼標準代碼。"
                "例如: L000001100002 → 経理　工；E000001010012 → 機具不分類，螺栓旋緊器具，使用費　天"
            ),
            inputSchema={
                "type": "object",
                "required": ["full_code"],
                "properties": {
                    "full_code": {
                        "type": "string",
                        "description": "PCCES 資源代碼 (13碼)，L=人力，E=機具，例如: L000001100002, E000001010012",
                    },
                    "db": {
                        "type": "string",
                        "description": "規則庫所在資料庫 (預設 Pcces)",
                        "default": "Pcces",
                    },
                },
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "list_databases":
            result = list_databases()
        elif name == "list_projects":
            result = list_projects(db=arguments.get("db"))
        elif name == "get_project_summary":
            result = get_project_summary(
                project_code=arguments["project_code"],
                db=arguments.get("db"),
            )
        elif name == "get_project_items":
            result = get_project_items(
                project_code=arguments["project_code"],
                db=arguments.get("db"),
            )
        elif name == "search_item_by_name":
            result = search_item_by_name(
                keyword=arguments["keyword"],
                db=arguments.get("db"),
            )
        elif name == "get_item_by_pcces_code":
            result = get_item_by_pcces_code(
                pcces_code=arguments["pcces_code"],
                db=arguments.get("db"),
            )
        elif name == "search_resource":
            result = search_resource(
                keyword=arguments["keyword"],
                db=arguments.get("db"),
                res_type=arguments.get("res_type"),
            )
        elif name == "get_unit_price_analysis":
            result = get_unit_price_analysis(
                project_code=arguments["project_code"],
                keyword=arguments["keyword"],
                db=arguments.get("db"),
            )
        elif name == "decode_work_item_code":
            result = decode_work_item_code(
                code10=arguments["code10"],
                db=arguments.get("db"),
            )
        elif name == "search_standard_codes":
            result = search_standard_codes(
                keyword=arguments["keyword"],
                db=arguments.get("db"),
                res_type=arguments.get("res_type"),
                limit=arguments.get("limit", 50),
            )
        elif name == "search_work_item_codes":
            result = search_work_item_codes(
                keyword=arguments["keyword"],
                unit=arguments.get("unit"),
                limit=arguments.get("limit", 50),
            )
        elif name == "decode_resource_code":
            result = decode_standard_resource_code(
                full_code=arguments["full_code"],
                db=arguments.get("db"),
            )
        else:
            result = {"error": f"未知工具: {name}"}

        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    except Exception as e:
        return [types.TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
