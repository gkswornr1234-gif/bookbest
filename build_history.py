"""
스냅샷(data/snapshots/*.json)들을 모아 도서별 순위 히스토리(history.json)를 만든다.
재수집(스크래핑) 없이 '이미 저장된' 데이터만 사용 → 차단 위험 없음.

history.json 구조:
  {
    "dates":  ["2026-06-12", ...],          # 오름차순(최근 90일)
    "stores": ["kyobo","yes","aladin"],
    "books": {
      "<gkey>": {
        "title","author","pub","isbn",
        "series": {                          # 카테고리별
          "all":  {"kyobo":[3,2,1,1], "yes":[...], "aladin":[...]},  # dates 와 길이 동일, 없으면 null
          "econ": { ... }
        }
      }
    }
  }

또한 data.json 각 책에 "hkey"(history 조회키)를 추가로 박아준다(프론트가 바로 조회).
"""
import os
import json
import glob

import compare  # norm / author_core / _ta 재사용 (동일 매칭 규칙)

HERE = os.path.dirname(__file__)
SNAP_DIR = os.path.join(HERE, "data", "snapshots")
HIST_PATH = os.path.join(HERE, "history.json")
DATA_PATH = os.path.join(HERE, "data.json")
STORES = ["kyobo", "yes", "aladin"]
MAX_DAYS = 90          # 너무 커지지 않게 최근 90일만


def _load_snapshots():
    out = []
    for f in sorted(glob.glob(os.path.join(SNAP_DIR, "*.json"))):
        d = os.path.splitext(os.path.basename(f))[0]
        try:
            with open(f, encoding="utf-8") as fp:
                out.append((d, json.load(fp)))
        except Exception:
            continue
    return out[-MAX_DAYS:]


def _global_bridge(snaps):
    """모든 날짜/카테고리/서점에서 (제목+저자)->ISBN 다리. 한 번이라도 ISBN 있으면 통일."""
    b = {}
    for _d, snap in snaps:
        for _cid, stores in snap.items():
            for _s, items in stores.items():
                for it in (items or []):
                    isbn = (it.get("isbn") or "").strip()
                    if isbn:
                        b.setdefault(compare._ta(it), isbn)
    return b


def _gkey(it, bridge):
    isbn = (it.get("isbn") or "").strip()
    if isbn:
        return "isbn:" + isbn
    ta = compare._ta(it)
    if ta in bridge:
        return "isbn:" + bridge[ta]
    return "ta:" + ta


def build():
    snaps = _load_snapshots()
    dates = [d for d, _ in snaps]
    if not dates:
        print("history: 스냅샷 없음 — 건너뜀")
        return
    dpos = {d: i for i, d in enumerate(dates)}
    bridge = _global_bridge(snaps)

    books = {}
    for d, snap in snaps:
        i = dpos[d]
        for cid, stores in snap.items():
            for s in STORES:
                for it in (stores.get(s) or []):
                    k = _gkey(it, bridge)
                    bk = books.get(k)
                    if bk is None:
                        bk = books[k] = {
                            "title": it.get("title", ""),
                            "author": it.get("author", ""),
                            "pub": it.get("publisher", ""),
                            "isbn": (it.get("isbn") or ""),
                            "series": {},
                        }
                    # ISBN 있는 항목을 메타 기준으로 선호(제목 표기 안정적)
                    if it.get("isbn") and not bk["isbn"]:
                        bk["isbn"] = it["isbn"]
                        bk["title"] = it.get("title", bk["title"])
                        bk["author"] = it.get("author", bk["author"])
                    ser = bk["series"].setdefault(cid, {})
                    arr = ser.get(s)
                    if arr is None:
                        arr = ser[s] = [None] * len(dates)
                    arr[i] = it.get("rank")

    payload = {"dates": dates, "stores": STORES, "books": books}
    with open(HIST_PATH, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, separators=(",", ":"))
    print(f"history.json 생성: {len(dates)}일치, 책 {len(books)}권")

    # data.json 각 책에 hkey 추가(있을 때만)
    if os.path.exists(DATA_PATH):
        with open(DATA_PATH, encoding="utf-8") as fp:
            data = json.load(fp)
        for cat in data.get("data", {}).values():
            for b in cat["books"]:
                it = {"isbn": b.get("isbn", ""),
                      "title": b.get("title", ""),
                      "author": b.get("author", "")}
                b["hkey"] = _gkey(it, bridge)
        with open(DATA_PATH, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
        print("data.json 에 hkey 추가 완료")


if __name__ == "__main__":
    build()
