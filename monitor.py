"""ふもとっぱら 予約空き監視（× → △/〇 で Slack or LINE 通知）"""
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.request

from playwright.sync_api import sync_playwright

URL = "https://reserve.fumotoppara.net/reserved/reserved-date-selection"
FUMO_ID = os.environ["FUMO_ID"]
FUMO_PW = os.environ["FUMO_PW"]
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
LINE_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_USER_ID = os.environ.get("LINE_USER_ID", "")
SITES = [s.strip() for s in os.environ.get("SITES", "キャンプ宿泊").split(",") if s.strip()]
DRY_RUN = os.environ.get("DRY_RUN", "0") == "1"
TARGET_DATES = sorted(
    d for d in (dt.date.fromisoformat(s.strip()) for s in os.environ["TARGET_DATES"].split(",") if s.strip())
    if d >= dt.date.today()
)

STATE_FILE = pathlib.Path("state.json")
DEBUG_DIR = pathlib.Path("debug")
AVAILABLE = {"〇", "○", "◯", "△"}
WEEK = "月火水木金土日"

# table.calendar-table を {施設名: {"10/24": "△ 残3", ...}} に変換
READ_TABLE_JS = r"""
() => {
  const rows = [...document.querySelectorAll('table.calendar-table tr')];
  if (!rows.length) return null;
  const head = [...rows[0].children].map(c => c.innerText.trim().split(/\s+/)[0]);
  const out = {};
  for (const r of rows.slice(1)) {
    const cells = [...r.children];
    const site = cells[0].innerText.trim();
    out[site] = {};
    cells.slice(1).forEach((c, i) => { out[site][head[i + 1]] = c.innerText.replace(/\s+/g, ' ').trim(); });
  }
  return out;
}
"""


def notify(text: str) -> None:
    if DRY_RUN:
        print("[DRY_RUN notify]", text)
        return
    if SLACK_WEBHOOK_URL:
        req = urllib.request.Request(
            SLACK_WEBHOOK_URL,
            data=json.dumps({"text": text}).encode(),
            headers={"Content-Type": "application/json"},
        )
    else:
        req = urllib.request.Request(
            "https://api.line.me/v2/bot/message/push",
            data=json.dumps({"to": LINE_USER_ID, "messages": [{"type": "text", "text": text}]}).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {LINE_TOKEN}"},
        )
    urllib.request.urlopen(req, timeout=20)


def fetch_table() -> dict:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(locale="ja-JP", timezone_id="Asia/Tokyo", viewport={"width": 1200, "height": 900})
        page.goto(URL, wait_until="networkidle")
        page.wait_for_selector("input[type=password], table.calendar-table", timeout=20000)
        if page.locator("input[type=password]").count():
            page.locator("input[type=text]").first.fill(FUMO_ID)
            page.locator("input[type=password]").first.fill(FUMO_PW)
            page.get_by_role("button", name="ログイン").first.click()
            page.wait_for_selector("input[type=password]", state="detached", timeout=20000)
            page.wait_for_timeout(2000)
            if not page.locator("table.calendar-table").count():
                page.goto(URL, wait_until="networkidle")
        try:
            page.wait_for_selector("table.calendar-table", timeout=20000)
            return page.evaluate(READ_TABLE_JS)
        except Exception:
            DEBUG_DIR.mkdir(exist_ok=True)
            page.screenshot(path=str(DEBUG_DIR / "error.png"), full_page=True)
            raise
        finally:
            browser.close()


def main() -> int:
    if not TARGET_DATES:
        print("監視対象の日付がありません")
        return 0
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    table = fetch_table()
    missing = []

    for site in SITES:
        row = table.get(site)
        if row is None:
            missing.append(f"施設が見つからない: {site}（候補: {', '.join(table)}）")
            continue
        for d in TARGET_DATES:
            cell = row.get(f"{d.month}/{d.day}")
            if cell is None:
                print(f"{d}: 表示範囲外（スキップ）")
                continue
            symbol = cell[:1]
            key = f"{site}|{d.isoformat()}"
            prev = state.get(key)
            print(f"{site} {d}: {prev} -> {cell}")
            if symbol in AVAILABLE and prev not in AVAILABLE:
                notify(f"⛺ ふもとっぱら {site} {d.month}/{d.day}({WEEK[d.weekday()]}) が「{cell}」になりました！\n{URL}")
            state[key] = symbol

    today = dt.date.today()
    state = {k: v for k, v in state.items() if dt.date.fromisoformat(k.split("|")[1]) >= today}
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True))

    if missing:
        print("\n".join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
