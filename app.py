# app.py
import json
from typing import Any, Dict, List

import streamlit as st
from openai import OpenAI


# -----------------------------
# Helpers
# -----------------------------
def build_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


def safe_json_loads(s: str) -> Dict[str, Any]:
    """
    모델 출력이 JSON이어야 하지만, 혹시 코드펜스/여분 텍스트가 섞이면 최대한 방어적으로 제거.
    """
    s = s.strip()

    # 코드펜스 방어
    if s.startswith("```"):
        # ```json\n{...}\n``` 같은 형태
        s = s.strip("`").strip()
        if "\n" in s:
            s = s.split("\n", 1)[1].strip()
        # 끝의 ``` 제거될 수도 있으니 한 번 더
        if s.endswith("```"):
            s = s[:-3].strip()

    # 앞뒤 잡텍스트가 섞인 경우를 대비해 첫 '{' ~ 마지막 '}'만 잘라보기(최후의 방어)
    if "{" in s and "}" in s:
        s2 = s[s.find("{") : s.rfind("}") + 1].strip()
        # 너무 공격적으로 자르면 깨질 수 있어서, 그래도 json 파싱 시도
        try:
            return json.loads(s2)
        except Exception:
            pass

    return json.loads(s)


def join_nonempty(items: List[str]) -> str:
    items = [x.strip() for x in items if x and x.strip()]
    return ", ".join(items)


def build_profile_text(
    preferred_genres: List[str],
    disliked_genres: List[str],
    emotions: List[str],
    played_games: str,
    platforms: List[str],
    hours_per_day: float,
) -> str:
    return f"""
[사용자 선호 프로필]
- 선호 장르: {join_nonempty(preferred_genres) if preferred_genres else "없음/미선택"}
- 비선호 장르: {join_nonempty(disliked_genres) if disliked_genres else "없음/미선택"}
- 원하는 감정(플레이 경험): {join_nonempty(emotions) if emotions else "없음/미선택"}
- 재미있게 플레이한 게임(참고): {played_games.strip() if played_games.strip() else "미입력"}
- 선호 플랫폼/기기: {join_nonempty(platforms) if platforms else "없음/미선택"}
- 하루 예상 플레이시간: {hours_per_day}시간
""".strip()


def call_openai_chat(
    client: OpenAI,
    model: str,
    system_instructions: str,
    messages: List[Dict[str, str]],
) -> str:
    """
    일반 채팅(자연어 응답). Responses API 사용.
    """
    convo = []
    for m in messages[-20:]:
        role = m.get("role", "user")
        content = m.get("content", "")
        convo.append(f"{role.upper()}: {content}")
    input_text = "\n".join(convo)

    resp = client.responses.create(
        model=model,
        instructions=system_instructions,
        input=input_text,
    )
    return (resp.output_text or "").strip()


def call_openai_recommendations(
    client: OpenAI,
    model: str,
    system_instructions: str,
    profile_text: str,
) -> Dict[str, Any]:
    """
    response_format을 쓰지 않고,
    프롬프트로 '유효 JSON만 출력'을 강제 + 파싱 실패 시 1회 수정 요청.
    """
    schema_hint = {
        "recommendations": [
            {
                "title": "string",
                "genre": "string",
                "platforms": ["string"],
                "price_range_krw": "string",
                "store_hint": "string",
                "why_recommended": "string",
                "fit_emotions": ["string"],
                "time_fit": "string",
                "caution_or_note": "string",
            }
        ],
        "summary": "string",
        "price_disclaimer": "string",
    }

    prompt = f"""
너는 게임 추천 전문가다.
아래 [사용자 선호 프로필]을 기반으로 게임 5개를 추천하라.

중요(반드시 준수):
- 출력은 "유효한 JSON" 하나만 출력한다. (설명/코드펜스/여분 텍스트/마크다운 금지)
- recommendations는 정확히 5개 항목만 포함한다.
- 비선호 장르는 최대한 피한다.
- 사용자의 플랫폼에서 플레이 가능한 타이틀을 우선한다.
- 가격은 실시간 조회가 아니라 "대략적인 가격대(원)"로 제시한다.
- 어떤 스토어에서 확인하면 되는지도 store_hint에 적는다. (예: Steam/PS Store/eShop/Google Play 등)
- 아래 JSON 키 이름을 정확히 그대로 사용한다.

[JSON 스키마 예시]
{json.dumps(schema_hint, ensure_ascii=False, indent=2)}

[사용자 선호 프로필]
{profile_text}
""".strip()

    # 1차 생성
    resp = client.responses.create(
        model=model,
        instructions=system_instructions,
        input=prompt,
    )
    text = (resp.output_text or "").strip()

    # 1차 파싱
    try:
        obj = safe_json_loads(text)
        if (
            isinstance(obj, dict)
            and "recommendations" in obj
            and isinstance(obj["recommendations"], list)
            and len(obj["recommendations"]) == 5
        ):
            return obj
        raise ValueError("JSON parsed but recommendations length != 5 or schema mismatch")
    except Exception:
        # 2차: JSON만 다시 내놓게 수정 요청
        fix_prompt = f"""
아래 출력은 JSON 파싱에 실패했거나 조건을 어겼다.
반드시 "유효한 JSON" 하나만 출력해서 수정해라. 다른 텍스트는 절대 출력하지 마라.
조건: recommendations는 정확히 5개.

[잘못된 출력]
{text}
""".strip()

        resp2 = client.responses.create(
            model=model,
            instructions=system_instructions,
            input=fix_prompt,
        )
        text2 = (resp2.output_text or "").strip()
        obj2 = safe_json_loads(text2)

        # 마지막 안전장치
        if (
            not isinstance(obj2, dict)
            or "recommendations" not in obj2
            or not isinstance(obj2["recommendations"], list)
            or len(obj2["recommendations"]) != 5
        ):
            raise ValueError("모델이 올바른 JSON(추천 5개)을 반환하지 못했습니다.")
        return obj2


# -----------------------------
# Streamlit App
# -----------------------------
st.set_page_config(page_title="플레이메이트", layout="wide")

# Sidebar - API key must be top-left => first element in sidebar
with st.sidebar:
    st.markdown("### 🔑 API 키 (왼쪽 위)")
    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="sk-... 또는 프로젝트 키",
        help="배포 시에는 st.secrets 사용을 권장.",
    )
    st.divider()

    st.markdown("### 🎮 취향 설정")

    GENRES = ["액션 게임", "슈팅 게임", "어드벤쳐 게임", "전략 게임", "롤플레잉 게임", "퍼즐 게임", "음악게임"]
    EMOTIONS = ["힐링", "성장", "경쟁", "공포", "수집", "몰입 스토리"]
    PLATFORMS = ["PC", "PS", "Xbox", "Switch", "모바일"]

    preferred_genres = st.multiselect("선호 장르", GENRES, default=[])
    disliked_genres = st.multiselect("비선호 장르", GENRES, default=[])
    emotions = st.multiselect("게임에서 원하는 감정", EMOTIONS, default=[])

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
        help="계정/프로젝트 설정에 따라 사용 가능 모델이 다를 수 있음.",
    )

    get_recs = st.button("✨ 추천 받기", use_container_width=True)

# Main title
st.title("플레이메이트")

# Session state init
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "안녕하세요! 저는 플레이메이트 🎮\n사이드바에서 취향을 고르고, 채팅으로 원하는 느낌을 말해줘요. (예: '스위치로 30~60분씩 협동 가능한 게임')",
        }
    ]
if "recommendations" not in st.session_state:
    st.session_state.recommendations = None

profile_text = build_profile_text(
    preferred_genres=preferred_genres,
    disliked_genres=disliked_genres,
    emotions=emotions,
    played_games=played_games,
    platforms=platforms,
    hours_per_day=float(hours_per_day),
)

system_instructions = f"""
너는 '플레이메이트'라는 게임 추천 챗봇이다.
- 한국어로 답한다.
- 사용자의 선호/비선호 장르, 원하는 감정, 재미있게 했던 게임, 플랫폼, 하루 플레이시간을 최우선 반영한다.
- 가격/플랫폼은 지역/세일/스토어에 따라 달라질 수 있으므로 "대략"으로만 말하고, 단정하지 않는다.
- 기본 답변은 짧고 명확하게. 사용자가 원하면 자세히 확장한다.

{profile_text}
""".strip()

# Render chat history
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Handle "추천 받기"
if get_recs:
    if not api_key:
        st.error("사이드바 왼쪽 위에 OpenAI API 키를 먼저 입력해줘.")
    else:
        try:
            client = build_client(api_key)
            with st.spinner("취향 분석 및 추천 생성 중..."):
                recs_obj = call_openai_recommendations(
                    client=client,
                    model=model,
                    system_instructions=system_instructions,
                    profile_text=profile_text,
                )
            st.session_state.recommendations = recs_obj
        except Exception as e:
            st.session_state.recommendations = None
            st.error(f"추천 생성 실패: {e}")

# Show recommendations (if any)
recs_obj = st.session_state.recommendations
if recs_obj:
    st.subheader("추천 게임 5선")
    st.caption(recs_obj.get("price_disclaimer", "가격은 스토어/지역/세일에 따라 달라질 수 있어요. 구매 전 스토어에서 확인하세요."))

    cols = st.columns(2)
    recs = recs_obj.get("recommendations", [])[:5]
    for i, r in enumerate(recs):
        col = cols[i % 2]
        with col:
            st.markdown(f"### {i+1}. {r.get('title','')}")
            st.markdown(f"- **장르:** {r.get('genre','')}")
            st.markdown(f"- **플랫폼:** {', '.join(r.get('platforms', []))}")
            st.markdown(f"- **가격대(원):** {r.get('price_range_krw','')}")
            st.markdown(f"- **가격/구매 확인:** {r.get('store_hint','')}")
            st.markdown(f"- **추천 이유:** {r.get('why_recommended','')}")
            st.markdown(f"- **맞는 감정:** {', '.join(r.get('fit_emotions', []))}")
            st.markdown(f"- **시간 적합:** {r.get('time_fit','')}")
            st.markdown(f"- **주의/메모:** {r.get('caution_or_note','')}")
            st.divider()

    st.info(recs_obj.get("summary", ""))

    st.markdown("원하면 채팅에 이렇게 물어봐도 돼요: `2번이랑 비슷한 게임 더`, `공포 강도 얼마나 세?`, `모바일로만 다시 추천해줘`")

# Chat input
user_text = st.chat_input("원하는 게임 느낌을 말해줘 (예: '힐링+수집, 스위치로 하루 1시간')")

if user_text:
    st.session_state.messages.append({"role": "user", "content": user_text})
    with st.chat_message("user"):
        st.markdown(user_text)

    if not api_key:
        assistant_text = "API 키가 아직 없어요. 사이드바 왼쪽 위에 OpenAI API 키를 먼저 입력해줘."
        st.session_state.messages.append({"role": "assistant", "content": assistant_text})
        with st.chat_message("assistant"):
            st.markdown(assistant_text)
    else:
        try:
            client = build_client(api_key)
            with st.spinner("답변 생성 중..."):
                assistant_text = call_openai_chat(
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
