#!/usr/bin/env python3
# © 2026 大國将 (Shou Ooguni). All Rights Reserved.
# 無断複製・改変・再配布・リバースエンジニアリングを禁じます。
"""
登録したレフェリー（加藤誉樹さん・島根県所属のレフェリーなど）の担当試合を、
バスケットLIVEで配信される大会の公式サイトから集めて games.json に保存する。
対象のレフェリーは referees.json で設定する（GitHubの画面から編集できる）。

対象（いずれもバスケットLIVEで全試合配信）
  B.LEAGUE … B.PREMIER / B.ONE / B.NEXT
             bleague.jp の日程ページで試合IDを集め、試合詳細の審判欄を確認する
  Wリーグ   … プレミア / フューチャー
             wjbl.org のボックススコアを試合ID順に確認する

・一度確認した試合は scan_state.json に記録し、次回からは飛ばす
・まだ行われていない試合は日付だけ覚えておき、試合日が来てから確認する
・ページは本物のブラウザ（Playwright）で開くので、後から読み込まれる情報も拾える
"""
import hashlib
import json
import os
import re
import sys
import unicodedata
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

# ---------------- 設定 ----------------
JST = ZoneInfo("Asia/Tokyo")
TODAY = datetime.now(JST).date()
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAMES_PATH = os.path.join(ROOT, "games.json")
STATE_PATH = os.path.join(ROOT, "scan_state.json")
DEBUG_DIR = os.path.join(ROOT, "debug")

STATE_VERSION = 3
SEASON_START = date(2026, 9, 1)     # これより前の試合は対象外
DONE_AFTER_DAYS = 2                 # 試合日から2日たったら確認済みにする（審判情報の掲載待ち）
RETRY_LIMIT = 3                     # 日付が読めないページは3回まで確認し直す
STOP_AFTER_ERRORS = 8               # 接続エラーがこれだけ続いたら中断
MAX_PAGES = int(os.environ.get("MAX_PAGES", "350"))        # 1回に開く試合ページの上限（残りは次回。60分以内に収める）
WAIT_MS = int(os.environ.get("WAIT_MS", "1500"))           # ページごとの待ち時間（相手サイトへの配慮）

# B.LEAGUE
BL_SCHEDULE_URL = os.environ.get(
    "BL_SCHEDULE_URL",
    "https://www.bleague.jp/schedule/?year={y}&mon={m:02d}&day={d:02d}&event=&club=&tab={tab}&ha=&fb=")
BL_DETAIL_URL = os.environ.get("BL_DETAIL_URL", "https://www.bleague.jp/game_detail/?ScheduleKey={key}&tab=4")
BL_TABS = {1: "B.PREMIER", 2: "B.ONE", 3: "B.NEXT"}
BL_LOOKBACK_DAYS = int(os.environ.get("BL_LOOKBACK_DAYS", "35"))  # 見逃し配信（30日）＋余裕
BL_LOOKAHEAD_DAYS = 3
BL_SHORT_LOOKBACK = 3               # 2回目以降の実行で見直す日数（1日1回は全期間を見直す）

# Wリーグ
WL_DETAIL_URL = os.environ.get(
    "WL_DETAIL_URL",
    "https://www.wjbl.org/schedule_result/detail/boxscore/?locale=SP&command=boxscore&schedule_id={key}")
WL_START_ID = int(os.environ.get("WL_START_ID", "7950"))    # 2026-27シーズン開幕戦（ID 8000前後）より少し前
WL_STOP_AFTER_MISSING = int(os.environ.get("WL_STOP_AFTER_MISSING", "40"))

LIVE_URL = "https://basketball.mb.softbank.jp/lives/{id}"

# 対象のレフェリー（referees.json が無いときの初期値）
CONFIG_PATH = os.path.join(ROOT, "referees.json")
REFS_VERSION = 1                    # 審判名の記録方式。変えたら見逃し配信期間内の試合を確認し直す
DEFAULT_GROUPS = [
    {"id": "kato", "label": "加藤 誉樹レフェリー", "badge": "#77 CC", "names": ["加藤 誉樹"]},
    {"id": "shimane", "label": "島根県所属レフェリー", "badge": "島根", "hidden": True, "name_hashes": []},
]

# ---------------- 読み取りルール ----------------
TARGET = re.compile(r"加藤[\s\u3000]*誉樹")
DATE_RES = [
    re.compile(r"(20\d{2})\s*[./年\-]\s*(\d{1,2})\s*[./月\-]\s*(\d{1,2})"),   # 2026.10.03 / 2026/10/03 / 2026年10月3日
    re.compile(r"(20\d{2})\s+(\d{1,2})\.(\d{1,2})"),                         # 2026 10.31（Wリーグ）
]
VS_RE = re.compile(r"([^\s|｜<>\[\]()（）]{2,20})\s*(?:vs\.?|VS|ＶＳ)\s*([^\s|｜<>\[\]()（）]{2,20})")
ROLE_WORDS = r"(?:審判員?|レフェリー|クルーチーフ|ファースト[アエ]ンパイア|セカンド[アエ]ンパイア|[アエ]ンパイア\s*[12１２]?|主審|副審|CC|U1|U2|Crew\s*Chief|Umpire\s*\d?|Referees?)"
ROLE_RE = re.compile(r"^" + ROLE_WORDS + r"\s*[:：]?\s*", re.I)
CONTEXT_RE = re.compile(r"(審判|レフェリー|クルーチーフ|[アエ]ンパイア|主審|Referee|Crew)", re.I)
ROLE_LABELS = r"(?:クルーチーフ|ファースト[アエ]ンパイア|セカンド[アエ]ンパイア|[アエ]ンパイア\s*[12１２]?|CC|U1|U2)"
ROLE_VALUE_RE = re.compile(ROLE_LABELS + r"\s*[：:]\s*([^\n：:]{2,30}?)(?=\s*" + ROLE_LABELS + r"\s*[：:]|\n|$)")
SECTION_RE = re.compile(r"^(?:審判員?|レフェリー|Referees?)\s*[:：]?$", re.I)
NAME_CH = r"[一-龥々〆ヵヶァ-ヴーぁ-ん]"
NAME_RE = re.compile(rf"{NAME_CH}{{1,5}}[ \u3000]{NAME_CH}{{1,5}}")   # 姓と名の間に空白がある表記
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
        best = None
        for rx in DATE_RES:
            for m in rx.finditer(t or ""):
                y, mo, da = int(m.group(1)), int(m.group(2)), int(m.group(3))
                if 2025 <= y <= 2028:
                    try:
                        d = date(y, mo, da)
                    except ValueError:
                        continue
                    if best is None or m.start() < best[0]:
                        best = (m.start(), d)
                    break
        if best:
            return best[1]
    return None


def strip_role(s):
    return ROLE_RE.sub("", s.strip()).strip()


def norm_name(s):
    s = s.replace("\u3000", " ").strip()
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


def is_role_only(s):
    return bool(ROLE_RE.fullmatch(s.strip() + " "))


def roles_crew(text):
    """「クルーチーフ：○○ ファーストアンパイア：○○ …」形式から名前を順に取り出す"""
    names = []
    for m in ROLE_VALUE_RE.finditer(text):
        v = norm_name(m.group(1))
        if not (2 <= len(v) <= 20) or re.search(r"\d", v):
            continue
        n = "加藤 誉樹" if TARGET.fullmatch(v) else v
        if n not in names:
            names.append(n)
    return names


def is_referee_hit(lines, text):
    """審判欄に加藤誉樹さんが載っているか（記事中の言及などは除く）"""
    if "加藤 誉樹" in roles_crew(text):
        return True
    for l in lines:
        if not TARGET.search(l):
            continue
        if as_name(l) == "加藤 誉樹" or CONTEXT_RE.search(l):
            return True
        if any(as_name(p) == "加藤 誉樹" for p in re.split(r"[／/、,|｜]", l)):
            return True
    return False


def dedup(seq):
    out = []
    for x in seq:
        if x and x not in out:
            out.append(x)
    return out


# 異体字のゆれ（髙→高 など）。部首記号などはNFKCで通常の漢字にそろえる
VARIANTS = str.maketrans({"髙": "高", "﨑": "崎", "𠮷": "吉", "邉": "辺", "邊": "辺", "濵": "浜", "栁": "柳", "德": "徳"})


def nkey(name):
    """名前の照合用（字形をそろえ、空白を無視）"""
    s = unicodedata.normalize("NFKC", str(name or "")).translate(VARIANTS)
    return re.sub(r"\s", "", s)


def hkey(name):
    """名前を公開しないための照合キー（SHA-256）"""
    return hashlib.sha256(("ref77|" + nkey(name)).encode("utf-8")).hexdigest()


def extract_refs(lines, text):
    """試合ページから審判員の名前を順番どおりに取り出す（読めなければ空）"""
    # Wリーグ：クルーチーフ：○○ ファーストアンパイア：○○ …
    names = [norm_name(m.group(1)) for m in ROLE_VALUE_RE.finditer(text)]
    names = [n for n in names if 2 <= len(n) <= 20 and not re.search(r"\d", n)]
    if len(names) >= 2:
        return dedup(names)[:4]
    # B.LEAGUE：レフェリー：○○／○○／○○
    for l in lines:
        m = re.match(r"^(?:レフェリー|審判員?|Referees?)\s*[:：]\s*(.+)$", l, re.I)
        if m:
            parts = [norm_name(strip_role(x)) for x in re.split(r"[／/、,|｜]", m.group(1)) if x.strip()]
            parts = [x for x in parts if 2 <= len(x) <= 20 and not re.search(r"\d", x)]
            if parts:
                return dedup(parts)[:4]
    # 「審判」の見出しの下に1行1人
    for i, l in enumerate(lines):
        if SECTION_RE.match(l):
            names = []
            for x in lines[i + 1:i + 12]:
                if is_role_only(x):
                    continue
                t = strip_role(x)
                n = as_name(x) or (t if re.fullmatch(NAME_CH + r"{2,8}", t) else None)
                if not n:
                    break
                names.append(norm_name(n))
            if names:
                return dedup(names)[:4]
    return []


def load_groups():
    """referees.json を読む。names（公開してよい名前）と name_hashes（非公開の名前）のどちらでも指定できる"""
    cfg = load_json(CONFIG_PATH, None) or {}
    out = []
    for g in cfg.get("groups") or DEFAULT_GROUPS:
        names = dedup([norm_name(n) for n in g.get("names", []) if str(n).strip()])
        hashes = set(str(h).strip().lower() for h in g.get("name_hashes", []) if str(h).strip())
        hashes |= {hkey(n) for n in names}
        if g.get("id") and hashes:
            out.append({"id": str(g["id"]), "label": g.get("label") or str(g["id"]),
                        "badge": g.get("badge", ""), "names": names, "hashes": hashes,
                        "hidden": bool(g.get("hidden"))})
    return out


def match_hits(refs, groups):
    """{分類ID: [その分類に当てはまる審判名]}"""
    out = {}
    for g in groups:
        hits = [r for r in refs if hkey(r) in g["hashes"]]
        if hits:
            out[g["id"]] = hits
    return out


def match_groups(refs, groups):
    return list(match_hits(refs, groups).keys())


def loose_names(lines, groups):
    """審判名の欄が読めないとき：審判らしい行に出てくる登録名を探す"""
    found, unclear = [], []
    for g in groups:
        for n in g["names"]:
            pat = re.compile(r"[\s\u3000]*".join(map(re.escape, n.split(" "))))
            hits = [l for l in lines if pat.search(l)]
            if not hits:
                continue
            if any(CONTEXT_RE.search(l) or as_name(l) for l in hits):
                found.append(n)
            else:
                unclear.append(n)
    return dedup(found), dedup(unclear)


def extract_crew(lines, text):
    """加藤誉樹さんを含む審判クルー表記を作る。見つからなければ「加藤 誉樹 ほか」。"""
    names = roles_crew(text)
    if "加藤 誉樹" in names and len(names) >= 2:
        return " ／ ".join(["加藤 誉樹"] + [n for n in names if n != "加藤 誉樹"][:2])

    idx = next((i for i, l in enumerate(lines) if TARGET.search(l)), None)
    if idx is None:
        return "加藤 誉樹 ほか"

    # 1行に複数名（例：レフェリー：加藤 誉樹／名越 龍男／富樫 彰子）
    line = lines[idx]
    body = re.sub(r"^.*?(?:審判員?|レフェリー|クルーチーフ)\s*[:：]?\s*", "", line)
    names = []
    for p in [strip_role(x) for x in re.split(r"[／/、,|｜]", body) if x.strip()]:
        n = as_name(p) or (p if 2 <= len(p) <= 20 and not re.search(r"\d", p) else None)
        if n:
            names.append(norm_name(n))
    if len(names) >= 2:
        if "加藤 誉樹" in names:
            names.remove("加藤 誉樹")
        return " ／ ".join(["加藤 誉樹"] + names[:2])

    # 1行に1人ずつ：加藤さんの行と連続する名前の行だけを集める（選手名を拾わないため）
    lo = idx
    while lo - 1 >= 0 and idx - (lo - 1) <= 6 and (as_name(lines[lo - 1]) or is_role_only(lines[lo - 1])):
        lo -= 1
        if SECTION_RE.match(lines[lo].strip()):
            break
    hi = idx
    while hi + 1 < len(lines) and (hi + 1) - idx <= 6 and (as_name(lines[hi + 1]) or is_role_only(lines[hi + 1])):
        hi += 1
    names = []
    for l in lines[lo:hi + 1]:
        n = as_name(l)
        if n and n not in names:
            names.append(n)
    if "加藤 誉樹" in names and len(names) >= 2:
        return " ／ ".join(["加藤 誉樹"] + [n for n in names if n != "加藤 誉樹"][:2])
    return "加藤 誉樹 ほか"


def extract_match(title, lines):
    for t in [title] + lines[:120]:
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


SCORE_RE = re.compile(r"^(\d{1,3})?\s*[-－]\s*(\d{1,3})?$")


def wl_match(lines):
    """Wリーグ：『ホーム / 点数（または -） / アウェー』の並びから対戦カードを作る"""
    for i, l in enumerate(lines):
        if SCORE_RE.match(l) and 0 < i < len(lines) - 1:
            home = lines[i - 1]
            away = lines[i + 1]
            if i + 2 < len(lines) and lines[i + 2] and lines[i + 2] in away and len(lines[i + 2]) < len(away):
                away = lines[i + 2]   # 正式名称の次の行にある略称を使う
            if 1 <= len(home) <= 20 and 1 <= len(away) <= 20 and not SCORE_RE.match(away):
                return f"{home} vs {away}"
    return ""


def bl_league(title, fallback):
    t = title or ""
    if re.search(r"B\.LEAGUE\s*PREMIER", t, re.I):
        return "B.PREMIER"
    if re.search(r"B\.LEAGUE\s*ONE", t, re.I):
        return "B.ONE"
    if re.search(r"B\.LEAGUE\s*NEXT", t, re.I):
        return "B.NEXT"
    return fallback or "B.LEAGUE"


def wl_league(text):
    head = text[:3000]
    if "フューチャー" in head:
        return "Wリーグ フューチャー"
    if "プレミア" in head:
        return "Wリーグ プレミア"
    return "Wリーグ"


def save_debug(name, sid, url, title, text, links=None):
    os.makedirs(DEBUG_DIR, exist_ok=True)
    with open(os.path.join(DEBUG_DIR, name), "w", encoding="utf-8") as f:
        f.write(f"# ID={sid}\n# URL={url}\n# TITLE={title}\n# LIVEリンク={links or []}\n"
                f"# 取得: {datetime.now(JST).isoformat(timespec='seconds')}\n\n")
        f.write(text[:20000])


# ---------------- ページ取得 ----------------
def fetch_page(page, url):
    """(状態, タイトル, 本文, バスケットLIVEの試合ID一覧) を返す。状態は ok / missing / error"""
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:  # noqa: BLE001
        print(f"  ! 接続エラー {type(e).__name__}: {url}")
        return "error", "", "", []
    if resp is not None and resp.status == 404:
        return "missing", "", "", []
    if resp is not None and resp.status >= 500:
        return "error", "", "", []

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
    live_ids, live_links = [], []
    try:
        hrefs = page.eval_on_selector_all("a[href*='basketball.mb.softbank.jp']", "els => els.map(e => e.href)")
        for h in hrefs:
            m = re.search(r"/lives/(\d+)", h) or re.search(r"game_id=(\d+)", h)
            if m and m.group(1) not in live_ids:
                live_ids.append(m.group(1))
        live_links = page.eval_on_selector_all(
            "a", "els => els.filter(e => /LIVE|ライブ/.test(e.innerText || '')).map(e => e.href).slice(0, 5)")
    except Exception:  # noqa: BLE001
        pass
    fetch_page.last_links = live_links
    return "ok", title, text, live_ids


# ---------------- メイン ----------------
def load_state(games):
    state = load_json(STATE_PATH, None) or {}
    if state.get("version") == STATE_VERSION:
        return state
    known = {}
    if state.get("version") == 2:
        # 旧版（B.PREMIERを番号順に確認）の確認済みIDを引き継ぐ
        for k in state.get("done", []):
            known["bl:" + str(k)] = {"d": None, "done": True, "lg": "B.PREMIER"}
        print(f"旧版の確認記録を引き継ぎました（{len(known)}件）")
    for k, g in games.items():
        sid = ("wl:" + k[1:]) if k.startswith("W") else ("bl:" + k)
        known.setdefault(sid, {"d": None, "done": g.get("verified") in (True, False)})
    return {"version": STATE_VERSION, "known": known, "retry": {}, "bl_full_scan": "", "wl_max_seen": WL_START_ID}


GROUPS = []


def main():
    global GROUPS
    GROUPS = load_groups()
    print("対象のレフェリー: " + " / ".join(
        f"{g['label']}（{len(g['hashes'])}名・非公開）" if g["hidden"] else f"{g['label']}（{'・'.join(g['names'])}）"
        for g in GROUPS))
    games_doc = load_json(GAMES_PATH, {"games": []})
    games = {str(g["key"]): g for g in games_doc.get("games", []) if g.get("key")}
    for k, g in games.items():  # 旧データの補完
        if not k.startswith("W"):
            g.setdefault("league", "B.PREMIER")
            g.setdefault("live_url", LIVE_URL.format(id=k))

    state = load_state(games)
    known = state["known"]
    retry = {str(k): int(v) for k, v in state.get("retry", {}).items()}
    today_iso = TODAY.isoformat()
    stats = {"pages": 0, "sched": 0, "new": 0, "updated": 0}
    run = {"errors": 0, "aborted": False}
    debug_saved = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=os.environ.get("CHROME") or None)
        ctx = browser.new_context(locale="ja-JP", timezone_id="Asia/Tokyo")
        ctx.route("**/*", lambda route: route.abort()
                  if route.request.resource_type in ("image", "media", "font") else route.continue_())
        page = ctx.new_page()

            # ---------- 1) B.LEAGUE：日程ページから試合IDを集める ----------
        if state.get("refs_version") != REFS_VERSION:
            state["bl_full_scan"] = ""      # 審判名の記録方式が変わったら、期間内の試合を全部見直す
        full = state.get("bl_full_scan") != today_iso
        back = BL_LOOKBACK_DAYS if full else BL_SHORT_LOOKBACK
        print(f"[B.LEAGUE] 日程を確認（{'全期間' if full else '直近'}：{back}日前〜{BL_LOOKAHEAD_DAYS}日後）")
        sched_ok = 0
        for offset in range(BL_LOOKAHEAD_DAYS, -back - 1, -1):
            d = TODAY + timedelta(days=offset)
            if d < SEASON_START:
                continue
            for tab, lg in BL_TABS.items():
                url = BL_SCHEDULE_URL.format(y=d.year, m=d.month, d=d.day, tab=tab)
                try:
                    r = page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    html = page.content() if (r is None or r.ok) else ""
                except Exception as e:  # noqa: BLE001
                    print(f"  ! 日程の取得エラー {type(e).__name__}: {url}")
                    html = ""
                stats["sched"] += 1
                if html:
                    sched_ok += 1
                for key in dict.fromkeys(re.findall(r"ScheduleKey=(\d{5,})", html)):
                    sid = "bl:" + key
                    if sid not in known:
                        known[sid] = {"d": d.isoformat(), "done": False, "lg": lg, "hint": True}
                    elif known[sid].get("hint") and d.isoformat() < (known[sid].get("d") or "9999"):
                        known[sid]["d"] = d.isoformat()   # 日程上の日付（仮）は早い方を採用
                    if known[sid].get("rv") != REFS_VERSION and not known[sid].get("missing"):
                        # 審判名を記録していない試合（旧方式で確認済み）は確認し直す
                        known[sid]["done"] = False
                        if not known[sid].get("d"):
                            known[sid].update({"d": d.isoformat(), "hint": True})
                page.wait_for_timeout(300)
        if sched_ok and full:
            state["bl_full_scan"] = today_iso

        # ---------- 2) 試合ページを確認する ----------
        def check(sid):
            src, num = sid.split(":", 1)
            url = (BL_DETAIL_URL if src == "bl" else WL_DETAIL_URL).format(key=num)
            status, title, text, live_ids = fetch_page(page, url)
            stats["pages"] += 1
            if status == "error":
                run["errors"] += 1
                if run["errors"] >= STOP_AFTER_ERRORS:
                    print("公式サイトに接続できないため中断します")
                    run["aborted"] = True
                return "error"
            run["errors"] = 0

            lines = [l.strip() for l in text.splitlines() if l.strip()]
            gdate = find_date(title, "\n".join(lines[:200])) if status == "ok" else None
            if gdate is None:
                retry[sid] = retry.get(sid, 0) + 1
                info = known.setdefault(sid, {"d": None, "done": False})
                info["missing"] = True
                if status == "missing" or retry[sid] >= RETRY_LIMIT:
                    info["done"] = True
                print(f"  ? {sid}: 試合なし／日付を読めず（{retry[sid]}回目）")
                return "missing"
            retry.pop(sid, None)
            known.get(sid, {}).pop("missing", None)

            lg = bl_league(title, known.get(sid, {}).get("lg")) if src == "bl" else wl_league(text)
            done = gdate < SEASON_START or gdate <= TODAY - timedelta(days=DONE_AFTER_DAYS)
            known[sid] = {"d": gdate.isoformat(), "done": done, "lg": lg}

            links = getattr(fetch_page, "last_links", [])
            if src + "_page" not in debug_saved:
                save_debug(f"{src}_page.txt", sid, url, title, text, links)
                debug_saved.add(src + "_page")

            refs = extract_refs(lines, text)
            found, unclear = loose_names(lines, GROUPS)
            if not refs and found:
                refs = found
            gids = match_groups(refs, GROUPS)
            if refs:
                live = live_ids[0] if live_ids else (num if src == "bl" else "")
                known[sid].update({
                    "rv": REFS_VERSION,
                    "refs": refs,
                    "m": (extract_match(title, lines) if src == "bl" else (wl_match(lines) or extract_match(title, lines))),
                    "v": extract_venue(lines),
                    "live": live,
                })
            tag = " ".join("★" + g["badge"] for g in GROUPS if g["id"] in gids)
            print(f"  {sid}: {gdate} {lg} {tag}")
            if unclear and not gids and src + "_unclear" not in debug_saved:
                save_debug(f"{src}_unclear.txt", sid, url, title, text, links)   # 読み取りルール調整用
                debug_saved.add(src + "_unclear")
            if gids and src + "_hit" not in debug_saved:
                save_debug(f"{src}_hit.txt", sid, url, title, text, links)
                debug_saved.add(src + "_hit")
            return "ok"

        # 優先順：試合日が来た未確認の試合（新しい順）→ 日付のわからない試合
        def due(sid):
            v = known.get(sid, {})
            return not v.get("done") and (v.get("d") is None or v["d"] <= today_iso)

        for k, g in games.items():  # 一覧にあるのに審判名の記録が無い試合も確認対象にする
            sid = ("wl:" + k[1:]) if k.startswith("W") else ("bl:" + k)
            v = known.setdefault(sid, {"d": None, "done": False})
            if v.get("rv") != REFS_VERSION and not v.get("missing"):
                v["done"] = False
        queue = [s for s in known if due(s)]
        queue.sort(key=lambda s: (known[s].get("d") or "0000", s), reverse=True)
        print(f"[確認] 試合日が来た未確認の試合: {len(queue)}件")
        for sid in queue:
            if stats["pages"] >= MAX_PAGES or run["aborted"]:
                break
            check(sid)
            page.wait_for_timeout(WAIT_MS)

        # ---------- 3) Wリーグ：新しい試合IDを番号順に探す ----------
        # 新しい試合IDは日程発表時にまとめて作られるので、探すのは1日1回で十分
        if not run["aborted"] and stats["pages"] < MAX_PAGES and state.get("wl_complete_on") != today_iso:
            print("[Wリーグ] 新しい試合IDを確認")
            wl_ids = [int(s[3:]) for s in known if s.startswith("wl:")]
            max_seen = max([state.get("wl_max_seen", WL_START_ID)] + [i for i in wl_ids if not known["wl:" + str(i)].get("missing")])
            n, missing_run = WL_START_ID, 0
            while stats["pages"] < MAX_PAGES and not run["aborted"]:
                sid = f"wl:{n}"
                if sid in known:
                    n += 1
                    continue
                r = check(sid)
                if r == "missing":
                    missing_run += 1
                    if n > max_seen and missing_run >= WL_STOP_AFTER_MISSING:
                        print("存在しないIDが続いたので終了（最新まで確認済み）")
                        state["wl_complete_on"] = today_iso
                        break
                elif r == "ok":
                    missing_run = 0
                    max_seen = max(max_seen, n)
                n += 1
                page.wait_for_timeout(WAIT_MS)
            # 最新の先にある「まだ存在しないID」は、次回また確認できるよう記録から外す
            for i in list(range(max_seen + 1, n + 1)):
                s = f"wl:{i}"
                if known.get(s, {}).get("missing"):
                    known.pop(s, None)
                    retry.pop(s, None)
            state["wl_max_seen"] = max_seen

        browser.close()

    now = datetime.now(JST).isoformat(timespec="seconds")

    # 記録した審判名から一覧を組み立てる（名前の設定を変えても、確認し直さずに反映される）
    before = {k: json.dumps(g, ensure_ascii=False, sort_keys=True) for k, g in games.items()}
    for sid, v in known.items():
        if not v.get("refs") or not v.get("d"):
            continue
        src, num = sid.split(":", 1)
        key = num if src == "bl" else "W" + num
        gdate = date.fromisoformat(v["d"])
        hits = match_hits(v["refs"], GROUPS)
        gids = list(hits.keys())
        if gdate < SEASON_START or not gids:
            games.pop(key, None)
            continue
        lg = v.get("lg") or ("B.LEAGUE" if src == "bl" else "Wリーグ")
        games[key] = {
            "key": key,
            "league": lg,
            "date": fmt_date(gdate),
            "match": v.get("m") or f"{lg} 試合 (ID:{num})",
            "venue": v.get("v", ""),
            "crew": " ／ ".join(v["refs"]),
            "groups": gids,
            "hits": hits,
            "status": "upcoming" if gdate > TODAY else "final",
            "verified": True,
            "live_url": LIVE_URL.format(id=v["live"]) if v.get("live") else "",
            "source_url": (BL_DETAIL_URL if src == "bl" else WL_DETAIL_URL).format(key=num),
        }
    for g in games.values():
        g.setdefault("groups", ["kato"])   # 旧データは加藤さんの試合
    stats["new"] = sum(1 for k in games if k not in before)
    stats["updated"] = sum(1 for k in games if k in before and before[k] != json.dumps(games[k], ensure_ascii=False, sort_keys=True))
    by_group = {g["id"]: sum(1 for x in games.values() if g["id"] in x.get("groups", [])) for g in GROUPS}

    def sort_key(g):
        return (re.sub(r"\s.*$", "", g.get("date", "")), g["key"])

    save_json(GAMES_PATH, {
        "referees": [{"id": g["id"], "label": g["label"], "badge": g["badge"],
                      **({} if g["hidden"] else {"names": g["names"]})} for g in GROUPS],
        "updated": now,
        "status": "error" if run["aborted"] else "ok",
        "sources": ["B.PREMIER", "B.ONE", "B.NEXT", "Wリーグ"],
        "games": sorted(games.values(), key=sort_key, reverse=True),
    })
    state.update({"version": STATE_VERSION, "known": known, "retry": retry, "last_run": now,
                  "refs_version": REFS_VERSION})
    save_json(STATE_PATH, state)
    pending = sum(1 for s in known if not known[s].get("done"))
    print(f"日程ページ: {stats['sched']} / 試合ページ: {stats['pages']} / 新着: {stats['new']} / "
          f"更新: {stats['updated']} / 合計: {len(games)}試合 {by_group} / 未確認(試合日待ちを含む): {pending}件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
