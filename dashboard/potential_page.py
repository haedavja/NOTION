"""
잠재적 급등/급락 요인 분석 대시보드
Potential Rally/Decline Analysis Dashboard
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from typing import List, Dict, Optional

from analysis.potential_analyzer import (
    PotentialAnalyzer,
    PotentialScreener,
    PotentialAnalysis,
    PotentialCatalyst,
    CatalystType,
    ImpactLevel,
    Probability,
    Timeframe
)


def render_potential_dashboard():
    """잠재적 급등/급락 분석 대시보드 렌더링"""
    st.header("🎯 잠재적 급등/급락 요인 분석")
    st.markdown("""
    아직 발생하지 않았지만 큰 주가 변동을 일으킬 수 있는 **잠재적 요인**을 분석합니다.
    """)

    # 메인 탭
    main_tab1, main_tab2, main_tab3 = st.tabs([
        "🚀 잠재적 급등 요인",
        "⚠️ 잠재적 급락 요인",
        "📊 종목 분석"
    ])

    with main_tab1:
        render_potential_rally_section()

    with main_tab2:
        render_potential_decline_section()

    with main_tab3:
        render_individual_analysis()


def render_potential_rally_section():
    """잠재적 급등 요인 섹션"""
    st.subheader("🚀 잠재적 급등 요인을 가진 종목")

    # 촉매 유형별 설명
    with st.expander("📖 상승 촉매 유형 설명", expanded=False):
        col1, col2 = st.columns(2)

        bullish_catalysts = [
            ("실적 서프라이즈", "예상보다 좋은 실적 발표 가능성"),
            ("신제품/서비스 출시", "새로운 제품이나 서비스 런칭"),
            ("시장 확대/진출", "새로운 시장으로의 확장"),
            ("규제 승인/인허가", "정부 승인이나 라이선스 획득"),
            ("파트너십/M&A", "전략적 제휴나 인수합병"),
            ("섹터 수혜/테마", "정책이나 트렌드 수혜"),
        ]

        bullish_catalysts2 = [
            ("저평가 해소", "밸류에이션 할인 해소"),
            ("숏스퀴즈", "공매도 포지션 청산 압력"),
            ("배당 확대", "배당금 증가"),
            ("자사주 매입", "회사의 자사주 매입"),
            ("턴어라운드", "실적 개선/흑자 전환"),
            ("비용 절감", "구조조정 효과"),
        ]

        with col1:
            for name, desc in bullish_catalysts:
                st.markdown(f"**{name}**: {desc}")

        with col2:
            for name, desc in bullish_catalysts2:
                st.markdown(f"**{name}**: {desc}")

    # 샘플 데이터 (실제로는 스크리너에서 가져옴)
    sample_stocks = _get_sample_bullish_stocks()

    if sample_stocks:
        for i, analysis in enumerate(sample_stocks):
            render_potential_card(analysis, is_bullish=True, key_prefix=f"bull_{i}")
    else:
        st.info("잠재적 급등 요인을 가진 종목을 분석 중입니다...")


def render_potential_decline_section():
    """잠재적 급락 요인 섹션"""
    st.subheader("⚠️ 잠재적 급락 요인을 가진 종목")

    # 촉매 유형별 설명
    with st.expander("📖 하락 촉매 유형 설명", expanded=False):
        col1, col2 = st.columns(2)

        bearish_catalysts = [
            ("실적 미스", "예상보다 나쁜 실적 발표 가능성"),
            ("경쟁 심화", "시장 점유율 하락 위험"),
            ("규제 리스크", "정부 규제나 법적 이슈"),
            ("부채/유동성", "재무 건전성 문제"),
            ("수요 둔화", "제품/서비스 수요 감소"),
            ("마진 압박", "수익성 악화"),
        ]

        bearish_catalysts2 = [
            ("경영진 이슈", "지배구조 문제"),
            ("섹터 역풍", "업종 전반 하락"),
            ("고평가 부담", "밸류에이션 버블"),
            ("내부자 매도", "대주주/경영진 지분 매각"),
            ("희석 리스크", "유상증자/전환사채"),
            ("매크로 민감도", "금리/환율 등 거시경제 영향"),
        ]

        with col1:
            for name, desc in bearish_catalysts:
                st.markdown(f"**{name}**: {desc}")

        with col2:
            for name, desc in bearish_catalysts2:
                st.markdown(f"**{name}**: {desc}")

    # 샘플 데이터
    sample_stocks = _get_sample_bearish_stocks()

    if sample_stocks:
        for i, analysis in enumerate(sample_stocks):
            render_potential_card(analysis, is_bullish=False, key_prefix=f"bear_{i}")
    else:
        st.info("잠재적 급락 요인을 가진 종목을 분석 중입니다...")


def render_individual_analysis():
    """개별 종목 잠재적 요인 분석"""
    st.subheader("📊 개별 종목 잠재적 요인 분석")

    col1, col2 = st.columns([3, 1])

    with col1:
        stock_input = st.text_input(
            "종목명 또는 티커",
            placeholder="예: 삼성전자, AAPL",
            key="potential_stock_input"
        )

    with col2:
        analyze_btn = st.button("분석하기", key="potential_analyze_btn", type="primary")

    if analyze_btn and stock_input:
        with st.spinner("잠재적 요인 분석 중..."):
            analysis = analyze_stock_potential(stock_input)

            if analysis:
                render_detailed_analysis(analysis)
            else:
                st.warning(f"'{stock_input}' 종목을 찾을 수 없습니다.")


def render_potential_card(analysis: PotentialAnalysis, is_bullish: bool, key_prefix: str):
    """잠재적 요인 카드 렌더링"""
    catalysts = analysis.bullish_catalysts if is_bullish else analysis.bearish_catalysts
    score = analysis.bullish_score if is_bullish else analysis.bearish_score

    if not catalysts:
        return

    # 색상 설정
    if is_bullish:
        border_color = "#4CAF50" if score >= 70 else "#8BC34A" if score >= 50 else "#CDDC39"
        icon = "🚀"
    else:
        border_color = "#F44336" if score >= 70 else "#FF5722" if score >= 50 else "#FF9800"
        icon = "⚠️"

    with st.container():
        st.markdown(f"""
        <div style="
            border: 2px solid {border_color};
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            background: linear-gradient(135deg, {border_color}15, transparent);
        ">
        """, unsafe_allow_html=True)

        # 헤더
        col1, col2, col3 = st.columns([3, 2, 2])

        with col1:
            st.markdown(f"### {icon} {analysis.name} ({analysis.symbol})")

        with col2:
            score_label = "상승 점수" if is_bullish else "하락 점수"
            st.metric(score_label, f"{score:.0f}점")

        with col3:
            st.metric("리스크/보상", f"{analysis.risk_reward_ratio:.1f}x")

        # 촉매 목록
        st.markdown("#### 주요 촉매")

        for i, catalyst in enumerate(catalysts[:3]):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

            with col1:
                st.markdown(f"**{i+1}. {catalyst.catalyst_type.value}**")
                st.caption(catalyst.description[:50])

            with col2:
                st.markdown(f"영향: **{catalyst.impact.korean}**")

            with col3:
                st.markdown(f"확률: **{catalyst.probability.korean}**")

            with col4:
                st.markdown(f"시점: **{catalyst.timeframe.korean}**")

        # 요약
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"**핵심 논리**: {analysis.key_thesis}")

        with col2:
            st.markdown(f"**권고**: {analysis.action_recommendation}")

        # 관찰 포인트
        if analysis.watch_points:
            with st.expander("👁️ 관찰 포인트", expanded=False):
                for point in analysis.watch_points:
                    st.markdown(f"• {point}")

        st.markdown("</div>", unsafe_allow_html=True)


def render_detailed_analysis(analysis: PotentialAnalysis):
    """상세 분석 결과 렌더링"""
    # 종합 점수 게이지
    st.markdown("### 📊 종합 분석")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("상승 점수", f"{analysis.bullish_score:.0f}점",
                  delta=None if analysis.bullish_score < 50 else "유망")

    with col2:
        st.metric("하락 점수", f"{analysis.bearish_score:.0f}점",
                  delta=None if analysis.bearish_score < 50 else "주의")

    with col3:
        bias_color = "green" if "상승" in analysis.overall_bias else "red" if "하락" in analysis.overall_bias else "gray"
        st.metric("방향성", analysis.overall_bias)

    with col4:
        st.metric("확신도", analysis.conviction_level)

    # 상승/하락 요인 비교 차트
    render_catalyst_comparison_chart(analysis)

    # 상승 촉매 상세
    st.markdown("### 🚀 상승 촉매")
    if analysis.bullish_catalysts:
        render_catalyst_table(analysis.bullish_catalysts, is_bullish=True)
    else:
        st.info("탐지된 상승 촉매가 없습니다.")

    # 하락 촉매 상세
    st.markdown("### ⚠️ 하락 촉매")
    if analysis.bearish_catalysts:
        render_catalyst_table(analysis.bearish_catalysts, is_bullish=False)
    else:
        st.info("탐지된 하락 촉매가 없습니다.")

    # 결론 및 권고
    st.markdown("### 📋 결론")

    st.info(f"""
    **핵심 논리**: {analysis.key_thesis}

    **행동 권고**: {analysis.action_recommendation}

    **리스크/보상 비율**: {analysis.risk_reward_ratio:.1f}x
    """)

    if analysis.watch_points:
        st.markdown("#### 👁️ 주요 관찰 포인트")
        for point in analysis.watch_points:
            st.markdown(f"• {point}")


def render_catalyst_comparison_chart(analysis: PotentialAnalysis):
    """상승/하락 촉매 비교 차트"""
    bullish_values = [c.expected_value() for c in analysis.bullish_catalysts]
    bearish_values = [c.expected_value() for c in analysis.bearish_catalysts]

    bullish_labels = [c.catalyst_type.value[:10] for c in analysis.bullish_catalysts]
    bearish_labels = [c.catalyst_type.value[:10] for c in analysis.bearish_catalysts]

    fig = go.Figure()

    # 상승 촉매 (오른쪽)
    if bullish_values:
        fig.add_trace(go.Bar(
            y=bullish_labels,
            x=bullish_values,
            orientation='h',
            name='상승 촉매',
            marker_color='#4CAF50',
            text=[f"{v:.1f}" for v in bullish_values],
            textposition='outside'
        ))

    # 하락 촉매 (왼쪽, 음수로 표시)
    if bearish_values:
        fig.add_trace(go.Bar(
            y=bearish_labels,
            x=[-v for v in bearish_values],
            orientation='h',
            name='하락 촉매',
            marker_color='#F44336',
            text=[f"{v:.1f}" for v in bearish_values],
            textposition='outside'
        ))

    fig.update_layout(
        title="상승 vs 하락 촉매 기대값 비교",
        xaxis_title="기대값 (영향도 x 확률)",
        barmode='overlay',
        height=300,
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)


def render_catalyst_table(catalysts: List[PotentialCatalyst], is_bullish: bool):
    """촉매 테이블 렌더링"""
    for i, catalyst in enumerate(catalysts):
        with st.expander(
            f"{'🟢' if is_bullish else '🔴'} {catalyst.catalyst_type.value}",
            expanded=(i == 0)
        ):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown(f"**설명**: {catalyst.description}")
                st.markdown(f"**영향도**: {catalyst.impact.korean} ({catalyst.impact.score}점)")
                st.markdown(f"**발생 확률**: {catalyst.probability.korean} ({catalyst.probability.value*100:.0f}%)")
                st.markdown(f"**예상 시점**: {catalyst.timeframe.description}")

            with col2:
                if catalyst.expected_move_pct:
                    st.markdown(f"**예상 주가 변동**: {catalyst.expected_move_pct[0]:.0f}% ~ {catalyst.expected_move_pct[1]:.0f}%")

                st.markdown(f"**기대값**: {catalyst.expected_value():.2f}")

            # 근거
            if catalyst.evidence:
                st.markdown("**근거:**")
                for ev in catalyst.evidence[:3]:
                    st.markdown(f"• {ev}")

            # 트리거/리스크
            if catalyst.triggers:
                st.markdown("**트리거 조건:**")
                for tr in catalyst.triggers[:3]:
                    st.markdown(f"• {tr}")

            if catalyst.risks:
                st.markdown("**관련 리스크:**")
                for risk in catalyst.risks[:3]:
                    st.markdown(f"• {risk}")


def analyze_stock_potential(stock_input: str) -> Optional[PotentialAnalysis]:
    """종목 잠재적 요인 분석"""
    analyzer = PotentialAnalyzer()

    # 간단한 티커/종목명 변환 (실제로는 더 정교하게)
    symbol = stock_input.upper()
    name = stock_input

    # 샘플 뉴스 데이터 (실제로는 뉴스 API에서)
    sample_news = [
        {"title": f"{name} 신제품 출시 예정", "content": "혁신적인 신제품으로 시장 확대 기대"},
        {"title": f"{name} 실적 개선 전망", "content": "컨센서스 상회 가능성 높아"},
    ]

    # 샘플 재무 데이터
    sample_financial = {
        "per": 15.5,
        "pbr": 1.2,
        "debt_ratio": 80,
        "operating_margin": 12.5,
        "prev_operating_margin": 10.2
    }

    # 샘플 기술적 데이터
    sample_technical = {
        "rsi": 45,
        "short_interest": 5.2,
        "ma_200_deviation": -5
    }

    return analyzer.analyze(
        symbol=symbol,
        name=name,
        news=sample_news,
        financial_data=sample_financial,
        technical_data=sample_technical
    )


def _get_sample_bullish_stocks() -> List[PotentialAnalysis]:
    """샘플 상승 잠재 종목 데이터"""
    analyzer = PotentialAnalyzer()

    samples = [
        {
            "symbol": "005930",
            "name": "삼성전자",
            "news": [
                {"title": "삼성전자 HBM3 양산 본격화", "content": "AI 반도체 수요 급증으로 HBM 매출 확대 전망"},
                {"title": "갤럭시 S25 출시 임박", "content": "신제품 출시로 스마트폰 점유율 회복 기대"}
            ],
            "financial_data": {"per": 12.5, "pbr": 1.1, "debt_ratio": 25, "operating_margin": 15},
            "technical_data": {"rsi": 42, "short_interest": 3.5, "ma_200_deviation": -8}
        },
        {
            "symbol": "000660",
            "name": "SK하이닉스",
            "news": [
                {"title": "SK하이닉스 HBM 수주 확대", "content": "엔비디아향 HBM 공급 증가"},
                {"title": "메모리 가격 반등 조짐", "content": "DRAM/NAND 가격 바닥 확인"}
            ],
            "financial_data": {"per": 8.5, "pbr": 1.5, "debt_ratio": 45, "operating_margin": 25},
            "technical_data": {"rsi": 38, "short_interest": 4.2, "ma_200_deviation": -12}
        },
        {
            "symbol": "035720",
            "name": "카카오",
            "news": [
                {"title": "카카오 AI 서비스 확대", "content": "카나나 AI 플랫폼 출시 예정"},
                {"title": "광고 매출 회복세", "content": "톡비즈 광고 수요 증가"}
            ],
            "financial_data": {"per": 35, "pbr": 2.1, "debt_ratio": 55, "operating_margin": 8},
            "technical_data": {"rsi": 32, "short_interest": 8.5, "ma_200_deviation": -25}
        }
    ]

    results = []
    for s in samples:
        analysis = analyzer.analyze(
            symbol=s["symbol"],
            name=s["name"],
            news=s["news"],
            financial_data=s["financial_data"],
            technical_data=s["technical_data"]
        )
        if analysis.bullish_score >= 30:
            results.append(analysis)

    return results


def _get_sample_bearish_stocks() -> List[PotentialAnalysis]:
    """샘플 하락 잠재 종목 데이터"""
    analyzer = PotentialAnalyzer()

    samples = [
        {
            "symbol": "000100",
            "name": "유한양행",
            "news": [
                {"title": "레이저티닙 경쟁 심화", "content": "경쟁사 신약 출시로 점유율 하락 우려"},
                {"title": "R&D 비용 증가", "content": "신약 개발 비용 부담 지속"}
            ],
            "financial_data": {"per": 85, "pbr": 4.5, "debt_ratio": 35, "operating_margin": 5},
            "technical_data": {"rsi": 68, "short_interest": 2.1, "ma_200_deviation": 45}
        },
        {
            "symbol": "003550",
            "name": "LG",
            "news": [
                {"title": "지주사 할인 지속", "content": "순자산 가치 대비 저평가 지속"},
                {"title": "자회사 실적 부진", "content": "LG전자, LG화학 실적 우려"}
            ],
            "financial_data": {"per": 12, "pbr": 0.4, "debt_ratio": 15, "operating_margin": 3},
            "technical_data": {"rsi": 55, "short_interest": 1.5, "ma_200_deviation": 5}
        },
        {
            "symbol": "028260",
            "name": "삼성물산",
            "news": [
                {"title": "건설 수주 감소", "content": "해외 건설 수주 둔화"},
                {"title": "원자재 가격 상승", "content": "건설 원가 부담 증가"}
            ],
            "financial_data": {"per": 18, "pbr": 0.6, "debt_ratio": 85, "operating_margin": 4},
            "technical_data": {"rsi": 48, "short_interest": 3.2, "ma_200_deviation": 8}
        }
    ]

    results = []
    for s in samples:
        analysis = analyzer.analyze(
            symbol=s["symbol"],
            name=s["name"],
            news=s["news"],
            financial_data=s["financial_data"],
            technical_data=s["technical_data"]
        )
        if analysis.bearish_score >= 20:
            results.append(analysis)

    return results
