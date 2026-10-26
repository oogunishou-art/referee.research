<!DOCTYPE html>
<html lang="ja">
<head>
  <!--
    B.PREMIER Referee Finder & Film Study Log
    Created for Masaru Okuni - Single HTML PWA Style
    Copyright (c) 2026 Masaru Okuni. All Rights Reserved.
  -->
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <meta name="robots" content="noindex, nofollow">
  <title>REF FINDER #77 | B.PREMIER 審判稼働検索 & 視聴管理</title>
  <style>
    :root {
      --bg: #0f172a;
      --card: #1e293b;
      --card-hover: #334155;
      --text: #f8fafc;
      --sub: #94a3b8;
      --accent: #f97316;
      --accent-hover: #ea580c;
      --green: #10b981;
      --blue: #3b82f6;
      --border: #334155;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Hiragino Sans", "Noto Sans JP", sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding-bottom: 60px;
    }
    header {
      background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
      border-bottom: 2px solid var(--accent);
      padding: 16px 20px;
      position: sticky;
      top: 0;
      z-index: 100;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .logo-area h1 {
      font-size: 1.2rem;
      font-weight: 800;
      letter-spacing: 0.05em;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .badge-77 {
      background: var(--accent);
      color: #fff;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.9rem;
    }
    .logo-area p {
      font-size: 0.75rem;
      color: var(--sub);
    }
    .container {
      max-width: 900px;
      margin: 0 auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 18px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.25);
    }
    .card-title {
      font-size: 1.05rem;
      font-weight: 700;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      gap: 8px;
      color: #fff;
      border-left: 4px solid var(--accent);
      padding-left: 10px;
    }
    .form-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 12px;
      margin-bottom: 14px;
    }
    label {
      display: block;
      font-size: 0.8rem;
      color: var(--sub);
      margin-bottom: 4px;
    }
    select, input, textarea {
      width: 100%;
      padding: 10px 12px;
      background: #0f172a;
      border: 1px solid var(--border);
      border-radius: 8px;
      color: var(--text);
      font-size: 0.95rem;
    }
    select:focus, input:focus, textarea:focus {
      outline: none;
      border-color: var(--accent);
    }
    .btn-group {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }
    .btn {
      cursor: pointer;
      border: none;
      border-radius: 8px;
      padding: 10px 16px;
      font-size: 0.9rem;
      font-weight: 700;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: all 0.15s ease;
      text-decoration: none;
    }
    .btn-primary {
      background: var(--accent);
      color: #fff;
      flex: 1;
    }
    .btn-primary:hover { background: var(--accent-hover); }
    .btn-secondary {
      background: #334155;
      color: var(--text);
    }
    .btn-secondary:hover { background: #475569; }
    .btn-blue {
      background: var(--blue);
      color: #fff;
    }
    .btn-sm {
      padding: 6px 10px;
      font-size: 0.8rem;
    }
    .game-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }
    .game-item {
      background: #0f172a;
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .game-item.watched {
      border-left: 4px solid var(--green);
    }
    .game-item.unwatched {
      border-left: 4px solid var(--accent);
    }
    .game-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      flex-wrap: wrap;
      gap: 8px;
    }
    .game-meta {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }
    .game-date {
      font-weight: 700;
      color: var(--accent);
      font-size: 0.95rem;
    }
    .game-matchup {
      font-size: 1.05rem;
      font-weight: 800;
    }
    .crew-box {
      font-size: 0.85rem;
      color: var(--sub);
      background: rgba(255,255,255,0.03);
      padding: 6px 10px;
      border-radius: 6px;
    }
    .crew-box strong {
      color: #fff;
    }
    .memo-box {
      font-size: 0.85rem;
      color: #cbd5e1;
      white-space: pre-wrap;
      background: #1e293b;
      padding: 8px 10px;
      border-radius: 6px;
      border-left: 3px solid var(--blue);
    }
    .status-badge {
      font-size: 0.75rem;
      padding: 3px 8px;
      border-radius: 999px;
      font-weight: 700;
      cursor: pointer;
      user-select: none;
    }
    .status-unwatched {
      background: rgba(249, 115, 22, 0.2);
      color: #fb923c;
      border: 1px solid #f97316;
    }
    .status-watched {
      background: rgba(16, 185, 129, 0.2);
      color: #34d399;
      border: 1px solid #10b981;
    }
    .helper-text {
      font-size: 0.8rem;
      color: var(--sub);
      margin-top: 8px;
    }
    .filter-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      flex-wrap: wrap;
      gap: 8px;
    }
  </style>
</head>
<body>

<header>
  <div class="logo-area">
    <h1><span class="badge-77">#77</span> REF FINDER</h1>
    <p>B.PREMIER レフェリー稼働特定 & バスケットLIVE 視聴管理</p>
  </div>
  <div>
    <button class="btn btn-secondary btn-sm" onclick="exportData()">JSON保存</button>
  </div>
</header>

<div class="container">

  <!-- 1. ピンポイント検索ランチャー -->
  <section class="card">
    <div class="card-title">🔍 1. 試合終了後の審判稼働 ピンポイント検索</div>
    <div class="form-grid">
      <div>
        <label>対象レフェリー</label>
        <select id="refSelect" onchange="syncCustomRef()">
          <option value="加藤 誉樹" selected>#77 加藤 誉樹（JBAプロ）</option>
          <option value="漆間 大吾">#4 漆間 大吾（JBAプロ）</option>
          <option value="阿部 聖">#25 阿部 聖（JBAプロ）</option>
          <option value="有澤 重行">#26 有澤 重行（JBAプロ）</option>
          <option value="大河原 則人">#43 大河原 則人（JBAプロ）</option>
          <option value="秋山 厚志">#92 秋山 厚志（JBAプロ）</option>
          <option value="岩井 遥河">#112 岩井 遥河（JBAプロ）</option>
          <option value="内田 祥平">内田 祥平（JBAプロ）</option>
          <option value="加藤 暁生">#90 加藤 暁生</option>
          <option value="custom">自由入力...</option>
        </select>
      </div>
      <div>
        <label>レフェリー名（姓と名の間にスペース）</label>
        <input type="text" id="customRef" value="加藤 誉樹" placeholder="例：加藤 誉樹">
      </div>
      <div>
        <label>期間フィルタ</label>
        <select id="timeRange">
          <option value="w">直近1週間以内</option>
          <option value="m" selected>直近1ヶ月以内</option>
          <option value="d">直近24時間以内</option>
          <option value="">全期間（2026-27シーズン）</option>
        </select>
      </div>
    </div>

    <div class="btn-group">
      <button class="btn btn-primary" onclick="searchBLeague(true)">
        🎯 主審（CC）担当試合を検索
      </button>
      <button class="btn btn-secondary" onclick="searchBLeague(false)">
        📋 クルー全体で検索
      </button>
      <a class="btn btn-secondary" href="https://note.com/refvision_b" target="_blank" rel="noopener">
        📘 RefVision_B (note)
      </a>
    </div>
    <p class="helper-text">
      ※Bリーグ公式の試合結果ページ（<code>bleague.jp/game_detail/</code>）にある「レフェリー：加藤 誉樹／...」を狙い撃ちでGoogle検索します。
    </p>
  </section>

  <!-- 2. 見つけた試合の登録フォーム -->
  <section class="card">
    <div class="card-title">➕ 2. 特定した試合・FILM STUDYメモを追加</div>
    <div class="form-grid">
      <div>
        <label>試合日</label>
        <input type="date" id="inDate" value="2026-10-26">
      </div>
      <div>
        <label>対戦カード（会場）</label>
        <input type="text" id="inMatch" placeholder="例：島根 vs 名古屋D（松江）">
      </div>
      <div>
        <label>ScheduleKey（公式URL末尾の6桁）</label>
        <input type="text" id="inKey" placeholder="例：506428（URLペーストも可）" oninput="extractKey(this)">
      </div>
    </div>
    <div class="form-grid">
      <div>
        <label>担当クルー（CC / U1 / U2）</label>
        <input type="text" id="inCrew" value="加藤 誉樹 ／ " placeholder="例：加藤 誉樹 ／ 名越 龍男 ／ 富樫 彰子">
      </div>
    </div>
    <div style="margin-bottom: 12px;">
      <label>FILM STUDY 学習メモ（所作・ビジブルカウント・FUL・メカニクス等）</label>
      <textarea id="inMemo" rows="2" placeholder="例：ビジブルカウントのテンポ（BPM55の感覚）、コール後の腕の高さ確認。"></textarea>
    </div>
    <button class="btn btn-blue" onclick="addGame()">＋ リストに保存する</button>
  </section>

  <!-- 3. 稼働ログ一覧 -->
  <section class="card">
    <div class="filter-bar">
      <div class="card-title" style="margin-bottom:0;">📺 3. #77 加藤誉樹レフェリー 稼働・視聴リスト (2026-27)</div>
      <div style="display:flex; gap:8px;">
        <select id="statusFilter" onchange="renderGames()" style="width:auto; padding:6px 10px; font-size:0.85rem;">
          <option value="all">すべて表示</option>
          <option value="unwatched">未視聴のみ</option>
          <option value="watched">視聴済のみ</option>
        </select>
      </div>
    </div>
    <div id="gameList" class="game-list"></div>
  </section>

</div>

<script>
  const STORAGE_KEY = "b_premier_ref77_games_v1";

  const defaultGames = [
    {
      id: "506503",
      date: "2026-10-24",
      match: "A東京 vs 三河（TOYOTA ARENA TOKYO）",
      crew: "加藤 誉樹 ／ 石田 祐二 ／ 佐久間 奈々",
      scheduleKey: "506503",
      watched: false,
      memo: "東地区上位の注目カード。ゲームコントロールとプレッシャー下でのプレゼンテーション確認用。"
    },
    {
      id: "506486",
      date: "2026-10-21",
      match: "北海道 vs 富山",
      crew: "加藤 誉樹 ／ 冨士 将史 ／ 山田 俊",
      scheduleKey: "506486",
      watched: false,
      memo: "平日開催の第4節。トランジションの速い展開でのトレイルの位置取り。"
    },
    {
      id: "506471",
      date: "2026-10-17",
      match: "千葉J vs 島根（LaLa arena）",
      crew: "加藤 誉樹 ／ 加藤 暁生 ／ 岩城 和利",
      scheduleKey: "506471",
      watched: false,
      memo: "島根アウェイ戦。W加藤レフェリー体制。"
    },
    {
      id: "506457",
      date: "2026-10-11",
      match: "東京SR vs 仙台",
      crew: "加藤 誉樹 ／ 柳田 雅人 ／ 大山 賢史",
      scheduleKey: "506457",
      watched: false,
      memo: "同カードGAME2の連続CC担当。"
    },
    {
      id: "506428",
      date: "2026-10-04",
      match: "島根 vs 名古屋D（松江）",
      crew: "加藤 誉樹 ／ 名越 龍男 ／ 富樫 彰子",
      scheduleKey: "506428",
      watched: true,
      memo: "【学習済】ビジブルカウントの動きはメトロノーム55くらいのゆったりとしたテンポ。コール後の腕の高さと残し方。"
    },
    {
      id: "506416",
      date: "2026-10-03",
      match: "島根 vs 名古屋D（松江）",
      crew: "加藤 誉樹 ／ 名越 龍男 ／ 富樫 彰子",
      scheduleKey: "506416",
      watched: true,
      memo: "開幕節 松江開催 GAME1。"
    }
  ];

  function loadGames() {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(defaultGames));
      return defaultGames;
    }
    try {
      return JSON.parse(raw);
    } catch (e) {
      return defaultGames;
    }
  }

  function saveGames(games) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(games));
  }

  function syncCustomRef() {
    const sel = document.getElementById("refSelect").value;
    const input = document.getElementById("customRef");
    if (sel !== "custom") {
      input.value = sel;
    } else {
      input.value = "";
      input.focus();
    }
  }

  function searchBLeague(ccOnly) {
    const refName = document.getElementById("customRef").value.trim() || "加藤 誉樹";
    const timeRange = document.getElementById("timeRange").value;
    let query = `site:bleague.jp/game_detail/ "2026-27" `;
    if (ccOnly) {
      query += `"レフェリー：${refName}"`;
    } else {
      query += `"${refName}" "レフェリー"`;
    }
    let url = `https://www.google.com/search?q=${encodeURIComponent(query)}`;
    if (timeRange) {
      url += `&tbs=qdr:${timeRange}`;
    }
    window.open(url, "_blank", "noopener");
  }

  function extractKey(inputEl) {
    const val = inputEl.value;
    const match = val.match(/ScheduleKey=(\d+)/i);
    if (match && match[1]) {
      inputEl.value = match[1];
    }
  }

  function addGame() {
    const date = document.getElementById("inDate").value;
    const match = document.getElementById("inMatch").value.trim();
    const scheduleKey = document.getElementById("inKey").value.trim();
    const crew = document.getElementById("inCrew").value.trim();
    const memo = document.getElementById("inMemo").value.trim();

    if (!match) {
      alert("対戦カードを入力してください。");
      return;
    }

    const games = loadGames();
    games.unshift({
      id: Date.now().toString(),
      date: date || "日付未定",
      match,
      crew: crew || "加藤 誉樹",
      scheduleKey,
      watched: false,
      memo
    });
    saveGames(games);
    renderGames();

    document.getElementById("inMatch").value = "";
    document.getElementById("inKey").value = "";
    document.getElementById("inMemo").value = "";
  }

  function toggleWatched(id) {
    const games = loadGames();
    const target = games.find(g => g.id === id);
    if (target) {
      target.watched = !target.watched;
      saveGames(games);
      renderGames();
    }
  }

  function editMemo(id) {
    const games = loadGames();
    const target = games.find(g => g.id === id);
    if (!target) return;
    const nextMemo = prompt("FILM STUDY メモを編集：", target.memo || "");
    if (nextMemo !== null) {
      target.memo = nextMemo;
      saveGames(games);
      renderGames();
    }
  }

  function deleteGame(id) {
    if (!confirm("この試合記録を削除しますか？")) return;
    const games = loadGames().filter(g => g.id !== id);
    saveGames(games);
    renderGames();
  }

  function exportData() {
    const data = localStorage.getItem(STORAGE_KEY) || "[]";
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ref77_filmstudy_${new Date().toISOString().slice(0,10)}.json`;
    a.click();
  }

  function renderGames() {
    const listEl = document.getElementById("gameList");
    const filter = document.getElementById("statusFilter").value;
    const games = loadGames();

    const filtered = games.filter(g => {
      if (filter === "watched") return g.watched;
      if (filter === "unwatched") return !g.watched;
      return true;
    });

    if (filtered.length === 0) {
      listEl.innerHTML = `<p class="helper-text">該当する試合がありません。</p>`;
      return;
    }

    listEl.innerHTML = filtered.map(g => {
      const bleagueUrl = g.scheduleKey
        ? `https://www.bleague.jp/game_detail/?ScheduleKey=${encodeURIComponent(g.scheduleKey)}&tab=4`
        : `https://www.google.com/search?q=${encodeURIComponent("site:bleague.jp/game_detail/ " + g.date + " " + g.match)}`;

      const basketLiveUrl = `https://basketball.mb.softbank.jp/search?keyword=${encodeURIComponent(g.match.split("（")[0].replace("vs", " "))}`;

      return `
        <div class="game-item ${g.watched ? 'watched' : 'unwatched'}">
          <div class="game-header">
            <div class="game-meta">
              <span class="game-date">${g.date}</span>
              <span class="game-matchup">${g.match}</span>
            </div>
            <span class="status-badge ${g.watched ? 'status-watched' : 'status-unwatched'}" onclick="toggleWatched('${g.id}')">
              ${g.watched ? '✔ 視聴・分析済' : '● 未視聴（タップで切替）'}
            </span>
          </div>
          <div class="crew-box">
            <strong>担当審判：</strong>${g.crew} ${g.scheduleKey ? `<span style="margin-left:8px; opacity:0.7;">(Key: ${g.scheduleKey})</span>` : ''}
          </div>
          ${g.memo ? `<div class="memo-box">${g.memo}</div>` : ''}
          <div class="btn-group" style="margin-top:4px;">
            <a class="btn btn-primary btn-sm" href="${basketLiveUrl}" target="_blank" rel="noopener">
              🏀 バスケットLIVEで探す
            </a>
            <a class="btn btn-secondary btn-sm" href="${bleagueUrl}" target="_blank" rel="noopener">
              📊 Bリーグ公式BoxScore
            </a>
            <button class="btn btn-secondary btn-sm" onclick="editMemo('${g.id}')">
              ✏️ メモ編集
            </button>
            <button class="btn btn-secondary btn-sm" onclick="deleteGame('${g.id}')" style="margin-left:auto; opacity:0.6;">
              削除
            </button>
          </div>
        </div>
      `;
    }).join("");
  }

  renderGames();
</script>
</body>
</html>