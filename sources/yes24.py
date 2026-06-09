"""
예스24 — 일간 베스트 (Playwright, 공용 브라우저 사용)

예스24는 목록을 페이지 HTML 에 직접 담아 보냅니다(별도 JSON 없음).
실제 구조 확인 완료(2026-06, yes24_debug.html 분석):
  한 권   : <li data-goods-no="147560984">     (id=bestSellerList 아님!)
  순위    : em.ico.rank
  순위변동: .rank_info (".. 위 상승/하락")  → prev_rank_site 로 참고 저장
  제목    : a.gd_name
  저자    : .info_auth        ("김애란 저" → '저' 제거)
  출판사  : .info_pub
  가격    : .info_price .yes_b ("15,120")
  상세URL : /product/goods/{data-goods-no}

준비(최초 1회): python -m playwright install chromium
테스트       : python -m sources.yes24
"""
STORE_ID = "yes"
BASE = "https://www.yes24.com/product/category/daybestseller"

_PAGE = None


def list_url(category_number="001", size=24):
    return (f"{BASE}?categoryNumber={category_number}"
            f"&pageNumber=1&pageSize={size}&type=day")


def _get_page():
    global _PAGE
    if _PAGE is None:
        from sources import browser
        _PAGE = browser.new_page()
    return _PAGE


def close():
    global _PAGE
    _PAGE = None


def fetch(limit: int = 24, category_number: str = "001"):
    page = _get_page()
    page.goto(list_url(category_number, size=limit), wait_until="domcontentloaded", timeout=40000)
    try:
        page.wait_for_selector("li[data-goods-no]", state="attached", timeout=20000)
    except Exception:
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
    page.wait_for_timeout(600)

    rows = page.evaluate(
        """(limit) => {
            const txt = (el) => el ? el.textContent.trim() : '';
            const out = [];
            const items = document.querySelectorAll('li[data-goods-no]');
            items.forEach((li) => {
                if (out.length >= limit) return;
                const goods = li.getAttribute('data-goods-no') || '';
                const title = txt(li.querySelector('a.gd_name'));
                if (!title) return;
                const rankEl = li.querySelector('em.ico.rank');
                const rank = rankEl ? parseInt(txt(rankEl), 10) : (out.length + 1);

                // 순위 변동(있으면): '16 위 상승' / '3 위 하락'
                let prev = null;
                const ri = li.querySelector('.rank_info');
                if (ri) {
                    const n = parseInt(txt(li.querySelector('.rank_info .txt.rank')), 10);
                    if (!isNaN(n)) {
                        if (ri.className.indexOf('rank_up') >= 0) prev = rank + n;
                        else if (ri.className.indexOf('rank_down') >= 0) prev = rank - n;
                    }
                }

                let author = txt(li.querySelector('.info_auth')).replace(/\\s*저$/, '').trim();
                const pub = txt(li.querySelector('.info_pub'));
                const priceStr = txt(li.querySelector('.info_price .yes_b')).replace(/[^0-9]/g, '');
                const price = priceStr ? parseInt(priceStr, 10) : null;

                out.push({rank, prev, title, author, pub, price, goods});
            });
            return out;
        }""",
        limit,
    )

    items = []
    for r in rows:
        items.append({
            "rank": r["rank"],
            "prev_rank_site": r.get("prev"),
            "title": r["title"],
            "author": r.get("author", ""),
            "publisher": r.get("pub", ""),
            "isbn": "",   # 목록에 ISBN 없음 → 제목+저자로 매칭
            "price": r.get("price"),
            "category": "",
            "url": f"https://www.yes24.com/product/goods/{r.get('goods','')}",
        })
    items.sort(key=lambda x: x["rank"])
    return items[:limit]


if __name__ == "__main__":
    try:
        print("[예스24 전체 일간 상위 10]")
        for b in fetch(10):
            mv = "" if b["prev_rank_site"] is None else f"(전일 {b['prev_rank_site']})"
            print(f"  {b['rank']:>2} {mv:>9}  {b['title']}  / {b['author']}  ({b['publisher']}) {b['price']}")
    finally:
        close()
        from sources import browser
        browser.close_all()
