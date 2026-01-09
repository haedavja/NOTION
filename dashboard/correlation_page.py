"""
상관관계 분석 페이지
종목 간 상관관계 분석 및 시각화
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from analysis.correlation import (
        CorrelationAnalyzer, correlation_analyzer
    )
    CORRELATION_AVAILABLE = True
except ImportError:
    CORRELATION_AVAILABLE = False

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


def fetch_stock_prices(code: str, days: int = 252) -> pd.Series:
    """종목 가격 데이터 조회"""
    if not KRX_AVAILABLE:
        return _generate_sample_prices(code, days)

    try:
        collector = KRXDataCollector()
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime('%Y%m%d')

        df = collector.get_stock_price(code, start_date, end_date)
        if df.empty:
            return _generate_sample_prices(code, days)

        return df['Close'].tail(days)
    except Exception:
        return _generate_sample_prices(code, days)


def get_stock_name(code: str) -> str:
    """종목명 조회"""
    if not KRX_AVAILABLE:
        return code

    try:
        collector = KRXDataCollector()
        info = collector.get_stock_by_code(code)
        return info.get('name', code) if info else code
    except Exception:
        return code


def _generate_sample_prices(code: str, days: int) -> pd.Series:
    """샘플 가격 생성"""
    np.random.seed(hash(code) % 10000)
    dates = pd.date_range(end=datetime.now(), periods=days, freq='B')
    returns = np.random.randn(days) * 0.02
    prices = 50000 * np.exp(np.cumsum(returns))
    return pd.Series(prices, index=dates)


def create_correlation_heatmap(corr_matrix: pd.DataFrame, stock_names: dict) -> go.Figure:
    """상관관계 히트맵 생성"""
    # 라벨 변환
    labels = [stock_names.get(col, col) for col in corr_matrix.columns]

    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=labels,
        y=labels,
        colorscale='RdBu_r',
        zmid=0,
        zmin=-1,
        zmax=1,
        text=np.round(corr_matrix.values, 2),
        texttemplate='%{text}',
        textfont={'size': 10},
        hoverongaps=False
    ))

    fig.update_layout(
        title='종목 간 상관관계 매트릭스',
        height=500,
        xaxis_title='',
        yaxis_title=''
    )

    return fig


def create_rolling_correlation_chart(
    rolling_corr: pd.Series,
    stock1_name: str,
    stock2_name: str
) -> go.Figure:
    """롤링 상관관계 차트"""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=rolling_corr.index,
        y=rolling_corr.values,
        mode='lines',
        name='롤링 상관계수',
        line=dict(color='#3498db', width=2)
    ))

    # 기준선
    fig.add_hline(y=0, line_dash='dash', line_color='gray')
    fig.add_hline(y=0.5, line_dash='dot', line_color='green', annotation_text='높음')
    fig.add_hline(y=-0.5, line_dash='dot', line_color='red', annotation_text='낮음')

    fig.update_layout(
        title=f'{stock1_name} vs {stock2_name} 롤링 상관관계 (20일)',
        xaxis_title='날짜',
        yaxis_title='상관계수',
        yaxis_range=[-1, 1],
        height=400
    )

    return fig


def render_correlation_page():
    """상관관계 분석 페이지 렌더링"""
    st.header("🔗 상관관계 분석")
    st.markdown("종목 간 상관관계를 분석하여 분산 투자 효과를 확인합니다.")

    if not CORRELATION_AVAILABLE:
        st.error("상관관계 분석 모듈을 사용할 수 없습니다.")
        return

    # 분석 유형 선택
    analysis_type = st.radio(
        "분석 유형",
        options=['두 종목 비교', '여러 종목 매트릭스'],
        horizontal=True
    )

    if analysis_type == '두 종목 비교':
        render_pair_correlation()
    else:
        render_matrix_correlation()


def render_pair_correlation():
    """두 종목 간 상관관계 분석"""
    col1, col2, col3 = st.columns(3)

    with col1:
        stock1 = st.text_input("종목 1", value="005930", help="첫 번째 종목 코드")
    with col2:
        stock2 = st.text_input("종목 2", value="000660", help="두 번째 종목 코드")
    with col3:
        period = st.selectbox(
            "분석 기간",
            options=[60, 120, 252],
            format_func=lambda x: {60: '3개월', 120: '6개월', 252: '1년'}[x],
            index=2
        )

    if st.button("📊 상관관계 분석", use_container_width=True):
        with st.spinner("분석 중..."):
            # 데이터 조회
            prices1 = fetch_stock_prices(stock1, period)
            prices2 = fetch_stock_prices(stock2, period)

            if prices1.empty or prices2.empty:
                st.error("데이터를 조회할 수 없습니다.")
                return

            # 종목명 조회
            name1 = get_stock_name(stock1)
            name2 = get_stock_name(stock2)

            # 상관관계 계산
            result = correlation_analyzer.calculate_correlation(
                prices1, prices2, stock1, stock2, name1, name2
            )

            # 결과 표시
            st.divider()

            # 핵심 지표
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                corr_color = '#22c55e' if abs(result.correlation) < 0.5 else '#ef4444'
                st.markdown(f"""
                <div style='text-align: center; padding: 1rem; background: {corr_color}20;
                            border-radius: 8px; border: 2px solid {corr_color};'>
                    <div style='font-size: 0.9em; color: gray;'>상관계수</div>
                    <div style='font-size: 2em; font-weight: bold; color: {corr_color};'>
                        {result.correlation:.3f}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.metric("공분산", f"{result.covariance:.6f}")

            with col3:
                if result.beta is not None:
                    st.metric(f"베타 ({name1}→{name2})", f"{result.beta:.2f}")

            with col4:
                abs_corr = abs(result.correlation)
                if abs_corr >= 0.8:
                    strength = "매우 강함"
                elif abs_corr >= 0.6:
                    strength = "강함"
                elif abs_corr >= 0.4:
                    strength = "보통"
                elif abs_corr >= 0.2:
                    strength = "약함"
                else:
                    strength = "매우 약함"
                st.metric("상관 강도", strength)

            # 해석
            st.info(f"💡 **해석**: {result.interpretation}")

            # 롤링 상관관계 차트
            if PLOTLY_AVAILABLE:
                st.subheader("📈 롤링 상관관계")
                rolling_corr = correlation_analyzer.get_rolling_correlation(prices1, prices2)
                fig = create_rolling_correlation_chart(rolling_corr, name1, name2)
                st.plotly_chart(fig, use_container_width=True)

            # 투자 제언
            st.subheader("💼 투자 제언")

            if abs(result.correlation) < 0.3:
                st.success("✅ **분산 투자에 적합**: 두 종목이 독립적으로 움직여 분산 효과가 큽니다.")
            elif abs(result.correlation) < 0.5:
                st.info("ℹ️ **적정 분산 효과**: 어느 정도 분산 효과를 기대할 수 있습니다.")
            elif result.correlation > 0.7:
                st.warning("⚠️ **분산 효과 미흡**: 두 종목이 유사하게 움직여 리스크 분산이 어렵습니다.")
            elif result.correlation < -0.5:
                st.info("ℹ️ **헤징 가능**: 음의 상관관계로 하락장 헤징에 활용할 수 있습니다.")


def render_matrix_correlation():
    """여러 종목 상관관계 매트릭스"""
    st.markdown("최대 10개 종목의 상관관계를 동시에 분석합니다.")

    # 종목 입력
    default_stocks = "005930, 000660, 035420, 035720, 051910"
    stocks_input = st.text_input(
        "종목 코드 (쉼표로 구분)",
        value=default_stocks,
        help="예: 005930, 000660, 035420"
    )

    period = st.selectbox(
        "분석 기간",
        options=[60, 120, 252],
        format_func=lambda x: {60: '3개월', 120: '6개월', 252: '1년'}[x],
        index=2,
        key="matrix_period"
    )

    if st.button("📊 매트릭스 분석", use_container_width=True):
        # 종목 코드 파싱
        stocks = [s.strip() for s in stocks_input.split(',') if s.strip()]

        if len(stocks) < 2:
            st.error("최소 2개 종목을 입력해주세요.")
            return

        if len(stocks) > 10:
            stocks = stocks[:10]
            st.warning("최대 10개 종목만 분석합니다.")

        with st.spinner("분석 중..."):
            # 데이터 조회
            price_data = {}
            stock_names = {}

            for code in stocks:
                prices = fetch_stock_prices(code, period)
                if not prices.empty:
                    price_data[code] = prices
                    stock_names[code] = get_stock_name(code)

            if len(price_data) < 2:
                st.error("데이터를 조회할 수 없습니다.")
                return

            # 포트폴리오 상관관계 분석
            analysis = correlation_analyzer.analyze_portfolio_correlation(price_data)

            # 결과 표시
            st.divider()

            # 요약 지표
            col1, col2, col3 = st.columns(3)

            with col1:
                avg_corr = analysis['average_correlation']
                color = '#22c55e' if avg_corr < 0.5 else '#ef4444'
                st.markdown(f"""
                <div style='text-align: center; padding: 1rem; background: {color}20;
                            border-radius: 8px; border: 2px solid {color};'>
                    <div style='font-size: 0.9em; color: gray;'>평균 상관계수</div>
                    <div style='font-size: 2em; font-weight: bold; color: {color};'>
                        {avg_corr:.3f}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                st.metric("분산 효과", analysis['diversification_grade'])

            with col3:
                st.metric("분석 종목 수", f"{analysis['stock_count']}개")

            # 분산 효과 설명
            st.info(f"💡 **분석 결과**: {analysis['diversification_description']}")

            # 히트맵
            if PLOTLY_AVAILABLE:
                st.subheader("📊 상관관계 매트릭스")
                fig = create_correlation_heatmap(analysis['correlation_matrix'], stock_names)
                st.plotly_chart(fig, use_container_width=True)

            # 최고/최저 상관관계
            col1, col2 = st.columns(2)

            with col1:
                highest = analysis['highest_correlation']
                if highest['pair']:
                    pair_names = f"{stock_names.get(highest['pair'][0], highest['pair'][0])} - {stock_names.get(highest['pair'][1], highest['pair'][1])}"
                    st.error(f"⚠️ **가장 높은 상관관계**\n\n{pair_names}\n\n상관계수: {highest['value']:.3f}")

            with col2:
                lowest = analysis['lowest_correlation']
                if lowest['pair']:
                    pair_names = f"{stock_names.get(lowest['pair'][0], lowest['pair'][0])} - {stock_names.get(lowest['pair'][1], lowest['pair'][1])}"
                    st.success(f"✅ **가장 낮은 상관관계**\n\n{pair_names}\n\n상관계수: {lowest['value']:.3f}")

            # 상관관계 테이블
            st.subheader("📋 상세 상관관계")

            # 매트릭스를 테이블로 변환
            matrix_data = []
            codes = list(price_data.keys())
            for i in range(len(codes)):
                for j in range(i + 1, len(codes)):
                    corr_val = analysis['correlation_matrix'].iloc[i, j]
                    matrix_data.append({
                        '종목 1': stock_names.get(codes[i], codes[i]),
                        '종목 2': stock_names.get(codes[j], codes[j]),
                        '상관계수': f"{corr_val:.3f}",
                        '분산 효과': '✅ 좋음' if abs(corr_val) < 0.5 else '⚠️ 주의'
                    })

            st.dataframe(pd.DataFrame(matrix_data), use_container_width=True, hide_index=True)

    # 사용 가이드
    with st.expander("ℹ️ 상관관계 해석 가이드"):
        st.markdown("""
        ### 상관계수 해석
        - **+1.0**: 완전 양의 상관 (동일하게 움직임)
        - **+0.7 ~ +0.9**: 강한 양의 상관
        - **+0.4 ~ +0.6**: 중간 양의 상관
        - **+0.1 ~ +0.3**: 약한 양의 상관
        - **0**: 상관관계 없음 (독립적)
        - **-0.1 ~ -0.3**: 약한 음의 상관
        - **-0.4 ~ -0.6**: 중간 음의 상관
        - **-0.7 ~ -0.9**: 강한 음의 상관
        - **-1.0**: 완전 음의 상관 (반대로 움직임)

        ### 분산 투자 활용
        - **상관계수 < 0.3**: 분산 효과 큼 → 포트폴리오에 함께 보유 권장
        - **상관계수 0.3~0.6**: 보통의 분산 효과
        - **상관계수 > 0.6**: 분산 효과 적음 → 하나만 선택 권장
        - **음의 상관관계**: 헤징에 유용

        ### 주의사항
        - 과거 상관관계가 미래를 보장하지 않음
        - 극단적 시장 상황에서는 상관관계가 수렴할 수 있음
        - 섹터 내 종목은 높은 상관관계를 보이는 경향
        """)


if __name__ == "__main__":
    render_correlation_page()
