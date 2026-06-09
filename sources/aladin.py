"""
알라딘 — 공식 OpenAPI (상품 리스트 API, QueryType=Bestseller)
TTBKey는 https://www.aladin.co.kr/ttb/wblog_manage.aspx 에서 발급 후
환경변수 ALADIN_TTB_KEY 로 넣어 둡니다.  (하루 5,000회 제한)

이 모듈만 별도로 테스트: python -m sources.aladin
"""
import os
import json
import requests

STORE_ID = "aladin"
API_URL = "https://www.aladin.co.kr/ttb/api/ItemList.aspx"


def fetch(max_results: int = 50, category_id: int = 0):
    key = os.environ.get("ALADIN_TTB_KEY")
    if not key:
        raise RuntimeError("환경변수 ALADIN_TTB_KEY 가 없습니다.")

    params = {
        "ttbkey": key,
        "QueryType": "Bestseller",   # 베스트셀러
        "SearchTarget": "Book",      # 국내도서
        "MaxResults": max_results,   # 최대 50
        "start": 1,
        "output": "js",              # JSON
        "Version": "20131101",
    }
    if category_id:                  # 0 = 전체
        params["CategoryId"] = category_id

    # 일시적 네트워크 흔들림 대비: 짧게 두 번까지 재시도
    last_err = None
    for attempt in range(2):
        try:
            r = requests.get(API_URL, params=params, timeout=15)
            r.raise_for_status()
            break
        except Exception as e:
            last_err = e
            if attempt == 0:
                import time; time.sleep(2)
            else:
                raise last_err

    # 알라딘 JSON 끝에 불필요한 세미콜론/개행이 붙는 경우가 있어 방어적으로 파싱
    text = r.text.strip().rstrip(";")
    data = json.loads(text)

    items = []
    for it in data.get("item", []):
        items.append({
            "rank": it.get("bestRank"),
            "title": (it.get("title") or "").strip(),
            "author": (it.get("author") or "").strip(),
            "publisher": (it.get("publisher") or "").strip(),
            "isbn": it.get("isbn13") or it.get("isbn") or "",
            "price": it.get("priceSales"),
            "url": it.get("link"),
        })
    items.sort(key=lambda x: x["rank"] or 9999)
    return items


if __name__ == "__main__":
    for b in fetch(10):
        print(b["rank"], b["title"], "/", b["author"], "/", b["isbn"])
