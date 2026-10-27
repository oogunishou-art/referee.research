#!/usr/bin/env python3
# © 2026 大國将 (Shou Ooguni). All Rights Reserved.
# 無断複製・改変・再配布・リバースエンジニアリングを禁じます。
"""
B.LEAGUE公式の試合ページを「試合ID（ScheduleKey）の番号順」に開き、
審判欄に加藤誉樹さんの名前がある試合を games.json に保存する。

・調べ終わったIDは scan_state.json に記録し、次回からは飛ばす
・まだ行われていない試合が続いたら、その回は終了（=最新まで追いついた）
・ページは本物のブラウザ（Playwright）で開くので、後から読み込まれる情報も拾える
"""
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

# ---------------- 設定 ----------------
JST = ZoneInfo("Asia/Tokyo")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES_PATH = os.path.join(ROOT, "games.json")
STATE_PATH = os.path.join(ROOT, "scan_state.json")
DEBUG_DIR = os.path.join(ROOT, "debug")

PAGE_URL = os.environ.get("PAGE_URL", "https://www.bleague.jp/game_detail/?ScheduleKey={key}&tab=4")
START_KEY = int(os.environ.get("START_KEY", "506300"))  # 今シーズン序盤の試合IDより少し前
SEASON_START = date(2026, 9, 1)     # これより前の試合は対象外
DONE_AFTER_DAYS = 2                 # 試合日から2日たったら「調査済み」にする（審判情報の掲載待ち）
STOP_AFTER_FUTURE = 25              # 未来の試合がこれだけ続いたら終了
STOP_AFTER_MISSING = 40             # 存在しないIDがこれだけ続いたら終了
STOP_AFTER_ERRORS = 8               # 接続エラーがこれだけ続いたら中断
MAX_PAGES = int(os.environ.get("MAX_PAGES", "500"))
WAIT_MS = int(os.environ.get("WAIT_MS", "1500"))  # ページごとの待ち時間（相手サイトへの配慮）

TARGET = re.compile(r"加藤[\s\u3000]*誉樹")
DATE_RE = re.compile(r"(20\d{2})\s*[./年\-]\s*(\d{1,2})\s*[./月\-]\s*(\d{1,2})")
VS_RE = re.compile(r"([^\s|｜<>\[\]()（）]{2,20})\s*(?:vs\.?|VS|ＶＳ)\s*([^\s|｜<>\[\]()（）]{2,20})")
ROLE_RE = re.compile(
    r"^(?:審判員?|レフェリー|クルーチーフ|アンパイア\s*[12１２]?|主審|副審|CC|U1|U2|"
    r"Crew\s*Chief|Umpire\s*\d?|Referees?)\s*[:：]?\s*",
    re.I,
)
NAME_CH = r"[一-龥々〆ヵヶァ-ヴーぁ-ん]"
NAME_RE = re.compile(rf"{NAME_CH}{{1,5}}[ \u3000]{NAME_CH}{{1,5}}")  # 姓と名の間に空白がある表記
WEEKDAYS = "月火水木金土日"


# ---------------- 補助 ----------------
def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def fmt_date(d):
    return f"{d.isoformat()} ({WEEKDAYS[d.weekday()]})"


def find_date(*texts):
    for t in texts:
        for m in DATE_RE.finditer(t or ""):
            y, mo, da = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if 2025 <= y <= 2028:
                try:
                    return date(y, mo, da)
                except ValueError:
                    continue
    return None


def strip_role(s):
    return ROLE_RE.sub("", s.strip()).strip()


def norm_name(s):
    s = s.replace("\u3000", " ").strip()
    if " " not in s and len(s) >= 3:
        return s  # 区切りが無い表記はそのまま
    return re.sub(r"\s+", " ", s)


def as_name(s):
    """名前らしい行なら正規化した名前を、そうでなければ None を返す"""
    t = strip_role(s)
    t = re.sub(r"\s*[（(#＃]?\s*\d{1,3}\s*[）)]?$", "", t).strip()  # 「加藤 誉樹 (77)」など
    if TARGET.fullmatch(t):
        return "加藤 誉樹"
    if NAME_RE.fullmatch(t):
        return norm_name(t)
    return None


SECTION_RE = re.compile(r"^(?:審判員?|レフェリー|Referees?)\s*[:：]?$", re.I)


def is_role_only(s):
    return bool(ROLE_RE.fullmatch(s.strip() + " "))


def is_name(s):
    return as_name(s) is not None


def is_referee_hit(lines):
    """審判欄に加藤誉樹さんが載っているか（記事中の言及などは除く）"""
    for l in lines:
        if not TARGET.search(l):
            continue
        if as_name(l) == "加藤 誉樹":
            return True
        if re.search(r"(審判|レフェリー|クルーチーフ|主審|Referee|Crew)", l, re.I):
            return True
        if any(as_name(p) == "加藤 誉樹" for p in re.split(r"[／/、,・|｜]", l)):
            return True
    return False


def extract_crew(lines):
    """加藤誉樹さんを含む審判クルー表記を作る。見つからなければ「加藤 誉樹 ほか」。"""
    idx = next((i for i, l in enumerate(lines) if TARGET.search(l)), None)
    if idx is None:
        return "加藤 誉樹 ほか"

    # 1) 1行に複数名が並んでいる場合（例：審判：加藤 誉樹 / ○○ ○○ / ○○ ○○）
    line = lines[idx]
    body = re.sub(r"^.*?(?:審判員?|レフェリー|クルーチーフ)\s*[:：]?\s*", "", line)
    parts = [p for p in re.split(r"[／/、,・|｜]", body) if p.strip()]
    names = [as_name(p) for p in parts if as_name(p)]
    if len(names) >= 2:
        return " ／ ".join(names[:4])

    # 2) 1行に1人ずつ並んでいる場合：加藤さんの行と「連続している名前の行」だけを集める
    #    （離れた位置にある選手名を拾わないため）
    lo = idx
    while lo - 1 >= 0 and idx - (lo - 1) <= 6 and (is_name(lines[lo - 1]) or is_role_only(lines[lo - 1])):
        lo -= 1
        if SECTION_RE.match(lines[lo].strip()):
            break  # 「審判」の見出しより上（選手一覧など）は見ない
    hi = idx
    while hi + 1 < len(lines) and (hi + 1) - idx <= 6 and (is_name(lines[hi + 1]) or is_role_only(lines[hi + 1])):
        hi += 1
    names = []
    for l in lines[lo:hi + 1]:
        n = as_name(l)
        if n and n not in names:
            names.append(n)
    if "加藤 誉樹" in names and len(names) >= 2:
        others = [n for n in names if n != "加藤 誉樹"][:2]  # 3人制：加藤さん＋2名
        return " ／ ".join(["加藤 誉樹"] + others)
    return "加藤 誉樹 ほか"


def extract_match(title, lines):
    for t in [title] + lines[:80]:
        m = VS_RE.search(t or "")
        if m:
            return f"{m.group(1)} vs {m.group(2)}"
    return ""


def extract_venue(lines):
    for i, l in enumerate(lines):
        s = l.strip()
        if s in ("会場", "会場：", "会場:") and i + 1 < len(lines):
            v = lines[i + 1].strip()
            return v if len(v) <= 40 else ""
        m = re.match(r"^会場\s*[:：]\s*(.{2,40})$", s)
        if m:
            return m.group(1).strip()
    return ""


def save_debug(name, key, url, title, text):
    os.makedirs(DEBUG_DIR, exist_ok=True)
    with open(os.path.join(DEBUG_DIR, name), "w", encoding="utf-8") as f:
        f.write(f"# ScheduleKey={key}\n# URL={url}\n# TITLE={title}\n# 取得: {datetime.now(JST).isoformat(timespec='seconds')}\n\n")
        f.write(text[:20000])


# ---------------- ページ取得 ----------------
def fetch_page(page, key):
    """(状態, タイトル, 本文) を返す。状態は ok / missing / error"""
    url = PAGE_URL.format(key=key)
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:  # noqa: BLE001
        print(f"  ! {key}: 接続エラー {type(e).__name__}")
        return "error", "", "", url
    if resp is not None and resp.status == 404:
        return "missing", "", "", url
    if resp is not None and resp.status >= 500:
        return "error", "", "", url

    # 後から読み込まれる情報を待つ：本文の長さが落ち着くまで最大10秒
    text, last_len, stable = "", -1, 0
    for _ in range(20):
        try:
            text = page.inner_text("body", timeout=5000)
        except Exception:  # noqa: BLE001
            text = ""
        if len(text) == last_len and len(text) > 40:
            stable += 1
            if stable >= 2:
                break
        else:
            stable = 0
        last_len = len(text)
        page.wait_for_timeout(500)
    try:
        title = page.title()
    except Exception:  # noqa: BLE001
        title = ""
    return "ok", title, text, url


# ---------------- メイン ----------------
def main():
    today = datetime.now(JST).date()
    games_doc = load_json(GAMES_PATH, {"games": []})
    games = {str(g["key"]): g for g in games_doc.get("games", []) if g.get("key")}

    state = load_json(STATE_PATH, None)
    if state is None:
        # 初回：手入力で登録済みの試合も公式ページで確かめ直す
        state = {"done": [], "max_seen": START_KEY}
    done = set(str(k) for k in state.get("done", []))
    max_seen = int(state.get("max_seen", START_KEY))

    stats = {"pages": 0, "new": 0, "updated": 0}
    future_run = missing_run = error_run = 0
    aborted = False
    saved_sample = saved_hit = saved_loose = False

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(locale="ja-JP", timezone_id="Asia/Tokyo")
        page = ctx.new_page()

        key = START_KEY
        while stats["pages"] < MAX_PAGES:
            k = str(key)
            if k in done:
                key += 1
                continue

            status, title, text, url = fetch_page(page, k)
            stats["pages"] += 1

            if status == "error":
                error_run += 1
                if error_run >= STOP_AFTER_ERRORS:
                    print("公式サイトに接続できないため中断します")
                    aborted = True
                    break
                key += 1
                page.wait_for_timeout(WAIT_MS)
                continue
            error_run = 0

            lines = [l.strip() for l in text.splitlines() if l.strip()]
            gdate = find_date(title, "\n".join(lines[:150]))

            if status == "missing" or gdate is None:
                missing_run += 1
                if key < max_seen:
                    done.add(k)  # 後ろに試合があるIDは、今後も存在しないとみなす
                print(f"  - {k}: 試合なし")
                if missing_run >= STOP_AFTER_MISSING and key > max_seen:
                    print("存在しないIDが続いたので終了")
                    break
                key += 1
                page.wait_for_timeout(WAIT_MS)
                continue

            missing_run = 0
            max_seen = max(max_seen, key)
            if not saved_sample:
                save_debug("sample_page.txt", k, url, title, text)
                saved_sample = True

            hit = is_referee_hit(lines)
            loose = not hit and bool(TARGET.search(text))
            tag = "★加藤" if hit else ("（名前はあるが審判欄か不明）" if loose else "")
            print(f"  {k}: {gdate} {tag}")
            if loose and not saved_loose:
                save_debug("sample_unclear.txt", k, url, title, text)  # 読み取りルール調整用
                saved_loose = True

            if not hit and not loose and k in games:
                print(f"  ※ {k}: 一覧にあるが、公式ページでは加藤さんの名前を確認できず（一覧には残します）")

            if hit and gdate >= SEASON_START:
                g = {
                    "key": k,
                    "date": fmt_date(gdate),
                    "match": extract_match(title, lines) or f"B.LEAGUE 試合 (ID:{k})",
                    "venue": extract_venue(lines),
                    "crew": extract_crew(lines),
                    "status": "upcoming" if gdate > today else "final",
                }
                if k in games:
                    if games[k] != g:
                        games[k].update(g)
                        stats["updated"] += 1
                else:
                    games[k] = g
                    stats["new"] += 1
                if not saved_hit:
                    save_debug("sample_hit.txt", k, url, title, text)
                    saved_hit = True

            if gdate > today:
                future_run += 1
                if future_run >= STOP_AFTER_FUTURE:
                    print("まだ行われていない試合が続いたので終了（最新まで確認済み）")
                    break
            else:
                future_run = 0
                if gdate < SEASON_START or gdate <= today - timedelta(days=DONE_AFTER_DAYS):
                    done.add(k)

            key += 1
            page.wait_for_timeout(WAIT_MS)

        browser.close()

    now = datetime.now(JST).isoformat(timespec="seconds")
    games_doc = {
        "referee": "加藤 誉樹",
        "updated": now,
        "status": "error" if aborted else "ok",
        "games": sorted(games.values(), key=lambda g: int(g["key"]), reverse=True),
    }
    save_json(GAMES_PATH, games_doc)
    save_json(STATE_PATH, {"done": sorted(done, key=int), "max_seen": max_seen, "last_run": now})

    print(f"確認ページ数: {stats['pages']} / 新着: {stats['new']} / 更新: {stats['updated']} / 合計: {len(games)}試合")
    return 0


if __name__ == "__main__":
    sys.exit(main())
