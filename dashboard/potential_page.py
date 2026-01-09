"""
잠재적 급등/급락 요인 분석 대시보드
Potential Rally/Decline Analysis Dashboard

실제 KRX 데이터와 연동하여 잠재적 요인을 분석합니다.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# 모듈 import
try:
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
    POTENTIAL_ANALYZER_AVAILABLE = True
except ImportError as e:
    POTENTIAL_ANALYZER_AVAILABLE = False
    logger.warning(f"PotentialAnalyzer import error: {e}")

try:
    from korea.krx_data import KRXDataCollector
    KRX_AVAILABLE = True
except ImportError:
    KRX_AVAILABLE = False


def render_potential_dashboard():
    """잠재적 급등/급락 분석 대시보드 렌더링"""
    st.header("🎯 잠재적 급등/급락 요인 분석")
    st.markdown("""
    아직 발생하지 않았지만 큰 주가 변동을 일으킬 수 있는 **잠재적 요인**을 분석합니다.
    """)

    if not POTENTIAL_ANALYZER_AVAILABLE:
        st.error("PotentialAnalyzer 모듈을 로드할 수 없습니다.")
        return

    if not KRX_AVAILABLE:
        st.warning("KRX 데이터 모듈이 없습니다. 일부 기능이 제한될 수 있습니다.")

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

    # 분석 시작 버튼
    col1, col2 = st.columns([2, 1])
    with col2:
        if st.button("🔄 분석 시작", key="start_bullish_analysis", type="primary"):
            st.session_state.run_bullish_potential = True

    if st.session_state.get('run_bullish_potential'):
        with st.spinner("잠재적 급등 요인 분석 중..."):
            stocks = _fetch_bullish_candidates()
            if stocks:
                for i, analysis in enumerate(stocks[:10]):
                    render_potential_card(analysis, is_bullish=True, key_prefix=f"bull_{i}")
            else:
                st.info("분석 가능한 종목이 없습니다.")


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

    # 분석 시작 버튼
    col1, col2 = st.columns([2, 1])
    with col2:
        if st.button("🔄 분석 시작", key="start_bearish_analysis", type="primary"):
            st.session_state.run_bearish_potential = True

    if st.session_state.get('run_bearish_potential'):
        with st.spinner("잠재적 급락 요인 분석 중..."):
            stocks = _fetch_bearish_candidates()
            if stocks:
                for i, analysis in enumerate(stocks[:10]):
                    render_potential_card(analysis, is_bullish=False, key_prefix=f"bear_{i}")
            else:
                st.info("분석 가능한 종목이 없습니다.")


def render_individual_analysis():
    """개별 종목 잠재적 요인 분석"""
    st.subheader("📊 개별 종목 잠재적 요인 분석")

    col1, col2 = st.columns([3, 1])

    with col1:
        stock_input = st.text_input(
            "종목명 또는 티커",
            placeholder="예: 삼성전자, 005930, AAPL",
            key="potential_stock_input"
        )

    with col2:
        analyze_btn = st.button("분석하기", key="potential_analyze_btn", type="primary")

    if analyze_btn and stock_input:
        with st.spinner(f"'{stock_input}' 잠재적 요인 분석 중..."):
            analysis = analyze_stock_potential(stock_input)

            if analysis:
                render_detailed_analysis(analysis)
            else:
                st.warning(f"'{stock_input}' 종목을 찾을 수 없거나 분석할 수 없습니다.")


def _fetch_bullish_candidates() -> List[PotentialAnalysis]:
    """실제 데이터에서 상승 잠재력 종목 조회"""
    results = []

    if not KRX_AVAILABLE:
        return _get_fallback_bullish_stocks()

    try:
        krx = KRXDataCollector()
        analyzer = PotentialAnalyzer()

        # 저PER/저PBR 종목 조회 (저평가 후보)
        stock_list = krx.get_stock_list('ALL')

        if stock_list.empty:
            return _get_fallback_bullish_stocks()

        # 상위 50개 종목 분석
        for _, row in stock_list.head(50).iterrows():
            code = row['code']
            name = row['name']

            try:
                # 가격 데이터
                price_data = krx.get_stock_price(code)
                if price_data.empty:
                    continue

                # 수급 데이터
                investor_data = krx.get_investor_trading_by_stock(code, 5)

                # 기술적 데이터 계산
                technical_data = _calculate_technical_data(price_data)

                # 재무 데이터 (간략화)
                financial_data = _estimate_financial_data(price_data)

                # 분석 실행
                analysis = analyzer.analyze(
                    symbol=code,
                    name=name,
                    news=[],  # 뉴스는 별도 API 필요
                    financial_data=financial_data,
                    technical_data=technical_data
                )

                # 상승 점수가 30 이상인 종목만
                if analysis.bullish_score >= 30:
                    results.append(analysis)

            except Exception as e:
                logger.debug(f"종목 분석 오류 ({code}): {e}")
                continue

        # 상승 점수 기준 정렬
        results.sort(key=lambda x: x.bullish_score, reverse=True)
        return results[:10]

    except Exception as e:
        logger.error(f"상승 후보 조회 오류: {e}")
        return _get_fallback_bullish_stocks()


def _fetch_bearish_candidates() -> List[PotentialAnalysis]:
    """실제 데이터에서 하락 위험 종목 조회"""
    results = []

    if not KRX_AVAILABLE:
        return _get_fallback_bearish_stocks()

    try:
        krx = KRXDataCollector()
        analyzer = PotentialAnalyzer()

        stock_list = krx.get_stock_list('ALL')

        if stock_list.empty:
            return _get_fallback_bearish_stocks()

        for _, row in stock_list.head(50).iterrows():
            code = row['code']
            name = row['name']

            try:
                price_data = krx.get_stock_price(code)
                if price_data.empty:
                    continue

                technical_data = _calculate_technical_data(price_data)
                financial_data = _estimate_financial_data(price_data)

                analysis = analyzer.analyze(
                    symbol=code,
                    name=name,
                    news=[],
                    financial_data=financial_data,
                    technical_data=technical_data
                )

                if analysis.bearish_score >= 30:
                    results.append(analysis)

            except Exception as e:
                logger.debug(f"종목 분석 오류 ({code}): {e}")
                continue

        results.sort(key=lambda x: x.bearish_score, reverse=True)
        return results[:10]

    except Exception as e:
        logger.error(f"하락 후보 조회 오류: {e}")
        return _get_fallback_bearish_stocks()


def _calculate_technical_data(price_data: pd.DataFrame) -> Dict:
    """가격 데이터에서 기술적 지표 계산"""
    if price_data.empty or len(price_data) < 14:
        return {}

    try:
        close = price_data['Close']
        current_price = float(close.iloc[-1])

        # RSI 계산
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_value = float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50

        # 200일 이동평균 이격도
        if len(close) >= 200:
            ma_200 = float(close.rolling(200).mean().iloc[-1])
            ma_200_deviation = ((current_price - ma_200) / ma_200) * 100
        else:
            ma_200_deviation = 0

        # 공매도 비율 (실제로는 별도 API 필요)
        short_interest = 0

        return {
            'rsi': rsi_value,
            'short_interest': short_interest,
            'ma_200_deviation': ma_200_deviation,
        }

    except Exception as e:
        logger.debug(f"기술적 지표 계산 오류: {e}")
        return {'rsi': 50, 'short_interest': 0, 'ma_200_deviation': 0}


def _estimate_financial_data(price_data: pd.DataFrame) -> Dict:
    """가격 데이터에서 재무 지표 추정 (간략화)"""
    # 실제로는 재무제표 API 연동 필요
    # 여기서는 가격 변동성 기반 추정만
    if price_data.empty:
        return {}

    try:
        close = price_data['Close']
        returns = close.pct_change().dropna()

        # 변동성 기반 추정 PER (높은 변동성 = 높은 PER 가정)
        volatility = float(returns.std()) * (252 ** 0.5) * 100

        if volatility > 50:
            estimated_per = 30 + volatility / 2
        elif volatility > 30:
            estimated_per = 15 + volatility / 3
        else:
            estimated_per = 10 + volatility / 4

        return {
            'per': estimated_per,
            'pbr': 1.0 + volatility / 100,
            'debt_ratio': 50 + volatility,
            'operating_margin': max(5, 20 - volatility / 5),
        }

    except Exception:
        return {'per': 15, 'pbr': 1.0, 'debt_ratio': 50, 'operating_margin': 10}


def analyze_stock_potential(stock_input: str) -> Optional[PotentialAnalysis]:
    """종목 잠재적 요인 분석"""
    analyzer = PotentialAnalyzer()

    # 종목 코드 변환
    symbol = stock_input.upper().strip()
    name = stock_input

    # 한국 주식인 경우 KRX에서 조회
    if KRX_AVAILABLE:
        try:
            from dashboard.portfolio_page import resolve_ticker
            ticker = resolve_ticker(stock_input)

            if ticker:
                code = ticker.replace('.KS', '').replace('.KQ', '')

                krx = KRXDataCollector()

                # 종목 정보
                stock_info = krx.get_stock_by_code(code)
                if stock_info:
                    name = stock_info.get('name', stock_input)
                    symbol = code

                # 가격 데이터
                price_data = krx.get_stock_price(code)
                if not price_data.empty:
                    technical_data = _calculate_technical_data(price_data)
                    financial_data = _estimate_financial_data(price_data)

                    # 수급 데이터
                    investor_data = krx.get_investor_trading_by_stock(code, 5)

                    # 뉴스 기반 분석 (간략화된 샘플)
                    news = _generate_context_news(name, technical_data)

                    return analyzer.analyze(
                        symbol=symbol,
                        name=name,
                        news=news,
                        financial_data=financial_data,
                        technical_data=technical_data
                    )

        except Exception as e:
            logger.warning(f"종목 분석 오류: {e}")

    # 폴백: 기본 분석
    return analyzer.analyze(
        symbol=symbol,
        name=name,
        news=[],
        financial_data={'per': 15, 'pbr': 1.0, 'debt_ratio': 50},
        technical_data={'rsi': 50, 'short_interest': 0, 'ma_200_deviation': 0}
    )


def _generate_context_news(name: str, technical_data: Dict) -> List[Dict]:
    """기술적 상태 기반 컨텍스트 뉴스 생성"""
    news = []

    rsi = technical_data.get('rsi', 50)
    ma_deviation = technical_data.get('ma_200_deviation', 0)

    # RSI 기반
    if rsi < 30:
        news.append({
            'title': f'{name} 기술적 과매도 구간 진입',
            'content': f'RSI {rsi:.0f}으로 반등 가능성'
        })
    elif rsi > 70:
        news.append({
            'title': f'{name} 기술적 과매수 경고',
            'content': f'RSI {rsi:.0f}으로 조정 가능성'
        })

    # 이격도 기반
    if ma_deviation < -20:
        news.append({
            'title': f'{name} 200일선 대비 저평가',
            'content': f'이격도 {ma_deviation:.0f}%로 반등 기대'
        })
    elif ma_deviation > 30:
        news.append({
            'title': f'{name} 200일선 대비 고평가',
            'content': f'이격도 +{ma_deviation:.0f}%로 조정 경계'
        })

    return news


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
                if catalyst.description:
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
        delta = "유망" if analysis.bullish_score >= 50 else None
        st.metric("상승 점수", f"{analysis.bullish_score:.0f}점", delta=delta)

    with col2:
        delta = "주의" if analysis.bearish_score >= 50 else None
        st.metric("하락 점수", f"{analysis.bearish_score:.0f}점", delta=delta)

    with col3:
        st.metric("방향성", analysis.overall_bias)

    with col4:
        st.metric("확신도", analysis.conviction_level)

    # 상승/하락 요인 비교 차트
    if analysis.bullish_catalysts or analysis.bearish_catalysts:
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


def _get_fallback_bullish_stocks() -> List[PotentialAnalysis]:
    """폴백: 기본 상승 후보 데이터"""
    analyzer = PotentialAnalyzer()

    stocks = [
        {"symbol": "005930", "name": "삼성전자",
         "financial": {"per": 12, "pbr": 1.1, "debt_ratio": 25},
         "technical": {"rsi": 42, "ma_200_deviation": -8}},
        {"symbol": "000660", "name": "SK하이닉스",
         "financial": {"per": 8, "pbr": 1.5, "debt_ratio": 45},
         "technical": {"rsi": 38, "ma_200_deviation": -12}},
        {"symbol": "035720", "name": "카카오",
         "financial": {"per": 25, "pbr": 2.1, "debt_ratio": 55},
         "technical": {"rsi": 32, "ma_200_deviation": -25}},
    ]

    results = []
    for s in stocks:
        analysis = analyzer.analyze(
            symbol=s["symbol"],
            name=s["name"],
            news=[],
            financial_data=s["financial"],
            technical_data=s["technical"]
        )
        if analysis.bullish_score >= 20:
            results.append(analysis)

    return results


def _get_fallback_bearish_stocks() -> List[PotentialAnalysis]:
    """폴백: 기본 하락 위험 데이터"""
    analyzer = PotentialAnalyzer()

    stocks = [
        {"symbol": "000100", "name": "유한양행",
         "financial": {"per": 85, "pbr": 4.5, "debt_ratio": 35},
         "technical": {"rsi": 68, "ma_200_deviation": 45}},
        {"symbol": "003550", "name": "LG",
         "financial": {"per": 12, "pbr": 0.4, "debt_ratio": 15},
         "technical": {"rsi": 55, "ma_200_deviation": 5}},
    ]

    results = []
    for s in stocks:
        analysis = analyzer.analyze(
            symbol=s["symbol"],
            name=s["name"],
            news=[],
            financial_data=s["financial"],
            technical_data=s["technical"]
        )
        if analysis.bearish_score >= 20:
            results.append(analysis)

    return results
