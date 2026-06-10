"""
통합 카테고리(교보 기준) → 각 서점 분류 ID 매핑.

- kyobo  : 교보 일간베스트 카테고리 코드. ✅ 전부 확인됨(사용자 제공).
- aladin : 알라딘 OpenAPI CategoryId. 확신하는 분류만 채움. None = 알라딘 건너뜀
           (None 인 분야는 교보만 표시됨. 알라딘 '모든 분야 카테고리' 엑셀에서
            CID 를 찾으면 채워 넣으면 됨: OpenAPI 안내 페이지 참고)
- yes24  : 예스24 분류번호. 현재 예스24는 OFF(collect.py) 라 미사용.
           켤 때 사이트에서 각 분야 categoryNumber 를 확인해 채울 것.

전체(all)는 aladin=0(전체 베스트), kyobo="" 로 동작.
"""

CATEGORIES = [
    # id,        label,            aladin CID,  yes24,  kyobo
    {"id": "all",      "label": "전체",          "aladin": 0,    "yes24": "001", "kyobo": ""},
    {"id": "novel",    "label": "소설",          "aladin": 1,    "yes24": "001001046", "kyobo": "01"},
    {"id": "essay",    "label": "시/에세이",     "aladin": 55889, "yes24": "001001047", "kyobo": "03"},
    {"id": "human",    "label": "인문",          "aladin": 656,  "yes24": "001001019", "kyobo": "05"},
    {"id": "home",     "label": "가정/육아",     "aladin": 2030, "yes24": "001001001", "kyobo": "07"},
    {"id": "cook",     "label": "요리",          "aladin": 1230, "yes24": "001001001001",    "kyobo": "08"},
    {"id": "health",   "label": "건강",          "aladin": 55890, "yes24": "001001011",    "kyobo": "09"},
    {"id": "hobby",    "label": "취미/실용/스포츠", "aladin": None, "yes24": "001001011",  "kyobo": "11"},
    {"id": "econ",     "label": "경제/경영",     "aladin": 170,  "yes24": "001001025", "kyobo": "13"},
    {"id": "self",     "label": "자기계발",      "aladin": 336,  "yes24": "001001026", "kyobo": "15"},
    {"id": "social",   "label": "정치/사회",     "aladin": 798,  "yes24": "001001022", "kyobo": "17"},
    {"id": "history",  "label": "역사/문화",     "aladin": 74,   "yes24": "001001010", "kyobo": "19"},
    {"id": "religion", "label": "종교",          "aladin": 1237, "yes24": "001001021",    "kyobo": "21"},
    {"id": "art",      "label": "예술/대중문화", "aladin": 517,  "yes24": "001001007", "kyobo": "23"},
    {"id": "ref_mh",   "label": "중/고등참고서", "aladin": None, "yes24": "",    "kyobo": "25"},
    {"id": "tech",     "label": "기술/공학",     "aladin": None, "yes24": "",    "kyobo": "26"},
    {"id": "lang",     "label": "외국어",        "aladin": 1322, "yes24": "001001004",    "kyobo": "27"},
    {"id": "science",  "label": "과학",          "aladin": 987,  "yes24": "001001002",    "kyobo": "29"},
    {"id": "exam",     "label": "취업/수험서",   "aladin": 1383, "yes24": "",    "kyobo": "31"},
    {"id": "travel",   "label": "여행",          "aladin": 1196, "yes24": "",    "kyobo": "32"},
    {"id": "it",       "label": "컴퓨터/IT",     "aladin": 351,  "yes24": "001001003",    "kyobo": "33"},
    {"id": "mag",      "label": "잡지",          "aladin": 2913, "yes24": "001001024",    "kyobo": "35"},
    {"id": "teen",     "label": "청소년",        "aladin": 1137, "yes24": "001001005",    "kyobo": "38"},
    {"id": "ref_e",    "label": "초등참고서",    "aladin": 50246, "yes24": "001001044",    "kyobo": "39"},
    {"id": "baby",     "label": "유아(0~7세)",   "aladin": 13789, "yes24": "001001027",    "kyobo": "41"},
    {"id": "kids",     "label": "어린이(초등)",  "aladin": 1108, "yes24": "001001016", "kyobo": "42"},
    {"id": "comic",    "label": "만화",          "aladin": 2551, "yes24": "001001008",    "kyobo": "47"},
]


def defs_for_frontend():
    return [{"id": c["id"], "label": c["label"]} for c in CATEGORIES]
