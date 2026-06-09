"""
공용 Playwright 브라우저.

교보·예스24가 각자 브라우저를 띄우면 한 프로세스 안에서 Playwright 가 충돌합니다
(Sync API inside asyncio loop). 그래서 '하나의 브라우저'를 함께 쓰도록 모읍니다.

- new_page() : 공용 브라우저에서 새 탭(page)을 하나 만들어 돌려줌
- close_all(): 수집이 모두 끝난 뒤 collect.py 가 한 번 호출해 정리
"""
_PW = None  # (playwright, browser)

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def _browser():
    global _PW
    if _PW is None:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        browser = pw.chromium.launch()
        _PW = (pw, browser)
    return _PW[1]


def new_page():
    return _browser().new_page(user_agent=_UA)


def close_all():
    global _PW
    if _PW:
        pw, browser = _PW
        try:
            browser.close(); pw.stop()
        except Exception:
            pass
        _PW = None
