"""
Snowflake 분석 및 맞춤 추천 페이지
Simply Wall St 스타일 시각화 + 토스 스타일 추천
"""

import streamlit as st
from typing import Dict, List, Optional

try:
    from analysis.snowflake_viz import (
        SnowflakeAnalyzer, SnowflakeScores,
        create_snowflake_chart, create_comparison_snowflake,
        get_score_interpretation, get_overall_rating,
        snowflake_analyzer
    )
    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SNOWFLAKE_AVAILABLE = False

try:
    from analysis.recommendation import (
        PersonalizedRecommender, Recommendation,
        get_recommendation_category_name, recommender
    )
    RECOMMENDATION_AVAILABLE = True
except ImportError:
    RECOMMENDATION_AVAILABLE = False

try:
    from korea.korean_stocks import KoreanStockAnalyzer
    KOREAN_STOCKS_AVAILABLE = True
except ImportError:
    KOREAN_STOCKS_AVAILABLE = False


# 샘플 종목 데이터 (API 없을 때 사용)
SAMPLE_STOCKS = {
    '005930': {
        'name': '삼성전자', 'sector': '반도체',
        'per': 15.2, 'pbr': 1.3, 'roe': 8.5, 'dividend_yield': 2.1,
        'debt_ratio': 35, 'current_ratio': 2.5, 'revenue_growth': 5,
        'earnings_growth': 8, 'operating_margin': 12, 'net_margin': 10
    },
    '000660': {
        'name': 'SK하이닉스', 'sector': '반도체',
        'per': 8.5, 'pbr': 1.8, 'roe': 21, 'dividend_yield': 1.2,
        'debt_ratio': 45, 'current_ratio': 2.0, 'revenue_growth': 25,
        'earnings_growth': 35, 'operating_margin': 20, 'net_margin': 18
    },
    '035420': {
        'name': 'NAVER', 'sector': 'IT',
        'per': 35, 'pbr': 2.0, 'roe': 6, 'dividend_yield': 0.3,
        'debt_ratio': 25, 'current_ratio': 3.0, 'revenue_growth': 10,
        'earnings_growth': 12, 'operating_margin': 15, 'net_margin': 12
    },
    '005380': {
        'name': '현대차', 'sector': '자동차',
        'per': 6.5, 'pbr': 0.6, 'roe': 10, 'dividend_yield': 4.5,
        'debt_ratio': 120, 'current_ratio': 1.2, 'revenue_growth': 8,
        'earnings_growth': 15, 'operating_margin': 8, 'net_margin': 6
    },
    '105560': {
        'name': 'KB금융', 'sector': '은행',
        'per': 5.5, 'pbr': 0.45, 'roe': 9, 'dividend_yield': 5.5,
        'debt_ratio': 1200, 'current_ratio': 1.0, 'revenue_growth': 3,
        'earnings_growth': 5, 'operating_margin': 25, 'net_margin': 20
    },
    '207940': {
        'name': '삼성바이오로직스', 'sector': '바이오',
        'per': 70, 'pbr': 6.0, 'roe': 12, 'dividend_yield': 0,
        'debt_ratio': 30, 'current_ratio': 2.8, 'revenue_growth': 25,
        'earnings_growth': 30, 'operating_margin': 35, 'net_margin': 28
    },
    '006400': {
        'name': '삼성SDI', 'sector': '2차전지',
        'per': 25, 'pbr': 2.2, 'roe': 9, 'dividend_yield': 0.3,
        'debt_ratio': 50, 'current_ratio': 1.8, 'revenue_growth': 30,
        'earnings_growth': 40, 'operating_margin': 10, 'net_margin': 8
    },
    '017670': {
        'name': 'SK텔레콤', 'sector': '통신',
        'per': 9, 'pbr': 0.8, 'roe': 10, 'dividend_yield': 6.5,
        'debt_ratio': 80, 'current_ratio': 1.5, 'revenue_growth': 2,
        'earnings_growth': 5, 'operating_margin': 12, 'net_margin': 10
    },
}


def render_snowflake_page():
    """Snowflake 분석 페이지 렌더링"""
    st.title("❄️ Snowflake 종목 분석")
    st.markdown("Simply Wall St 스타일 5축 레이더 차트로 종목의 강점과 약점을 한눈에 파악하세요.")

    if not SNOWFLAKE_AVAILABLE:
        st.error("Snowflake 모듈을 불러올 수 없습니다.")
        return

    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["📊 개별 분석", "⚖️ 종목 비교", "🎯 맞춤 추천"])

    with tab1:
        render_individual_analysis()

    with tab2:
        render_comparison_analysis()

    with tab3:
        render_recommendations()


def render_individual_analysis():
    """개별 종목 Snowflake 분석"""
    st.subheader("개별 종목 분석")

    # 종목 선택
    col1, col2 = st.columns([2, 1])
    with col1:
        stock_options = {f"{v['name']} ({k})": k for k, v in SAMPLE_STOCKS.items()}
        selected = st.selectbox(
            "종목 선택",
            options=list(stock_options.keys()),
            key="snowflake_stock_select"
        )
        code = stock_options.get(selected, '005930')

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_btn = st.button("🔍 분석", key="snowflake_analyze", use_container_width=True)

    if analyze_btn or 'snowflake_result' in st.session_state:
        if analyze_btn:
            st.session_state.snowflake_code = code

        current_code = st.session_state.get('snowflake_code', code)
        stock_data = SAMPLE_STOCKS.get(current_code, SAMPLE_STOCKS['005930'])

        # Snowflake 점수 계산
        scores = snowflake_analyzer.calculate_scores(
            fundamentals=stock_data,
            sector=stock_data.get('sector', 'default')
        )

        st.session_state.snowflake_result = scores

        # 결과 표시
        col1, col2 = st.columns([1, 1])

        with col1:
            # 레이더 차트
            fig = create_snowflake_chart(scores, stock_data['name'])
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # 종합 등급
            grade, emoji, description = get_overall_rating(scores)
            st.markdown(f"""
            ### {emoji} 종합 등급: {grade}
            **{description}**

            | 지표 | 점수 |
            |:---:|:---:|
            | 가치 | {scores.value:.1f}/6 |
            | 미래 | {scores.future:.1f}/6 |
            | 과거 | {scores.past:.1f}/6 |
            | 배당 | {scores.dividend:.1f}/6 |
            | 건전성 | {scores.health:.1f}/6 |
            | **종합** | **{scores.total:.1f}/6** |
            """)

        # 상세 해석
        st.divider()
        st.subheader("📋 상세 해석")

        interpretations = get_score_interpretation(scores)
        cols = st.columns(5)

        for i, (category, interp) in enumerate(interpretations.items()):
            with cols[i]:
                st.markdown(f"**{category}**")
                st.markdown(interp)

        # 주요 펀더멘털
        st.divider()
        st.subheader("📈 주요 지표")

        metrics_col1, metrics_col2, metrics_col3, metrics_col4 = st.columns(4)
        with metrics_col1:
            st.metric("PER", f"{stock_data.get('per', 'N/A')}")
            st.metric("ROE", f"{stock_data.get('roe', 'N/A')}%")
        with metrics_col2:
            st.metric("PBR", f"{stock_data.get('pbr', 'N/A')}")
            st.metric("부채비율", f"{stock_data.get('debt_ratio', 'N/A')}%")
        with metrics_col3:
            st.metric("배당수익률", f"{stock_data.get('dividend_yield', 0)}%")
            st.metric("매출성장률", f"{stock_data.get('revenue_growth', 'N/A')}%")
        with metrics_col4:
            st.metric("영업이익률", f"{stock_data.get('operating_margin', 'N/A')}%")
            st.metric("유동비율", f"{stock_data.get('current_ratio', 'N/A')}")


def render_comparison_analysis():
    """종목 비교 분석"""
    st.subheader("종목 비교")
    st.markdown("최대 5개 종목을 동시에 비교할 수 있습니다.")

    # 종목 선택
    stock_options = {f"{v['name']} ({k})": k for k, v in SAMPLE_STOCKS.items()}

    selected_stocks = st.multiselect(
        "비교할 종목 선택 (최대 5개)",
        options=list(stock_options.keys()),
        default=list(stock_options.keys())[:3],
        max_selections=5,
        key="comparison_stocks"
    )

    if len(selected_stocks) >= 2:
        if st.button("📊 비교 분석", key="compare_btn"):
            # 각 종목 점수 계산
            comparison_data = []

            for stock_name in selected_stocks:
                code = stock_options[stock_name]
                data = SAMPLE_STOCKS[code]
                scores = snowflake_analyzer.calculate_scores(
                    fundamentals=data,
                    sector=data.get('sector', 'default')
                )
                comparison_data.append((data['name'], scores))

            # 비교 차트
            fig = create_comparison_snowflake(comparison_data)
            st.plotly_chart(fig, use_container_width=True)

            # 비교 테이블
            st.divider()
            st.subheader("📋 점수 비교")

            import pandas as pd
            comparison_df = []
            for name, scores in comparison_data:
                grade, _, _ = get_overall_rating(scores)
                comparison_df.append({
                    '종목': name,
                    '가치': f"{scores.value:.1f}",
                    '미래': f"{scores.future:.1f}",
                    '과거': f"{scores.past:.1f}",
                    '배당': f"{scores.dividend:.1f}",
                    '건전성': f"{scores.health:.1f}",
                    '종합': f"{scores.total:.1f}",
                    '등급': grade
                })

            df = pd.DataFrame(comparison_df)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # 승자 분석
            best_idx = max(range(len(comparison_data)),
                          key=lambda i: comparison_data[i][1].total)
            best_name = comparison_data[best_idx][0]
            best_score = comparison_data[best_idx][1].total

            st.success(f"🏆 종합 1위: **{best_name}** (종합 점수: {best_score:.1f}/6)")

    else:
        st.info("비교하려면 최소 2개 종목을 선택하세요.")


def render_recommendations():
    """맞춤 추천 섹션"""
    st.subheader("🎯 맞춤 추천")

    if not RECOMMENDATION_AVAILABLE:
        st.error("추천 모듈을 불러올 수 없습니다.")
        return

    st.markdown("보유 종목과 투자 스타일에 맞는 종목을 추천해드립니다.")

    # 사용자 설정
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📂 보유 종목 선택**")
        stock_options = {f"{v['name']} ({k})": k for k, v in SAMPLE_STOCKS.items()}
        portfolio = st.multiselect(
            "현재 보유 중인 종목",
            options=list(stock_options.keys()),
            default=[list(stock_options.keys())[0]],  # 삼성전자
            key="portfolio_select"
        )
        portfolio_codes = [stock_options[s] for s in portfolio]

    with col2:
        st.markdown("**🎨 투자 스타일**")
        style = st.selectbox(
            "선호하는 투자 스타일",
            options=['balanced', 'value', 'growth', 'dividend', 'quality', 'momentum'],
            format_func=lambda x: {
                'balanced': '균형 투자',
                'value': '가치 투자 (저PER/PBR)',
                'growth': '성장 투자 (고성장)',
                'dividend': '배당 투자 (고배당)',
                'quality': '우량주 투자 (고ROE)',
                'momentum': '모멘텀 투자 (급성장)'
            }.get(x, x),
            key="style_select"
        )

    # 선호 섹터
    st.markdown("**🏭 선호 섹터 (선택사항)**")
    sectors = ['반도체', 'IT', '자동차', '2차전지', '바이오', '은행', '통신', '화학']
    preferred_sectors = st.multiselect(
        "관심 있는 섹터",
        options=sectors,
        key="sector_select"
    )

    # 선택한 스타일 설명
    style_desc = get_investment_style_description(style)
    if style_desc:
        st.info(f"💡 {style_desc}")

    st.divider()

    if st.button("🔮 추천받기", type="primary", use_container_width=True):
        # 추천 생성
        recommender.set_user_profile(
            portfolio=portfolio_codes,
            preferred_sectors=preferred_sectors,
            investment_style=style
        )

        recommendations = recommender.get_recommendations(limit=6)

        if not recommendations:
            st.warning("추천할 종목이 없습니다. 설정을 변경해보세요.")
            return

        st.subheader(f"✨ {len(recommendations)}개 종목 추천")

        # 추천 카드 표시
        for i in range(0, len(recommendations), 2):
            cols = st.columns(2)

            for j, col in enumerate(cols):
                if i + j < len(recommendations):
                    rec = recommendations[i + j]
                    with col:
                        render_recommendation_card(rec)


def render_recommendation_card(rec):
    """추천 카드 렌더링"""
    category_name = get_recommendation_category_name(rec.category)

    # 카드 스타일
    card_color = {
        'similar': '#3498db',
        'sector': '#2ecc71',
        'style': '#9b59b6',
        'dividend_king': '#f1c40f',
        'undervalued': '#e74c3c'
    }.get(rec.category, '#95a5a6')

    highlights_html = " ".join([
        f"<span style='background: rgba(255,255,255,0.2); padding: 2px 8px; "
        f"border-radius: 10px; font-size: 0.8em;'>{h}</span>"
        for h in rec.highlights
    ])

    st.markdown(f"""
    <div style='background: linear-gradient(135deg, {card_color}, {card_color}cc);
                padding: 1rem; border-radius: 10px; color: white; margin-bottom: 1rem;'>
        <div style='font-size: 0.8em; opacity: 0.8;'>{category_name}</div>
        <div style='font-size: 1.3em; font-weight: bold;'>{rec.name}</div>
        <div style='font-size: 0.9em;'>{rec.code}</div>
        <div style='margin: 0.5rem 0;'>
            <span style='font-size: 1.5em; font-weight: bold;'>{rec.match_score:.0f}</span>
            <span style='font-size: 0.9em;'>점 매칭</span>
        </div>
        <div style='font-size: 0.85em; opacity: 0.9;'>{rec.reason}</div>
        <div style='margin-top: 0.5rem;'>{highlights_html}</div>
    </div>
    """, unsafe_allow_html=True)


def get_investment_style_description(style: str) -> str:
    """투자 스타일 설명"""
    descriptions = {
        'balanced': "수익성, 밸류에이션, 배당을 균형 있게 고려합니다.",
        'value': "PER, PBR이 낮은 저평가 종목을 찾습니다.",
        'growth': "매출/이익 성장률이 높은 성장주를 찾습니다.",
        'dividend': "배당수익률이 높은 고배당주를 찾습니다.",
        'quality': "ROE가 높고 시가총액이 큰 우량주를 찾습니다.",
        'momentum': "급성장 중인 모멘텀 종목을 찾습니다."
    }
    return descriptions.get(style, "")


# 메인 실행용
if __name__ == "__main__":
    st.set_page_config(page_title="Snowflake 분석", layout="wide")
    render_snowflake_page()
