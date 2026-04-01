"""
법제처 Open API 종합 법령 분석 모듈
- 법령, 행정규칙(훈령/예규/고시/지침), 판례, 해석례, 행정심판례 병렬 검색
- API 키: LAW_OC 환경변수 또는 호출 시 직접 전달
- 발급: https://open.law.go.kr/LSO/openApi/guideResult.do
"""

import os
import re
import urllib.request
import urllib.parse
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

LAW_API_BASE = "https://www.law.go.kr/DRF"
DEFAULT_DISPLAY = 5
_INVALID_KEYS = {"", "YOUR_API_KEY_HERE", "ryuseungin"}


def _load_dotenv():
    """앱 루트의 .env 파일에서 LAW_OC를 로드 (환경변수 미설정 시)"""
    if os.environ.get("LAW_OC"):
        return
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


_load_dotenv()


def _get_api_key():
    key = os.environ.get("LAW_OC", "").strip()
    return key if key not in _INVALID_KEYS else None


def _fetch(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; LawAnalyzer/1.0)",
            "Accept": "application/xml, text/xml, */*",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            return raw.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code == 401 or e.code == 403:
            return f"<error>API 키 인증 실패 (HTTP {e.code}). 법제처 키를 확인하세요.</error>"
        return f"<error>HTTP 오류 {e.code}: {e.reason}</error>"
    except urllib.error.URLError as e:
        reason = str(e.reason)
        if "403" in reason or "host_not_allowed" in reason or "Forbidden" in reason:
            return "<error>네트워크 차단: 이 서버 환경에서 law.go.kr 접근이 제한되어 있습니다. 로컬 환경에서 실행하세요.</error>"
        return f"<error>네트워크 연결 실패: {e.reason}. law.go.kr에 접근할 수 없습니다.</error>"
    except TimeoutError:
        return "<error>요청 시간 초과 (15초). 네트워크 상태를 확인하세요.</error>"
    except Exception as e:
        return f"<error>알 수 없는 오류: {e}</error>"


def _extract(content: str, tag: str) -> str:
    m = re.search(rf"<{tag}><!\[CDATA\[([\s\S]*?)\]\]></{tag}>", content)
    if m:
        return m.group(1).strip()
    m = re.search(rf"<{tag}>([\s\S]*?)</{tag}>", content)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return ""


def _parse_items(xml: str, root_tag: str, item_tag: str, fields: list) -> list:
    # 오류 응답 처리
    err_m = re.search(r"<error>([\s\S]*?)</error>", xml)
    if err_m:
        return []

    root_m = re.search(rf"<{root_tag}[^>]*>([\s\S]*?)</{root_tag}>", xml)
    if not root_m:
        return []

    body = root_m.group(1)
    items = []
    for m in re.finditer(rf"<{item_tag}[^>]*>([\s\S]*?)</{item_tag}>", body):
        item = {f: _extract(m.group(1), f) for f in fields}
        items.append(item)
    return items


def _get_error(xml: str) -> str:
    m = re.search(r"<error>([\s\S]*?)</error>", xml)
    return m.group(1).strip() if m else ""


def _build_url(endpoint: str, params: dict) -> str:
    return f"{LAW_API_BASE}/{endpoint}?{urllib.parse.urlencode(params, quote_via=urllib.parse.quote)}"


# ── 개별 검색 함수 ──────────────────────────────────────────────────

def search_law(query: str, api_key: str, display: int = DEFAULT_DISPLAY) -> dict:
    """법령 검색 (법률·시행령·시행규칙)"""
    url = _build_url("lawSearch.do", {
        "OC": api_key, "type": "XML", "target": "law",
        "query": query, "display": display,
    })
    xml = _fetch(url)
    err = _get_error(xml)
    items = _parse_items(xml, "LawSearch", "law", [
        "법령명", "법령명한글", "법령일련번호", "현행연혁코드",
        "공포일자", "공포번호", "소관부처명", "법령구분명",
        "시행일자", "법령상세링크",
    ])
    for it in items:
        if not it.get("법령명"):
            it["법령명"] = it.get("법령명한글", "")
    total = _extract(xml, "totalCnt")
    return {"category": "법령", "total": total, "items": items, "error": err}


def search_admin_rule(query: str, api_key: str, knd: str = "", display: int = DEFAULT_DISPLAY) -> dict:
    """행정규칙 검색 (훈령/예규/고시/공고/지침)"""
    knd_names = {"1": "훈령", "2": "예규", "3": "고시", "4": "공고", "5": "지침"}
    cat = knd_names.get(knd, "행정규칙")
    params = {"OC": api_key, "type": "XML", "target": "admrul", "query": query, "display": display}
    if knd:
        params["knd"] = knd
    xml = _fetch(_build_url("lawSearch.do", params))
    err = _get_error(xml)
    items = _parse_items(xml, "admrulSearch", "admrul", [
        "행정규칙명", "행정규칙종류", "발령기관명", "발령번호",
        "발령일자", "시행일자", "소관부처명", "행정규칙상세링크",
    ])
    total = _extract(xml, "totalCnt")
    return {"category": cat, "total": total, "items": items, "error": err}


def search_precedents(query: str, api_key: str, display: int = DEFAULT_DISPLAY) -> dict:
    """판례 검색"""
    url = _build_url("lawSearch.do", {
        "OC": api_key, "type": "XML", "target": "prec",
        "query": query, "display": display,
    })
    xml = _fetch(url)
    err = _get_error(xml)
    items = _parse_items(xml, "PrecSearch", "prec", [
        "사건명", "사건번호", "법원명", "선고일자", "판결유형", "판례상세링크",
    ])
    total = _extract(xml, "totalCnt")
    return {"category": "판례", "total": total, "items": items, "error": err}


def search_interpretations(query: str, api_key: str, display: int = DEFAULT_DISPLAY) -> dict:
    """법령해석례 검색"""
    url = _build_url("lawSearch.do", {
        "OC": api_key, "type": "XML", "target": "expc",
        "query": query, "display": display,
    })
    xml = _fetch(url)
    err = _get_error(xml)
    items = _parse_items(xml, "Expc", "expc", [
        "안건명", "안건번호", "회신일자", "회신기관명", "소관부처명",
        "질의요지", "회답", "법령해석례상세링크",
    ])
    total = _extract(xml, "totalCnt")
    return {"category": "해석례", "total": total, "items": items, "error": err}


def search_admin_appeals(query: str, api_key: str, display: int = DEFAULT_DISPLAY) -> dict:
    """행정심판례 검색"""
    url = _build_url("lawSearch.do", {
        "OC": api_key, "type": "XML", "target": "admAdj",
        "query": query, "display": display,
    })
    xml = _fetch(url)
    err = _get_error(xml)
    items = _parse_items(xml, "Decc", "decc", [
        "사건명", "사건번호", "처분일자", "의결일자",
        "처분청", "재결청", "재결구분명", "행정심판례상세링크",
    ])
    total = _extract(xml, "totalCnt")
    return {"category": "행정심판", "total": total, "items": items, "error": err}


# ── 종합 분석 (병렬) ─────────────────────────────────────────────────

def analyze(query: str, api_key: str = None) -> dict:
    """
    법령·훈령·예규·고시·지침·판례·해석례·행정심판례 병렬 검색

    Args:
        query:   검색어
        api_key: 법제처 Open API 키 (없으면 LAW_OC 환경변수 사용)

    Returns:
        {
          "query": str,
          "results": {
            "법령":   {"category", "total", "items": [...], "error"},
            "훈령":   {...},
            "예규":   {...},
            "고시":   {...},
            "지침":   {...},
            "판례":   {...},
            "해석례": {...},
            "행정심판": {...},
          }
        }
    """
    if not api_key:
        api_key = _get_api_key()
    if not api_key:
        return {
            "error": (
                "API 키가 설정되지 않았습니다.\n"
                "법제처 Open API(https://open.law.go.kr)에서 무료 발급 후\n"
                "LAW_OC 환경변수에 설정하거나 아래 입력란에 직접 입력하세요."
            )
        }

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
                results[name] = {
                    "category": name, "total": "0",
                    "items": [], "error": str(e),
                }

    return {"query": query, "results": results}
