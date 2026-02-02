# app.py
import random
import requests
import streamlit as st

# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(
    page_title="TMDB 연동 심리테스트 (영화 추천)",
    page_icon="🎬",
    layout="wide",
)

CSS = """
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

.block-container{ padding-top: 1.2rem; }
body { background: var(--bg); color: var(--text); }

.panel{
  background: linear-gradient(180deg, rgba(18,26,51,.95), rgba(12,18,40,.95));
  border:1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: 16px;
}

.small-muted{ color: var(--muted); font-size: 12px; }
.badge{
  display:inline-block;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: rgba(255,255,255,.04);
  color: var(--muted);
  font-size: 12px;
}
.badge.ok{
  border-color: rgba(34,197,94,.35);
  background: rgba(34,197,94,.08);
  color: #d8ffe8;
}
.badge.err{
  border-color: rgba(239,68,68,.35);
  background: rgba(239,68,68,.08);
  color: #ffd7d7;
}
.movie-card{
  border:1px solid var(--border);
  border-radius: 14px;
  overflow:hidden;
  background: rgba(255,255,255,.03);
  padding: 12px;
  height: 100%;
}
.movie-title{ font-weight: 900; margin: 0 0 6px; }
.meta{ color: var(--muted); font-size: 12px; margin-bottom: 8px; }
.reason{
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid rgba(255,255,255,.08);
  color: var(--muted);
  font-size: 12px;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# -----------------------------
# TMDB / 장르
# -----------------------------
GENRES = {
    "action":   {"id": 28,    "name": "액션"},
    "comedy":   {"id": 35,    "name": "코미디"},
    "drama":    {"id": 18,    "name": "드라마"},
    "scifi":    {"id": 878,   "name": "SF"},
    "romance":  {"id": 10749, "name": "로맨스"},
    "fantasy":  {"id": 14,    "name": "판타지"},
}

TMDB_DISCOVER_URL = "https://api.themoviedb.org/3/discover/movie"
POSTER_BASE = "https://image.tmdb.org/t/p/w500"

# -----------------------------
# 심리테스트 문항(가중치)
# -----------------------------
QUESTIONS = [
    {
        "id": "q1",
        "title": "Q1. 요즘 에너지는 어떤 쪽이야?",
        "options": [
            ("몸이 근질근질. 뭔가 터뜨리고 싶다", {"action": 3, "scifi": 1}),
            ("가볍게 웃고 싶다", {"comedy": 3}),
            ("조용히 감정 정리하고 싶다", {"drama": 3}),
            ("설레는 감정이 필요하다", {"romance": 3}),
            ("현실 탈출. 완전히 다른 세계로 가고 싶다", {"fantasy": 3, "scifi": 1}),
        ],
    },
    {
        "id": "q2",
        "title": "Q2. 스트레스 풀 때 더 끌리는 건?",
        "options": [
            ("시원한 한 방 / 역전 / 쾌감", {"action": 2, "scifi": 1}),
            ("드립, 상황극, 웃참 실패", {"comedy": 2}),
            ("사람 이야기, 성장, 관계", {"drama": 2, "romance": 1}),
            ("사랑, 케미, 여운", {"romance": 2, "drama": 1}),
            ("마법/룰/세계관 파고들기", {"fantasy": 2, "scifi": 1}),
        ],
    },
    {
        "id": "q3",
        "title": "Q3. 결말은 어떤 스타일이 좋아?",
        "options": [
            ("악당 박살! 깔끔한 승리", {"action": 2}),
            ("마지막까지 웃기면서 마무리", {"comedy": 2}),
            ("현실적이거나 씁쓸해도 여운", {"drama": 2}),
            ("감정 폭발 + 로맨틱한 마무리", {"romance": 2}),
            ("반전/설정 회수/세계 확장", {"scifi": 2, "fantasy": 1}),
        ],
    },
    {
        "id": "q4",
        "title": "Q4. 주인공 타입은?",
        "options": [
            ("무력/전투력으로 해결하는 타입", {"action": 2}),
            ("말빨/눈치/드립으로 살아남는 타입", {"comedy": 2}),
            ("내면이 깊고 상처가 있는 타입", {"drama": 2}),
            ("사랑 하나로 미친 듯이 달리는 타입", {"romance": 2}),
            ("규칙을 깨고 미지의 것을 탐험하는 타입", {"scifi": 2, "fantasy": 1}),
        ],
    },
    {
        "id": "q5",
        "title": "Q5. 보고 나서 남는 감정은?",
        "options": [
            ("심장이 뛴다. 아드레날린", {"action": 2}),
            ("기분 좋아짐. 피식피식", {"comedy": 2}),
            ("생각이 많아짐. 사람/삶/선택", {"drama": 2}),
            ("설렘/애틋함. 잔상이 남음", {"romance": 2}),
            ("와… 세계관. 상상력이 폭발", {"fantasy": 2, "scifi": 1}),
        ],
    },
    {
        "id": "q6",
        "title": "Q6. 너의 ‘현실 도피’ 방식은?",
        "options": [
            ("땀나는 액티비티/승부", {"action": 2}),
            ("친구랑 웃고 떠들기", {"comedy": 2}),
            ("혼자 조용히 몰입해서 울/웃", {"drama": 2}),
            ("누군가와의 관계/설렘 상상", {"romance": 2}),
            ("다른 세계로 순간이동", {"fantasy": 2, "scifi": 1}),
        ],
    },
]

# -----------------------------
# 유틸 / 분석 로직
# -----------------------------
def score_to_stars(vote_average: float) -> str:
    v = float(vote_average or 0.0)
    stars = round((v / 10.0) * 5)
    return "★" * stars + "☆" * (5 - stars)

def pick_top_traits(answers: dict) -> list[str]:
    tags = []
    # Q1, Q3, Q5 중심 라벨링
    q1 = answers.get("q1", "")
    q3 = answers.get("q3", "")
    q5 = answers.get("q5", "")
    text = f"{q1} {q3} {q5}"

    if any(k in text for k in ["아드레날린", "근질근질", "한 방", "승부", "전투", "박살"]):
        tags.append("자극/속도감")
    if any(k in text for k in ["웃", "드립", "피식", "상황극"]):
        tags.append("유머/가벼움")
    if any(k in text for k in ["여운", "생각", "내면", "상처", "현실적", "선택"]):
        tags.append("감정/여운")
    if any(k in text for k in ["설렘", "로맨틱", "관계", "애틋"]):
        tags.append("설렘/관계")
    if any(k in text for k in ["세계관", "마법", "반전", "탐험", "미지"]):
        tags.append("상상/세계관")

    # 중복 제거 + 2개로 제한
    out = []
    for t in tags:
        if t not in out:
            out.append(t)
    return out[:2]

def build_reason(best_key: str, scores: dict, traits: list[str]) -> str:
    gname = GENRES[best_key]["name"]
    trait_text = f"({', '.join(traits)})" if traits else ""
    base = {
        "action":  "지금은 ‘속도감 + 쾌감’이 제일 잘 먹히는 상태라",
        "comedy":  "머리를 쉬게 해주는 ‘가벼운 텐션’이 필요해 보여서",
        "drama":   "감정선이 탄탄한 이야기에 몰입하면 정리가 될 것 같아서",
        "romance": "설렘과 케미가 있는 관계 서사가 기분을 올려줄 것 같아서",
        "fantasy": "현실에서 잠깐 벗어나 ‘다른 세계’에 빠지는 게 맞아 보여서",
        "scifi":   "설정/아이디어로 뇌를 자극하는 쪽이 지금 딱이라",
    }[best_key]

    hint = f"최종 장르는 {gname}{trait_text} 쪽 점수가 가장 높게 나왔어요."
    return f"{base} {gname}를 추천. {hint}"

def analyze_genre(selected_options: dict) -> dict:
    scores = {k: 0 for k in GENRES.keys()}

    for q in QUESTIONS:
        qid = q["id"]
        picked_text, picked_score = selected_options[qid]
        for key, add in picked_score.items():
            scores[key] += int(add)

    # 동점 처리: 우선순위로 안정적으로 선택
    priority = ["drama", "romance", "comedy", "action", "fantasy", "scifi"]
    best_key = priority[0]
    for k in scores.keys():
        if scores[k] > scores[best_key]:
            best_key = k
        elif scores[k] == scores[best_key]:
            if priority.index(k) < priority.index(best_key):
                best_key = k

    traits = pick_top_traits({qid: selected_options[qid][0] for qid in selected_options})
    reason = build_reason(best_key, scores, traits)
    return {"best_key": best_key, "scores": scores, "traits": traits, "reason": reason}

@st.cache_data(show_spinner=False, ttl=600)
def fetch_top_movies_by_genre(api_key: str, genre_id: int, page: int = 1) -> list[dict]:
    params = {
        "api_key": api_key,
        "with_genres": genre_id,
        "language": "ko-KR",
        "sort_by": "popularity.desc",
        "page": page,
    }
    r = requests.get(TMDB_DISCOVER_URL, params=params, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(f"TMDB 요청 실패: HTTP {r.status_code} / {r.text[:200]}")
    data = r.json()
    results = data.get("results") or []
    return results[:5]

def build_movie_reason(best_key: str, traits: list[str], overview: str) -> str:
    t = ", ".join(traits) if traits else "지금 기분"
    presets = {
        "action":  [f"{t}에 맞는 속도감", "몰입 빠른 전개", "카타르시스가 확실"],
        "comedy":  [f"{t}에 맞는 가벼운 텐션", "웃음 포인트가 확실", "피로도 낮은 관람감"],
        "drama":   [f"{t}에 맞는 감정선", "인물 관계가 탄탄", "여운이 오래 남음"],
        "romance": [f"{t}에 맞는 설렘", "케미 중심", "감정 몰입이 쉬움"],
        "fantasy": [f"{t}에 맞는 세계관", "현실 탈출감", "상상력을 자극"],
        "scifi":   [f"{t}에 맞는 아이디어", "설정이 흥미롭다", "생각할 거리 제공"],
    }
    base = random.choice(presets.get(best_key, [f"{t}에 맞는 분위기"]))

    extra = ""
    ov = overview or ""
    if any(k in ov for k in ["우주", "행성", "외계", "미래", "AI", "로봇", "시간"]):
        extra = "설정 맛이 좋음"
    elif any(k in ov for k in ["사랑", "연인", "로맨스", "결혼", "첫사랑", "이별"]):
        extra = "감정선이 직관적"
    elif any(k in ov for k in ["가족", "성장", "인생", "관계"]):
        extra = "관계 서사에 강함"
    elif any(k in ov for k in ["전쟁", "추격", "암살", "범죄", "복수"]):
        extra = "긴장감이 빠르게 올라감"
    elif any(k in ov for k in ["마법", "왕국", "용", "괴물", "저주", "모험"]):
        extra = "판타지 감성이 뚜렷"

    return f"{base}" + (f" · {extra}" if extra else "")

# -----------------------------
# 세션 상태
# -----------------------------
if "api_key" not in st.session_state:
    st.session_state.api_key = ""
if "result" not in st.session_state:
    st.session_state.result = None  # {"best_key", "traits", "reason"}
if "movies" not in st.session_state:
    st.session_state.movies = None

# -----------------------------
# Sidebar: API Key 입력
# -----------------------------
with st.sidebar:
    st.markdown("## 🔑 TMDB API Key")
    api_key = st.text_input(
        "API Key (password)",
        value=st.session_state.api_key,
        type="password",
        placeholder="TMDB API Key 입력",
    )
    st.session_state.api_key = api_key.strip()

    if st.session_state.api_key:
        st.markdown('<span class="badge ok">API Key: 설정됨</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="badge err">API Key: 미설정</span>', unsafe_allow_html=True)

    st.caption("※ 실제 서비스는 키 노출 방지를 위해 서버(프록시)에서 호출하는 게 안전합니다.")

# -----------------------------
# UI
# -----------------------------
st.title("🎬 TMDB 연동 심리테스트")
st.write("답변을 분석해서 장르를 결정한 뒤, TMDB에서 해당 장르의 **인기 영화 5개**를 추천합니다.")

colA, colB = st.columns([1.2, 0.8], gap="large")

# 퀴즈 입력
with colA:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("심리테스트 문항")

    selected = {}
    for q in QUESTIONS:
        opts_text = [t for (t, _) in q["options"]]
        # radio 기본값 없음 처리: index=None은 최신 streamlit에서 지원(버전에 따라 다를 수 있어 안전하게 처리)
        choice = st.radio(q["title"], opts_text, index=0, key=q["id"])
        # 사용자가 바꾸지 않고 넘어가도 동작하도록, 기본값은 0으로 둠(원하면 index=None + validation로 바꾸면 됨)
        # 하지만 요구사항 "미응답이면 결과 안나오기"를 정확히 하고 싶으면 아래 validation을 별도로 구현.
        picked_score = dict(q["options"][opts_text.index(choice)][1])
        selected[q["id"]] = (choice, picked_score)

    btn1, btn2, btn3 = st.columns([0.25, 0.25, 0.5])
    with btn1:
        do_result = st.button("결과 보기", use_container_width=True)
    with btn2:
        do_reset = st.button("초기화", use_container_width=True)
    with btn3:
        st.markdown('<div class="small-muted">문항/가중치는 코드에서 QUESTIONS만 바꾸면 됩니다.</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# 장르 후보 안내
with colB:
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("장르 후보")
    st.write("점수가 가장 높은 장르 1개를 최종 선택합니다.")
    st.markdown(
        """
- 액션 (28)
- 코미디 (35)
- 드라마 (18)
- SF (878)
- 로맨스 (10749)
- 판타지 (14)
        """.strip()
    )
    st.markdown('<div class="small-muted">결과는 “답변 → 장르 점수 합산” 룰 기반입니다.</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------
# 버튼 로직
# -----------------------------
if do_reset:
    st.session_state.result = None
    st.session_state.movies = None
    st.success("초기화 완료.")

if do_result:
    if not st.session_state.api_key:
        st.error("TMDB API Key가 필요합니다. 사이드바에서 입력하세요.")
    else:
        # 분석
        analysis = analyze_genre(selected)
        best_key = analysis["best_key"]
        genre_id = GENRES[best_key]["id"]

        st.session_state.result = {
            "best_key": best_key,
            "traits": analysis["traits"],
            "reason": analysis["reason"],
        }

        # TMDB 호출
        try:
            with st.spinner("TMDB에서 인기 영화 불러오는 중..."):
                movies = fetch_top_movies_by_genre(st.session_state.api_key, genre_id, page=1)
            st.session_state.movies = movies
            st.success("완료. 아래 결과를 확인하세요.")
        except Exception as e:
            st.session_state.movies = None
            st.error(f"에러: {e}")

# -----------------------------
# 결과 출력
# -----------------------------
if st.session_state.result:
    best_key = st.session_state.result["best_key"]
    genre_name = GENRES[best_key]["name"]
    genre_id = GENRES[best_key]["id"]
    traits = st.session_state.result["traits"]
    reason = st.session_state.result["reason"]

    st.markdown("---")
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.subheader("결과")
    c1, c2 = st.columns([0.7, 0.3])
    with c1:
        st.markdown(f"### 당신에게 맞는 장르: **{genre_name}**")
        st.write(reason)
        if traits:
            st.markdown(f'<span class="badge">키워드: {", ".join(traits)}</span>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<span class="badge ok">GENRE_ID: {genre_id}</span>', unsafe_allow_html=True)

        reroll = st.button("같은 장르로 다시 추천", use_container_width=True)
        if reroll:
            if not st.session_state.api_key:
                st.error("TMDB API Key가 필요합니다.")
            else:
                try:
                    page = random.randint(1, 3)
                    with st.spinner("다시 불러오는 중..."):
                        movies = fetch_top_movies_by_genre(st.session_state.api_key, genre_id, page=page)
                    st.session_state.movies = movies
                    st.success("갱신 완료.")
                except Exception as e:
                    st.error(f"에러: {e}")

    st.markdown("</div>", unsafe_allow_html=True)

    movies = st.session_state.movies or []
    if movies:
        st.markdown("### 추천 영화 5개")
        cols = st.columns(5)
        for i, m in enumerate(movies):
            title = (m.get("title") or "").strip() or "제목 정보 없음"
            overview = (m.get("overview") or "").strip() or "줄거리 정보가 부족합니다."
            vote = float(m.get("vote_average") or 0.0)
            poster_path = m.get("poster_path")
            poster_url = f"{POSTER_BASE}{poster_path}" if poster_path else None
            why = build_movie_reason(best_key, traits, overview)

            with cols[i]:
                st.markdown('<div class="movie-card">', unsafe_allow_html=True)
                if poster_url:
                    st.image(poster_url, use_container_width=True)
                else:
                    st.info("포스터 없음")
                st.markdown(f'<div class="movie-title">{title}</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="meta">평점 {vote:.1f}/10 · {score_to_stars(vote)}</div>',
                    unsafe_allow_html=True
                )
                st.write(overview)
                st.markdown(f'<div class="reason"><b>추천 이유:</b> {why}</div>', unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("영화 결과가 비었습니다. API Key/장르/네트워크 상태를 확인하세요.")
