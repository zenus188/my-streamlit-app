<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>TMDB 연동 심리테스트 (영화 추천)</title>
  <style>
    :root{
      --bg:#0b1020;
      --panel:#121a33;
      --panel2:#0f1730;
      --text:#e9edff;
      --muted:#a9b2d6;
      --accent:#7c5cff;
      --accent2:#22c55e;
      --danger:#ef4444;
      --border: rgba(255,255,255,.10);
      --shadow: 0 10px 30px rgba(0,0,0,.35);
      --radius: 16px;
    }
    *{box-sizing:border-box}
    body{
      margin:0;
      font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans KR", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
      background: radial-gradient(1200px 600px at 20% -10%, rgba(124,92,255,.35), transparent 60%),
                  radial-gradient(1000px 500px at 90% 10%, rgba(34,197,94,.18), transparent 55%),
                  var(--bg);
      color:var(--text);
      line-height:1.4;
    }
    header{
      position: sticky;
      top:0;
      z-index: 5;
      backdrop-filter: blur(10px);
      background: rgba(11,16,32,.65);
      border-bottom:1px solid var(--border);
    }
    .topbar{
      max-width: 1100px;
      margin: 0 auto;
      padding: 14px 16px;
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:12px;
    }
    .brand{
      display:flex; align-items:center; gap:10px;
      font-weight:800;
      letter-spacing:.2px;
    }
    .badge{
      font-size:12px;
      padding: 4px 10px;
      border:1px solid var(--border);
      border-radius:999px;
      color: var(--muted);
      background: rgba(255,255,255,.04);
    }
    .btn{
      border:1px solid var(--border);
      background: rgba(255,255,255,.06);
      color:var(--text);
      padding:10px 14px;
      border-radius: 12px;
      cursor:pointer;
      transition:.15s;
      font-weight:700;
    }
    .btn:hover{ transform: translateY(-1px); background: rgba(255,255,255,.10); }
    .btn.primary{
      background: linear-gradient(135deg, rgba(124,92,255,.95), rgba(124,92,255,.55));
      border-color: rgba(124,92,255,.35);
    }
    .btn.primary:hover{ background: linear-gradient(135deg, rgba(124,92,255,1), rgba(124,92,255,.65)); }
    .btn.good{
      background: linear-gradient(135deg, rgba(34,197,94,.95), rgba(34,197,94,.55));
      border-color: rgba(34,197,94,.35);
    }
    .btn.danger{
      background: rgba(239,68,68,.12);
      border-color: rgba(239,68,68,.25);
      color:#ffd7d7;
    }

    .layout{
      max-width: 1100px;
      margin: 0 auto;
      padding: 18px 16px 60px;
      display:grid;
      grid-template-columns: 1fr;
      gap:18px;
    }

    .card{
      background: linear-gradient(180deg, rgba(18,26,51,.95), rgba(12,18,40,.95));
      border:1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      overflow:hidden;
    }
    .card .inner{ padding: 16px; }

    .grid2{
      display:grid;
      grid-template-columns: 1fr;
      gap: 14px;
    }
    @media (min-width: 920px){
      .grid2{ grid-template-columns: 1.1fr .9fr; }
    }

    .question{
      border:1px solid var(--border);
      border-radius: 14px;
      padding: 14px;
      background: rgba(255,255,255,.03);
    }
    .qtitle{
      font-weight:800;
      margin: 0 0 10px;
    }
    .options{
      display:grid;
      gap: 8px;
    }
    label.opt{
      display:flex; align-items:flex-start; gap:10px;
      padding: 10px 12px;
      border:1px solid var(--border);
      border-radius: 12px;
      cursor:pointer;
      background: rgba(255,255,255,.03);
      transition:.12s;
    }
    label.opt:hover{ background: rgba(255,255,255,.06); transform: translateY(-1px); }
    input[type="radio"]{ margin-top: 3px; }

    .muted{ color:var(--muted); }
    .hint{ font-size: 13px; color: var(--muted); }
    .row{
      display:flex; gap:10px; flex-wrap:wrap; align-items:center;
    }

    /* Sidebar */
    .backdrop{
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,.55);
      display:none;
      z-index: 10;
    }
    .backdrop.show{ display:block; }
    .sidebar{
      position: fixed;
      top:0;
      right:0;
      height:100%;
      width: 360px;
      max-width: 92vw;
      background: rgba(12,18,40,.98);
      border-left:1px solid var(--border);
      box-shadow: -10px 0 30px rgba(0,0,0,.45);
      transform: translateX(100%);
      transition: .18s ease;
      z-index: 11;
      display:flex;
      flex-direction: column;
    }
    .sidebar.show{ transform: translateX(0); }
    .sidebar header{
      position: unset;
      background: transparent;
      border-bottom:1px solid var(--border);
      backdrop-filter: none;
    }
    .sidebar .content{
      padding: 16px;
      display:flex;
      flex-direction: column;
      gap: 12px;
    }
    .field label{
      display:block;
      font-size: 12px;
      color: var(--muted);
      margin-bottom: 6px;
    }
    .field input{
      width:100%;
      padding: 12px 12px;
      border-radius: 12px;
      border:1px solid var(--border);
      background: rgba(255,255,255,.04);
      color: var(--text);
      outline:none;
    }
    .field input:focus{ border-color: rgba(124,92,255,.6); }
    .pill{
      display:inline-flex;
      gap:8px;
      align-items:center;
      font-size: 12px;
      padding: 6px 10px;
      border-radius: 999px;
      border:1px solid var(--border);
      background: rgba(255,255,255,.04);
      color: var(--muted);
    }

    /* Results */
    .resultsTop{
      display:flex;
      flex-wrap:wrap;
      align-items:center;
      justify-content:space-between;
      gap: 12px;
    }
    .genreBig{
      font-size: 20px;
      font-weight: 900;
      margin: 0;
    }
    .movies{
      display:grid;
      grid-template-columns: 1fr;
      gap: 12px;
      margin-top: 12px;
    }
    @media (min-width: 720px){
      .movies{ grid-template-columns: 1fr 1fr; }
    }
    @media (min-width: 1020px){
      .movies{ grid-template-columns: 1fr 1fr 1fr; }
    }
    .movie{
      border:1px solid var(--border);
      border-radius: 14px;
      overflow:hidden;
      background: rgba(255,255,255,.03);
      display:flex;
      flex-direction: column;
      min-height: 100%;
    }
    .poster{
      width:100%;
      aspect-ratio: 2/3;
      object-fit: cover;
      background: rgba(255,255,255,.04);
    }
    .movie .body{
      padding: 12px;
      display:flex;
      flex-direction: column;
      gap: 8px;
      flex:1;
    }
    .movie h4{
      margin:0;
      font-size: 15px;
      font-weight: 900;
    }
    .meta{
      display:flex;
      align-items:center;
      justify-content:space-between;
      gap:10px;
      color: var(--muted);
      font-size: 12px;
    }
    .overview{
      margin:0;
      color: rgba(233,237,255,.90);
      font-size: 13px;
      display: -webkit-box;
      -webkit-line-clamp: 6;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .reason{
      margin:0;
      font-size: 12px;
      color: var(--muted);
      padding-top: 6px;
      border-top: 1px solid rgba(255,255,255,.08);
    }

    .status{
      margin-top: 10px;
      padding: 10px 12px;
      border-radius: 12px;
      border:1px solid var(--border);
      background: rgba(255,255,255,.03);
      color: var(--muted);
      font-size: 13px;
      display:none;
    }
    .status.show{ display:block; }
    .status.error{
      border-color: rgba(239,68,68,.35);
      background: rgba(239,68,68,.08);
      color: #ffd7d7;
    }
    .status.ok{
      border-color: rgba(34,197,94,.35);
      background: rgba(34,197,94,.08);
      color: #d8ffe8;
    }
    .small{
      font-size: 12px;
      color: var(--muted);
    }
    .divider{
      height:1px;
      background: rgba(255,255,255,.10);
      margin: 10px 0;
    }
  </style>
</head>

<body>
  <header>
    <div class="topbar">
      <div class="brand">
        <span style="display:inline-flex;width:34px;height:34px;border-radius:12px;background:rgba(124,92,255,.18);align-items:center;justify-content:center;border:1px solid rgba(124,92,255,.35)">🎬</span>
        <div>
          <div style="font-size:14px; font-weight:900;">TMDB 연동 심리테스트</div>
          <div class="muted" style="font-size:12px;">답변 기반 장르 → 인기 영화 5개 추천</div>
        </div>
      </div>
      <div class="row">
        <span id="keyBadge" class="pill">API Key: 미설정</span>
        <button class="btn" id="openSidebarBtn">API Key 설정</button>
      </div>
    </div>
  </header>

  <!-- Sidebar -->
  <div class="backdrop" id="backdrop"></div>
  <aside class="sidebar" id="sidebar">
    <header>
      <div class="topbar" style="padding:14px 16px;">
        <div class="brand">
          <span style="display:inline-flex;width:34px;height:34px;border-radius:12px;background:rgba(255,255,255,.06);align-items:center;justify-content:center;border:1px solid var(--border)">🔑</span>
          <div>
            <div style="font-size:14px; font-weight:900;">TMDB API Key</div>
            <div class="muted" style="font-size:12px;">로컬 저장(localStorage)</div>
          </div>
        </div>
        <button class="btn" id="closeSidebarBtn">닫기</button>
      </div>
    </header>
    <div class="content">
      <div class="field">
        <label for="apiKeyInput">API Key</label>
        <input id="apiKeyInput" type="password" placeholder="여기에 TMDB API Key 입력" />
        <div class="small" style="margin-top:8px;">
          ※ 프론트엔드에 키를 두면 노출됩니다. 실제 서비스는 서버(프록시)로 숨기는 게 안전합니다.
        </div>
      </div>

      <div class="row">
        <button class="btn good" id="saveKeyBtn">저장</button>
        <button class="btn danger" id="clearKeyBtn">삭제</button>
      </div>

      <div class="divider"></div>
      <div class="small">
        TMDB Discover API를 사용합니다.<br/>
        language=ko-KR, with_genres로 필터링합니다.
      </div>
    </div>
  </aside>

  <main class="layout">
    <section class="card">
      <div class="inner grid2">
        <div>
          <h2 style="margin:0 0 8px; font-weight:900;">심리테스트</h2>
          <p class="muted" style="margin:0 0 14px;">
            아래 질문에 답하면, 당신의 “기분/성향”에 맞는 장르를 뽑아서 TMDB 인기 영화 5개를 추천합니다.
          </p>

          <div id="quiz"></div>

          <div class="row" style="margin-top: 14px;">
            <button class="btn primary" id="resultBtn">결과 보기</button>
            <button class="btn" id="resetBtn">초기화</button>
            <span class="hint">※ 모든 문항에 답하지 않으면 결과가 안 나옵니다.</span>
          </div>

          <div id="status" class="status"></div>
        </div>

        <div class="card" style="box-shadow:none;">
          <div class="inner">
            <h3 style="margin:0 0 8px; font-weight:900;">장르 후보</h3>
            <p class="muted" style="margin:0 0 10px;">점수가 가장 높은 장르 1개를 최종 선택합니다.</p>
            <ul class="muted" style="margin:0; padding-left: 18px; font-size: 13px;">
              <li>액션 (28)</li>
              <li>코미디 (35)</li>
              <li>드라마 (18)</li>
              <li>SF (878)</li>
              <li>로맨스 (10749)</li>
              <li>판타지 (14)</li>
            </ul>
            <div class="divider"></div>
            <div class="small">
              결과는 “답변 → 장르 점수 합산” 방식이라 단순하지만, 심리테스트 느낌은 충분히 납니다.
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="card" id="resultsCard" style="display:none;">
      <div class="inner">
        <div class="resultsTop">
          <div>
            <p class="muted" style="margin:0 0 6px;">당신에게 맞는 장르</p>
            <h3 class="genreBig" id="finalGenreTitle">-</h3>
            <p class="muted" style="margin:6px 0 0;" id="finalGenreReason"></p>
          </div>
          <div class="row">
            <span class="pill" id="finalGenreIdPill">GENRE_ID: -</span>
            <button class="btn" id="refreshBtn">같은 장르로 다시 추천</button>
          </div>
        </div>

        <div id="movies" class="movies"></div>
      </div>
    </section>
  </main>

  <script>
    /***********************
     * 1) 장르 정의 / 매핑
     ************************/
    const GENRES = {
      action:   { id: 28,    name: "액션" },
      comedy:   { id: 35,    name: "코미디" },
      drama:    { id: 18,    name: "드라마" },
      scifi:    { id: 878,   name: "SF" },
      romance:  { id: 10749, name: "로맨스" },
      fantasy:  { id: 14,    name: "판타지" },
    };

    // 심리테스트 문항: 선택지마다 장르 점수 가중치
    // (원하면 여기 문항/가중치만 바꾸면 테스트 성향이 바뀜)
    const QUESTIONS = [
      {
        id: "q1",
        title: "Q1. 요즘 에너지는 어떤 쪽이야?",
        options: [
          { text: "몸이 근질근질. 뭔가 터뜨리고 싶다", score: { action: 3, scifi: 1 } },
          { text: "가볍게 웃고 싶다", score: { comedy: 3 } },
          { text: "조용히 감정 정리하고 싶다", score: { drama: 3 } },
          { text: "설레는 감정이 필요하다", score: { romance: 3 } },
          { text: "현실 탈출. 완전히 다른 세계로 가고 싶다", score: { fantasy: 3, scifi: 1 } },
        ]
      },
      {
        id: "q2",
        title: "Q2. 스트레스 풀 때 더 끌리는 건?",
        options: [
          { text: "시원한 한 방 / 역전 / 쾌감", score: { action: 2, scifi: 1 } },
          { text: "드립, 상황극, 웃참 실패", score: { comedy: 2 } },
          { text: "사람 이야기, 성장, 관계", score: { drama: 2, romance: 1 } },
          { text: "사랑, 케미, 여운", score: { romance: 2, drama: 1 } },
          { text: "마법/룰/세계관 파고들기", score: { fantasy: 2, scifi: 1 } },
        ]
      },
      {
        id: "q3",
        title: "Q3. 결말은 어떤 스타일이 좋아?",
        options: [
          { text: "악당 박살! 깔끔한 승리", score: { action: 2 } },
          { text: "마지막까지 웃기면서 마무리", score: { comedy: 2 } },
          { text: "현실적이거나 씁쓸해도 여운", score: { drama: 2 } },
          { text: "감정 폭발 + 로맨틱한 마무리", score: { romance: 2 } },
          { text: "반전/설정 회수/세계 확장", score: { scifi: 2, fantasy: 1 } },
        ]
      },
      {
        id: "q4",
        title: "Q4. 주인공 타입은?",
        options: [
          { text: "무력/전투력으로 해결하는 타입", score: { action: 2 } },
          { text: "말빨/눈치/드립으로 살아남는 타입", score: { comedy: 2 } },
          { text: "내면이 깊고 상처가 있는 타입", score: { drama: 2 } },
          { text: "사랑 하나로 미친 듯이 달리는 타입", score: { romance: 2 } },
          { text: "규칙을 깨고 미지의 것을 탐험하는 타입", score: { scifi: 2, fantasy: 1 } },
        ]
      },
      {
        id: "q5",
        title: "Q5. 보고 나서 남는 감정은?",
        options: [
          { text: "심장이 뛴다. 아드레날린", score: { action: 2 } },
          { text: "기분 좋아짐. 피식피식", score: { comedy: 2 } },
          { text: "생각이 많아짐. 사람/삶/선택", score: { drama: 2 } },
          { text: "설렘/애틋함. 잔상이 남음", score: { romance: 2 } },
          { text: "와… 세계관. 상상력이 폭발", score: { fantasy: 2, scifi: 1 } },
        ]
      },
      {
        id: "q6",
        title: "Q6. 너의 ‘현실 도피’ 방식은?",
        options: [
          { text: "땀나는 액티비티/승부", score: { action: 2 } },
          { text: "친구랑 웃고 떠들기", score: { comedy: 2 } },
          { text: "혼자 조용히 몰입해서 울/웃", score: { drama: 2 } },
          { text: "누군가와의 관계/설렘 상상", score: { romance: 2 } },
          { text: "다른 세계로 순간이동", score: { fantasy: 2, scifi: 1 } },
        ]
      },
    ];

    /***********************
     * 2) DOM 유틸
     ************************/
    const $ = (sel) => document.querySelector(sel);
    const quizEl = $("#quiz");
    const statusEl = $("#status");
    const resultsCard = $("#resultsCard");
    const moviesEl = $("#movies");

    function setStatus(msg, type = "info") {
      statusEl.textContent = msg;
      statusEl.classList.add("show");
      statusEl.classList.remove("error","ok");
      if (type === "error") statusEl.classList.add("error");
      if (type === "ok") statusEl.classList.add("ok");
    }
    function clearStatus() {
      statusEl.textContent = "";
      statusEl.className = "status";
    }

    /***********************
     * 3) API Key (사이드바)
     ************************/
    const LS_KEY = "tmdb_api_key";
    const sidebar = $("#sidebar");
    const backdrop = $("#backdrop");
    const keyBadge = $("#keyBadge");
    const apiKeyInput = $("#apiKeyInput");

    function getApiKey() {
      return localStorage.getItem(LS_KEY) || "";
    }
    function setApiKey(key) {
      localStorage.setItem(LS_KEY, key);
      refreshKeyBadge();
    }
    function clearApiKey() {
      localStorage.removeItem(LS_KEY);
      refreshKeyBadge();
    }
    function refreshKeyBadge() {
      const key = getApiKey();
      keyBadge.textContent = key ? "API Key: 설정됨" : "API Key: 미설정";
      keyBadge.style.borderColor = key ? "rgba(34,197,94,.35)" : "rgba(255,255,255,.10)";
      keyBadge.style.background = key ? "rgba(34,197,94,.08)" : "rgba(255,255,255,.04)";
      keyBadge.style.color = key ? "#d8ffe8" : "var(--muted)";
    }

    function openSidebar() {
      apiKeyInput.value = getApiKey();
      backdrop.classList.add("show");
      sidebar.classList.add("show");
    }
    function closeSidebar() {
      backdrop.classList.remove("show");
      sidebar.classList.remove("show");
    }

    $("#openSidebarBtn").addEventListener("click", openSidebar);
    $("#closeSidebarBtn").addEventListener("click", closeSidebar);
    backdrop.addEventListener("click", closeSidebar);

    $("#saveKeyBtn").addEventListener("click", () => {
      const key = apiKeyInput.value.trim();
      if (!key) return setStatus("API Key가 비어있습니다.", "error");
      setApiKey(key);
      setStatus("API Key 저장 완료.", "ok");
      closeSidebar();
    });

    $("#clearKeyBtn").addEventListener("click", () => {
      clearApiKey();
      apiKeyInput.value = "";
      setStatus("API Key 삭제 완료.", "ok");
    });

    refreshKeyBadge();

    /***********************
     * 4) 퀴즈 렌더링
     ************************/
    function renderQuiz() {
      quizEl.innerHTML = "";
      QUESTIONS.forEach((q, idx) => {
        const wrapper = document.createElement("div");
        wrapper.className = "question";
        wrapper.innerHTML = `
          <p class="qtitle">${q.title}</p>
          <div class="options">
            ${q.options.map((opt, i) => `
              <label class="opt">
                <input type="radio" name="${q.id}" value="${i}" />
                <span>${opt.text}</span>
              </label>
            `).join("")}
          </div>
        `;
        quizEl.appendChild(wrapper);
      });
    }
    renderQuiz();

    function getAnswers() {
      const answers = {};
      for (const q of QUESTIONS) {
        const checked = document.querySelector(`input[name="${q.id}"]:checked`);
        if (!checked) return null;
        answers[q.id] = Number(checked.value);
      }
      return answers;
    }

    /***********************
     * 5) 사용자 답변 분석 → 장르 결정
     ************************/
    function analyzeGenre(answers) {
      const scores = {
        action:0, comedy:0, drama:0, scifi:0, romance:0, fantasy:0
      };

      for (const q of QUESTIONS) {
        const pickedIndex = answers[q.id];
        const picked = q.options[pickedIndex];
        for (const [genreKey, add] of Object.entries(picked.score)) {
          scores[genreKey] += add;
        }
      }

      // 최고점 장르 고르기 (동점이면 랜덤이 아니라 "우선순위"로 안정적으로 선택)
      const priority = ["drama","romance","comedy","action","fantasy","scifi"];
      let bestKey = priority[0];
      for (const key of Object.keys(scores)) {
        if (scores[key] > scores[bestKey]) bestKey = key;
        if (scores[key] === scores[bestKey] && priority.indexOf(key) < priority.indexOf(bestKey)) bestKey = key;
      }

      // 간단한 “추천 이유” 템플릿
      const topTraits = pickTopTraits(answers);
      const reason = buildReason(bestKey, scores, topTraits);

      return { bestKey, scores, reason, traits: topTraits };
    }

    function pickTopTraits(answers) {
      // 답변에서 반복적으로 드러나는 키워드를 2~3개 뽑는 느낌 (간단 룰 기반)
      // 실제 심리테스트처럼 보이게 하는 “라벨링” 정도만 한다.
      const tags = [];
      // Q1, Q3, Q5를 중심으로 라벨링
      const q1 = QUESTIONS[0].options[answers["q1"]].text;
      const q3 = QUESTIONS[2].options[answers["q3"]].text;
      const q5 = QUESTIONS[4].options[answers["q5"]].text;

      if (/아드레날린|근질근질|한 방|승부|전투|박살/.test(q1 + q5 + q3)) tags.push("자극/속도감");
      if (/웃|드립|피식|상황극/.test(q1 + q5 + q3)) tags.push("유머/가벼움");
      if (/여운|생각|내면|상처|현실적|선택/.test(q1 + q5 + q3)) tags.push("감정/여운");
      if (/설렘|로맨틱|관계|애틋/.test(q1 + q5 + q3)) tags.push("설렘/관계");
      if (/세계관|마법|반전|탐험|미지/.test(q1 + q5 + q3)) tags.push("상상/세계관");

      // 2개 정도로 정리
      return [...new Set(tags)].slice(0, 2);
    }

    function buildReason(bestKey, scores, traits) {
      const gname = GENRES[bestKey].name;
      const traitText = traits.length ? `(${traits.join(", ")})` : "";
      // 장르별 한 줄 코멘트
      const base = {
        action:  "지금은 ‘속도감 + 쾌감’이 제일 잘 먹히는 상태라",
        comedy:  "머리를 쉬게 해주는 ‘가벼운 텐션’이 필요해 보여서",
        drama:   "감정선이 탄탄한 이야기에 몰입하면 정리가 될 것 같아서",
        romance: "설렘과 케미가 있는 관계 서사가 기분을 올려줄 것 같아서",
        fantasy: "현실에서 잠깐 벗어나 ‘다른 세계’에 빠지는 게 맞아 보여서",
        scifi:   "설정/아이디어로 뇌를 자극하는 쪽이 지금 딱이라",
      }[bestKey];

      // 점수 힌트(너무 길지 않게)
      const hint = `최종 장르는 ${gname}${traitText} 쪽 점수가 가장 높게 나왔어요.`;
      return `${base} ${gname}를 추천. ${hint}`;
    }

    /***********************
     * 6) TMDB API 호출 → 인기 영화 5개
     ************************/
    const TMDB_DISCOVER_URL = "https://api.themoviedb.org/3/discover/movie";
    const POSTER_BASE = "https://image.tmdb.org/t/p/w500";

    async function fetchTopMoviesByGenre(genreId, apiKey) {
      const url = `${TMDB_DISCOVER_URL}?api_key=${encodeURIComponent(apiKey)}&with_genres=${encodeURIComponent(genreId)}&language=ko-KR&sort_by=popularity.desc&page=1`;
      const res = await fetch(url);
      if (!res.ok) {
        const txt = await res.text().catch(() => "");
        throw new Error(`TMDB 요청 실패 (${res.status}) ${txt}`);
      }
      const data = await res.json();
      const list = Array.isArray(data.results) ? data.results : [];
      return list.slice(0, 5);
    }

    function safeText(s, fallback = "정보 없음") {
      if (typeof s !== "string") return fallback;
      const t = s.trim();
      return t ? t : fallback;
    }

    function scoreToStars(voteAverage) {
      // 0~10 → 0~5로 압축
      const v = typeof voteAverage === "number" ? voteAverage : 0;
      const stars = Math.round((v / 10) * 5);
      return "★".repeat(stars) + "☆".repeat(5 - stars);
    }

    function buildMovieReason(bestGenreKey, traits, movie) {
      // 장르 + traits 기반 “짧은 추천 이유”
      const t = traits.length ? traits.join(", ") : "지금 기분";
      const pieces = {
        action:  [`${t}에 맞는 속도감`, "몰입 빠른 전개", "강한 한 방의 카타르시스"],
        comedy:  [`${t}에 맞는 가벼운 텐션`, "웃음 포인트가 확실", "피로도 낮은 관람감"],
        drama:   [`${t}에 맞는 감정선`, "인물 관계가 탄탄", "여운이 오래 남는 타입"],
        romance: [`${t}에 맞는 설렘`, "케미 중심", "감정 몰입이 쉽다"],
        fantasy: [`${t}에 맞는 세계관`, "현실 탈출감", "상상력을 자극"],
        scifi:   [`${t}에 맞는 아이디어`, "설정이 흥미롭다", "생각할 거리 제공"],
      }[bestGenreKey] || [`${t}에 맞는 분위기`];

      // 영화 자체 힌트 1개 정도 섞기(줄거리/제목 기반 간단 룰)
      const ov = (movie && typeof movie.overview === "string") ? movie.overview : "";
      const extra =
        /우주|행성|외계|미래|AI|로봇|시간/.test(ov) ? "설정 맛이 좋음" :
        /사랑|연인|로맨스|결혼|첫사랑|이별/.test(ov) ? "감정선이 직관적" :
        /가족|성장|인생|관계/.test(ov) ? "관계 서사에 강함" :
        /전쟁|추격|암살|범죄|복수/.test(ov) ? "긴장감이 빠르게 올라감" :
        /마법|왕국|용|괴물|저주|모험/.test(ov) ? "판타지 감성이 뚜렷" :
        "";

      const base = pieces[Math.floor(Math.random() * pieces.length)];
      return extra ? `${base} · ${extra}` : base;
    }

    function renderResults(bestKey, reasonText, movies, traits) {
      const genre = GENRES[bestKey];
      $("#finalGenreTitle").textContent = genre.name;
      $("#finalGenreIdPill").textContent = `GENRE_ID: ${genre.id}`;
      $("#finalGenreReason").textContent = reasonText;

      moviesEl.innerHTML = movies.map(m => {
        const poster = m.poster_path ? `${POSTER_BASE}${m.poster_path}` : "";
        const title = safeText(m.title || m.name || "");
        const overview = safeText(m.overview, "줄거리 정보가 부족합니다.");
        const vote = (typeof m.vote_average === "number") ? m.vote_average.toFixed(1) : "0.0";
        const stars = scoreToStars(m.vote_average);
        const why = buildMovieReason(bestKey, traits, m);

        return `
          <article class="movie">
            ${
              poster
              ? `<img class="poster" src="${poster}" alt="${title} 포스터" loading="lazy" />`
              : `<div class="poster" style="display:flex;align-items:center;justify-content:center;color:var(--muted);">포스터 없음</div>`
            }
            <div class="body">
              <h4>${title}</h4>
              <div class="meta">
                <span>평점 ${vote} / 10</span>
                <span style="letter-spacing:.5px;">${stars}</span>
              </div>
              <p class="overview">${overview}</p>
              <p class="reason"><b>추천 이유:</b> ${why}</p>
            </div>
          </article>
        `;
      }).join("");

      resultsCard.style.display = "block";
      resultsCard.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    /***********************
     * 7) 버튼 동작: "결과 보기"
     ************************/
    let lastFinal = null; // { bestKey, reason, traits }

    async function runRecommendation() {
      clearStatus();

      const apiKey = getApiKey();
      if (!apiKey) {
        setStatus("TMDB API Key가 필요합니다. 우측 상단에서 설정하세요.", "error");
        openSidebar();
        return;
      }

      const answers = getAnswers();
      if (!answers) {
        setStatus("모든 문항에 답해야 결과를 볼 수 있습니다.", "error");
        return;
      }

      const analysis = analyzeGenre(answers);
      const { bestKey, reason, traits } = analysis;

      setStatus(`장르 분석 완료: ${GENRES[bestKey].name}. TMDB에서 인기 영화 불러오는 중...`, "ok");

      try {
        $("#resultBtn").disabled = true;
        $("#refreshBtn").disabled = true;

        const movies = await fetchTopMoviesByGenre(GENRES[bestKey].id, apiKey);
        if (!movies.length) {
          setStatus("영화 결과가 비었습니다. 장르/키를 확인해보세요.", "error");
          return;
        }

        lastFinal = { bestKey, reason, traits };
        renderResults(bestKey, reason, movies, traits);
        setStatus("완료. 아래에 추천 결과가 표시됩니다.", "ok");
      } catch (err) {
        setStatus(`에러: ${err.message}`, "error");
      } finally {
        $("#resultBtn").disabled = false;
        $("#refreshBtn").disabled = false;
      }
    }

    $("#resultBtn").addEventListener("click", runRecommendation);

    // 같은 장르로 다시 추천(인기순이라 보통 비슷하지만, TMDB 결과 변동/페이지 바꾸면 바뀔 수 있음)
    $("#refreshBtn").addEventListener("click", async () => {
      clearStatus();
      const apiKey = getApiKey();
      if (!apiKey) {
        setStatus("TMDB API Key가 필요합니다.", "error");
        openSidebar();
        return;
      }
      if (!lastFinal) {
        setStatus("먼저 테스트를 진행하고 결과를 만들어주세요.", "error");
        return;
      }

      try {
        $("#refreshBtn").disabled = true;
        setStatus(`같은 장르(${GENRES[lastFinal.bestKey].name})로 다시 불러오는 중...`, "ok");

        // 페이지 랜덤으로 살짝 바꿔 변동 주기 (1~3)
        const page = 1 + Math.floor(Math.random() * 3);
        const url = `${TMDB_DISCOVER_URL}?api_key=${encodeURIComponent(apiKey)}&with_genres=${encodeURIComponent(GENRES[lastFinal.bestKey].id)}&language=ko-KR&sort_by=popularity.desc&page=${page}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(`TMDB 요청 실패 (${res.status})`);
        const data = await res.json();
        const list = Array.isArray(data.results) ? data.results : [];
        const movies = list.slice(0, 5);

        renderResults(lastFinal.bestKey, lastFinal.reason, movies, lastFinal.traits);
        setStatus("갱신 완료.", "ok");
      } catch (err) {
        setStatus(`에러: ${err.message}`, "error");
      } finally {
        $("#refreshBtn").disabled = false;
      }
    });

    // 초기화
    $("#resetBtn").addEventListener("click", () => {
      clearStatus();
      // 라디오 체크 해제
      document.querySelectorAll('input[type="radio"]').forEach(r => r.checked = false);
      resultsCard.style.display = "none";
      moviesEl.innerHTML = "";
      lastFinal = null;
      setStatus("초기화 완료.", "ok");
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  </script>
</body>
</html>
