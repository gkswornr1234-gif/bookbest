"""
교보문고 — 온라인 일간 베스트

교보 내부 API는 'x-api-gw-key'(만료되는 임시 토큰)를 요구하는데, 이 키는
교보 페이지의 스크립트가 요청에 끼워 넣습니다. 빈손 fetch 로는 401 이 납니다.

→ 방법: Playwright 로 교보 페이지를 한 번 열면, 페이지가 스스로 API 를 호출하면서
  그 요청 헤더에 키를 담습니다. 그 키를 '가로채' 두었다가, 같은 키를 달고
  우리가 원하는 파라미터(per=50, 카테고리별)로 다시 호출합니다.
  키는 브라우저를 열 때마다 새로 얻으므로 만료 걱정이 없습니다.

준비(최초 1회): python -m playwright install chromium
테스트       : python -m sources.kyobo
"""
STORE_ID = "kyobo"
API = "https://store.kyobobook.co.kr/api/gw/best/best-seller/online"
PAGE = "https://store.kyobobook.co.kr/bestseller/online/daily"

_PAGE = None     # 공용 브라우저에서 받은 탭
_KEY = None      # 가로챈 x-api-gw-key


def _build_params(limit, category_code):
    if category_code:
        return {"page": 1, "per": limit, "period": "001",
                "dsplDvsnCode": "001", "dsplTrgtDvsnCode": "004",
                "saleCmdtClstCode": category_code}
    return {"page": 1, "per": limit, "period": "001",
            "dsplDvsnCode": "000", "dsplTrgtDvsnCode": "001"}


def _parse(payload, limit):
    rows = (payload or {}).get("data", {}).get("bestSeller", []) or []
    items = []
    for it in rows:
        items.append({
            "rank": it.get("prstRnkn"),
            "prev_rank_site": it.get("frmrRnkn"),
            "title": (it.get("cmdtName") or "").strip(),
            "author": (it.get("chrcName") or "").strip(),
            "publisher": (it.get("pbcmName") or "").strip(),
            "isbn": it.get("cmdtCode") or "",
            "price": it.get("sapr") or it.get("price"),
            "category": it.get("saleCmdtClstName") or "",
            "url": f"https://product.kyobobook.co.kr/detail/{it.get('saleCmdtid','')}",
        })
    items = [x for x in items if x["rank"]]
    items.sort(key=lambda x: x["rank"])
    return items[:limit]


def _ensure_page():
    """공용 브라우저에서 탭을 열고, 페이지가 보내는 API 요청에서 키를 가로챈다."""
    global _PAGE, _KEY
    if _PAGE is not None:
        return _PAGE
    from sources import browser
    page = browser.new_page()

    def on_request(req):
        global _KEY
        if _KEY is None and "/api/gw/best/best-seller/online" in req.url:
            k = req.headers.get("x-api-gw-key")
            if k:
                _KEY = k
    page.on("request", on_request)

    page.goto(PAGE, wait_until="networkidle", timeout=40000)
    for _ in range(20):
        if _KEY:
            break
        page.wait_for_timeout(300)
    _PAGE = page
    return page


def close():
    # 실제 브라우저 종료는 collect.py 가 browser.close_all() 로 한 번에 처리
    global _PAGE, _KEY
    _PAGE = None
    _KEY = None


def fetch(limit: int = 50, category_code: str = ""):
    page = _ensure_page()
    if not _KEY:
        raise RuntimeError("교보 인증 키(x-api-gw-key)를 가로채지 못했습니다.")
    params = {k: str(v) for k, v in _build_params(limit, category_code).items()}
    result = page.evaluate(
        """async ({api, params, key}) => {
            const qs = new URLSearchParams(params).toString();
            const res = await fetch(api + '?' + qs, {
                headers: {'Accept': 'application/json, text/plain, */*',
                          'x-api-gw-key': key},
                credentials: 'include'
            });
            if (!res.ok) throw new Error('HTTP ' + res.status);
            return await res.json();
        }""",
        {"api": API, "params": params, "key": _KEY},
    )
    return _parse(result, limit)


if __name__ == "__main__":
    try:
        print("[전체]")
        for b in fetch(10):
            print(f"  {b['rank']:>2} (전일 {b['prev_rank_site']:>3})  {b['title']}  [{b['category']}]")
        print("[소설 01]")
        for b in fetch(5, "01"):
            print(f"  {b['rank']:>2}  {b['title']}  [{b['category']}]")
    finally:
        close()
        from sources import browser
        browser.close_all()
