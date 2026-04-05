import os
import pyodbc
from typing import Optional
from tools.resource_decoder import (
    decode_resource_code as _decode_resource_code,
    decode_work_item_code as _decode_work_item_code,
    get_code_index as _get_code_index,
)

_SYSTEM_DATABASES = {"master", "tempdb", "model", "msdb"}

# SQL Server 連線設定（可透過環境變數覆蓋）
# 預設值適用於 PCCES 標準安裝（SQL Server Express，本機預設執行個體）
_SQL_SERVER = os.environ.get("PCCES_SQL_SERVER", r".\SQLEXPRESS")
_SQL_DRIVER = os.environ.get("PCCES_SQL_DRIVER", "SQL Server")


def _detect_pcces_databases() -> list[str]:
    """從 master 動態偵測所有使用者資料庫（排除系統資料庫）"""
    try:
        conn = pyodbc.connect(
            f"DRIVER={{{_SQL_DRIVER}}};SERVER={_SQL_SERVER};DATABASE=master;Trusted_Connection=yes;"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sys.databases WHERE state = 0 ORDER BY name")
        dbs = [row[0] for row in cursor.fetchall() if row[0] not in _SYSTEM_DATABASES]
        conn.close()
        return dbs
    except Exception:
        return []


def get_available_databases() -> list[str]:
    return _detect_pcces_databases()


def get_connection(db: str = None):
    available = get_available_databases()
    if not available:
        raise ValueError(
            f"找不到任何使用者資料庫，請確認 SQL Server 已啟動\n"
            f"目前連線設定: SERVER={_SQL_SERVER}\n"
            f"如需變更，請設定環境變數 PCCES_SQL_SERVER"
        )
    if db is None:
        db = available[0]
    if db not in available:
        raise ValueError(f"找不到資料庫: {db}，目前可用: {available}")
    conn_str = (
        f"DRIVER={{{_SQL_DRIVER}}};"
        f"SERVER={_SQL_SERVER};"
        f"DATABASE={db};"
        "Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)


def list_databases() -> list[dict]:
    """列出所有可用的 PCCES 資料庫及其專案數量"""
    result = []
    for db in get_available_databases():
        try:
            conn = get_connection(db)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM budProject")
            proj_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM mrsBaseA")
            mrs_count = cursor.fetchone()[0]
            conn.close()
            result.append({"db": db, "project_count": proj_count, "resource_count": mrs_count})
        except Exception as e:
            result.append({"db": db, "error": str(e)})
    return result


def list_projects(db: str = None) -> list[dict]:
    """列出指定資料庫中的所有專案"""
    conn = get_connection(db)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT projectCode, projectNameC, projamt, addDate
        FROM budProject
        ORDER BY addDate DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "projectCode": r[0].strip(),
            "projectNameC": r[1],
            "projamt": float(r[2]) if r[2] else 0,
            "addDate": str(r[3]),
        }
        for r in rows
    ]


def get_project_items(project_code: str, db: str = None) -> list[dict]:
    """取得指定專案的所有工項明細"""
    conn = get_connection(db)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT sNo, itemNo, levelNo, cName, unitName, cost, qty, amount, PccesCode, kind
        FROM budItemA
        WHERE projectCode = ?
        ORDER BY sNo
    """, project_code)
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "sNo": r[0],
            "itemNo": r[1].strip() if r[1] else "",
            "levelNo": r[2],
            "cName": r[3],
            "unitName": r[4].strip() if r[4] else "",
            "cost": float(r[5]) if r[5] else 0,
            "qty": float(r[6]) if r[6] else 0,
            "amount": float(r[7]) if r[7] else 0,
            "pccesCode": r[8].strip() if r[8] else "",
            "kind": r[9].strip() if r[9] else "",
        }
        for r in rows
    ]


def search_item_by_name(keyword: str, db: str = None) -> list[dict]:
    """依名稱關鍵字搜尋工項"""
    conn = get_connection(db)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT TOP 50 projectCode, sNo, itemNo, cName, unitName, cost, qty, amount, PccesCode
        FROM budItemA
        WHERE cName LIKE ?
        ORDER BY projectCode, sNo
    """, f"%{keyword}%")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "projectCode": r[0].strip(),
            "sNo": r[1],
            "itemNo": r[2].strip() if r[2] else "",
            "cName": r[3],
            "unitName": r[4].strip() if r[4] else "",
            "cost": float(r[5]) if r[5] else 0,
            "qty": float(r[6]) if r[6] else 0,
            "amount": float(r[7]) if r[7] else 0,
            "pccesCode": r[8].strip() if r[8] else "",
        }
        for r in rows
    ]


def get_item_by_pcces_code(pcces_code: str, db: str = None) -> list[dict]:
    """依 PCCES 標準編碼查詢工項"""
    conn = get_connection(db)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT projectCode, sNo, itemNo, cName, unitName, cost, qty, amount
        FROM budItemA
        WHERE PccesCode LIKE ?
        ORDER BY projectCode, sNo
    """, f"%{pcces_code}%")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "projectCode": r[0].strip(),
            "sNo": r[1],
            "itemNo": r[2].strip() if r[2] else "",
            "cName": r[3],
            "unitName": r[4].strip() if r[4] else "",
            "cost": float(r[5]) if r[5] else 0,
            "qty": float(r[6]) if r[6] else 0,
            "amount": float(r[7]) if r[7] else 0,
        }
        for r in rows
    ]


def search_resource(keyword: str, db: str = None, res_type: Optional[str] = None) -> list[dict]:
    """搜尋資源庫（材料/人力/機具）

    res_type: None=全部, 'L'=人力, 'E'=機具, 'M'=材料
    """
    conn = get_connection(db)
    cursor = conn.cursor()
    if res_type:
        cursor.execute("""
            SELECT TOP 50 resCode, pccesCode, cName, unitName, cost, resType
            FROM mrsBaseA
            WHERE cName LIKE ? AND resType LIKE ?
            ORDER BY resCode
        """, f"%{keyword}%", f"%{res_type}%")
    else:
        cursor.execute("""
            SELECT TOP 50 resCode, pccesCode, cName, unitName, cost, resType
            FROM mrsBaseA
            WHERE cName LIKE ?
            ORDER BY resCode
        """, f"%{keyword}%")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "resCode": r[0].strip() if r[0] else "",
            "pccesCode": r[1].strip() if r[1] else "",
            "cName": r[2],
            "unitName": r[3].strip() if r[3] else "",
            "cost": float(r[4]) if r[4] else 0,
            "resType": r[5].strip() if r[5] else "",
        }
        for r in rows
    ]


def get_unit_price_analysis(project_code: str, keyword: str, db: str = None) -> list[dict]:
    """查詢指定專案內符合關鍵字的工項單價分析（含費率與子工項明細）"""
    conn = get_connection(db)
    cursor = conn.cursor()

    # 找出符合關鍵字且有單價分析的工項
    cursor.execute("""
        SELECT sNo, itemNo, cName, unitName, cost, pubCode, PccesCode
        FROM budItemA
        WHERE projectCode = ? AND cName LIKE ? AND pubCode IS NOT NULL AND pubCode > 0
        ORDER BY sNo
    """, project_code, f"%{keyword}%")
    items = cursor.fetchall()

    results = []
    for item in items:
        sNo, itemNo, cName, unitName, cost, pubCode, pccesCode = item

        # 取得費率（人工/機具/材料/其他）
        cursor.execute("""
            SELECT mRate, lRate, eRate, wRate
            FROM mrsBaseA
            WHERE pubCode = ?
        """, pubCode)
        rate_row = cursor.fetchone()
        rates = {}
        if rate_row:
            rates = {
                "mRate": float(rate_row[0]) if rate_row[0] else 0,
                "lRate": float(rate_row[1]) if rate_row[1] else 0,
                "eRate": float(rate_row[2]) if rate_row[2] else 0,
                "wRate": float(rate_row[3]) if rate_row[3] else 0,
            }

        # 取得子工項明細
        cursor.execute("""
            SELECT b.listNo, a2.cName, a2.unitName, b.qty, b.cost, b.amount, a2.pccesCode, a2.resType
            FROM mrsBaseB b
            LEFT JOIN mrsBaseA a2 ON a2.pubCode = b.pubCode
            WHERE b.parentCode = ?
            ORDER BY b.listNo
        """, pubCode)
        sub_rows = cursor.fetchall()
        sub_items = [
            {
                "listNo": r[0],
                "cName": r[1],
                "unitName": r[2].strip() if r[2] else "",
                "qty": float(r[3]) if r[3] else 0,
                "cost": float(r[4]) if r[4] else 0,
                "amount": float(r[5]) if r[5] else 0,
                "pccesCode": r[6].strip() if r[6] else "",
                "resType": r[7].strip() if r[7] else "",
            }
            for r in sub_rows
        ]

        results.append({
            "sNo": sNo,
            "itemNo": itemNo.strip() if itemNo else "",
            "cName": cName,
            "unitName": unitName.strip() if unitName else "",
            "cost": float(cost) if cost else 0,
            "pubCode": pubCode,
            "pccesCode": pccesCode.strip() if pccesCode else "",
            "rates": rates,
            "sub_items": sub_items,
        })

    conn.close()
    return results


def decode_work_item_code(code10: str, db: str = None) -> dict:
    """
    解碼 PCCES 10碼工項代碼，回傳章節名稱、工項名稱與單位。

    優先使用演算法從 AutoNumA/AutoNumB 解碼（取最新命名），
    若演算法失敗則備援查 mrsBaseA（取專案儲存時的名稱）。
    """
    if not code10:
        return {"error": "代碼不可為空"}
    code10 = code10.strip()
    if len(code10) != 10:
        return {"error": f"工項代碼應為10碼，收到 {len(code10)} 碼: {code10}"}

    conn = get_connection(db or "Pcces")
    cursor = conn.cursor()

    # 1. 演算法解碼
    decoded = _decode_work_item_code(cursor, code10)

    # 2. 備援查 mrsBaseA（可能存有此代碼的名稱）
    cursor.execute(
        "SELECT pccesCode, cName, unitName FROM mrsBaseA WHERE pccesCode = ?",
        code10,
    )
    db_row = cursor.fetchone()
    conn.close()

    result = {"input_code": code10, "chap_code": code10[:5], "suffix": code10[5:]}

    if decoded:
        result["chapName"] = decoded["chapName"]
        result["cName"] = decoded["cName"]
        result["unitName"] = decoded["unitName"]
        result["source"] = "algorithm"
    elif db_row:
        result["cName"] = db_row[1]
        result["unitName"] = db_row[2].strip() if db_row[2] else ""
        result["source"] = "db_only"
    else:
        # 至少回傳章節名稱
        conn2 = get_connection(db or "Pcces")
        c2 = conn2.cursor()
        c2.execute("SELECT cName FROM AutoNumA WHERE RTRIM(itemCode) = ?", code10[:5])
        chap_row = c2.fetchone()
        conn2.close()
        if chap_row:
            result["chapName"] = chap_row[0]
            result["error"] = f"無法解碼 suffix={code10[5:]}，該章節為: {chap_row[0]}"
        else:
            result["error"] = f"無法解碼代碼 {code10}，章節 {code10[:5]} 不存在於標準庫"
        return result

    # 附上 mrsBaseA 對照資訊
    if db_row:
        result["db_cName"] = db_row[1]
        result["db_unitName"] = db_row[2].strip() if db_row[2] else ""

    return result


def search_standard_codes(keyword: str, db: str = None, res_type: Optional[str] = None, limit: int = 50) -> list[dict]:
    """
    搜尋 PCCES 標準資源代碼庫。

    同時搜尋兩個來源並合併結果：
    1. mrsBaseA — 資料庫儲存的標準資源（含費率）
    2. 全代碼索引 — 由 AutoNumB_12 演算法列舉的所有 L/E 代碼（涵蓋 mrsBaseA 沒有的代碼）

    res_type: None=全部, 'L'=人力, 'E'=機具, 'M'=材料, 'W'=其他
    """
    conn = get_connection(db or "Pcces")
    cursor = conn.cursor()

    limit = max(1, min(limit, 200))
    rt = res_type.upper() if res_type else None

    # ── 1. 搜尋 mrsBaseA ──────────────────────────────────────────────────────
    prefix_filter = ""
    params: list = [f"%{keyword}%"]
    if rt:
        prefix_filter = "AND pccesCode LIKE ?"
        params.append(f"{rt}%")

    cursor.execute(
        f"""
        SELECT TOP {limit} pccesCode, cName, unitName, cost
        FROM mrsBaseA
        WHERE cName LIKE ? {prefix_filter}
        ORDER BY pccesCode
        """,
        params,
    )
    db_rows = cursor.fetchall()

    # ── 2. 搜尋全代碼索引（L/E，首次呼叫時建立快取）────────────────────────
    code_index = _get_code_index(cursor)
    conn.close()

    # ── 3. 合併，以 pccesCode 去重 ────────────────────────────────────────────
    seen: set[str] = set()
    results: list[dict] = []

    # 先加入 mrsBaseA 結果（含費率資訊）
    for r in db_rows:
        code = r[0].strip() if r[0] else ""
        if code in seen:
            continue
        seen.add(code)
        results.append({
            "pccesCode": code,
            "cName": r[1],
            "unitName": r[2].strip() if r[2] else "",
            "resType": code[0].upper() if code else "",
            "cost": float(r[3]) if r[3] else 0,
        })

    # 再加入索引中 mrsBaseA 沒有的代碼
    for entry in code_index:
        if rt and entry["resType"] != rt:
            continue
        if keyword not in entry["cName"]:
            continue
        code = entry["pccesCode"]
        if code in seen:
            continue
        seen.add(code)
        results.append({
            "pccesCode": code,
            "cName": entry["cName"],
            "unitName": entry["unitName"],
            "resType": entry["resType"],
            "cost": 0,
        })

    # 依代碼排序後截斷
    results.sort(key=lambda x: x["pccesCode"])
    return results[:limit]


def decode_standard_resource_code(full_code: str, db: str = None) -> dict:
    """
    解碼 PCCES 標準資源代碼 (L=人力, E=機具)

    支援:
    - L 開頭13碼: 人力資源代碼
    - E 開頭13碼: 機具資源代碼

    回傳解碼結果 {"cName", "unitName", "resType"} 或 {"error", "db_lookup": {...}}
    """
    if not full_code:
        return {"error": "代碼不可為空"}

    prefix = full_code[0].upper()
    if prefix not in ("L", "E"):
        return {"error": f"目前僅支援 L (人力) 和 E (機具) 代碼，收到: {full_code}"}
    if len(full_code) != 13:
        return {"error": f"資源代碼應為13碼，收到 {len(full_code)} 碼: {full_code}"}

    # 先嘗試演算法解碼
    conn = get_connection(db or "Pcces")
    cursor = conn.cursor()

    decoded = _decode_resource_code(cursor, full_code)

    # 同時查 mrsBaseA 確認 DB 存在
    cursor.execute(
        "SELECT pccesCode, cName, unitName, resType FROM mrsBaseA WHERE pccesCode = ?",
        full_code,
    )
    db_row = cursor.fetchone()
    conn.close()

    result = {"input_code": full_code}

    if decoded:
        result["cName"] = decoded["cName"]
        result["unitName"] = decoded["unitName"]
        result["resType"] = decoded["resType"]
        result["source"] = "algorithm"
    elif db_row:
        result["cName"] = db_row[1]
        result["unitName"] = db_row[2].strip() if db_row[2] else ""
        result["resType"] = db_row[3].strip() if db_row[3] else ""
        result["source"] = "db_only"
    else:
        result["error"] = f"無法解碼代碼 {full_code}，且不在 mrsBaseA 標準庫中"
        return result

    # 若 DB 有記錄，附上比對結果
    if db_row:
        result["db_cName"] = db_row[1]
        result["db_unitName"] = db_row[2].strip() if db_row[2] else ""
        result["db_match"] = (
            result["cName"] == result["db_cName"]
            and result["unitName"] == result["db_unitName"]
        )

    return result


def get_project_summary(project_code: str, db: str = None) -> dict:
    """取得專案摘要（含總金額與各章節小計）"""
    conn = get_connection(db)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT projectCode, projectNameC, projectAddress, projamt, addDate
        FROM budProject
        WHERE projectCode = ?
    """, project_code)
    proj = cursor.fetchone()
    if not proj:
        conn.close()
        return {"error": f"找不到專案: {project_code}"}

    cursor.execute("""
        SELECT itemNo, cName, amount
        FROM budItemA
        WHERE projectCode = ? AND levelNo = 1
        ORDER BY sNo
    """, project_code)
    chapters = cursor.fetchall()
    conn.close()

    return {
        "projectCode": proj[0].strip(),
        "projectNameC": proj[1],
        "projectAddress": proj[2],
        "projamt": float(proj[3]) if proj[3] else 0,
        "addDate": str(proj[4]),
        "chapters": [
            {"itemNo": c[0].strip() if c[0] else "", "cName": c[1], "amount": float(c[2]) if c[2] else 0}
            for c in chapters
        ],
    }
