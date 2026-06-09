"""
카테고리별 전날 대비 비교 + 3사 병합 → 프론트엔드용 data.json 생성.

스냅샷 구조(날짜별):  { "<catId>": { "<store>": [ {rank,title,...}, ... ] } }
data.json 구조:
  {
    generated_at, today, prev, surge_gap,
    categories: [ {id,label}, ... ],
    data: { "<catId>": { "books": [ {isbn,title,author,pub,
                                     kyobo:{t,p}|null, yes:..., aladin:...}, ... ] } }
  }
"""
import re
import os
import json
import glob
import datetime

import categories as cats

SURGE_GAP = 4
STORES = ["kyobo", "yes", "aladin"]   # 프론트엔드 키와 동일

HERE = os.path.dirname(__file__)
SNAP_DIR = os.path.join(HERE, "data", "snapshots")
OUT_PATH = os.path.join(HERE, "data.json")   # index.html 과 같은 위치


# ---------- 책 식별/매칭 ----------
def norm(s):
    s = (s or "").lower()
    s = re.sub(r"\(.*?\)|\[.*?\]", "", s)
    s = re.sub(r"[^0-9a-z가-힣]", "", s)
    return s


def author_core(s):
    s = (s or "").split(",")[0].split("·")[0]
    s = re.sub(r"(지음|저|글|옮김|엮음|편저|공저|그림)$", "", s.strip())
    return norm(s)[:12]


def _ta(it):
    return norm(it.get("title")) + "|" + author_core(it.get("author"))


def make_keyer(ta_to_isbn):
    def unikey(it):
        isbn = (it.get("isbn") or "").strip()
        if isbn:
            return "isbn:" + isbn
        ta = _ta(it)
        if ta in ta_to_isbn:
            return "isbn:" + ta_to_isbn[ta]
        return "ta:" + ta
    return unikey


def _bridge(today_lists):
    b = {}
    for items in today_lists.values():
        for it in (items or []):
            isbn = (it.get("isbn") or "").strip()
            if isbn:
                b.setdefault(_ta(it), isbn)
    return b


def _rankmap(lst, keyer):
    return {keyer(it): it["rank"] for it in (lst or [])}


# ---------- 한 카테고리 비교 ----------
def build_category(today_lists, prev_lists):
    """today_lists/prev_lists = {store: [items]} (한 카테고리). books 리스트 반환."""
    keyer = make_keyer(_bridge(today_lists))
    today_rm = {s: _rankmap(today_lists.get(s), keyer) for s in STORES}
    prev_rm = {s: _rankmap(prev_lists.get(s), keyer) for s in STORES}

    meta = {}
    for s in ["aladin", "kyobo", "yes"]:          # 메타데이터는 알라딘 우선
        for it in today_lists.get(s, []):
            k = keyer(it)
            if k not in meta or (not meta[k].get("isbn") and it.get("isbn")):
                meta[k] = it

    books = []
    # today 아이템을 키로 빠르게 찾기 위한 맵 (prev_rank_site 조회용)
    today_item = {}
    for s in STORES:
        for it in (today_lists.get(s) or []):
            today_item[(s, keyer(it))] = it

    for k in {kk for s in STORES for kk in today_rm[s]}:
        m = meta.get(k, {})
        entry = {"isbn": m.get("isbn", ""), "title": m.get("title", ""),
                 "author": m.get("author", ""), "pub": m.get("publisher", "")}
        for s in STORES:
            if k not in today_rm[s]:
                entry[s] = None
                continue
            t = today_rm[s][k]
            # 교보/예스: 서점이 직접 주는 전날 순위(prev_rank_site) 우선 사용.
            #   prev_rank_site 가 0 또는 None 이면 어제 순위권 밖 → NEW(p=None).
            # 알라딘: prev_rank_site 가 없으므로 우리 스냅샷 비교값 사용.
            p = prev_rm[s].get(k)
            if s in ("kyobo", "yes"):
                it = today_item.get((s, k), {})
                if "prev_rank_site" in it:
                    prs = it.get("prev_rank_site")
                    p = prs if (prs not in (0, None)) else None
            entry[s] = {"t": t, "p": p}
        books.append(entry)
    return books


# ---------- 스냅샷 ----------
def latest_prev_snapshot(today):
    prev_date, prev_data = None, {}
    for f in sorted(glob.glob(os.path.join(SNAP_DIR, "*.json"))):
        d = os.path.splitext(os.path.basename(f))[0]
        if d < today:
            prev_date = d
            with open(f, encoding="utf-8") as fp:
                prev_data = json.load(fp)
    return prev_date, prev_data


# ---------- 전체 빌드 ----------
def _kst_today():
    # GitHub 서버는 UTC 라서, 한국 날짜(KST=UTC+9)로 맞춰야 어제/오늘이 제대로 구분됨
    kst = datetime.timezone(datetime.timedelta(hours=9))
    return datetime.datetime.now(kst).date().isoformat()


def build_all(today_by_cat, today=None):
    """today_by_cat = { catId: { store: [items] } }"""
    today = today or _kst_today()

    os.makedirs(SNAP_DIR, exist_ok=True)
    with open(os.path.join(SNAP_DIR, f"{today}.json"), "w", encoding="utf-8") as fp:
        json.dump(today_by_cat, fp, ensure_ascii=False, indent=2)

    prev_date, prev_by_cat = latest_prev_snapshot(today)

    data = {}
    used_cats = []
    for c in cats.CATEGORIES:
        cid = c["id"]
        today_lists = today_by_cat.get(cid)
        if not today_lists:
            continue                       # 수집 안 된 카테고리는 건너뜀
        books = build_category(today_lists, prev_by_cat.get(cid, {}))
        if books:
            data[cid] = {"books": books}
            used_cats.append({"id": cid, "label": c["label"]})

    return {
        "generated_at": datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec="seconds"),
        "today": today,
        "prev": prev_date,
        "surge_gap": SURGE_GAP,
        "categories": used_cats,
        "data": data,
    }


def save(payload):
    with open(OUT_PATH, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, ensure_ascii=False, indent=2)
    total = sum(len(v["books"]) for v in payload["data"].values())
    print(f"data.json 생성: {len(payload['categories'])}개 카테고리, 총 {total}권 "
          f"(today={payload['today']}, prev={payload['prev']})")
