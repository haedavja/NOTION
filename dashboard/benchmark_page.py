"""
벤치마크 비교 페이지
포트폴리오 또는 개별 종목의 성과를 벤치마크와 비교
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from analysis.benchmark import (
        BenchmarkAnalyzer, BenchmarkComparison, PerformanceMetrics,
        BENCHMARKS, SECTOR_BENCHMARKS, benchmark_analyzer
    )
    BENCHMARK_AVAILABLE = True
except ImportError:
    BENCHMARK_AVAILABLE = False

try:
    from korea.krx_data import KRXDataCollector
    KRX_AVAILABLE = True
except ImportError:
    KRX_AVAILABLE = False

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


def fetch_stock_prices(code: str, days: int = 252) -> pd.Series:
    """종목 가격 데이터 조회"""
    if not KRX_AVAILABLE:
        return _generate_sample_prices(days)

    try:
        collector = KRXDataCollector()
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime('%Y%m%d')

        df = collector.get_stock_price(code, start_date, end_date)
        if df.empty:
            return _generate_sample_prices(days)

        return df['Close'].tail(days)
    except Exception:
        return _generate_sample_prices(days)


def fetch_benchmark_prices(benchmark_key: str, days: int = 252) -> pd.Series:
    """벤치마크 가격 데이터 조회"""
    if not KRX_AVAILABLE:
        return _generate_sample_benchmark(days, benchmark_key)

    try:
        collector = KRXDataCollector()
        df = collector.get_index_data(benchmark_key, days)
        if df.empty:
            return _generate_sample_benchmark(days, benchmark_key)

        return df['Close'].tail(days)
    except Exception:
        return _generate_sample_benchmark(days, benchmark_key)


def _generate_sample_prices(days: int) -> pd.Series:
    """샘플 종목 가격 생성"""
    np.random.seed(int(datetime.now().timestamp()) % 1000)
    dates = pd.date_range(end=datetime.now(), periods=days, freq='B')
    returns = np.random.randn(days) * 0.02  # 일간 2% 변동성
    prices = 50000 * np.exp(np.cumsum(returns))
    return pd.Series(prices, index=dates)


def _generate_sample_benchmark(days: int, key: str) -> pd.Series:
    """샘플 벤치마크 가격 생성"""
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=days, freq='B')
    returns = np.random.randn(days) * 0.01

    base = 2500 if key in ['KOSPI', 'KOSPI200'] else 850
    prices = base * np.exp(np.cumsum(returns))
    return pd.Series(prices, index=dates)


def create_performance_chart(
    target_prices: pd.Series,
    benchmark_prices: pd.Series,
    target_name: str,
    benchmark_name: str
) -> go.Figure:
    """성과 비교 차트 생성"""
    # 수익률로 정규화 (시작=100)
    target_norm = target_prices / target_prices.iloc[0] * 100
    bench_norm = benchmark_prices / benchmark_prices.iloc[0] * 100

    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.7, 0.3],
        shared_xaxes=True,
        subplot_titles=('누적 수익률 비교', '상대 성과'),
        vertical_spacing=0.1
    )

    # 누적 수익률
    fig.add_trace(
        go.Scatter(
            x=target_norm.index,
            y=target_norm.values,
            name=target_name,
            line=dict(color='#3498db', width=2)
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=bench_norm.index,
            y=bench_norm.values,
            name=benchmark_name,
            line=dict(color='#e74c3c', width=2)
        ),
        row=1, col=1
    )

    # 상대 성과 (초과 수익률)
    relative = target_norm - bench_norm
    colors = ['green' if v >= 0 else 'red' for v in relative.values]

    fig.add_trace(
        go.Bar(
            x=relative.index,
            y=relative.values,
            name='초과 수익',
            marker_color=colors,
            showlegend=False
        ),
        row=2, col=1
    )

    fig.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)

    fig.update_layout(
        height=600,
        title=f'{target_name} vs {benchmark_name}',
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        hovermode='x unified'
    )

    fig.update_yaxes(title_text='수익률 (%)', row=1, col=1)
    fig.update_yaxes(title_text='초과 수익 (%p)', row=2, col=1)

    return fig


def render_metrics_card(metrics: PerformanceMetrics, title: str, is_benchmark: bool = False):
    """성과 지표 카드 렌더링"""
    color = '#e74c3c' if is_benchmark else '#3498db'

    st.markdown(f"""
    <div style='background: linear-gradient(135deg, {color}20, {color}10);
                padding: 1rem; border-radius: 8px; border-left: 4px solid {color};'>
        <h4 style='margin: 0 0 0.5rem 0;'>{title}</h4>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        if metrics.return_1m is not None:
            st.metric("1개월", f"{metrics.return_1m:+.1f}%")
        if metrics.return_3m is not None:
            st.metric("3개월", f"{metrics.return_3m:+.1f}%")

    with col2:
        if metrics.return_6m is not None:
            st.metric("6개월", f"{metrics.return_6m:+.1f}%")
        if metrics.return_1y is not None:
            st.metric("1년", f"{metrics.return_1y:+.1f}%")

    with col3:
        if metrics.volatility is not None:
            st.metric("변동성", f"{metrics.volatility:.1f}%")
        if metrics.sharpe_ratio is not None:
            st.metric("샤프 비율", f"{metrics.sharpe_ratio:.2f}")


def render_benchmark_page():
    """벤치마크 비교 페이지 렌더링"""
    st.header("📊 벤치마크 비교")
    st.markdown("포트폴리오 또는 개별 종목의 성과를 시장 지수와 비교합니다.")

    if not BENCHMARK_AVAILABLE:
        st.error("벤치마크 모듈을 사용할 수 없습니다.")
        return

    # 입력 섹션
    col1, col2, col3 = st.columns(3)

    with col1:
        stock_code = st.text_input(
            "종목 코드",
            value="005930",
            help="비교할 종목의 코드 (6자리)"
        )

    with col2:
        benchmark_options = {**BENCHMARKS, **SECTOR_BENCHMARKS}
        benchmark_key = st.selectbox(
            "벤치마크",
            options=list(benchmark_options.keys()),
            format_func=lambda x: benchmark_options[x].name,
            index=0
        )

    with col3:
        period = st.selectbox(
            "분석 기간",
            options=[60, 120, 252, 504],
            format_func=lambda x: {60: '3개월', 120: '6개월', 252: '1년', 504: '2년'}[x],
            index=2
        )

    # 분석 실행
    if st.button("📊 비교 분석", use_container_width=True):
        with st.spinner("분석 중..."):
            # 데이터 조회
            target_prices = fetch_stock_prices(stock_code, period)
            benchmark_prices = fetch_benchmark_prices(benchmark_key, period)

            if target_prices.empty or len(target_prices) < 20:
                st.error("종목 데이터를 조회할 수 없습니다.")
                return

            # 길이 맞춤
            min_len = min(len(target_prices), len(benchmark_prices))
            target_prices = target_prices.tail(min_len)
            benchmark_prices = benchmark_prices.tail(min_len)

            # 종목명 조회
            stock_name = stock_code
            if KRX_AVAILABLE:
                try:
                    collector = KRXDataCollector()
                    info = collector.get_stock_by_code(stock_code)
                    if info:
                        stock_name = info.get('name', stock_code)
                except Exception:
                    pass

            # 비교 분석
            comparison = benchmark_analyzer.compare_with_benchmark(
                target_name=stock_name,
                target_prices=target_prices,
                benchmark_key=benchmark_key,
                benchmark_prices=benchmark_prices
            )

            # 결과 표시
            st.divider()

            # 차트
            if PLOTLY_AVAILABLE:
                fig = create_performance_chart(
                    target_prices, benchmark_prices,
                    stock_name, comparison.benchmark_name
                )
                st.plotly_chart(fig, use_container_width=True)

            # 성과 지표 비교
            st.subheader("📈 성과 지표 비교")

            col1, col2 = st.columns(2)
            with col1:
                render_metrics_card(comparison.target_metrics, stock_name)
            with col2:
                render_metrics_card(comparison.benchmark_metrics, comparison.benchmark_name, True)

            # 상대 성과
            st.subheader("📊 상대 성과")

            rel = comparison.relative_performance
            rel_data = []
            period_names = {
                'return_1d': '1일', 'return_1w': '1주', 'return_1m': '1개월',
                'return_3m': '3개월', 'return_6m': '6개월', 'return_1y': '1년'
            }

            for key, name in period_names.items():
                if key in rel:
                    value = rel[key]
                    status = "🟢 초과" if value > 0 else "🔴 미달"
                    rel_data.append({
                        '기간': name,
                        '초과 수익': f"{value:+.2f}%p",
                        '상태': status
                    })

            if rel_data:
                st.dataframe(pd.DataFrame(rel_data), use_container_width=True, hide_index=True)

            # 리스크 지표
            st.subheader("⚠️ 리스크 분석")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if comparison.target_metrics.beta is not None:
                    beta = comparison.target_metrics.beta
                    beta_status = "공격적" if beta > 1.2 else ("방어적" if beta < 0.8 else "중립적")
                    st.metric("베타", f"{beta:.2f}", help="1보다 크면 시장보다 변동성이 큼")
                    st.caption(beta_status)

            with col2:
                if comparison.target_metrics.alpha is not None:
                    alpha = comparison.target_metrics.alpha
                    st.metric("알파", f"{alpha:+.2f}%", help="벤치마크 대비 초과 수익")

            with col3:
                if comparison.target_metrics.max_drawdown is not None:
                    mdd = comparison.target_metrics.max_drawdown
                    st.metric("최대 낙폭", f"{mdd:.1f}%", help="최고점 대비 최대 하락률")

            with col4:
                if comparison.correlation is not None:
                    corr = comparison.correlation
                    corr_status = "높음" if corr > 0.7 else ("낮음" if corr < 0.3 else "중간")
                    st.metric("상관관계", f"{corr:.2f}", help="벤치마크와의 상관계수")
                    st.caption(corr_status)

            # 요약
            st.subheader("📝 분석 요약")
            summary = benchmark_analyzer.get_performance_summary(comparison)
            st.markdown(summary)

            # 세션에 저장
            if 'benchmark_history' not in st.session_state:
                st.session_state.benchmark_history = []

            st.session_state.benchmark_history.append({
                'target': stock_name,
                'benchmark': benchmark_key,
                'comparison': comparison,
                'timestamp': datetime.now()
            })
            st.session_state.benchmark_history = st.session_state.benchmark_history[-5:]

    # 분석 이력
    if 'benchmark_history' in st.session_state and st.session_state.benchmark_history:
        st.divider()
        st.subheader("📜 최근 분석 이력")

        history_data = []
        for h in reversed(st.session_state.benchmark_history):
            comp = h['comparison']
            rel_1m = comp.relative_performance.get('return_1m', 0)
            history_data.append({
                '종목': h['target'],
                '벤치마크': h['benchmark'],
                '1개월 초과': f"{rel_1m:+.2f}%p",
                '베타': f"{comp.target_metrics.beta:.2f}" if comp.target_metrics.beta else "N/A",
                '시간': h['timestamp'].strftime('%H:%M:%S')
            })

        st.dataframe(pd.DataFrame(history_data), use_container_width=True, hide_index=True)

    # 사용 가이드
    with st.expander("ℹ️ 지표 해석 가이드"):
        st.markdown("""
        ### 성과 지표
        - **수익률**: 해당 기간 동안의 가격 변화율
        - **변동성**: 가격 변동의 표준편차 (연간화)
        - **샤프 비율**: 위험 조정 수익률 (높을수록 좋음)

        ### 리스크 지표
        - **베타**: 시장 대비 민감도 (1 = 시장과 동일, >1 = 더 공격적)
        - **알파**: 벤치마크 대비 초과 수익 (양수가 좋음)
        - **최대 낙폭**: 최고점에서 최저점까지의 하락률
        - **상관관계**: 벤치마크와의 동조화 정도 (1 = 완전 동조)

        ### 해석
        - **높은 알파 + 낮은 베타**: 이상적인 투자 대상
        - **높은 베타**: 상승장에서 유리, 하락장에서 위험
        - **낮은 상관관계**: 분산 투자 효과 기대
        """)


if __name__ == "__main__":
    render_benchmark_page()
