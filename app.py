# app.py
import json
import re
from typing import Any, Dict, List, Optional, Tuple

import requests
import streamlit as st
from openai import OpenAI


# -----------------------------
# Config
# -----------------------------
RAWG_BASE = "https://api.rawg.io/api"
TIMEOUT = 15


# -----------------------------
# Helpers (general)
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
        s = s.strip()
        s = re.sub(r"^```[a-zA-Z]*\n?", "", s)
        s = re.sub(r"```$", "", s).strip()

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


# -----------------------------
# RAWG API helpers
# -----------------------------
def rawg_get(
    rawg_key: str, endpoint: str, params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
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
    게임명 검색 -> 가장 그럴듯한 1개 결과 반환 (id 포함).
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
    # 보통 첫 결과가 가장 적합. 필요하면 여기서 scoring 개선 가능.
    return results[0]


@st.cache_data(show_spinner=False, ttl=60 * 60 * 24)
def rawg_game_detail(rawg_key: str, game_id: int) -> Dict[str, Any]:
    return rawg_get(rawg_key, f"/games/{game_id}")


def map_platform_choice_to_rawg(platform_choice: str) -> List[str]:
    """
    RAWG 플랫폼 이름과 대략 매칭.
    """
    mapping = {
        "PC": ["PC"],
        "PS": ["PlayStation"],
        "Xbox": ["Xbox"],
        "Switch": ["Nintendo Switch", "Nintendo"],
        "모바일": ["Android", "iOS"],
    }
    return mapping.get(platform_choice, [])


def game_platforms_from_detail(detail: Dict[str, Any]) -> List[str]:
    plats = []
    for p in detail.get("platforms") or []:
        plat = (p.get("platform") or {}).get("name")
        if plat:
            plats.append(plat)
    # 중복 제거(순서 유지)
    seen = set()
    out = []
    for x in plats:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


def game_genres_from_detail(detail: Dict[str, Any]) -> List[str]:
    genres = []
    for g in detail.get("genres") or []:
        name = g.get("name")
        if name:
            genres.append(name)
    return genres


def game_stores_from_detail(detail: Dict[str, Any]) -> List[Tuple[str, str]]:
    """
    (store_name, url) 목록.
    """
    stores = []
    for s in detail.get("stores") or []:
        store = (s.get("store") or {}).get("name")
        url = s.get("url")
        if store and url:
            stores.append((store, url))
    return stores


def platform_filter_pass(user_platforms: List[str], game_platforms: List[str]) -> bool:
    """
    사용자가 플랫폼을 선택했으면, 게임이 그 플랫폼 계열을 하나라도 포함해야 통과.
    선택 안 했으면 통과.
    """
    if not user_platforms:
        return True

    acceptable_tokens = []
    for up in user_platforms:
        acceptable_tokens.extend(map_platform_choice_to_rawg(up))

    gp = " | ".join(game_platforms).lower()
    for token in acceptable_tokens:
        if token.lower() in gp:
            return True
    return False


# -----------------------------
# OpenAI steps
# -----------------------------
def openai_get_candidates(
    client: OpenAI,
    model: str,
    system_instructions: str,
    profile_text: str,
) -> List[str]:
    """
    1) 모델에게 '후보 게임명만' 12개 뽑게 함 (정보는 RAWG로 확정할 거라서 이름만 받음)
    """
    prompt = f"""
너는 게임 추천 전문가다.
아래 프로필을 보고 사용자가 좋아할 가능성이 높은 "게임 후보 제목" 12개를 뽑아라.

규칙:
- 출력은 "유효한 JSON" 하나만 출력. (설명/마크다운/코드펜스 금지)
- 키는 candidates 하나만 사용: {{ "candidates": ["title1", ...] }}
- candidates는 정확히 12개.
- 비선호 장르는 최대한 피하고, 선호 플랫폼을 우선 고려.
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
    if not isinstance(cands, list) or len(cands) != 12:
        raise ValueError("후보 게임명 생성(JSON) 실패 또는 개수 불일치")
    # 문자열만
    cands = [str(x).strip() for x in cands if str(x).strip()]
    return cands[:12]


def openai_pick_top5_from_facts(
    client: OpenAI,
    model: str,
    system_instructions: str,
    profile_text: str,
    factual_games: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    2) RAWG에서 가져온 '팩트' 목록을 모델에게 주고,
       그 중 5개를 고르고 왜 추천인지 설명만 생성.
       (게임 정보는 fact 그대로 표시)
    """
    # 모델이 보기 좋게 요약 팩트만 전달
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
                "stores": g.get("stores", [])[:5],
            }
        )

    schema_hint = {
        "selected": [
            {
                "id": 123,
                "why_recommend_
