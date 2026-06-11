"""
3사(교보·예스24·알라딘) 배송/출고 문구를 '한 가지 규칙'으로 통일한다.

규칙(사용자 합의):
  · 당일 계열(양탄자배송·잠들기전·당일배송·오늘 도착·새벽배송 등),
    그리고 교보의 재고-있음 빠른배송("내일(금) 오전 7시 전 도착" 류)
        → "당일 배송"
  · 출고/배송 예정일이 적힌 경우(예: "6월 17일 출고", "6/17 출고예정")
        → "M/D(요일) 출고예정"     예) "6/17(수) 출고예정"
  · 그 외 / 정보 없음
        → ""   (빈 문자열 = 표시 안 함)

판정 순서가 중요하다:
  1) 명시적 당일배송 단어
  2) 근시일 도착/발송 문구(오늘·내일·새벽·오전 + 도착·출발·발송)  ← 교보 빠른배송
  3) 날짜(M월D일 / M/D)
  '오늘'이라는 낱말만으로는 당일배송으로 보지 않는다.
  ('오늘 주문하면 6/17 출고' → 날짜로 잡혀 '출고예정' 이 됨)
"""
import re
from datetime import date, datetime, timedelta, timezone

_WD = "월화수목금토일"

# (1) 당일/즉시 배송을 뜻하는 '분명한' 표현(공백 제거 후 부분 일치)
_SAME_DAY = (
    "양탄자배송", "잠들기전", "당일배송", "오늘도착",
    "총알배송", "새벽배송", "바로드림", "오늘출발", "당일발송",
)
# (2) 교보·알라딘 등: "내일 오전 7시 전 도착", "내일 수령" 같은 재고-있음 빠른배송
_NEAR = ("오늘", "내일", "새벽", "오전")
_ARRIVE = ("도착", "출발", "발송", "수령")


def _kst_today():
    return (datetime.now(timezone.utc) + timedelta(hours=9)).date()


def _resolve(mo, da, today):
    today = today or _kst_today()
    for y in (today.year, today.year + 1):
        try:
            d = date(y, mo, da)
        except ValueError:
            return None
        # 출고일은 보통 가까운 미래 → 너무 과거면 내년으로 해석
        if d >= today - timedelta(days=20):
            return d
    return None


def normalize(raw, today=None):
    if not raw:
        return ""
    flat = raw.replace(" ", "")

    # 1) 명시적 당일배송 단어
    if any(k in flat for k in _SAME_DAY):
        return "당일 배송"

    # 2) 근시일 도착/발송 (교보 빠른배송) → 당일 배송
    #    단, 미래 날짜가 박혀 있으면 그 날짜(출고예정)를 우선한다.
    has_date = re.search(r"\d{1,2}\s*월\s*\d{1,2}\s*일", raw) or re.search(r"\d{1,2}/\d{1,2}", raw)
    if not has_date and any(n in flat for n in _NEAR) and any(a in flat for a in _ARRIVE):
        return "당일 배송"

    # 3) 출고/배송 예정일
    m = (re.search(r"(\d{1,2})\s*월\s*(\d{1,2})\s*일", raw)
         or re.search(r"(\d{1,2})/(\d{1,2})", raw))
    if m:
        mo, da = int(m.group(1)), int(m.group(2))
        d = _resolve(mo, da, today)
        if d:
            return f"{mo}/{da}({_WD[d.weekday()]}) 출고예정"
        return f"{mo}/{da} 출고예정"

    return ""


if __name__ == "__main__":
    T = date(2026, 6, 11)   # 테스트 기준일 고정
    cases = [
        # (서점, 원문, 기대값)
        ("교보", "내일(금) 오전 7시 전 도착", "당일 배송"),
        ("교보", "6/17(수) 출고예정", "6/17(수) 출고예정"),
        ("알라딘", "지금 택배로 주문하면 6월 17일 출고", "6/17(수) 출고예정"),
        ("알라딘", "양탄자배송 밤 11시 잠들기전 배송", "당일 배송"),
        ("예스24", "당일배송 오늘(목) 도착", "당일 배송"),
        ("함정", "오늘 주문하면 6/17 출고", "6/17(수) 출고예정"),  # '오늘'에 속으면 안 됨
        ("없음", "", ""),
    ]
    ok = True
    for store, raw, want in cases:
        got = normalize(raw, today=T)
        mark = "OK " if got == want else "FAIL"
        if got != want:
            ok = False
        print(f"[{mark}] {store:4} {raw!r:42} -> {got!r}")
    print("\n전부 통과 ✅" if ok else "\n불일치 있음 ❌")
