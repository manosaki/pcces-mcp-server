# -*- coding: utf-8 -*-
"""
PCCES 資源代碼解碼器
支援 L (人力)、E (機具) 代碼的解碼

L 碼結構: L(1) + 0000(4) + 0(1) + Sec06(2) + Sec07(1) + Sec08(1) + Sec09(1) + Sec10(1) + Sec11(1) = 13碼
E 碼結構: E(1) + 00000(5) + ChapCode(2) + Sec07(1或2) + Sec08(1或2) + Sec09(1) + Sec10(1) + Sec11(1) = 13碼
"""

# 全代碼索引快取（首次呼叫時建立，之後重用）
_CODE_INDEX: list[dict] | None = None


def _get_sec_data(cursor, chap: str, sec: str, res_type: str) -> list[dict]:
    """從 AutoNumB_12 取得指定 ChapCode + Section 的所有代碼資料"""
    cursor.execute(
        """
        SELECT RTRIM(Code), MinRow, MaxRow, SelfRow, Content
        FROM AutoNumB_12
        WHERE ChapCode = ? AND CodeSection = ? AND resType = ?
          AND Code IS NOT NULL AND LEN(RTRIM(Code)) > 0
        ORDER BY SelfRow
        """,
        chap, sec, res_type,
    )
    return [
        {
            "code": r[0],
            "minrow": r[1],
            "maxrow": r[2],
            "selfrow": r[3],
            "content": r[4] or "",
        }
        for r in cursor.fetchall()
    ]


def decode_labor_code(cursor, full_code: str) -> dict | None:
    """
    解碼 L 碼 (人力資源代碼)

    結構: L + 0000 + 0 + Sec06(2) + Sec07(1) + Sec08(1) + Sec09(1) + Sec10(1) + Sec11(1)
    解碼規則: 只有 available 完全為空才跳過 section (Code=[0] 空內容仍佔位)

    回傳: {"cName": str, "unitName": str} 或 None (解碼失敗)
    """
    if not full_code or not full_code.startswith("L") or len(full_code) != 13:
        return None

    chap = "0000"
    suffix = full_code[6:]  # 7碼: Sec06(2)+Sec07~11(各1)

    current_selfrow = None
    i = 0
    name_parts = []

    for sec in ["06", "07", "08", "09", "10", "11"]:
        sec_data = _get_sec_data(cursor, chap, sec, "L")
        if not sec_data:
            continue

        if current_selfrow is None:
            available = sec_data
        else:
            available = [
                d for d in sec_data
                if d["minrow"] <= current_selfrow <= d["maxrow"]
            ]

        if not available:
            continue

        digit_count = max(len(d["code"]) for d in available)
        if i + digit_count > len(suffix):
            return None

        code_val = suffix[i:i + digit_count]
        i += digit_count

        match = next((d for d in available if d["code"] == code_val), None)
        if not match:
            return None

        current_selfrow = match["selfrow"]
        if match["content"]:
            name_parts.append(match["content"])

    if i != len(suffix) or not name_parts:
        return None

    unit = name_parts[-1]
    cname_parts = name_parts[:-1]
    cname = "，".join(cname_parts) if cname_parts else unit

    return {"cName": cname, "unitName": unit}


def decode_equip_code(cursor, full_code: str) -> dict | None:
    """
    解碼 E 碼 (機具資源代碼)

    結構: E + 00000 + ChapCode(2) + suffix(5)
    解碼規則: 當某節有2位碼時，跳過下一節 (skip_next)

    回傳: {"cName": str, "unitName": str} 或 None (解碼失敗)
    """
    if not full_code or not full_code.startswith("E") or len(full_code) != 13:
        return None

    chap = full_code[6:8]   # ChapCode (2碼)
    suffix = full_code[8:]  # suffix (5碼)

    # 取得 ChapCode 的 Sec06 資料 (章節名稱 & SelfRow)
    sec06_data = _get_sec_data(cursor, chap, "06", "E")
    if not sec06_data:
        return None

    chap_entry = sec06_data[0]  # ChapCode 通常只有一個 Sec06 entry
    chap_name = chap_entry["content"]
    start_selfrow = chap_entry["selfrow"]

    current_selfrow = start_selfrow
    i = 0
    name_parts = [chap_name] if chap_name else []
    skip_next = False

    for sec in ["07", "08", "09", "10", "11"]:
        if skip_next:
            skip_next = False
            continue

        sec_data = _get_sec_data(cursor, chap, sec, "E")
        if not sec_data:
            continue

        available = [
            d for d in sec_data
            if d["minrow"] <= current_selfrow <= d["maxrow"]
        ]
        if not available:
            continue

        # 依代碼長度由長到短嘗試比對（處理同節混有1碼與2碼的情況）
        match = None
        matched_len = 0
        for clen in sorted({len(d["code"]) for d in available}, reverse=True):
            if i + clen > len(suffix):
                continue
            code_val = suffix[i:i + clen]
            match = next((d for d in available if d["code"] == code_val), None)
            if match:
                matched_len = clen
                break

        if not match:
            return None

        # 僅當匹配到2位碼時，下一節跳過
        skip_next = matched_len > 1
        i += matched_len

        current_selfrow = match["selfrow"]
        if match["content"]:
            name_parts.append(match["content"])

    if i != len(suffix) or not name_parts:
        return None

    unit = name_parts[-1]
    cname_parts = name_parts[:-1]
    cname = "，".join(cname_parts) if cname_parts else unit

    return {"cName": cname, "unitName": unit}


def decode_work_item_code(cursor, code10: str) -> dict | None:
    """
    解碼 PCCES 10碼工項代碼

    結構: ChapCode(5碼) + suffix(5碼)
    - ChapCode 查 AutoNumA 取得章節名稱
    - suffix 依序查 AutoNumB Sec06~Sec10，Sec06 不過濾(全部可用)，Sec07 以後用 MinRow/MaxRow 過濾

    回傳: {"chapName": str, "cName": str, "unitName": str} 或 None (解碼失敗)
    """
    if not code10 or len(code10) != 10:
        return None

    chap = code10[:5]
    suffix = code10[5:]

    cursor.execute("SELECT cName, RTRIM(IsShow) FROM AutoNumA WHERE RTRIM(itemCode) = ?", chap)
    r = cursor.fetchone()
    if not r:
        return None
    chap_name, chap_isshow = r[0], (r[1] or "").strip()

    cursor.execute(
        "SELECT COUNT(*) FROM AutoNumB WHERE ChapCode = ? AND CodeSection = '06'", chap
    )
    if cursor.fetchone()[0] == 0:
        return None

    current_selfrow = None  # Sec06: 全部可用，不過濾
    i = 0
    # 章節名稱只有 IsShow='*' 才加入名稱（例如 09500 天花板加入，03110 場鑄混凝土模板不加入）
    name_parts = [chap_name] if chap_isshow == "*" else []
    skip_next = False

    for sec in ["06", "07", "08", "09", "10"]:
        if skip_next:
            skip_next = False
            continue

        cursor.execute(
            """
            SELECT RTRIM(Code), MinRow, MaxRow, SelfRow, Content
            FROM AutoNumB
            WHERE ChapCode = ? AND CodeSection = ? AND Code IS NOT NULL AND LEN(RTRIM(Code)) > 0
            ORDER BY SelfRow
            """,
            chap, sec,
        )
        sec_data = [
            {
                "code": r[0],
                "minrow": r[1],
                "maxrow": r[2],
                "selfrow": r[3],
                "content": r[4] or "",
            }
            for r in cursor.fetchall()
        ]
        if not sec_data:
            continue

        if current_selfrow is None:
            available = sec_data  # Sec06: 全部可用
        else:
            available = [
                d for d in sec_data
                if d["minrow"] <= current_selfrow <= d["maxrow"]
            ]
        if not available:
            continue

        digit_count = max(len(d["code"]) for d in available)
        if digit_count == 0:
            continue
        if digit_count > 1:
            skip_next = True

        if i + digit_count > len(suffix):
            return None

        code_val = suffix[i:i + digit_count]
        i += digit_count

        match = next((d for d in available if d["code"] == code_val), None)
        if not match:
            return None

        current_selfrow = match["selfrow"]
        if match["content"]:
            name_parts.append(match["content"])

    if i != len(suffix) or not name_parts:
        return None

    unit = name_parts[-1]
    cname = "，".join(name_parts[:-1])
    return {"chapName": chap_name, "cName": cname, "unitName": unit}


def _load_all_sec_data(cursor, res_type: str) -> dict:
    """
    一次性載入 AutoNumB_12 中指定 res_type 的所有資料到記憶體。
    回傳 dict，key = (ChapCode, CodeSection)，value = list[dict]
    """
    cursor.execute(
        """
        SELECT RTRIM(ChapCode), RTRIM(CodeSection), RTRIM(Code), MinRow, MaxRow, SelfRow, Content
        FROM AutoNumB_12
        WHERE resType = ? AND Code IS NOT NULL AND LEN(RTRIM(Code)) > 0
        ORDER BY ChapCode, CodeSection, SelfRow
        """,
        res_type,
    )
    cache = {}
    for r in cursor.fetchall():
        chap, sec, code, minrow, maxrow, selfrow, content = r
        key = (chap, sec)
        if key not in cache:
            cache[key] = []
        cache[key].append({
            "code": code,
            "minrow": minrow,
            "maxrow": maxrow,
            "selfrow": selfrow,
            "content": content or "",
        })
    return cache


def _enumerate_paths(data_cache, chap, sections, current_selfrow,
                     suffix_chars, name_parts, target_len, skip_next=False):
    """
    遞迴列舉所有合法的代碼路徑。

    回傳 list of (suffix_str, name_parts_list)，
    其中 len(suffix_str) == target_len。
    """
    current_len = sum(len(c) for c in suffix_chars)
    if current_len > target_len:
        return []

    if not sections:
        if current_len == target_len and name_parts:
            return [("".join(suffix_chars), list(name_parts))]
        return []

    sec = sections[0]
    remaining = sections[1:]

    if skip_next:
        return _enumerate_paths(data_cache, chap, remaining, current_selfrow,
                                suffix_chars, name_parts, target_len, False)

    sec_data = data_cache.get((chap, sec), [])

    if not sec_data:
        # 此節無資料，跳過
        return _enumerate_paths(data_cache, chap, remaining, current_selfrow,
                                suffix_chars, name_parts, target_len, False)

    if current_selfrow is None:
        available = sec_data
    else:
        available = [d for d in sec_data
                     if d["minrow"] <= current_selfrow <= d["maxrow"]]

    if not available:
        # 沒有可用選項，跳過此節
        return _enumerate_paths(data_cache, chap, remaining, current_selfrow,
                                suffix_chars, name_parts, target_len, False)

    results = []
    for match in available:
        # 每個代碼用自身長度決定是否觸發 skip_next（處理混合1碼/2碼的情況）
        next_skip = len(match["code"]) > 1
        new_suffix = suffix_chars + [match["code"]]
        new_name = name_parts + ([match["content"]] if match["content"] else [])
        results.extend(
            _enumerate_paths(data_cache, chap, remaining, match["selfrow"],
                             new_suffix, new_name, target_len, next_skip)
        )
    return results


def _paths_to_records(paths, res_type, code_prefix):
    """將路徑列表轉換成資源代碼記錄"""
    records = []
    for suffix, name_parts in paths:
        if not name_parts:
            continue
        unit = name_parts[-1]
        cname_parts = name_parts[:-1]
        cname = "，".join(cname_parts) if cname_parts else unit
        records.append({
            "pccesCode": code_prefix + suffix,
            "cName": cname,
            "unitName": unit,
            "resType": res_type,
        })
    return records


def enumerate_labor_codes(cursor) -> list[dict]:
    """列舉所有可由演算法解碼的 L 碼（人力資源）"""
    data_cache = _load_all_sec_data(cursor, "L")
    chap = "0000"
    sec06_data = data_cache.get((chap, "06"), [])

    results = []
    for entry in sec06_data:
        paths = _enumerate_paths(
            data_cache, chap,
            ["07", "08", "09", "10", "11"],
            entry["selfrow"],
            [entry["code"]],                             # Sec06 已貢獻 2 字元
            [entry["content"]] if entry["content"] else [],
            target_len=7,                                # Sec06(2) + Sec07~11(5) = 7
        )
        results.extend(_paths_to_records(paths, "L", "L00000"))
    return results


def enumerate_equip_codes(cursor) -> list[dict]:
    """列舉所有可由演算法解碼的 E 碼（機具資源）"""
    data_cache = _load_all_sec_data(cursor, "E")

    # 取得所有 E 碼的 ChapCode（Sec06 的 ChapCode 即為代碼本身的 2 字元）
    chap_codes = sorted({k[0] for k in data_cache if k[1] == "06"})

    results = []
    for chap in chap_codes:
        sec06_data = data_cache.get((chap, "06"), [])
        if not sec06_data:
            continue
        chap_entry = sec06_data[0]
        chap_name = chap_entry["content"]
        start_selfrow = chap_entry["selfrow"]

        paths = _enumerate_paths(
            data_cache, chap,
            ["07", "08", "09", "10", "11"],
            start_selfrow,
            [],                                          # ChapCode 已寫入 code_prefix
            [chap_name] if chap_name else [],
            target_len=5,                                # Sec07~11 = 5 字元
        )
        results.extend(_paths_to_records(paths, "E", f"E00000{chap}"))
    return results


def build_code_index(cursor) -> list[dict]:
    """建立完整的 L + E 代碼索引（一次性列舉）"""
    index = []
    index.extend(enumerate_labor_codes(cursor))
    index.extend(enumerate_equip_codes(cursor))
    return index


def get_code_index(cursor) -> list[dict]:
    """取得全代碼索引（首次呼叫時建立，之後從快取回傳）"""
    global _CODE_INDEX
    if _CODE_INDEX is None:
        _CODE_INDEX = build_code_index(cursor)
    return _CODE_INDEX


def reset_code_index() -> None:
    """清除快取，強制下次重建（用於測試或資料更新後）"""
    global _CODE_INDEX
    _CODE_INDEX = None


def _load_work_item_sec_data(cursor, chap_code: str) -> dict:
    """一次性載入 AutoNumB 中指定章節的所有代碼資料"""
    cursor.execute(
        """
        SELECT RTRIM(CodeSection), RTRIM(Code), MinRow, MaxRow, SelfRow, Content
        FROM AutoNumB
        WHERE ChapCode = ? AND Code IS NOT NULL AND LEN(RTRIM(Code)) > 0
        ORDER BY CodeSection, SelfRow
        """,
        chap_code,
    )
    cache = {}
    for r in cursor.fetchall():
        sec, code, minrow, maxrow, selfrow, content = r
        key = (chap_code, sec)
        if key not in cache:
            cache[key] = []
        cache[key].append({
            "code": code,
            "minrow": minrow,
            "maxrow": maxrow,
            "selfrow": selfrow,
            "content": content or "",
        })
    return cache


def enumerate_work_item_codes(cursor, chap_code: str) -> list[dict]:
    """列舉指定章節的所有有效工項代碼（從 AutoNumB 演算法解碼）"""
    cursor.execute("SELECT cName, RTRIM(IsShow) FROM AutoNumA WHERE RTRIM(itemCode) = ?", chap_code)
    r = cursor.fetchone()
    if not r:
        return []
    chap_name, chap_isshow = r[0], (r[1] or "").strip()

    data_cache = _load_work_item_sec_data(cursor, chap_code)
    sec06_data = data_cache.get((chap_code, "06"), [])
    if not sec06_data:
        return []

    records = []
    for entry in sec06_data:
        # 章節名稱（AutoNumA.cName）只有 IsShow='*' 才加入；AutoNumB Sec06 的 Content 直接加入
        init_name = ([chap_name] if chap_isshow == "*" else [])
        if entry["content"]:
            init_name = init_name + [entry["content"]]
        paths = _enumerate_paths(
            data_cache, chap_code,
            ["07", "08", "09", "10"],
            entry["selfrow"],
            [entry["code"]],
            init_name,
            target_len=5,
        )
        for suffix, name_parts in paths:
            if not name_parts:
                continue
            unit = name_parts[-1]
            cname = "，".join(name_parts[:-1]) if len(name_parts) > 1 else name_parts[0]
            records.append({
                "pccesCode": chap_code + suffix,
                "cName": cname,
                "unitName": unit,
            })
    return records


def decode_resource_code(cursor, full_code: str) -> dict | None:
    """
    自動判斷資源代碼類型並解碼

    支援:
    - L 開頭: 人力代碼 (13碼)
    - E 開頭: 機具代碼 (13碼)

    回傳: {"cName": str, "unitName": str, "resType": str} 或 None
    """
    if not full_code:
        return None

    prefix = full_code[0].upper()
    if prefix == "L":
        result = decode_labor_code(cursor, full_code)
        if result:
            result["resType"] = "L"
        return result
    elif prefix == "E":
        result = decode_equip_code(cursor, full_code)
        if result:
            result["resType"] = "E"
        return result

    return None
