"""
전체 실행기: 카테고리별로 3사 수집 → 스냅샷 저장 → data.json 생성.

로컬 실행:
    pip install -r requirements.txt
    python -m playwright install chromium
    export ALADIN_TTB_KEY=...        # (Windows) set ALADIN_TTB_KEY=...
    python collect.py

- categories.py 의 CATEGORIES 를 돌며 각 서점에서 해당 분야 베스트를 받습니다.
- 한 서점/카테고리 수집이 실패해도 나머지는 진행합니다.
- 예스24/교보의 카테고리 ID가 비어 있거나 틀리면 그 분야는 자동으로 건너뜁니다.
"""
import traceback

import compare
import categories as cats
from sources import aladin, yes24, kyobo

# 예스24 ON (전체 카테고리는 categoryNumber=001 로 수집)
ENABLE_YES24 = True


def safe(label, fn):
    try:
        data = fn()
        print(f"    {label}: {len(data)}권")
        return data
    except Exception as e:
        print(f"    {label}: 실패 ({e.__class__.__name__}) {str(e)[:160]}")
        return []


def main():
    today_by_cat = {}
    for c in cats.CATEGORIES:
        cid, label = c["id"], c["label"]
        print(f"[{label}]")
        lists = {}

        # 개수: 전체(all)=50, 분야별=30
        N = 50 if c["id"] == "all" else 30

        # 알라딘 (CID 가 있을 때만; None = 알라딘 미지원 분야 → 건너뜀)
        if c.get("aladin") is not None:
            lists["aladin"] = safe("알라딘", lambda: aladin.fetch(N, category_id=c["aladin"]))

        # 예스24 (categoryNumber 있을 때만 + 스위치 ON 일 때만)
        if ENABLE_YES24 and c.get("yes24"):
            lists["yes"] = safe("예스24", lambda: yes24.fetch(N, category_number=c["yes24"]))

        # 교보 (kyobo 코드 있을 때만; 전체는 코드 없이 동작)
        if c["id"] == "all" or c.get("kyobo"):
            lists["kyobo"] = safe("교보문고", lambda: kyobo.fetch(N, category_code=c.get("kyobo", "")))

        if any(lists.values()):
            today_by_cat[cid] = lists

    payload = compare.build_all(today_by_cat)
    compare.save(payload)
    from sources import browser
    browser.close_all()   # 공용 브라우저(교보+예스24) 한 번에 정리


if __name__ == "__main__":
    main()
