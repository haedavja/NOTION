"""
사이드바 네비게이션 시스템
기능 그룹화 및 즐겨찾기 지원
"""

import streamlit as st
from dataclasses import dataclass
from typing import Dict, List, Callable, Optional
from enum import Enum


class MenuCategory(Enum):
    """메뉴 카테고리"""
    HOME = "home"
    MARKET = "market"
    STOCK = "stock"
    PORTFOLIO = "portfolio"
    TOOLS = "tools"
    AI = "ai"
    SETTINGS = "settings"


@dataclass
class MenuItem:
    """메뉴 아이템"""
    id: str
    name: str
    icon: str
    category: MenuCategory
    description: str = ""
    available: bool = True


# 메뉴 구조 정의
MENU_STRUCTURE: Dict[MenuCategory, Dict] = {
    MenuCategory.HOME: {
        "name": "홈",
        "icon": "🏠",
        "items": [
            MenuItem("dashboard", "대시보드", "📊", MenuCategory.HOME, "핵심 지표 요약"),
            MenuItem("prediction", "종합 예측", "🎯", MenuCategory.HOME, "시장 방향 예측"),
        ]
    },
    MenuCategory.MARKET: {
        "name": "시장 분석",
        "icon": "📈",
        "items": [
            MenuItem("macro", "거시경제", "🌐", MenuCategory.MARKET, "금리, 인플레이션, GDP"),
            MenuItem("fund_flow", "자금흐름", "💹", MenuCategory.MARKET, "섹터별 자금 이동"),
            MenuItem("sentiment", "센티먼트", "📰", MenuCategory.MARKET, "뉴스 및 심리 분석"),
            MenuItem("technical", "기술적 분석", "📊", MenuCategory.MARKET, "차트 패턴, 지표"),
            MenuItem("sector_rotation", "섹터 회전", "🔄", MenuCategory.MARKET, "섹터별 순환 분석"),
        ]
    },
    MenuCategory.STOCK: {
        "name": "종목 분석",
        "icon": "🔍",
        "items": [
            MenuItem("korea", "한국 주식", "🇰🇷", MenuCategory.STOCK, "KRX 종목 검색/분석"),
            MenuItem("snowflake", "Snowflake 분석", "❄️", MenuCategory.STOCK, "5축 레이더 차트 분석"),
            MenuItem("scorecard", "종합 스코어카드", "📋", MenuCategory.STOCK, "통합 투자 평가"),
            MenuItem("rally", "급등/급락 분석", "🔥", MenuCategory.STOCK, "상승/하락 논리 분석"),
            MenuItem("potential", "잠재 요인", "🎯", MenuCategory.STOCK, "잠재적 급등락 요인"),
        ]
    },
    MenuCategory.PORTFOLIO: {
        "name": "포트폴리오",
        "icon": "💼",
        "items": [
            MenuItem("portfolio", "포트폴리오 분석", "💼", MenuCategory.PORTFOLIO, "보유 종목 분석"),
            MenuItem("backtest", "백테스트", "📈", MenuCategory.PORTFOLIO, "전략 검증"),
            MenuItem("benchmark", "벤치마크 비교", "📊", MenuCategory.PORTFOLIO, "지수 대비 성과"),
            MenuItem("correlation", "상관관계 분석", "🔗", MenuCategory.PORTFOLIO, "종목간 상관관계"),
        ]
    },
    MenuCategory.TOOLS: {
        "name": "도구",
        "icon": "🛠️",
        "items": [
            MenuItem("tools", "투자 도구", "🛠️", MenuCategory.TOOLS, "계산기, 스크리너"),
            MenuItem("calendar", "캘린더/워치", "📅", MenuCategory.TOOLS, "경제 일정, 워치리스트"),
            MenuItem("advanced", "고급 기능", "🔧", MenuCategory.TOOLS, "고급 설정"),
            MenuItem("advanced_analysis", "고급 분석", "🔬", MenuCategory.TOOLS, "심층 분석 도구"),
        ]
    },
    MenuCategory.AI: {
        "name": "AI",
        "icon": "🤖",
        "items": [
            MenuItem("ai_analysis", "AI 분석", "🤖", MenuCategory.AI, "AI 기반 시장 분석"),
            MenuItem("ai_chat", "AI 어시스턴트", "🧠", MenuCategory.AI, "대화형 AI"),
        ]
    },
    MenuCategory.SETTINGS: {
        "name": "설정",
        "icon": "⚙️",
        "items": [
            MenuItem("notifications", "알림", "🔔", MenuCategory.SETTINGS, "알림 설정/내역"),
        ]
    },
}


def init_navigation_state():
    """네비게이션 상태 초기화"""
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'dashboard'
    if 'favorites' not in st.session_state:
        st.session_state.favorites = ['dashboard', 'prediction', 'korea']
    if 'show_onboarding' not in st.session_state:
        st.session_state.show_onboarding = True
    if 'sidebar_expanded' not in st.session_state:
        st.session_state.sidebar_expanded = {}


def toggle_favorite(item_id: str):
    """즐겨찾기 토글"""
    # session_state 리스트 직접 수정 대신 복사본 사용
    if not isinstance(st.session_state.favorites, list):
        st.session_state.favorites = []

    favorites = st.session_state.favorites.copy()
    if item_id in favorites:
        favorites.remove(item_id)
    else:
        favorites.append(item_id)
    st.session_state.favorites = favorites


def get_menu_item(item_id: str) -> Optional[MenuItem]:
    """메뉴 아이템 조회"""
    for category_data in MENU_STRUCTURE.values():
        for item in category_data["items"]:
            if item.id == item_id:
                return item
    return None


def render_sidebar(availability: Dict[str, bool] = None):
    """사이드바 렌더링"""
    if availability is None:
        availability = {}

    with st.sidebar:
        # 로고/타이틀
        st.markdown("""
        <div style='text-align: center; padding: 1rem 0;'>
            <h2 style='margin: 0;'>📊 NOTION</h2>
            <p style='margin: 0; font-size: 0.8rem; color: gray;'>시장 예측 시스템</p>
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # 즐겨찾기 섹션
        if st.session_state.favorites:
            with st.expander("⭐ 즐겨찾기", expanded=True):
                for fav_id in st.session_state.favorites:
                    item = get_menu_item(fav_id)
                    if item:
                        is_available = availability.get(item.id, item.available)
                        if is_available:
                            col1, col2 = st.columns([5, 1])
                            with col1:
                                if st.button(
                                    f"{item.icon} {item.name}",
                                    key=f"fav_{item.id}",
                                    use_container_width=True,
                                    type="primary" if st.session_state.current_page == item.id else "secondary"
                                ):
                                    st.session_state.current_page = item.id
                                    st.rerun()
                            with col2:
                                if st.button("★", key=f"unfav_{item.id}", help="즐겨찾기 해제"):
                                    toggle_favorite(item.id)
                                    st.rerun()

            st.divider()

        # 메뉴 카테고리별 렌더링
        for category, category_data in MENU_STRUCTURE.items():
            category_key = f"expand_{category.value}"

            # 카테고리 헤더
            is_expanded = st.session_state.sidebar_expanded.get(category_key, False)

            col1, col2 = st.columns([5, 1])
            with col1:
                if st.button(
                    f"{category_data['icon']} **{category_data['name']}**",
                    key=f"cat_{category.value}",
                    use_container_width=True
                ):
                    st.session_state.sidebar_expanded[category_key] = not is_expanded
                    st.rerun()
            with col2:
                st.markdown("▼" if is_expanded else "▶", unsafe_allow_html=True)

            # 하위 메뉴
            if is_expanded:
                for item in category_data["items"]:
                    is_available = availability.get(item.id, item.available)
                    is_current = st.session_state.current_page == item.id
                    is_favorite = item.id in st.session_state.favorites

                    if is_available:
                        col1, col2 = st.columns([5, 1])
                        with col1:
                            btn_label = f"  {item.icon} {item.name}"
                            if st.button(
                                btn_label,
                                key=f"menu_{item.id}",
                                use_container_width=True,
                                type="primary" if is_current else "secondary"
                            ):
                                st.session_state.current_page = item.id
                                st.rerun()
                        with col2:
                            star = "★" if is_favorite else "☆"
                            if st.button(star, key=f"star_{item.id}", help="즐겨찾기"):
                                toggle_favorite(item.id)
                                st.rerun()
                    else:
                        st.markdown(
                            f"<span style='color: gray; padding-left: 1rem;'>"
                            f"  {item.icon} {item.name} (비활성)</span>",
                            unsafe_allow_html=True
                        )

        # 하단 정보
        st.divider()
        st.markdown("""
        <div style='font-size: 0.7rem; color: gray; text-align: center;'>
            <p>v2.0 | 사이드바 네비게이션</p>
            <p>? 도움말 | ⚙️ 설정</p>
        </div>
        """, unsafe_allow_html=True)


def render_onboarding():
    """첫 사용자 온보딩 가이드"""
    if not st.session_state.show_onboarding:
        return

    with st.container():
        st.markdown("""
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 2rem; border-radius: 15px; color: white; margin-bottom: 2rem;'>
            <h2>👋 NOTION 시장 예측 시스템에 오신 것을 환영합니다!</h2>
            <p>이 시스템은 거시경제 데이터와 AI를 활용하여 시장을 분석합니다.</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("""
            ### 🚀 시작하기
            1. **대시보드**에서 핵심 지표 확인
            2. **시장 분석**에서 심층 분석
            3. **종목 분석**에서 개별 종목 탐색
            """)

        with col2:
            st.markdown("""
            ### ⭐ 즐겨찾기
            - 자주 쓰는 메뉴는 ☆를 클릭
            - 즐겨찾기 섹션에서 빠른 접근
            - 개인화된 워크플로우 구성
            """)

        with col3:
            st.markdown("""
            ### 💡 팁
            - 사이드바에서 카테고리 클릭으로 펼치기
            - 실시간 데이터는 5분마다 갱신
            - AI 어시스턴트에 질문하세요
            """)

        if st.button("✓ 가이드 닫기", type="primary"):
            st.session_state.show_onboarding = False
            st.rerun()

        st.divider()


def get_page_title(page_id: str) -> str:
    """페이지 타이틀 반환"""
    item = get_menu_item(page_id)
    if item:
        return f"{item.icon} {item.name}"
    return "📊 NOTION"
