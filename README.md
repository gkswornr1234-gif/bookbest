# 일간 베스트셀러 3사 비교 (교보 · 예스24 · 알라딘)

매일 세 서점의 일간 베스트를 모아 **전날 대비 순위 변동 · 급등 · 신규 진입**을
한 화면에서 비교하는 프로젝트입니다.

```
collect.py            전체 실행기 (카테고리 루프 → 수집 → 스냅샷 → data.json)
compare.py            카테고리별 전날 대비 비교 · ISBN 매칭 · 병합
categories.py         통합 카테고리(교보 기준) → 각 서점 분류 ID 매핑
sources/aladin.py     알라딘 공식 OpenAPI (CategoryId 지원)  ← 바로 동작
sources/yes24.py      예스24 (Playwright)  ← 선택자 + 분류번호 확인 필요
sources/kyobo.py      교보문고 (Playwright) ← 선택자 + 분류코드 확인 필요
index.html            화면 (카테고리 필터 + data.json 로드, 없으면 샘플)
data.json             최신 결과 (프론트엔드가 읽음)
data/snapshots/       날짜별 원본 스냅샷 (전날 비교에 사용)
.github/workflows/    매일 자동 수집
```

## 카테고리 필터

화면 상단의 카테고리 칩(전체 · 소설 · 인문 · 정치/사회 · 역사/문화 · 과학 …)으로
분야별 베스트를 전환해 봅니다. 분야별 순위는 **그 카테고리 안에서의 순위**이며,
전날 대비 변동·급등도 카테고리별로 따로 계산됩니다.

카테고리 ↔ 각 서점 분류 ID 는 `categories.py` 에서 관리합니다.
- **알라딘**: CategoryId 핵심 분류는 이미 채워져 있어 바로 동작합니다.
  더 세분화하려면 알라딘 OpenAPI 안내의 '모든 분야 카테고리' 엑셀을 참고하세요.
- **예스24 / 교보**: 분류 ID/코드는 직접 확인이 필요합니다(아래).
  비어 있거나 틀린 분야는 수집 시 자동으로 건너뜁니다 → 화면에서 흐리게 표시됩니다.

예스24·교보 분류 ID 확인: 각 사이트에서 해당 분야 일간베스트로 들어간 뒤
주소창의 `categoryNumber`(예스24) 또는 경로/코드(교보)를 복사해 `categories.py` 에 넣습니다.

## 1. 준비

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

알라딘 TTBKey 발급(무료, 하루 5,000회):
https://www.aladin.co.kr/ttb/wblog_manage.aspx → 발급 후

```bash
export ALADIN_TTB_KEY=ttb본인키          # Windows: set ALADIN_TTB_KEY=...
```

## 2. 선택자 한 번 맞추기 (예스24 · 교보)

목록이 JS로 그려지므로, 한 번만 직접 확인해 `sources/*.py` 상단 `SEL` 을 채웁니다.

```bash
python -m sources.yes24 --discover    # 반복 많은 class 후보 출력
python -m sources.yes24               # 상위 10권이 나오면 성공
python -m sources.kyobo --discover    # 교보는 내부 JSON 엔드포인트 후보도 출력
python -m sources.kyobo
```

교보는 개발자도구(F12) → Network → Fetch/XHR 에서 책 목록이 담긴 JSON 요청을
찾으면, `sources/kyobo.py` 의 `use_api()` 로 더 가볍고 안정적으로 받을 수 있습니다.

## 3. 실행

```bash
python collect.py        # data.json 과 data/snapshots/오늘.json 생성
```

화면 확인: `index.html` 을 간단한 서버로 띄웁니다(파일 직접 열기는 fetch 가 막힘).

```bash
python -m http.server 8000   # http://localhost:8000 접속
```

> 첫날은 비교할 전날 스냅샷이 없어 변동 표시가 비어 있습니다. 둘째 날부터 정상 표시됩니다.

## 4. 매일 자동화 + 공개 (GitHub)

1. 이 폴더를 GitHub 리포지토리로 올립니다.
2. **Settings → Secrets and variables → Actions** 에 `ALADIN_TTB_KEY` 등록.
3. **Settings → Pages** 에서 소스를 `main` 브랜치 루트로 지정 → `index.html` 이 공개됨.
4. `.github/workflows/daily.yml` 이 매일 09:05(KST) 수집 후 결과를 커밋합니다.
   (`Actions` 탭의 **Run workflow** 로 수동 실행도 가능)

## 조정 포인트

- 카테고리 추가/수정: `categories.py` (라벨·각 서점 분류 ID). 프론트엔드 칩은 data.json 의 categories 를 따라갑니다.
- 급등 기준: `compare.py` 의 `SURGE_GAP` (기본 4계단).
- 등락 색: `index.html` 의 `--green`(상승) / `--red`(하락) — 주식식(상승 빨강)으로 바꾸려면 두 변수 값을 서로 바꾸면 됩니다.
- 수집 권수: `collect.py` 의 `fetch(n)` 인자.

## 참고

- 알라딘은 공식 API라 약관 내 사용입니다. 예스24·교보 수집은 각 사 이용약관을 확인하고
  과도한 호출을 피하세요(하루 1회면 충분). 개인·비상업 용도를 권장합니다.
- 책 식별은 ISBN13 우선, 없으면 제목+저자 정규화로 매칭합니다. 한쪽 서점만 ISBN을
  제공해도 제목+저자로 다리를 놓아 같은 책으로 합칩니다.
