"""
종목 검색 자동완성 컴포넌트
사용자 친화적인 종목 검색 UI
"""

import streamlit as st
from typing import List, Dict, Optional, Callable
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from korea.krx_data import KRXDataCollector, search_korean_stock
    KRX_AVAILABLE = True
except ImportError:
    KRX_AVAILABLE = False


# 인기 종목 목록 (빠른 선택용)
POPULAR_STOCKS = [
    {'code': '005930', 'name': '삼성전자', 'market': 'KOSPI'},
    {'code': '000660', 'name': 'SK하이닉스', 'market': 'KOSPI'},
    {'code': '035420', 'name': 'NAVER', 'market': 'KOSPI'},
    {'code': '035720', 'name': '카카오', 'market': 'KOSPI'},
    {'code': '051910', 'name': 'LG화학', 'market': 'KOSPI'},
    {'code': '006400', 'name': '삼성SDI', 'market': 'KOSPI'},
    {'code': '005380', 'name': '현대차', 'market': 'KOSPI'},
    {'code': '000270', 'name': '기아', 'market': 'KOSPI'},
    {'code': '373220', 'name': 'LG에너지솔루션', 'market': 'KOSPI'},
    {'code': '207940', 'name': '삼성바이오로직스', 'market': 'KOSPI'},
    {'code': '068270', 'name': '셀트리온', 'market': 'KOSPI'},
    {'code': '247540', 'name': '에코프로비엠', 'market': 'KOSDAQ'},
    {'code': '086520', 'name': '에코프로', 'market': 'KOSDAQ'},
    {'code': '196170', 'name': '알테오젠', 'market': 'KOSDAQ'},
    {'code': '352820', 'name': '하이브', 'market': 'KOSPI'},
]


def search_stocks(query: str, limit: int = 10) -> List[Dict]:
    """
    종목 검색

    Args:
        query: 검색어 (종목명 또는 코드)
        limit: 최대 결과 수

    Returns:
        검색 결과 리스트
    """
    if not query or len(query.strip()) < 1:
        return []

    query = query.strip()

    # KRX 검색 시도
    if KRX_AVAILABLE:
        try:
            results = search_korean_stock(query, limit)
            if results:
                return results
        except Exception:
            pass

    # 폴백: 인기 종목에서 검색
    results = []
    query_lower = query.lower()

    for stock in POPULAR_STOCKS:
        if (query_lower in stock['name'].lower() or
            query in stock['code']):
            results.append(stock)
            if len(results) >= limit:
                break

    return results


def render_stock_search(
    key: str = "stock_search",
    label: str = "종목 검색",
    placeholder: str = "종목명 또는 코드 입력 (예: 삼성전자, 005930)",
    show_popular: bool = True,
    on_select: Optional[Callable[[Dict], None]] = None
) -> Optional[Dict]:
    """
    종목 검색 UI 렌더링

    Args:
        key: Streamlit 위젯 키
        label: 레이블
        placeholder: 플레이스홀더
        show_popular: 인기 종목 표시 여부
        on_select: 선택 시 콜백 함수

    Returns:
        선택된 종목 정보 또는 None
    """
    selected_stock = None

    # 검색 입력
    col1, col2 = st.columns([4, 1])

    with col1:
        search_query = st.text_input(
            label,
            key=f"{key}_input",
            placeholder=placeholder,
            help="종목명(한글) 또는 6자리 코드로 검색"
        )

    with col2:
        search_btn = st.button("🔍", key=f"{key}_btn", use_container_width=True)

    # 검색 결과 표시
    if search_query and (search_btn or len(search_query) >= 2):
        results = search_stocks(search_query)

        if results:
            st.markdown("##### 검색 결과")

            # 결과를 버튼으로 표시
            cols = st.columns(min(len(results), 3))
            for i, stock in enumerate(results[:9]):
                col_idx = i % 3
                with cols[col_idx]:
                    btn_label = f"{stock['name']}\n({stock['code']})"
                    if st.button(btn_label, key=f"{key}_result_{i}", use_container_width=True):
                        selected_stock = stock
                        if on_select:
                            on_select(stock)
                        st.session_state[f"{key}_selected"] = stock
        else:
            st.info("검색 결과가 없습니다. 다른 키워드로 검색해보세요.")

    # 인기 종목 표시
    if show_popular and not search_query:
        with st.expander("⭐ 인기 종목 바로가기", expanded=False):
            cols = st.columns(5)
            for i, stock in enumerate(POPULAR_STOCKS[:15]):
                col_idx = i % 5
                with cols[col_idx]:
                    if st.button(
                        stock['name'],
                        key=f"{key}_popular_{i}",
                        help=f"{stock['code']} ({stock['market']})",
                        use_container_width=True
                    ):
                        selected_stock = stock
                        if on_select:
                            on_select(stock)
                        st.session_state[f"{key}_selected"] = stock

    # 세션에서 선택된 종목 반환
    if selected_stock:
        return selected_stock

    return st.session_state.get(f"{key}_selected")


def render_stock_selector(
    key: str = "stock_selector",
    label: str = "종목 선택",
    default_code: str = "005930"
) -> str:
    """
    간단한 종목 선택기 (selectbox 스타일)

    Args:
        key: 위젯 키
        label: 레이블
        default_code: 기본 종목 코드

    Returns:
        선택된 종목 코드
    """
    # 종목 목록 생성
    stock_options = {f"{s['name']} ({s['code']})": s['code'] for s in POPULAR_STOCKS}

    # 기본값 찾기
    default_label = None
    for label_text, code in stock_options.items():
        if code == default_code:
            default_label = label_text
            break

    # 직접 입력 옵션 추가
    options = ["직접 입력"] + list(stock_options.keys())

    selected = st.selectbox(
        label,
        options=options,
        index=options.index(default_label) if default_label else 0,
        key=f"{key}_select"
    )

    if selected == "직접 입력":
        code = st.text_input(
            "종목 코드 입력",
            value=default_code,
            key=f"{key}_manual",
            max_chars=6
        )
        return code
    else:
        return stock_options[selected]


def render_multi_stock_selector(
    key: str = "multi_stock",
    label: str = "종목 선택 (복수)",
    default_codes: List[str] = None,
    max_stocks: int = 10
) -> List[str]:
    """
    복수 종목 선택기

    Args:
        key: 위젯 키
        label: 레이블
        default_codes: 기본 선택 종목 코드들
        max_stocks: 최대 선택 가능 종목 수

    Returns:
        선택된 종목 코드 리스트
    """
    if default_codes is None:
        default_codes = ['005930', '000660']

    # 종목 옵션
    stock_options = {s['code']: f"{s['name']} ({s['code']})" for s in POPULAR_STOCKS}

    # 기본 선택 라벨
    default_labels = [stock_options.get(code, code) for code in default_codes if code in stock_options]

    selected = st.multiselect(
        label,
        options=list(stock_options.values()),
        default=default_labels,
        max_selections=max_stocks,
        key=f"{key}_multi"
    )

    # 라벨 → 코드 변환
    label_to_code = {v: k for k, v in stock_options.items()}
    selected_codes = [label_to_code.get(s, s) for s in selected]

    # 직접 입력 옵션
    with st.expander("➕ 종목 직접 추가"):
        manual_input = st.text_input(
            "종목 코드 입력 (쉼표로 구분)",
            key=f"{key}_manual_multi",
            placeholder="005930, 000660"
        )

        if manual_input:
            manual_codes = [c.strip() for c in manual_input.split(',') if c.strip()]
            for code in manual_codes:
                if code not in selected_codes and len(code) == 6 and code.isdigit():
                    selected_codes.append(code)

    return selected_codes[:max_stocks]


def get_stock_display_name(code: str) -> str:
    """종목 코드에서 표시명 반환"""
    for stock in POPULAR_STOCKS:
        if stock['code'] == code:
            return f"{stock['name']} ({code})"

    # KRX 조회
    if KRX_AVAILABLE:
        try:
            collector = KRXDataCollector()
            info = collector.get_stock_by_code(code)
            if info:
                return f"{info['name']} ({code})"
        except Exception:
            pass

    return code
