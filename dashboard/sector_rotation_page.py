"""
섹터 회전 분석 페이지
섹터별 순환 패턴 및 자금 흐름 시각화
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from analysis.sector_rotation import (
        SectorRotationAnalyzer, MarketPhase, SECTOR_ETFS,
        sector_rotation_analyzer
    )
    ROTATION_AVAILABLE = True
except ImportError:
    ROTATION_AVAILABLE = False

try:
    from korea.krx_data import KRXDataCollector
    KRX_AVAILABLE = True
except ImportError:
    KRX_AVAILABLE = False

try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def fetch_sector_prices(days: int = 120) -> dict:
    """섹터 ETF 가격 데이터 조회"""
    sector_prices = {}

    if not KRX_AVAILABLE:
        return _generate_sample_sector_prices(days)

    try:
        collector = KRXDataCollector()
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime('%Y%m%d')

        for sector_name, sector_info in SECTOR_ETFS.items():
            try:
                df = collector.get_stock_price(sector_info['code'], start_date, end_date)
                if not df.empty:
                    sector_prices[sector_name] = df['Close'].tail(days)
            except Exception:
                continue

        if not sector_prices:
            return _generate_sample_sector_prices(days)

        return sector_prices
    except Exception:
        return _generate_sample_sector_prices(days)


def fetch_benchmark_prices(days: int = 120) -> pd.Series:
    """KOSPI 벤치마크 가격 조회"""
    if not KRX_AVAILABLE:
        return _generate_sample_benchmark(days)

    try:
        collector = KRXDataCollector()
        df = collector.get_index_data('KOSPI', days)
        if df.empty:
            return _generate_sample_benchmark(days)
        return df['Close'].tail(days)
    except Exception:
        return _generate_sample_benchmark(days)


def _generate_sample_sector_prices(days: int) -> dict:
    """샘플 섹터 가격 생성"""
    sector_prices = {}
    dates = pd.date_range(end=datetime.now(), periods=days, freq='B')

    for i, (sector_name, _) in enumerate(SECTOR_ETFS.items()):
        np.random.seed(42 + i)
        drift = np.random.uniform(-0.0001, 0.0002)
        returns = np.random.randn(days) * 0.015 + drift
        base = np.random.uniform(10000, 50000)
        prices = base * np.exp(np.cumsum(returns))
        sector_prices[sector_name] = pd.Series(prices, index=dates)

    return sector_prices


def _generate_sample_benchmark(days: int) -> pd.Series:
    """샘플 벤치마크 생성"""
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=days, freq='B')
    returns = np.random.randn(days) * 0.01
    prices = 2500 * np.exp(np.cumsum(returns))
    return pd.Series(prices, index=dates)


def create_sector_momentum_chart(performances) -> go.Figure:
    """섹터 모멘텀 바 차트"""
    names = [p.name for p in performances]
    scores = [p.momentum_score for p in performances]
    colors = ['#22c55e' if s > 0 else '#ef4444' for s in scores]

    fig = go.Figure(data=[
        go.Bar(
            x=names,
            y=scores,
            marker_color=colors,
            text=[f'{s:.1f}' for s in scores],
            textposition='outside'
        )
    ])

    fig.add_hline(y=0, line_dash='dash', line_color='gray')

    fig.update_layout(
        title='섹터별 모멘텀 점수',
        xaxis_title='섹터',
        yaxis_title='모멘텀 점수',
        height=400
    )

    return fig


def create_sector_heatmap(performances) -> go.Figure:
    """섹터 수익률 히트맵"""
    data = []
    for p in performances:
        data.append({
            '섹터': p.name,
            '1주': p.return_1w,
            '1개월': p.return_1m,
            '3개월': p.return_3m
        })

    df = pd.DataFrame(data)
    df = df.set_index('섹터')

    fig = go.Figure(data=go.Heatmap(
        z=df.values,
        x=['1주', '1개월', '3개월'],
        y=df.index,
        colorscale='RdYlGn',
        zmid=0,
        text=np.round(df.values, 1),
        texttemplate='%{text}%',
        textfont={'size': 10}
    ))

    fig.update_layout(
        title='섹터별 기간 수익률 (%)',
        height=500
    )

    return fig


def create_rotation_clock(phase: MarketPhase, performances) -> go.Figure:
    """섹터 로테이션 시계 (원형 차트)"""
    # 극좌표 사용한 섹터 배치
    fig = go.Figure()

    names = [p.name for p in performances]
    scores = [max(0, p.momentum_score + 10) for p in performances]  # 음수 방지를 위해 10 추가
    colors = ['#22c55e' if p.momentum_score > 2 else ('#facc15' if p.momentum_score > -2 else '#ef4444')
              for p in performances]

    fig.add_trace(go.Barpolar(
        r=scores,
        theta=names,
        marker_color=colors,
        marker_line_color='white',
        marker_line_width=1,
        opacity=0.8
    ))

    fig.update_layout(
        title=f'섹터 로테이션 현황 (현재: {phase.value})',
        polar=dict(
            radialaxis=dict(visible=True, range=[0, max(scores) * 1.2]),
            angularaxis=dict(direction='clockwise')
        ),
        height=500
    )

    return fig


def render_sector_rotation_page():
    """섹터 회전 분석 페이지 렌더링"""
    st.header("🔄 섹터 회전 분석")
    st.markdown("섹터별 순환 패턴을 분석하여 투자 기회를 발굴합니다.")

    if not ROTATION_AVAILABLE:
        st.error("섹터 회전 분석 모듈을 사용할 수 없습니다.")
        return

    # 분석 기간 선택
    period = st.selectbox(
        "분석 기간",
        options=[60, 120, 252],
        format_func=lambda x: {60: '3개월', 120: '6개월', 252: '1년'}[x],
        index=1
    )

    if st.button("📊 섹터 분석", use_container_width=True):
        with st.spinner("섹터 데이터 분석 중..."):
            # 데이터 조회
            sector_prices = fetch_sector_prices(period)
            benchmark_prices = fetch_benchmark_prices(period)

            if not sector_prices:
                st.error("섹터 데이터를 조회할 수 없습니다.")
                return

            # 회전 분석
            analysis = sector_rotation_analyzer.analyze_sector_rotation(
                sector_prices, benchmark_prices
            )

            # 결과 표시
            st.divider()

            # 시장 국면
            phase_colors = {
                MarketPhase.EARLY_EXPANSION: '#22c55e',
                MarketPhase.LATE_EXPANSION: '#84cc16',
                MarketPhase.EARLY_CONTRACTION: '#facc15',
                MarketPhase.LATE_CONTRACTION: '#ef4444',
                MarketPhase.RECOVERY: '#3b82f6',
                MarketPhase.UNKNOWN: '#888888'
            }

            phase_color = phase_colors.get(analysis.current_phase, '#888888')

            st.markdown(f"""
            <div style='text-align: center; padding: 1.5rem; background: linear-gradient(135deg, {phase_color}40, {phase_color}20);
                        border-radius: 12px; border: 2px solid {phase_color}; margin-bottom: 1rem;'>
                <div style='font-size: 1em; color: gray;'>현재 시장 국면</div>
                <div style='font-size: 2.5em; font-weight: bold; color: {phase_color};'>
                    {analysis.current_phase.value}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 핵심 정보
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("### 🚀 선도 섹터")
                for sector in analysis.leading_sectors:
                    st.markdown(f"✅ **{sector}**")

            with col2:
                st.markdown("### 📉 후행 섹터")
                for sector in analysis.lagging_sectors:
                    st.markdown(f"⚠️ {sector}")

            with col3:
                st.markdown("### 💡 추천 섹터")
                recommended = sector_rotation_analyzer.get_recommended_sectors(analysis.current_phase)
                for sector in recommended[:3]:
                    st.markdown(f"⭐ **{sector}**")

            # 회전 신호
            st.info(f"📊 **로테이션 신호**: {analysis.rotation_signal}")

            # 차트
            if PLOTLY_AVAILABLE:
                tab1, tab2, tab3 = st.tabs(["모멘텀 순위", "수익률 히트맵", "로테이션 시계"])

                with tab1:
                    fig = create_sector_momentum_chart(analysis.sector_performances)
                    st.plotly_chart(fig, use_container_width=True)

                with tab2:
                    fig = create_sector_heatmap(analysis.sector_performances)
                    st.plotly_chart(fig, use_container_width=True)

                with tab3:
                    fig = create_rotation_clock(analysis.current_phase, analysis.sector_performances)
                    st.plotly_chart(fig, use_container_width=True)

            # 상세 테이블
            st.subheader("📋 섹터별 상세 성과")

            ranking_df = sector_rotation_analyzer.calculate_sector_momentum_ranking(sector_prices)
            if not ranking_df.empty:
                st.dataframe(ranking_df, use_container_width=True, hide_index=True)

            # 인사이트
            st.subheader("💡 분석 인사이트")
            insights = sector_rotation_analyzer.get_rotation_insights(analysis)
            for insight in insights:
                st.markdown(f"• {insight}")

            # 투자 전략 제안
            st.subheader("📈 투자 전략")

            if analysis.current_phase == MarketPhase.EARLY_EXPANSION:
                st.success("""
                **초기 확장기 전략**
                - 경기민감주 (IT, 반도체, 자동차) 비중 확대
                - 성장주 중심 포트폴리오 구성
                - 공격적 투자 적합
                """)
            elif analysis.current_phase == MarketPhase.LATE_EXPANSION:
                st.warning("""
                **후기 확장기 전략**
                - 에너지, 원자재 섹터 주목
                - 인플레이션 헤지 자산 고려
                - 방어주로 점진적 전환 준비
                """)
            elif analysis.current_phase == MarketPhase.EARLY_CONTRACTION:
                st.warning("""
                **초기 수축기 전략**
                - 방어주 (은행, 유틸리티) 비중 확대
                - 현금 비중 증가 고려
                - 경기민감주 비중 축소
                """)
            elif analysis.current_phase == MarketPhase.LATE_CONTRACTION:
                st.error("""
                **후기 수축기 전략**
                - 현금 및 채권 비중 확대
                - 배당주, 필수소비재 선호
                - 회복기 대비 저가 매수 기회 모색
                """)
            elif analysis.current_phase == MarketPhase.RECOVERY:
                st.info("""
                **회복기 전략**
                - 성장주 점진적 비중 확대
                - 낙폭과대 우량주 매수 기회
                - 초기 확장기 준비
                """)

    # 사용 가이드
    with st.expander("ℹ️ 섹터 로테이션 가이드"):
        st.markdown("""
        ### 시장 국면별 특징

        **1. 초기 확장기 (Early Expansion)**
        - 경기 회복 초기 단계
        - 금리 인하 효과 발현
        - 선호 섹터: IT, 반도체, 자동차, 건설

        **2. 후기 확장기 (Late Expansion)**
        - 경기 과열 조짐
        - 인플레이션 압력 증가
        - 선호 섹터: 에너지, 철강, 화학

        **3. 초기 수축기 (Early Contraction)**
        - 경기 둔화 시작
        - 금리 동결/인상
        - 선호 섹터: 은행, 바이오, 유틸리티

        **4. 후기 수축기 (Late Contraction)**
        - 경기 침체 심화
        - 금리 인하 기대
        - 선호 섹터: 유틸리티, 필수소비재, 통신

        **5. 회복기 (Recovery)**
        - 바닥 확인 후 반등
        - 유동성 공급 확대
        - 선호 섹터: 2차전지, IT, 반도체

        ### 모멘텀 점수 해석
        - **+5 이상**: 강한 상승 모멘텀
        - **+2 ~ +5**: 상승 추세
        - **-2 ~ +2**: 중립
        - **-5 ~ -2**: 하락 추세
        - **-5 이하**: 강한 하락 모멘텀
        """)


if __name__ == "__main__":
    render_sector_rotation_page()
