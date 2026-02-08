# app.py
import json
import re
from typing import Any, Dict, List, Optional

import requests
import streamlit as st
from openai import OpenAI


# -----------------------------
# App Config
# -----------------------------
st.set_page_config(
    page_title="Select Game",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded",
)

RAWG_BASE = "https://api.rawg.io/api"
TIMEOUT = 15

# 후보를 넉넉히 만들되, 최종 추천은 "확신 있는 것만" (개수 강제 X)
CANDIDATE_COUNT = 18
RAWG_MATCH_LIMIT = 18  # RAWG 팩트 확정 최대치 (모델에게 너무 많이 던지지 않기)


# -----------------------------
# Magazine UI (CSS)
# -----------------------------
MAGAZINE_CSS = """
<style>
:root{
  --bg:#0b0f19;
  --panel:#0f1628;
  --panel2:#0c1324;
  --ink:#e8eefc;
  --muted:#9fb0d0;
  --accent:#7c5cff;
  --accent2:#00d4ff;
  --card:#101a33;
  --line:rgba(255,255,255,0.08);
  --shadow: 0 14px 40px rgba(0,0,0,.35);
  --radius: 18px;
}

/* App background */
.stApp{
  background: radial-gradient(1200px 600px at 10% 0%, rgba(124,92,255,.22), transparent 60%),
              radial-gradient(900px 500px at 90% 15%, rgba(0,212,255,.16), transparent 55%),
              linear-gradient(180deg, var(--bg), #070a12);
  color: var(--ink);
}

/* Sidebar */
section[data-testid="stSidebar"]{
  background: linear-gradient(180deg, rgba(15,22,40,.96), rgba(10,15,25,.96));
  border-right: 1px solid var(--line);
}
section[data-testid="stSidebar"] *{
  color: var(--ink);
}
section[data-testid="stSidebar"] .stTextInput input,
section[data-testid="stSidebar"] .stTextArea textarea,
section[data-testid="stSidebar"] .stNumberInput input{
  background: rgba(255,255,255,.06) !important;
  border: 1px solid rgba(255,255,255,.10) !important;
  color: var(--ink) !important;
  border-radius: 12px !important;
}
section[data-testid="stSidebar"] .stMultiSelect div[data-baseweb="select"]{
  background: rgba(255,255,255,.06) !important;
  border: 1px solid rgba(255,255,255,.10) !important;
  border-radius: 12px !important;
}
section[data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"]{
  background: rgba(255,255,255,.06) !important;
  border: 1px solid rgba(255,255,255,.10) !important;
  border-radius: 12px !important;
}
section[data-testid="stSidebar"] button{
  border-radius: 14px !important;
}

/* Headline blocks */
.sg-hero{
  padding: 22px 22px;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: linear-gradient(135deg, rgba(124,92,255,.20), rgba(0,212,255,.10));
  box-shadow: var(--shadow);
}
.sg-hero h1{
  font-size: 40px;
  margin: 0;
  letter-spacing: -0.02em;
}
.sg-hero p{
  margin: 8px 0 0 0;
  color: var(--muted);
  font-size: 15px;
  line-height: 1.5;
}

/* Section title */
.sg-section{
  margin-top: 18px;
  margin-bottom: 8px;
  display:flex;
  align-items:center;
  gap:10px;
}
.sg-pill{
  font-size: 12px;
  color: var(--ink);
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: rgba(255,255,255,.06);
}
.sg-section h2{
  margin:0;
  font-size: 18px;
  letter-spacing: -0.01em;
}
.sg-sub{
  color: var(--muted);
  margin: 4px 0 0 0;
  font-size: 13px;
}

/* Game card */
.sg-card{
  border: 1px solid var(--line);
  border-radius: var(--radius);
  background: linear-gradient(180deg, rgba(16,26,51,.85), rgba(12,19,36,.92));
  box-shadow: var(--shadow);
  overflow: hidden;
}
.sg-card .sg-cover{
  width:100%;
  height: 220px;
  object-fit: cover;
  display:block;
  filter: saturate(1.05) contrast(1.03);
}
.sg-card .sg-body{
  padding: 14px 14px 12px 14px;
}
.sg-title{
  font-size: 18px;
  margin: 0;
  line-height: 1.2;
}
.sg-meta{
  margin-top: 8px;
  display:flex;
  flex-wrap: wrap;
  gap: 8px;
}
.sg-tag{
  font-size: 12px;
  color: var(--ink);
  padding: 5px 9px;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,.12);
  background: rgba(255,255,255,.05);
}
.sg-text{
  margin-top: 10px;
  color: var(--ink);
  font-size: 13.5px;
  line-height: 1.55;
}
.sg-muted{
  color: var(--muted);
}
.sg-divider{
  height: 1px;
  background: var(--line);
  margin: 12px 0;
}
.sg-links a{
  text-decoration: none;
}
.sg-links a:hover{
  text-decoration: underline;
}

/* Chat look */
[data-testid="stChatMessage"]{
  border-radius: 16px;
  border: 1px solid var(--line);
  background: rgba(255,255,255,.03);
}

/* Reduce default whitespace a bit */
.block-container{
  padding-top: 1.2rem;
  padding-bottom: 2.0rem;
}
</style>
"""
st.markdown(MAGAZINE_CSS, unsafe_allow_html=True)


# -----------------------------
# Utilities
# -----------------------------
def build_openai_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


def safe_json_loads(s: str) -> Dict[str, Any]:
    s = (s or "").strip()

    # code fence 방어
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s).strip()
        s = re.sub(r"\n?```$", "", s).strip()

    # 최후: 첫 '{'~마지막 '}' 추출 시도
    if "{" in s and "}" in s:
        s2 = s[s.find("{") : s.rfind("}") + 1].strip()
        try:
            return json.loads(s2)
        except Exception:
            pass

    return json.loads(s)


def join_nonempty(items: List[str]) -> str:
    items = [x.strip() for x in items if x and x.strip()]
    return ", ".join(items)


def map_platform_choice_to_rawg_tokens(platform_choice: str) -> List[str]:
    mapping = {
        "PC": ["PC"],
        "PS": ["PlayStation"],
        "Xbox": ["Xbox"],
        "Switch": ["Nintendo Switch", "Nintendo"],
        "모바일": ["Android", "iOS"],
    }
    return mapping.get(platform_choice, [])


# -----------------------------
# RAWG API helpers
# -----------------------------
def rawg_get(rawg_key: str, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not rawg_key:
        raise ValueError("RAWG API 키가 필요합니다.")
    params = params or {}
    params["key"] = rawg_key
    url = f"{RAWG_BASE}{endpoint}"
    r = requests.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def rawg_search_top(rawg_key: str, query: str) -> Optional[Dict[str, Any]]:
    data = rawg_get(
        rawg_key,
        "/games",
        params={
            "search": query,
            "page_size": 5,
            "search_precise": True,
        },
    )
    results = data.get("results") or []
    return results[0] if results else None


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def rawg_game_detail(rawg_key: str, game_id: int) -> Dict[str, Any]:
    return rawg_get(rawg_key, f"/games/{game_id}")


def game_platforms(detail: Dict[str, Any]) -> List[str]:
    out = []
    for p in detail.get("platforms") or []:
        name = (p.get("platform") or {}).get("name")
        if name:
            out.append(name)
    seen = set()
    uniq = []
    for x in out:
        if x not in seen:
            uniq.append(x)
            seen.add(x)
    return uniq


def game_genres(detail: Dict[str, Any]) -> List[str]:
    out = []
    for g in detail.get("genres") or []:
        name = g.get("name")
        if name:
            out.append(name)
    return out


def game_stores(detail: Dict[str, Any]) -> List[Dict[str, str]]:
    stores = []
    for s in detail.get("stores") or []:
        store_name = (s.get("store") or {}).get("name")
        url = s.get("url")
        if store_name and url:
            stores.append({"name": store_name, "url": url})
    return stores


def platform_filter_pass(user_platforms: List[str], game_plats: List[str]) -> bool:
    if not user_platforms:
        return True
    tokens: List[str] = []
    for up in user_platforms:
        tokens.extend(map_platform_choice_to_rawg_tokens(up))
    gp = " | ".join(game_plats).lower()
    return any(t.lower() in gp for t in tokens)


# -----------------------------
# Profile builder
# -----------------------------
def build_profile_text(
    preferred_genres: List[str],
    emotions: List[str],
    emotions_free: str,
    played_games: str,
    platforms: List[str],
    hours_per_day: float,
) -> str:
    free = emotions_free.strip()
    emotions_part = join_nonempty(emotions) if emotions else "없음/미선택"
    if free:
        emotions_part = f"{emotions_part} + 자유입력: {free}" if emotions_part != "없음/미선택" else f"자유입력: {free}"

    return f"""
[사용자 선호 프로필]
- 선호 장르: {join_nonempty(preferred_genres) if preferred_genres else "없음/미선택"}
- 원하는 감정(플레이 경험): {emotions_part}
- 재미있게 플레이한 게임(참고): {played_games.strip() if played_games.strip() else "미입력"}
- 선호 플랫폼/기기: {join_nonempty(platforms) if platforms else "없음/미선택"}
- 하루 예상 플레이시간: {hours_per_day}시간
""".strip()


# -----------------------------
# OpenAI steps
# -----------------------------
def openai_get_candidates(
    client: OpenAI,
    model: str,
    system_instructions: str,
    profile_text: str,
    n: int,
) -> List[str]:
    prompt = f"""
너는 게임 추천 전문가다.
아래 프로필을 보고 사용자가 좋아할 가능성이 높은 "게임 후보 제목" {n}개를 뽑아라.

규칙:
- 출력은 "유효한 JSON" 하나만 출력. (설명/마크다운/코드펜스 금지)
- 키는 candidates 하나만 사용: {{ "candidates": ["title1", ...] }}
- candidates는 정확히 {n}개.
- 게임 제목은 가능한 한 공식적으로 통용되는 영문/국문 제목으로.

{profile_text}
""".strip()

    resp = client.responses.create(model=model, instructions=system_instructions, input=prompt)
    obj = safe_json_loads(resp.output_text)

    cands = obj.get("candidates", [])
    if not isinstance(cands, list) or len(cands) != n:
        raise ValueError("후보 게임명 생성(JSON) 실패 또는 개수 불일치")

    cands = [str(x).strip() for x in cands if str(x).strip()]
    seen = set()
    uniq: List[str] = []
    for t in cands:
        key = t.lower()
        if key not in seen:
            uniq.append(t)
            seen.add(key)
    return uniq[:n]


def openai_select_from_facts(
    client: OpenAI,
    model: str,
    system_instructions: str,
    profile_text: str,
    factual_games: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    요구사항:
    - '맞는감정' 제거
    - '주의/메모' -> '요약/메모'로 변경 + 내용 더 추가(더 길고 구체적)
    - 추천 개수 고정 X: 정말 잘 맞는 것만
    """
    compact = []
    for g in factual_games:
        compact.append(
            {
                "id": g["id"],
                "name": g["name"],
                "released": g.get("released"),
                "genres": g.get("genres", []),
                "platforms": g.get("platforms", []),
                "metacritic": g.get("metacritic"),
                "rating": g.get("rating"),
            }
        )

    schema_hint = {
        "selected": [
            {
                "id": 123,
                "why_recommended": "string (2~3문장)",
                "time_fit": "string (플레이시간 적합 설명)",
                "summary_memo": "string (요약/메모: 더 길게. 난이도/분위기/플레이 루프/주의점/추천 상황 포함)",
            }
        ],
        "summary": "string",
        "price_disclaimer": "string",
    }

    prompt = f"""
너는 'Select Game'의 편집장(게임 잡지 스타일)이다.
아래 [사용자 선호 프로필]과 [게임 팩트 목록]을 보고, 정말 잘 맞는 게임만 selected에 담아라.

핵심 규칙:
- 추천 개수를 억지로 채우지 마라. 확신이 낮으면 제외한다. (보통 2~8개가 자연스러움)
- selected의 id는 반드시 팩트 목록에 존재해야 한다.
- 출력은 "유효한 JSON" 하나만 출력. (설명/마크다운/코드펜스 금지)
- JSON 키는 스키마 예시와 동일하게.
- summary_memo는 '요약/메모'로서 분량을 더 주고, 아래 요소를 가능하면 포함:
  1) 게임의 핵심 재미 루프(예: 전투-파밍-빌드 / 탐험-수집-제작 등)
  2) 분위기/톤(힐링/긴장/코지/하드코어 등)
  3) 플레이 팁 1개(초반 빌드/설정/추천 난이도 등)
  4) 주의점 1개(멀미/난이도/호불호 포인트/시간 빨림 등)
- why_recommended는 2~3문장으로 짧고 날카롭게.

[JSON 스키마 예시]
{json.dumps(schema_hint, ensure_ascii=False, indent=2)}

[사용자 선호 프로필]
{profile_text}

[게임 팩트 목록]
{json.dumps(compact, ensure_ascii=False)}
""".strip()

    resp = client.responses.create(model=model, instructions=system_instructions, input=prompt)
    text = (resp.output_text or "").strip()

    # 파싱 실패 시 1회 수정 요청
    try:
        obj = safe_json_loads(text)
    except Exception:
        fix_prompt = f"""
아래 출력은 JSON 파싱에 실패했거나 조건을 어겼다.
반드시 "유효한 JSON" 하나만 출력해서 수정해라. 다른 텍스트는 절대 출력하지 마라.
조건: selected의 id는 팩트 목록의 id만 사용.

[잘못된 출력]
{text}
""".strip()
        resp2 = client.responses.create(model=model, instructions=system_instructions, input=fix_prompt)
        obj = safe_json_loads(resp2.output_text)

    sel = obj.get("selected", [])
    if not isinstance(sel, list):
        raise ValueError("선정 결과 JSON 형식이 올바르지 않습니다.")
    return obj


def openai_chat(
    client: OpenAI,
    model: str,
    system_instructions: str,
    messages: List[Dict[str, str]],
) -> str:
    convo = []
    for m in messages[-20:]:
        convo.append(f"{m['role'].upper()}: {m['content']}")
    resp = client.responses.create(model=model, instructions=system_instructions, input="\n".join(convo))
    return (resp.output_text or "").strip()


# -----------------------------
# Sidebar (controls)
# -----------------------------
with st.sidebar:
    st.markdown("## 🎮 Select Game")
    st.caption("RAWG로 팩트를 확정하고, 편집장 스타일로 추천합니다.")
    st.markdown("---")

    st.markdown("### 🔑 Keys")
    openai_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    rawg_key = st.text_input("RAWG API Key", type="password", placeholder="RAWG 키")

    st.markdown("---")
    st.markdown("### 🧩 취향 입력")

    GENRES = ["액션 게임", "슈팅 게임", "어드벤쳐 게임", "전략 게임", "롤플레잉 게임", "퍼즐 게임", "음악게임"]
    EMOTIONS = ["힐링", "성장", "경쟁", "공포", "수집", "몰입 스토리"]
    PLATFORMS = ["PC", "PS", "Xbox", "Switch", "모바일"]

    preferred_genres = st.multiselect("선호 장르", GENRES, default=[])

    emotions = st.multiselect("원하는 감정(선지)", EMOTIONS, default=[])
    emotions_free = st.text_input(
        "원하는 감정(자유 입력)",
        placeholder="예: 잔잔한 코지, 미친 손맛, 스팀팩 같은 타격감, 여운 있는 스토리…",
    )

    played_games = st.text_area(
        "재미있게 플레이한 게임",
        placeholder="예: Hades, Zelda: BOTW, Slay the Spire …",
        height=90,
    )

    platforms = st.multiselect("플랫폼/기기", PLATFORMS, default=[])

    hours_per_day = st.number_input(
        "하루 예상 플레이시간(시간)",
        min_value=0.0,
        max_value=24.0,
        value=1.5,
        step=0.5,
    )

    st.markdown("---")
    model = st.selectbox(
        "모델",
        options=["gpt-4.1-mini", "gpt-4.1", "gpt-5", "gpt-5.2"],
        index=0,
    )

    get_recs = st.button("📰 오늘의 추천호 발행", use_container_width=True)


# -----------------------------
# Main (Magazine layout)
# -----------------------------
st.markdown(
    """
<div class="sg-hero">
  <h1>SELECT GAME</h1>
  <p>
    게임 잡지처럼, <b>팩트는 RAWG</b>로 확정하고 <b>추천은 편집장 톤</b>으로 정리합니다.
    억지 추천 없이 “확신 있는 게임만” 올려요.
  </p>
</div>
""",
    unsafe_allow_html=True,
)

profile_text = build_profile_text(
    preferred_genres=preferred_genres,
    emotions=emotions,
    emotions_free=emotions_free,
    played_games=played_games,
    platforms=platforms,
    hours_per_day=float(hours_per_day),
)

system_instructions = f"""
너는 'Select Game'이라는 게임 추천 챗봇이다.
- 한국어로 답한다.
- 사용자의 선호 장르, 원하는 감정(자유입력 포함), 플레이한 게임, 플랫폼, 하루 플레이시간을 최우선 반영한다.
- 게임 정보(출시일/플랫폼/장르/표지)는 RAWG 팩트를 우선한다.
- 추천 개수는 억지로 채우지 않는다. 확신이 낮으면 제외한다.
- 문체는 게임 잡지 편집장처럼: 짧고 임팩트 있게, 그러나 과장/허위는 금지.

{profile_text}
""".strip()

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "원하는 분위기/플랫폼/플레이 시간만 정확히 주면, 잡지 한 페이지처럼 추천해줄게.",
        }
    ]
if "recommendations" not in st.session_state:
    st.session_state.recommendations = None


# -----------------------------
# Recommendation Flow
# -----------------------------
if get_recs:
    if not openai_key:
        st.error("OpenAI API 키를 먼저 입력해줘.")
    elif not rawg_key:
        st.error("RAWG API 키도 입력해줘. (게임 정보 확정용)")
    else:
        try:
            client = build_openai_client(openai_key)

            with st.spinner("1) 후보 게임명 수집 중..."):
                candidates = openai_get_candidates(
                    client=client,
                    model=model,
                    system_instructions=system_instructions,
                    profile_text=profile_text,
                    n=CANDIDATE_COUNT,
                )

            with st.spinner("2) RAWG에서 팩트 확정 중..."):
                factual: List[Dict[str, Any]] = []
                seen_ids = set()

                for title in candidates:
                    top = rawg_search_top(rawg_key, title)
                    if not top or not top.get("id"):
                        continue

                    gid = int(top["id"])
                    if gid in seen_ids:
                        continue

                    detail = rawg_game_detail(rawg_key, gid)
                    plats = game_platforms(detail)

                    if not platform_filter_pass(platforms, plats):
                        continue

                    seen_ids.add(gid)
                    factual.append(
                        {
                            "id": gid,
                            "name": detail.get("name") or top.get("name") or title,
                            "released": detail.get("released"),
                            "genres": game_genres(detail),
                            "platforms": plats,
                            "metacritic": detail.get("metacritic"),
                            "rating": detail.get("rating"),
                            "background_image": detail.get("background_image"),
                            "stores": game_stores(detail),
                        }
                    )

                    if len(factual) >= RAWG_MATCH_LIMIT:
                        break

                if not factual:
                    raise ValueError(
                        "RAWG에서 매칭되는 게임을 찾지 못했습니다. 플랫폼 선택을 완화하거나, '재미있게 플레이한 게임'에 힌트를 더 넣어봐."
                    )

            with st.spinner("3) 확신 있는 게임만 선별/원고 작성 중..."):
                picked_obj = openai_select_from_facts(
                    client=client,
                    model=model,
                    system_instructions=system_instructions,
                    profile_text=profile_text,
                    factual_games=factual,
                )

            fact_map = {g["id"]: g for g in factual}
            selected_merged: List[Dict[str, Any]] = []

            for s in picked_obj.get("selected", []):
                try:
                    gid = int(s.get("id"))
                except Exception:
                    continue
                if gid in fact_map:
                    merged = {**fact_map[gid], **s}
                    selected_merged.append(merged)

            st.session_state.recommendations = {
                "selected": selected_merged,
                "summary": picked_obj.get("summary", ""),
                "price_disclaimer": picked_obj.get(
                    "price_disclaimer",
                    "가격은 지역/세일/에디션에 따라 달라집니다. 스토어 링크에서 최종 가격을 확인하세요.",
                ),
            }

        except Exception as e:
            st.session_state.recommendations = None
            st.error(f"추천 생성 실패: {e}")


# -----------------------------
# Render Magazine "Issue"
# -----------------------------
recs_obj = st.session_state.recommendations

st.markdown(
    """
<div class="sg-section">
  <span class="sg-pill">ISSUE</span>
  <h2>오늘의 추천 지면</h2>
</div>
<p class="sg-sub">추천은 확신 있는 게임만. 표지/장르/플랫폼/출시일은 RAWG 팩트를 사용합니다.</p>
""",
    unsafe_allow_html=True,
)

if recs_obj is not None:
    st.caption(recs_obj.get("price_disclaimer", ""))

    selected = recs_obj.get("selected", [])
    if not selected:
        st.warning("이번 조건에선 확신 있게 추천할 게임이 부족했어. 플랫폼을 넓히거나(예: PC 추가), 감정 자유입력을 더 구체적으로 써봐.")
    else:
        # 3열 카드 그리드(잡지 레이아웃 느낌)
        cols = st.columns(3, gap="large")
        for idx, g in enumerate(selected):
            col = cols[idx % 3]
            with col:
                cover = g.get("background_image")
                title = g.get("name", "")
                released = g.get("released") or "정보 없음"
                genres = ", ".join(g.get("genres", [])) or "정보 없음"
                plats = ", ".join(g.get("platforms", [])) or "정보 없음"

                meta_bits = []
                meta_bits.append(f"출시: {released}")
                if g.get("metacritic") is not None:
                    meta_bits.append(f"MC {g['metacritic']}")
                if g.get("rating") is not None:
                    meta_bits.append(f"RAWG {g['rating']}")
                meta_line = " · ".join(meta_bits)

                why = g.get("why_recommended", "").strip()
                time_fit = g.get("time_fit", "").strip()
                memo = g.get("summary_memo", "").strip()

                stores = g.get("stores", [])[:4]

                # Build HTML card
                card_html = f"""
<div class="sg-card">
  {f'<img class="sg-cover" src="{cover}" />' if cover else ''}
  <div class="sg-body">
    <h3 class="sg-title">{idx+1}. {title}</h3>
    <div class="sg-meta">
      <span class="sg-tag">{meta_line}</span>
      <span class="sg-tag">장르: {genres}</span>
      <span class="sg-tag">플랫폼: {plats}</span>
    </div>

    <div class="sg-divider"></div>

    <div class="sg-text"><b>한줄 추천</b><br><span class="sg-muted">{why if why else "—"}</span></div>
    <div class="sg-text"><b>플레이 타임 핏</b><br><span class="sg-muted">{time_fit if time_fit else "—"}</span></div>
    <div class="sg-text"><b>요약/메모</b><br><span class="sg-muted">{memo if memo else "—"}</span></div>

    <div class="sg-divider"></div>

    <div class="sg-text sg-links"><b>스토어</b><br>
      {"".join([f'- <a href="{s["url"]}" target="_blank">{s["name"]}</a><br>' for s in stores]) if stores else '<span class="sg-muted">스토어 링크 정보 없음(또는 RAWG 미제공)</span>'}
    </div>
  </div>
</div>
"""
                st.markdown(card_html, unsafe_allow_html=True)

        if recs_obj.get("summary"):
            st.markdown(
                f"""
<div class="sg-section">
  <span class="sg-pill">EDITOR'S NOTE</span>
  <h2>편집장 메모</h2>
</div>
""",
                unsafe_allow_html=True,
            )
            st.info(recs_obj["summary"])


# -----------------------------
# Chat (kept simple, magazine + Q&A corner vibe)
# -----------------------------
st.markdown(
    """
<div class="sg-section">
  <span class="sg-pill">Q&A</span>
  <h2>추가 요청</h2>
</div>
<p class="sg-sub">예: “추천 중에서 스위치로만 다시”, “난이도 낮은 쪽만”, “스토리 몰입 최우선”</p>
""",
    unsafe_allow_html=True,
)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

user_text = st.chat_input("질문/조건을 더 추가해줘 (예: ‘공포는 약하게’, ‘로그라이크는 제외’)")

if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    if not openai_key:
        assistant_text = "OpenAI API 키가 없어요. 사이드바에 입력해줘."
        st.session_state.messages.append({"role": "assistant", "content": assistant_text})
        with st.chat_message("assistant"):
            st.markdown(assistant_text)
    else:
        try:
            client = build_openai_client(openai_key)
            with st.spinner("답변 작성 중..."):
                assistant_text = openai_chat(
                    client=client,
                    model=model,
                    system_instructions=system_instructions,
                    messages=st.session_state.messages,
                )
            st.session_state.messages.append({"role": "assistant", "content": assistant_text})
            with st.chat_message("assistant"):
                st.markdown(assistant_text)
        except Exception as e:
            err = f"오류: {e}"
            st.session_state.messages.append({"role": "assistant", "content": err})
            with st.chat_message("assistant"):
                st.markdown(err)
