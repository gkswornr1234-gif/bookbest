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


# 판본 구분자: 같은 제목이라도 한정판/일반판 등은 다른 책(SKU)이므로 키를 분리한다.
#   norm() 이 괄호를 지워 "…(한정판)" 과 "…" 가 같은 키가 되는 걸 막는다.
_EDITIONS = ("한정판", "특별판", "리미티드", "양장본", "개정판", "합본", "스페셜")


def _edition_tag(title):
    t = (title or "")
    for kw in _EDITIONS:
        if kw in t:
            return kw            # 모든 서점이 동일 키워드를 쓰면 서로 매칭됨
    return ""


def author_core(s):
    s = (s or "")
    # 여러 저자/역자 중 '첫 저자'만 사용: , · / '외' 앞에서 자른다
    #   예) "짐 머피 저/지여울 역" -> "짐 머피 저"
    s = re.split(r"[,/·]|\s외\b|\s외$", s)[0]
    # 끝쪽 역할어 제거(공백 뒤에 붙은 경우): 지음/저/글/옮김/역/엮음/편저/공저/그림/지은이/옮긴이
    #   만화 표기도 포함: 원저/원작/글그림/그림글 (알라딘 "(지은이)" vs 예스 "원저/글그림" 통일)
    #   예) "짐 머피 저" -> "짐 머피",  "야마다 카네히토 원저" -> "야마다 카네히토"
    s = re.sub(r"(\s+(지은이|옮긴이|글그림|그림글|원저|원작|지음|옮김|엮음|편저|공저|그림|글|저|역))+\s*$", "", s.strip())
    return norm(s)[:12]


def _core_title(title):
    # 판본 키워드를 본체에서 제거해 정규화 → "…(한정판)" 과 "… 한정판" 이 같은 본체가 됨
    t = (title or "")
    for kw in _EDITIONS:
        t = t.replace(kw, " ")
    return norm(t)


def _ta(it):
    # (판본 제거한 제목 본체) + 첫저자 + (판본 태그)
    #   → 한정판끼리는 서점 표기가 달라도 매칭되고, 한정판 vs 일반판은 분리됨
    return _core_title(it.get("title")) + "|" + author_core(it.get("author")) + "|" + _edition_tag(it.get("title"))


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
    # 같은 키가 둘 이상이면(드묾) 더 좋은(작은) 순위를 남긴다 — 상위 항목이 사라지지 않도록
    rm = {}
    for it in (lst or []):
        k = keyer(it); r = it["rank"]
        if k not in rm or r < rm[k]:
            rm[k] = r
    return rm


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
            it = today_item.get((s, k), {}) or {}
            # 교보만 서점 제공 전날순위(prev_rank_site) 사용 — 값이 정확함.
            #   prev_rank_site 가 0 또는 None 이면 어제 순위권 밖 → NEW(p=None).
            # 예스24·알라딘: 우리 스냅샷 비교값 사용.
            #   (예스24 prev_rank_site 는 대부분 null 로 누락돼 신뢰 불가)
            p = prev_rm[s].get(k)
            if s == "kyobo":
                if "prev_rank_site" in it:
                    prs = it.get("prev_rank_site")
                    p = prs if (prs not in (0, None)) else None
            entry[s] = {"t": t, "p": p, "ship": it.get("ship", "")}
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


def _store_has_data(snap_by_cat, store):
    """스냅샷(={cat:{store:[...]}})에서 해당 서점이 한 권이라도 있는지."""
    return any((snap_by_cat.get(cid) or {}).get(store) for cid in snap_by_cat)


def per_store_prev_snapshots(today):
    """서점별로, 그 서점 데이터가 '있는' 가장 최근 스냅샷(< today)을 고른다.
    한 서점이 어제 비었더라도(차단 등), 그 서점은 마지막 정상일과 비교하게 되어
    복구 직후 순위변동이 전부 NEW/급등으로 뜨는 문제를 막는다."""
    dated = []
    for f in sorted(glob.glob(os.path.join(SNAP_DIR, "*.json"))):
        d = os.path.splitext(os.path.basename(f))[0]
        if d < today:
            with open(f, encoding="utf-8") as fp:
                dated.append((d, json.load(fp)))
    dated.sort(key=lambda x: x[0])                 # 날짜 오름차순
    prev_date = dated[-1][0] if dated else None    # 표시용: 가장 최근 스냅샷
    chosen = {}                                    # store -> (date, snap_by_cat)
    for s in STORES:
        for d, snap in reversed(dated):            # 최신부터 거슬러 올라가며
            if _store_has_data(snap, s):
                chosen[s] = (d, snap)
                break
    return prev_date, chosen


def _prev_lists_for_cat(chosen, cid):
    """카테고리별 prev_lists = {store:[items]} 를 서점별 선택 스냅샷에서 조립."""
    out = {}
    for s in STORES:
        sel = chosen.get(s)
        if sel:
            out[s] = (sel[1].get(cid) or {}).get(s, []) or []
    return out


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

    prev_date, chosen = per_store_prev_snapshots(today)

    data = {}
    used_cats = []
    for c in cats.CATEGORIES:
        cid = c["id"]
        today_lists = today_by_cat.get(cid)
        if not today_lists:
            continue                       # 수집 안 된 카테고리는 건너뜀
        books = build_category(today_lists, _prev_lists_for_cat(chosen, cid))
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
