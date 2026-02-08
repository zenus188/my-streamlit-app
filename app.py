# app.py
import json
import re
from typing import Any, Dict, List, Optional

import requests
import streamlit as st
from openai import OpenAI


# -----------------------------
# Config
# -----------------------------
RAWG_BASE = "https://api.rawg.io/api"
TIMEOUT = 15

# 추천 후보를 얼마나 넓게 뽑을지 (너무 낮으면 적게 나오고, 너무 높으면 RAWG 호출이 많아짐)
CANDIDATE_COUNT = 18  # OpenAI가 뽑는 "게임 제목 후보" 개수
RAWG_MATCH_LIMIT = 16  # RAWG로 팩트 확정 후 남길 최대 후보 수(너무 많으면 모델에게 부담)


# -----------------------------
# Utilities
# -----------------------------
def build_openai_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


def safe_json_loads(s: str) -> Dict[str, Any]:
    """
    모델 출력이 JSON이어야 하지만, 혹시 코드펜스/여분 텍스트가 섞이면 최대한 방어적으로 제거.
    """
    s = (s or "").strip()

    # code fence 방어
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s).strip()
        s = re.sub(r"\n?```$", "", s).strip()

    # 최후의 방어: 첫 '{'~마지막 '}'만 잘라 시도
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
    """
    게임명 검색 -> 상위 결과 1개 반환 (id 포함)
    """
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
    if not results:
        return None
    return results[0]


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def rawg_game_detail(rawg_key: str, game_id: int) -> Dict[str, Any]:
    return rawg_get(rawg_key, f"/games/{game_id}")


def map_platform_choice_to_rawg_tokens(platform_choice: str) -> List[str]:
    """
    RAWG 플랫폼 이름에 대한 느슨한 토큰 매칭(부정확하지만 실용적).
    """
    mapping = {
        "PC": ["PC"],
        "PS": ["PlayStation"],
        "Xbox": ["Xbox"],
        "Switch": ["Nintendo Switch", "Nintendo"],
        "모바일": ["Android", "iOS"],
    }
    return mapping.get(platform_choice, [])


def game_platforms(detail: Dict[str, Any]) -> List[str]:
    out = []
    for p in detail.get("platforms") or []:
        name = (p.get("platform") or {}).get("name")
        if name:
            out.append(name)
    # dedupe keep order
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
    """
    사용자가 플랫폼을 골랐으면 그 계열과 하나라도 맞아야 통과.
    아무것도 안 고르면 통과.
    """
    if not user_platforms:
        return True

    tokens = []
    for up in user_platforms:
        tokens.extend(map_platform_choice_to_rawg_tokens(up))

    gp = " | ".join(game_plats).lower()
    return any(t.lower() in gp for t in tokens)


# -----------------------------
# Profile text
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
    """
    모델에게 '후보 게임명'만 n개 뽑게 함.
    (팩트는 RAWG로 확정하므로 이름만 받는다)
    """
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

    resp = client.responses.create(
        model=model,
        instructions=system_instructions,
        input=prompt,
    )
    obj = safe_json_loads(resp.output_text)
    cands = obj.get("candidates", [])
    if not isinstance(cands, list) or len(cands) != n:
        raise ValueError("후보 게임명 생성(JSON) 실패 또는 개수 불일치")
    cands = [str(x).strip() for x in cands if str(x).strip()]
    # 중복 제거(순서 유지)
    seen = set()
    uniq = []
    for t in cands:
        low = t.lower()
        if low not in seen:
            uniq.append(t)
            seen.add(low)
    return uniq[:n]


def openai_rank_and_select(
    client: OpenAI,
    model: str,
    system_instructions: str,
    profile_text: str,
    factual_games: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    RAWG 팩트 목록을 주고, 그 중 "진짜로 잘 맞는 것만" 선택하도록 함.
    - 개수 고정 X (0~10개 사이 권장)
    - id는 반드시 팩트 목록에 존재해야 함
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
                "why_recommended": "string",
                "fit_emotions": ["힐링"],
                "time_fit": "string",
                "caution_or_note": "string",
            }
        ],
        "summary": "string",
        "price_disclaimer": "string",
    }

    prompt = f"""
너는 '플레이메이트' 추천 엔진이다.
아래 [사용자 선호 프로필]과 [게임 팩트 목록]을 보고, 정말 잘 맞는 것만 selected에 담아라.

중요:
- 추천 개수를 억지로 채우지 마라. (0개도 가능하지만, 보통은 3~8개 정도가 자연스럽다)
- 확신이 낮거나 애매하면 제외한다.
- selected의 각 항목 id는 반드시 팩트 목록에 존재해야 한다.
- 출력은 "유효한 JSON" 하나만 출력. (설명/마크다운/코드펜스 금지)
- JSON 키는 아래 스키마 예시와 동일하게.
- why_recommended는 짧고 명확하게(2~3문장).

[JSON 스키마 예시]
{json.dumps(schema_hint, ensure_ascii=False, indent=2)}

[사용자 선호 프로필]
{profile_text}

[게임 팩트 목록]
{json.dumps(compact, ensure_ascii=False)}
""".strip()

    resp = client.responses.create(
        model=model,
        instructions=system_instructions,
        input=prompt,
    )

    text = (resp.output_text or "").strip()
    try:
        obj = safe_json_loads(text)
    except Exception:
        fix_prompt = f"""
아래 출력은 JSON 파싱에 실패했거나 조건을 어겼다.
반드시 "유효한 JSON" 하나만 출력해서 수정해라. 다른 텍스트는 절대 출력하지 마라.
조건: id는 팩트 목록의 id만 사용.

[잘못된 출력]
{text}
""".strip()
        resp2 = client.responses.create(
            model=model,
            instructions=system_instructions,
            input=fix_prompt,
        )
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
    resp = client.responses.create(
        model=model,
        instructions=system_instructions,
        input="\n".join(convo),
    )
    return (resp.output_text or "").strip()


# -----------------------------
# Streamlit UI
# -----------------------------
st.set_page_config(page_title="플레이메이트", layout="wide")

with st.sidebar:
    st.markdown("### 🔑 API 키 (왼쪽 위)")
    openai_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    rawg_key = st.text_input("RAWG API Key", type="password", placeholder="RAWG 키")
    st.divider()

    st.markdown("### 🎮 취향 설정")

    GENRES = ["액션 게임", "슈팅 게임", "어드벤쳐 게임", "전략 게임", "롤플레잉 게임", "퍼즐 게임", "음악게임"]
    EMOTIONS = ["힐링", "성장", "경쟁", "공포", "수집", "몰입 스토리"]

    PLATFORMS = ["PC", "PS", "Xbox", "Switch", "모바일"]

    preferred_genres = st.multiselect("선호 장르", GENRES, default=[])

    # (요구사항 2) 비선호 장르 제거 ✅

    # (요구사항 3) 감정: 선지 + 자유입력 ✅
    emotions = st.multiselect("게임에서 원하는 감정", EMOTIONS, default=[])
    emotions_free = st.text_input(
        "원하는 감정(자유 입력, 선택사항)",
        placeholder="예: 잔잔한 우울, 광기, 뇌빼고 파밍, 따뜻한 여운...",
    )

    played_games = st.text_area(
        "재미있게 플레이한 게임 (자유 입력)",
        placeholder="예: 젤다 야숨, 엘든 링, 하데스 ...",
        height=90,
    )

    platforms = st.multiselect("플랫폼/기기", PLATFORMS, default=[])

    hours_per_day = st.number_input(
        "하루 예상 플레이시간 (시간)",
        min_value=0.0,
        max_value=24.0,
        value=1.5,
        step=0.5,
    )

    st.divider()

    model = st.selectbox(
        "모델",
        options=["gpt-4.1-mini", "gpt-4.1", "gpt-5", "gpt-5.2"],
        index=0,
        help="사용 가능 모델은 계정/프로젝트 설정에 따라 달라질 수 있음.",
    )

    get_recs = st.button("✨ 추천 받기", use_container_width=True)

st.title("플레이메이트")

# session state
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "안녕하세요! 플레이메이트 🎮\n추천은 RAWG로 게임 정보를 확정해서(표지/플랫폼/장르/출시일) 정확도를 높여요.",
        }
    ]
if "recommendations" not in st.session_state:
    st.session_state.recommendations = None

profile_text = build_profile_text(
    preferred_genres=preferred_genres,
    emotions=emotions,
    emotions_free=emotions_free,
    played_games=played_games,
    platforms=platforms,
    hours_per_day=float(hours_per_day),
)

system_instructions = f"""
너는 '플레이메이트'라는 게임 추천 챗봇이다.
- 한국어로 답한다.
- 사용자의 선호 장르, 원하는 감정(자유입력 포함), 플레이한 게임, 플랫폼, 하루 플레이시간을 최우선 반영한다.
- 게임 정보(출시일/플랫폼/장르/표지)는 "외부 DB(=RAWG) 팩트"를 우선한다.
- 추천 개수는 억지로 채우지 않는다. 확신이 낮으면 제외한다.
- 기본 답변은 짧고 명확하게.

{profile_text}
""".strip()

# render chat
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Recommendation flow
if get_recs:
    if not openai_key:
        st.error("OpenAI API 키를 먼저 입력해줘.")
    elif not rawg_key:
        st.error("RAWG API 키도 입력해줘. (정확한 게임 정보 확정용)")
    else:
        try:
            client = build_openai_client(openai_key)

            with st.spinner("1) 후보 게임명 생성 중..."):
                candidates = openai_get_candidates(
                    client=client,
                    model=model,
                    system_instructions=system_instructions,
                    profile_text=profile_text,
                    n=CANDIDATE_COUNT,
                )

            with st.spinner("2) RAWG에서 게임 정보 확정 중..."):
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

                if len(factual) == 0:
                    raise ValueError(
                        "RAWG에서 매칭되는 게임을 찾지 못했습니다. 플랫폼 선택을 완화하거나, '재미있게 플레이한 게임'에 힌트를 더 넣어보세요."
                    )

            with st.spinner("3) 확정된 팩트 중 '진짜로 잘 맞는 것만' 선별 중..."):
                picked_obj = openai_rank_and_select(
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

            # 개수 강제 X
            st.session_state.recommendations = {
                "selected": selected_merged,
                "summary": picked_obj.get("summary", ""),
                "price_disclaimer": picked_obj.get(
                    "price_disclaimer",
                    "가격은 지역/세일/에디션에 따라 달라집니다. 아래 스토어 링크에서 최종 가격을 확인하세요.",
                ),
            }

        except Exception as e:
            st.session_state.recommendations = None
            st.error(f"추천 생성 실패: {e}")

# Show recommendations
recs_obj = st.session_state.recommendations
if recs_obj is not None:
    selected = recs_obj.get("selected", [])

    st.subheader("추천 게임 (RAWG 팩트 기반)")
    st.caption(recs_obj.get("price_disclaimer", ""))

    if not selected:
        st.warning("이번 조건에선 확신 있게 추천할 게임을 충분히 찾지 못했어. 플랫폼 선택을 늘리거나, 원하는 감정을 더 구체적으로 써봐.")
    else:
        cols = st.columns(2)
        for i, g in enumerate(selected):
            col = cols[i % 2]
            with col:
                st.markdown(f"### {i+1}. {g.get('name','')}")
                # (요구사항 4) 표지 이미지 ✅ (RAWG background_image)
                cover = g.get("background_image")
                if cover:
                    st.image(cover, use_container_width=True)

                released = g.get("released") or "정보 없음"
                genres = ", ".join(g.get("genres", [])) or "정보 없음"
                plats = ", ".join(g.get("platforms", [])) or "정보 없음"

                st.markdown(f"- **출시일:** {released}")
                st.markdown(f"- **장르(팩트):** {genres}")
                st.markdown(f"- **플랫폼(팩트):** {plats}")

                if g.get("metacritic") is not None:
                    st.markdown(f"- **Metacritic:** {g['metacritic']}")
                if g.get("rating") is not None:
                    st.markdown(f"- **RAWG Rating:** {g['rating']}")

                st.markdown(f"- **추천 이유:** {g.get('why_recommended','')}")
                st.markdown(f"- **맞는 감정:** {', '.join(g.get('fit_emotions', []))}")
                st.markdown(f"- **시간 적합:** {g.get('time_fit','')}")
                st.markdown(f"- **주의/메모:** {g.get('caution_or_note','')}")

                stores = g.get("stores", [])
                if stores:
                    st.markdown("**스토어 링크(팩트):**")
                    for s in stores[:5]:
                        st.markdown(f"- [{s['name']}]({s['url']})")
                else:
                    st.markdown("- **스토어 링크:** 정보 없음(또는 RAWG 미제공)")

                st.divider()

        if recs_obj.get("summary"):
            st.info(recs_obj["summary"])

# Chat
user_text = st.chat_input("원하는 게임 느낌을 말해줘 (예: '힐링+수집, 스위치로 1시간')")

if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    if not openai_key:
        assistant_text = "OpenAI API 키가 없어요. 사이드바 왼쪽 위에 먼저 입력해줘."
        st.session_state.messages.append({"role": "assistant", "content": assistant_text})
        with st.chat_message("assistant"):
            st.markdown(assistant_text)
    else:
        try:
            client = build_openai_client(openai_key)
            with st.spinner("답변 생성 중..."):
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
