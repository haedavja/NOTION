"""
Rally Analyzer 대시보드 페이지
상승 종목/섹터의 논리와 신뢰도를 평가
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


def render_rally_dashboard():
    """Rally Analyzer 대시보드 렌더링"""
    st.header("📊 상승 논리 분석기")
    st.caption("급등 종목의 상승 이유와 신뢰도를 평가합니다")

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


if __name__ == "__main__":
    st.set_page_config(page_title="Rally Analyzer", layout="wide")
    render_rally_dashboard()
