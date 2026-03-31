"""
법제처 Open API 종합 법령 분석 모듈
- 법령, 행정규칙(훈령/예규/고시/지침), 판례, 해석례 병렬 검색
"""

import os
import re
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

LAW_API_BASE = "https://www.law.go.kr/DRF"
DEFAULT_DISPLAY = 5


def _get_api_key():
    key = os.environ.get("LAW_OC", "")
    if not key or key in ("YOUR_API_KEY_HERE", "ryuseungin"):
        return None
    return key


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            return raw.decode("utf-8", errors="replace")
    except Exception as e:
        return f"<error>{e}</error>"


def _extract(content: str, tag: str) -> str:
    m = re.search(rf"<{tag}><!\[CDATA\[([\s\S]*?)\]\]></{tag}>", content)
    if m:
        return m.group(1).strip()
    m = re.search(rf"<{tag}>([\s\S]*?)</{tag}>", content)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return ""


def _parse_items(xml: str, root_tag: str, item_tag: str, fields: list[str]) -> list[dict]:
    root_m = re.search(rf"<{root_tag}[^>]*>([\s\S]*?)</{root_tag}>", xml)
    if not root_m:
        return []
    body = root_m.group(1)
    items = []
    for m in re.finditer(rf"<{item_tag}[^>]*>([\s\S]*?)</{item_tag}>", body):
        item = {f: _extract(m.group(1), f) for f in fields}
        items.append(item)
    return items


# ── 개별 검색 함수 ──────────────────────────────────────────────────

def search_law(query: str, api_key: str, display: int = DEFAULT_DISPLAY) -> dict:
    params = urllib.parse.urlencode({
        "OC": api_key, "type": "XML", "target": "law",
        "query": query, "display": display,
    })
    xml = _fetch(f"{LAW_API_BASE}/lawSearch.do?{params}")
    items = _parse_items(xml, "LawSearch", "law", [
        "법령명", "법령명한글", "법령일련번호", "현행연혁코드", "공포일자",
        "공포번호", "소관부처명", "법령구분명", "시행일자", "법령상세링크",
    ])
    # 법령명 정규화
    for it in items:
        if not it.get("법령명"):
            it["법령명"] = it.get("법령명한글", "")
    total = _extract(xml, "totalCnt")
    return {"category": "법령", "total": total, "items": items}


def search_admin_rule(query: str, api_key: str, knd: str = "", display: int = DEFAULT_DISPLAY) -> dict:
    knd_names = {"1": "훈령", "2": "예규", "3": "고시", "4": "공고", "5": "지침"}
    cat = knd_names.get(knd, "행정규칙")
    p = {"OC": api_key, "type": "XML", "target": "admrul", "query": query, "display": display}
    if knd:
        p["knd"] = knd
    params = urllib.parse.urlencode(p)
    xml = _fetch(f"{LAW_API_BASE}/lawSearch.do?{params}")
    items = _parse_items(xml, "admrulSearch", "admrul", [
        "행정규칙명", "행정규칙종류", "발령기관명", "발령번호", "발령일자",
        "시행일자", "소관부처명", "행정규칙상세링크",
    ])
    total = _extract(xml, "totalCnt")
    return {"category": cat, "total": total, "items": items}


def search_precedents(query: str, api_key: str, display: int = DEFAULT_DISPLAY) -> dict:
    params = urllib.parse.urlencode({
        "OC": api_key, "type": "XML", "target": "prec",
        "query": query, "display": display,
    })
    xml = _fetch(f"{LAW_API_BASE}/lawSearch.do?{params}")
    items = _parse_items(xml, "PrecSearch", "prec", [
        "사건명", "사건번호", "법원명", "선고일자", "판결유형", "판례상세링크",
    ])
    total = _extract(xml, "totalCnt")
    return {"category": "판례", "total": total, "items": items}


def search_interpretations(query: str, api_key: str, display: int = DEFAULT_DISPLAY) -> dict:
    params = urllib.parse.urlencode({
        "OC": api_key, "type": "XML", "target": "expc",
        "query": query, "display": display,
    })
    xml = _fetch(f"{LAW_API_BASE}/lawSearch.do?{params}")
    items = _parse_items(xml, "Expc", "expc", [
        "안건명", "안건번호", "회신일자", "회신기관명", "소관부처명",
        "질의요지", "회답", "법령해석례상세링크",
    ])
    total = _extract(xml, "totalCnt")
    return {"category": "해석례", "total": total, "items": items}


def search_admin_appeals(query: str, api_key: str, display: int = DEFAULT_DISPLAY) -> dict:
    params = urllib.parse.urlencode({
        "OC": api_key, "type": "XML", "target": "admAdj",
        "query": query, "display": display,
    })
    xml = _fetch(f"{LAW_API_BASE}/lawSearch.do?{params}")
    items = _parse_items(xml, "Decc", "decc", [
        "사건명", "사건번호", "처분일자", "의결일자", "처분청",
        "재결청", "재결구분명", "행정심판례상세링크",
    ])
    total = _extract(xml, "totalCnt")
    return {"category": "행정심판례", "total": total, "items": items}


# ── 종합 분석 (병렬) ─────────────────────────────────────────────────

def analyze(query: str, api_key: str = None) -> dict:
    """
    법령·훈령·예규·고시·지침·판례·해석례·행정심판례 병렬 검색
    """
    if not api_key:
        api_key = _get_api_key()
    if not api_key:
        return {"error": "API 키가 없습니다. 법제처(https://open.law.go.kr)에서 무료 발급 후 LAW_OC 환경변수에 설정하세요."}

    tasks = {
        "법령":     lambda: search_law(query, api_key),
        "훈령":     lambda: search_admin_rule(query, api_key, knd="1"),
        "예규":     lambda: search_admin_rule(query, api_key, knd="2"),
        "고시":     lambda: search_admin_rule(query, api_key, knd="3"),
        "지침":     lambda: search_admin_rule(query, api_key, knd="5"),
        "판례":     lambda: search_precedents(query, api_key),
        "해석례":   lambda: search_interpretations(query, api_key),
        "행정심판": lambda: search_admin_appeals(query, api_key),
    }

    results = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fn): name for name, fn in tasks.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except Exception as e:
                results[name] = {"category": name, "total": "0", "items": [], "error": str(e)}

    return {"query": query, "results": results}
