"""
Rally & Decline Analyzer 대시보드 페이지
상승/하락 종목의 논리와 신뢰도를 평가
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from analysis.rally_analyzer import (
        RallyAnalyzer, RallyDetector, CredibilityLevel,
        ThesisType, RallyReport, analyze_stock_rally
    )
    RALLY_ANALYZER_AVAILABLE = True
except ImportError as e:
    RALLY_ANALYZER_AVAILABLE = False
    print(f"Rally Analyzer import error: {e}")

try:
    from analysis.decline_analyzer import (
        DeclineAnalyzer, DeclineDetector, OversoldLevel,
        RecoveryPotential, DeclineReport, analyze_stock_decline
    )
    DECLINE_ANALYZER_AVAILABLE = True
except ImportError as e:
    DECLINE_ANALYZER_AVAILABLE = False
    print(f"Decline Analyzer import error: {e}")


def render_rally_dashboard():
    """Rally & Decline Analyzer 대시보드 렌더링"""
    st.header("📊 상승/하락 논리 분석기")
    st.caption("급등/급락 종목의 논리와 신뢰도를 평가합니다")

    # 메인 탭: 상승 vs 하락
    main_tab1, main_tab2 = st.tabs(["📈 상승 분석", "📉 하락 분석"])

    with main_tab1:
        render_rally_section()

    with main_tab2:
        render_decline_section()


def render_rally_section():
    """상승 분석 섹션"""
    if not RALLY_ANALYZER_AVAILABLE:
        st.error("Rally Analyzer 모듈을 불러올 수 없습니다.")
        return

    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["🔥 급등 종목", "🔍 종목 분석", "📈 섹터 분석"])

    with tab1:
        render_top_rallies()

    with tab2:
        render_single_analysis()

    with tab3:
        render_sector_analysis()


def render_top_rallies():
    """급등 종목 탭"""
    st.subheader("🔥 최근 급등 종목 분석")

    col1, col2 = st.columns([2, 1])
    with col1:
        period = st.selectbox(
            "기간",
            ["5일", "1일", "1개월"],
            key="rally_period"
        )
    with col2:
        if st.button("🔄 분석 시작", key="start_rally_analysis", type="primary"):
            st.session_state.run_rally_analysis = True

    if st.session_state.get('run_rally_analysis'):
        with st.spinner("급등 종목 분석 중..."):
            try:
                detector = RallyDetector()
                period_map = {"1일": "1d", "5일": "5d", "1개월": "1m"}
                rallies = detector.detect_rallying_stocks(
                    top_n=15,
                    period=period_map.get(period, "5d")
                )

                if rallies:
                    # 결과 테이블
                    data = []
                    for r in rallies:
                        data.append({
                            '종목코드': r.symbol,
                            '종목명': r.name,
                            '현재가': f"{r.current_price:,.0f}",
                            '1일': f"{r.change_1d:+.1f}%",
                            '5일': f"{r.change_5d:+.1f}%",
                            '1개월': f"{r.change_1m:+.1f}%",
                            '거래량비': f"{r.volume_ratio:.1f}x",
                        })

                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True, hide_index=True)

                    # 상위 5개 상세 분석
                    st.markdown("---")
                    st.subheader("📋 상세 분석 (상위 5개)")

                    analyzer = RallyAnalyzer()
                    for i, rally in enumerate(rallies[:5]):
                        with st.expander(f"{i+1}. {rally.name} ({rally.symbol}) - {rally.change_5d:+.1f}%"):
                            report = analyzer.analyze_rally(rally.symbol, rally.name)
                            if report:
                                render_rally_report(report)
                            else:
                                st.warning("분석 결과를 가져올 수 없습니다.")
                else:
                    st.info("급등 종목이 없습니다.")

            except Exception as e:
                st.error(f"분석 오류: {e}")
                with st.expander("🔧 문제 해결 방법"):
                    st.markdown("""
                    **가능한 원인:**
                    - pykrx 패키지가 설치되지 않음
                    - 네트워크 연결 문제
                    - KRX 서버 응답 지연

                    **해결 방법:**
                    1. `pip install pykrx` 실행
                    2. 네트워크 연결 확인
                    3. 잠시 후 다시 시도
                    """)


def render_single_analysis():
    """단일 종목 분석 탭"""
    st.subheader("🔍 종목별 상승 논리 분석")

    col1, col2 = st.columns([3, 1])
    with col1:
        symbol = st.text_input(
            "종목 검색",
            placeholder="종목명 또는 코드 (예: 삼성전자, 005930)",
            key="rally_symbol_input"
        )
    with col2:
        analyze_btn = st.button("분석", key="analyze_single", type="primary")

    if analyze_btn and symbol:
        with st.spinner(f"'{symbol}' 분석 중..."):
            try:
                # 종목 코드 변환
                from dashboard.portfolio_page import resolve_ticker
                ticker = resolve_ticker(symbol)

                if ticker:
                    # .KS, .KQ 제거
                    code = ticker.replace('.KS', '').replace('.KQ', '')

                    analyzer = RallyAnalyzer()
                    report = analyzer.analyze_rally(code, symbol)

                    if report:
                        st.success(f"✅ {report.rally_info.name} 분석 완료")
                        render_rally_report(report)
                    else:
                        st.warning("분석 결과를 가져올 수 없습니다.")
                else:
                    st.error(f"'{symbol}' 종목을 찾을 수 없습니다.")

            except Exception as e:
                st.error(f"분석 오류: {e}")
                with st.expander("🔧 문제 해결 방법"):
                    st.markdown("""
                    **가능한 원인:**
                    - pykrx 패키지가 설치되지 않음
                    - 네트워크 연결 문제
                    - KRX 서버 응답 지연

                    **해결 방법:**
                    1. `pip install pykrx` 실행
                    2. 네트워크 연결 확인
                    3. 잠시 후 다시 시도
                    """)


def render_sector_analysis():
    """섹터 분석 탭"""
    st.subheader("📈 섹터별 상승 분석")

    if st.button("🔄 섹터 분석", key="analyze_sectors"):
        with st.spinner("섹터 분석 중..."):
            try:
                detector = RallyDetector()
                sectors = detector.detect_sector_rallies(top_n=10)

                if sectors:
                    # 섹터 차트
                    df = pd.DataFrame(sectors)

                    fig = px.bar(
                        df,
                        x='sector',
                        y='change_5d',
                        color='change_5d',
                        color_continuous_scale=['red', 'yellow', 'green'],
                        title="섹터별 5일 수익률"
                    )
                    fig.update_layout(
                        xaxis_title="섹터",
                        yaxis_title="수익률 (%)",
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # 테이블
                    st.dataframe(
                        df[['sector', 'change_5d', 'current_price']].rename(columns={
                            'sector': '섹터',
                            'change_5d': '5일 수익률(%)',
                            'current_price': 'ETF 가격'
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("섹터 데이터를 가져올 수 없습니다.")

            except Exception as e:
                st.error(f"섹터 분석 오류: {e}")


def render_rally_report(report: RallyReport):
    """Rally Report 렌더링"""
    rally = report.rally_info
    cred = report.credibility

    # 기본 정보
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "현재가",
            f"{rally.current_price:,.0f}원",
            f"{rally.change_1d:+.1f}% (1일)"
        )
    with col2:
        st.metric(
            "5일 수익률",
            f"{rally.change_5d:+.1f}%",
            f"거래량 {rally.volume_ratio:.1f}배"
        )
    with col3:
        # 신뢰도 색상
        cred_color = get_credibility_color(cred.level)
        st.markdown(f"""
        <div style="text-align: center; padding: 10px; background-color: {cred_color}; border-radius: 10px;">
            <h3 style="margin: 0; color: white;">신뢰도</h3>
            <h2 style="margin: 0; color: white;">{cred.overall:.0f}점</h2>
            <p style="margin: 0; color: white;">{cred.level.value}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 신뢰도 세부 점수
    st.markdown("### 📊 신뢰도 분석")
    col1, col2 = st.columns(2)

    with col1:
        # 레이더 차트
        categories = ['펀더멘털', '수급', '기술적', '내러티브', '안정성']
        values = [
            cred.fundamental_score,
            cred.supply_demand_score,
            cred.technical_score,
            cred.narrative_score,
            100 - cred.risk_score,  # 리스크는 반전
        ]

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]],  # 닫기
            theta=categories + [categories[0]],
            fill='toself',
            name='신뢰도'
        ))
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=False,
            height=300
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # 점수 바
        scores = [
            ("펀더멘털 근거", cred.fundamental_score),
            ("수급 근거", cred.supply_demand_score),
            ("기술적 근거", cred.technical_score),
            ("스토리 일관성", cred.narrative_score),
            ("안정성", 100 - cred.risk_score),
        ]

        for label, score in scores:
            color = "green" if score >= 60 else "orange" if score >= 40 else "red"
            st.markdown(f"**{label}**: {score:.0f}점")
            st.progress(score / 100)

    st.markdown("---")

    # 상승 논리
    st.markdown("### 🔍 상승 논리 검증")

    for v in report.validations:
        claim = v.claim
        icon = "✅" if v.is_valid else "❌"
        conf_pct = v.confidence * 100

        with st.container():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{icon} {claim.claim_type.value}**")
                st.caption(claim.description)
                if v.validation_details:
                    st.info(v.validation_details)
            with col2:
                st.markdown(f"**{conf_pct:.0f}%**")
                st.caption("신뢰도")

            if v.risks:
                for risk in v.risks:
                    st.warning(f"⚠️ {risk}")

            st.markdown("---")

    # 추천 및 경고
    st.markdown("### 💡 투자 의견")
    st.markdown(f"**{report.recommendation}**")

    if report.warnings:
        st.markdown("### ⚠️ 주의사항")
        for warning in report.warnings:
            st.warning(warning)


def get_credibility_color(level: CredibilityLevel) -> str:
    """신뢰도 레벨에 따른 색상"""
    colors = {
        CredibilityLevel.VERY_HIGH: "#2E7D32",  # 진한 녹색
        CredibilityLevel.HIGH: "#4CAF50",  # 녹색
        CredibilityLevel.MEDIUM: "#FFC107",  # 노란색
        CredibilityLevel.LOW: "#FF9800",  # 주황색
        CredibilityLevel.VERY_LOW: "#F44336",  # 빨간색
        CredibilityLevel.SPECULATIVE: "#9E9E9E",  # 회색
    }
    return colors.get(level, "#9E9E9E")


# ==================== 하락 분석 섹션 ====================

def render_decline_section():
    """하락 분석 섹션"""
    if not DECLINE_ANALYZER_AVAILABLE:
        st.error("Decline Analyzer 모듈을 불러올 수 없습니다.")
        return

    # 탭 구성
    tab1, tab2, tab3 = st.tabs(["📉 급락 종목", "🔍 종목 분석", "📊 섹터 분석"])

    with tab1:
        render_top_declines()

    with tab2:
        render_single_decline_analysis()

    with tab3:
        render_sector_declines()


def render_top_declines():
    """급락 종목 탭"""
    st.subheader("📉 최근 급락 종목 분석")

    col1, col2 = st.columns([2, 1])
    with col1:
        period = st.selectbox(
            "기간",
            ["5일", "1일", "1개월"],
            key="decline_period"
        )
    with col2:
        if st.button("🔄 분석 시작", key="start_decline_analysis", type="primary"):
            st.session_state.run_decline_analysis = True

    if st.session_state.get('run_decline_analysis'):
        with st.spinner("급락 종목 분석 중..."):
            try:
                detector = DeclineDetector()
                period_map = {"1일": "1d", "5일": "5d", "1개월": "1m"}
                declines = detector.detect_declining_stocks(
                    top_n=15,
                    period=period_map.get(period, "5d")
                )

                if declines:
                    # 결과 테이블
                    data = []
                    for d in declines:
                        data.append({
                            '종목코드': d.symbol,
                            '종목명': d.name,
                            '현재가': f"{d.current_price:,.0f}",
                            '1일': f"{d.change_1d:+.1f}%",
                            '5일': f"{d.change_5d:+.1f}%",
                            '고점대비': f"{d.change_from_high:+.1f}%",
                            'RSI': f"{d.rsi:.0f}",
                        })

                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True, hide_index=True)

                    # 상위 5개 상세 분석
                    st.markdown("---")
                    st.subheader("📋 상세 분석 (상위 5개)")

                    analyzer = DeclineAnalyzer()
                    for i, decline in enumerate(declines[:5]):
                        with st.expander(f"{i+1}. {decline.name} ({decline.symbol}) - {decline.change_5d:+.1f}%"):
                            report = analyzer.analyze_decline(decline.symbol, decline.name)
                            if report:
                                render_decline_report(report)
                            else:
                                st.warning("분석 결과를 가져올 수 없습니다.")
                else:
                    st.info("급락 종목이 없습니다.")

            except Exception as e:
                st.error(f"분석 오류: {e}")
                with st.expander("🔧 문제 해결 방법"):
                    st.markdown("""
                    **가능한 원인:**
                    - pykrx 패키지가 설치되지 않음
                    - 네트워크 연결 문제
                    - KRX 서버 응답 지연

                    **해결 방법:**
                    1. `pip install pykrx` 실행
                    2. 네트워크 연결 확인
                    3. 잠시 후 다시 시도
                    """)


def render_single_decline_analysis():
    """단일 종목 하락 분석 탭"""
    st.subheader("🔍 종목별 하락 분석")

    col1, col2 = st.columns([3, 1])
    with col1:
        symbol = st.text_input(
            "종목 검색",
            placeholder="종목명 또는 코드 (예: 삼성전자, 005930)",
            key="decline_symbol_input"
        )
    with col2:
        analyze_btn = st.button("분석", key="analyze_decline", type="primary")

    if analyze_btn and symbol:
        with st.spinner(f"'{symbol}' 하락 분석 중..."):
            try:
                from dashboard.portfolio_page import resolve_ticker
                ticker = resolve_ticker(symbol)

                if ticker:
                    code = ticker.replace('.KS', '').replace('.KQ', '')

                    analyzer = DeclineAnalyzer()
                    report = analyzer.analyze_decline(code, symbol)

                    if report:
                        st.success(f"✅ {report.decline_info.name} 분석 완료")
                        render_decline_report(report)
                    else:
                        st.warning("분석 결과를 가져올 수 없습니다.")
                else:
                    st.error(f"'{symbol}' 종목을 찾을 수 없습니다.")

            except Exception as e:
                st.error(f"분석 오류: {e}")
                with st.expander("🔧 문제 해결 방법"):
                    st.markdown("""
                    **가능한 원인:**
                    - pykrx 패키지가 설치되지 않음
                    - 네트워크 연결 문제
                    - KRX 서버 응답 지연

                    **해결 방법:**
                    1. `pip install pykrx` 실행
                    2. 네트워크 연결 확인
                    3. 잠시 후 다시 시도
                    """)


def render_sector_declines():
    """섹터별 하락 분석 탭"""
    st.subheader("📊 섹터별 하락 분석")

    if st.button("🔄 섹터 분석", key="analyze_sector_declines"):
        with st.spinner("섹터 분석 중..."):
            try:
                detector = DeclineDetector()
                sectors = detector.detect_sector_declines(top_n=10)

                if sectors:
                    df = pd.DataFrame(sectors)

                    fig = px.bar(
                        df,
                        x='sector',
                        y='change_5d',
                        color='change_5d',
                        color_continuous_scale=['red', 'orange', 'yellow'],
                        title="섹터별 5일 수익률 (하락순)"
                    )
                    fig.update_layout(
                        xaxis_title="섹터",
                        yaxis_title="수익률 (%)",
                        showlegend=False
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    st.dataframe(
                        df[['sector', 'change_5d', 'current_price']].rename(columns={
                            'sector': '섹터',
                            'change_5d': '5일 수익률(%)',
                            'current_price': 'ETF 가격'
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("섹터 데이터를 가져올 수 없습니다.")

            except Exception as e:
                st.error(f"섹터 분석 오류: {e}")


def render_decline_report(report: DeclineReport):
    """Decline Report 렌더링"""
    decline = report.decline_info
    oversold = report.oversold
    recovery = report.recovery

    # 기본 정보
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "현재가",
            f"{decline.current_price:,.0f}원",
            f"{decline.change_1d:+.1f}% (1일)"
        )
    with col2:
        st.metric(
            "고점 대비",
            f"{decline.change_from_high:+.1f}%",
            f"RSI: {decline.rsi:.0f}"
        )
    with col3:
        oversold_color = get_oversold_color(oversold.level)
        st.markdown(f"""
        <div style="text-align: center; padding: 10px; background-color: {oversold_color}; border-radius: 10px;">
            <h3 style="margin: 0; color: white;">과매도</h3>
            <h2 style="margin: 0; color: white;">{oversold.technical_score:.0f}점</h2>
            <p style="margin: 0; color: white;">{oversold.level.value}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 과매도 및 반등 분석
    st.markdown("### 📊 과매도 & 반등 분석")
    col1, col2 = st.columns(2)

    with col1:
        # 과매도 지표
        st.markdown("**📉 과매도 지표**")
        metrics = [
            ("RSI 점수", oversold.rsi_score),
            ("이격도", min(oversold.price_deviation, 50) * 2),
            ("투매 여부", 100 if oversold.volume_capitulation else 0),
        ]
        for label, score in metrics:
            color = "green" if score >= 60 else "orange" if score >= 40 else "red"
            st.markdown(f"**{label}**: {score:.0f}점")
            st.progress(score / 100)

    with col2:
        # 반등 가능성
        recovery_color = get_recovery_color(recovery.potential)
        st.markdown(f"""
        <div style="text-align: center; padding: 15px; background-color: {recovery_color}; border-radius: 10px; margin-bottom: 10px;">
            <h3 style="margin: 0; color: white;">반등 가능성</h3>
            <h2 style="margin: 0; color: white;">{recovery.score:.0f}점</h2>
            <p style="margin: 0; color: white;">{recovery.potential.value}</p>
        </div>
        """, unsafe_allow_html=True)

        if recovery.target_price:
            st.info(f"🎯 목표가: {recovery.target_price:,.0f}원 ({recovery.time_horizon})")

    st.markdown("---")

    # 하락 원인
    st.markdown("### 🔍 하락 원인 분석")
    for v in report.validations:
        claim = v.claim
        severity_icon = "🔴" if claim.severity == "high" else "🟡" if claim.severity == "medium" else "🟢"
        temp_badge = "⏱️ 일시적" if claim.is_temporary else "📌 구조적"

        with st.container():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"**{severity_icon} {claim.claim_type.value}** {temp_badge}")
                st.caption(claim.description)
            with col2:
                st.markdown(f"**{v.reversal_potential * 100:.0f}%**")
                st.caption("반전 가능성")

            st.markdown("---")

    # 반등 촉매 & 리스크
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🚀 반등 촉매")
        if recovery.catalysts:
            for catalyst in recovery.catalysts:
                st.success(f"✅ {catalyst}")
        else:
            st.info("특별한 반등 촉매 없음")

    with col2:
        st.markdown("### ⚠️ 리스크 요인")
        if recovery.risks:
            for risk in recovery.risks:
                st.warning(f"⚠️ {risk}")
        else:
            st.info("주요 리스크 없음")

    # 추천 및 경고
    st.markdown("---")
    st.markdown("### 💡 투자 의견")
    st.markdown(f"**{report.recommendation}**")

    if report.warnings:
        st.markdown("### ⚠️ 주의사항")
        for warning in report.warnings:
            st.warning(warning)


def get_oversold_color(level: OversoldLevel) -> str:
    """과매도 레벨에 따른 색상"""
    colors = {
        OversoldLevel.EXTREME: "#1565C0",  # 진한 파랑
        OversoldLevel.SEVERE: "#1976D2",  # 파랑
        OversoldLevel.MODERATE: "#42A5F5",  # 밝은 파랑
        OversoldLevel.MILD: "#90CAF9",  # 연한 파랑
        OversoldLevel.NEUTRAL: "#9E9E9E",  # 회색
        OversoldLevel.OVERBOUGHT: "#F44336",  # 빨강
    }
    return colors.get(level, "#9E9E9E")


def get_recovery_color(potential: RecoveryPotential) -> str:
    """반등 가능성에 따른 색상"""
    colors = {
        RecoveryPotential.VERY_HIGH: "#2E7D32",  # 진한 녹색
        RecoveryPotential.HIGH: "#4CAF50",  # 녹색
        RecoveryPotential.MEDIUM: "#FFC107",  # 노란색
        RecoveryPotential.LOW: "#FF9800",  # 주황색
        RecoveryPotential.VERY_LOW: "#F44336",  # 빨간색
        RecoveryPotential.AVOID: "#9E9E9E",  # 회색
    }
    return colors.get(potential, "#9E9E9E")


if __name__ == "__main__":
    st.set_page_config(page_title="Rally & Decline Analyzer", layout="wide")
    render_rally_dashboard()
