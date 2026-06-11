"""
알라딘 — 어제(일간) 베스트셀러  (Playwright, 공용 브라우저 사용)

[변경 이유] 기존엔 공식 OpenAPI(QueryType=Bestseller)를 썼지만 그건 '주간'
베스트라, 교보·예스24의 '일간'과 기준이 달랐습니다. 그래서 '어제 베스트'
웹페이지(wbest.aspx?BestType=DailyBest)를 직접 읽어 일간으로 통일합니다.
(기존 OpenAPI 코드는 aladin_openapi_backup.py 로 보관)

페이지 구조(2026-06 확인):
  한 권     : div.ss_book_box            (itemId 속성 = 알라딘 상품 ItemId)
  순위      : 박스 등장 순서(1,2,3…)     (박스 안 "1." div 도 있으나 순서가 더 안전)
  제목      : a.bo3 의 '직접' 텍스트      (부제 span.ss_f_g2 는 제외)
  저자      : tit_category 다음 li 의 첫 번째 AuthorSearch 링크(대표 저자)
  출판사    : 같은 li 의 PublisherSearch 링크
  가격      : span.ss_p2 em              ("16,920원" → 16920)
  ISBN후보  : input[name^="chkCart."] 값
              · 숫자 10자리 = ISBN10 → ISBN13 으로 변환(교보와 매칭됨)
              · K… 로 시작 = 신간이라 ISBN 미발급 → 빈값(제목+저자로 매칭)
  상세URL   : a.bo3 href

일간 전체 : CID=0,  분야별 : CID={알라딘 분야 코드}
테스트    : python -m sources.aladin
"""
STORE_ID = "aladin"
BASE = "https://www.aladin.co.kr/shop/common/wbest.aspx"

from sources import delivery

_PAGE = None


def list_url(category_id=0):
    # cnt 를 넉넉히 줘서 한 페이지에 충분히 받음(우리는 상위 N개만 사용)
    return (f"{BASE}?BestType=DailyBest&BranchType=1"
            f"&CID={category_id}&cnt=200&SortOrder=1")


def _get_page():
    global _PAGE
    if _PAGE is None:
        from sources import browser
        _PAGE = browser.new_page()
    return _PAGE


def close():
    global _PAGE
    _PAGE = None


def _isbn10_to_13(s):
    """숫자 10자리 ISBN10 → ISBN13(978 접두 + 체크자리 재계산)."""
    s = (s or "").strip().upper()
    if len(s) != 10 or not s[:9].isdigit():
        return ""
    body = "978" + s[:9]
    total = 0
    for i, ch in enumerate(body):
        n = int(ch)
        total += n if i % 2 == 0 else n * 3
    check = (10 - (total % 10)) % 10
    return body + str(check)


# 페이지에서 책 목록을 뽑는 브라우저 측 스크립트(셀렉터는 위 docstring 과 일치)
_JS_EXTRACT = r"""
(limit) => {
    const txt = (el) => el ? el.textContent.trim() : '';
    const out = [];
    const boxes = document.querySelectorAll('div.ss_book_box');
    boxes.forEach((box) => {
        if (out.length >= limit) return;
        const a = box.querySelector('a.bo3');
        if (!a) return;

        // 제목: a.bo3 의 직접 텍스트 노드만(부제 span 제외)
        let title = '';
        a.childNodes.forEach((n) => { if (n.nodeType === 3) title += n.textContent; });
        title = (title || txt(a)).trim();
        if (!title) return;

        // ItemId (상세 URL 용)
        const mm = (a.getAttribute('href') || '').match(/ItemId=(\d+)/);
        const itemId = mm ? mm[1] : '';

        // 저자/출판사: tit_category 가 든 li 의 '다음' li
        let author = '', pub = '';
        const titCat = box.querySelector('.tit_category');
        if (titCat) {
            const liTitle = titCat.closest('li');
            const liMeta = liTitle ? liTitle.nextElementSibling : null;
            if (liMeta) {
                const a1 = liMeta.querySelector('a[href*="AuthorSearch"]');
                author = txt(a1);  // 대표(첫) 저자
                const p1 = liMeta.querySelector('a[href*="PublisherSearch"]');
                pub = txt(p1);
            }
        }

        // 가격: 할인가 ss_p2 em
        const priceStr = txt(box.querySelector('.ss_p2 em')).replace(/[^0-9]/g, '');
        const price = priceStr ? parseInt(priceStr, 10) : null;

        // 배송: span.a_black 에 정적으로 들어있음(예: "지금 택배로 주문하면 내일 수령",
        //       "…6월 17일 출고", "양탄자배송 …"). 배송 관련 문장만 골라낸다.
        let deliv = '';
        box.querySelectorAll('span.a_black').forEach((el) => {
            if (deliv) return;
            const t = txt(el).replace(/\s+/g, ' ');
            if (/주문하면|출고|수령|도착|발송|배송/.test(t)) deliv = t;
        });

        // ISBN 후보: chkCart.XXXX
        let code = '';
        const chk = box.querySelector('input[name^="chkCart."]');
        if (chk) { code = (chk.getAttribute('name') || '').split('.')[1] || ''; }

        out.push({title, author, pub, price, itemId, code, deliv});
    });
    return out;
}
"""


def _rows_to_items(rows, limit):
    items = []
    for i, r in enumerate(rows, start=1):
        code = (r.get("code") or "").strip()
        isbn = _isbn10_to_13(code) if (code.isdigit() and len(code) == 10) else ""
        items.append({
            "rank": i,
            "title": r["title"],
            "author": r.get("author", ""),
            "publisher": r.get("pub", ""),
            "isbn": isbn,                      # 신간(K…)은 빈값 → 제목+저자 매칭
            "price": r.get("price"),
            "ship": delivery.normalize(r.get("deliv")),
            "url": f"https://www.aladin.co.kr/shop/wproduct.aspx?ItemId={r.get('itemId','')}",
        })
    return items[:limit]


def _load_once(page, category_id, limit):
    page.goto(list_url(category_id), wait_until="domcontentloaded", timeout=40000)
    try:
        page.wait_for_selector("div.ss_book_box", state="attached", timeout=20000)
    except Exception:
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
    page.wait_for_timeout(500)
    return page.evaluate(_JS_EXTRACT, limit)


def fetch(limit: int = 50, category_id: int = 0):
    import time
    page = _get_page()
    rows = _load_once(page, category_id, limit)
    if not rows:
        # 0권일 때: 실제로 무슨 페이지가 왔는지 로그로 남기고(차단/캡차 여부 확인) 1회 재시도
        try:
            info = (f"title={page.title()!r} url={page.url} "
                    f"본문앞={page.inner_text('body')[:120].strip()!r}")
        except Exception as e:
            info = f"진단수집실패({e.__class__.__name__})"
        print(f"      [알라딘 0권 진단] {info}")
        time.sleep(3)
        rows = _load_once(page, category_id, limit)
        if rows:
            print(f"      [알라딘 재시도 성공] {len(rows)}권")
    return _rows_to_items(rows, limit)


if __name__ == "__main__":
    try:
        print("[알라딘 어제(일간) 전체 상위 10]")
        for b in fetch(10):
            print(f"  {b['rank']:>2}  {b['title']}  / {b['author']}  ({b['publisher']})  "
                  f"{b['price']}  isbn={b['isbn']}")
    finally:
        close()
        from sources import browser
        browser.close_all()
