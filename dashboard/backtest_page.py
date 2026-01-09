"""
백테스트 대시보드 페이지
Snowflake 필터 통합 버전
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.engine import BacktestEngine, BacktestResult
from backtest.strategies import (
    BuyAndHoldStrategy, MovingAverageCrossStrategy,
    RSIStrategy, MomentumStrategy, MeanReversionStrategy,
    DualMomentumStrategy
)
from backtest.metrics import PerformanceMetrics

# Snowflake 통합 (선택적)
try:
    from analysis.integration_utils import get_snowflake_scores_for_stock
    SNOWFLAKE_FILTER_AVAILABLE = True
except ImportError:
    SNOWFLAKE_FILTER_AVAILABLE = False

# yfinance (선택적)
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


def fetch_snowflake_for_symbol(symbol: str) -> dict:
    """종목의 Snowflake 점수 조회"""
    if not SNOWFLAKE_FILTER_AVAILABLE or not YFINANCE_AVAILABLE:
        return None

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        fundamentals = {
            'per': info.get('trailingPE'),
            'pbr': info.get('priceToBook'),
            'roe': info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else None,
            'dividend_yield': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
            'debt_ratio': info.get('debtToEquity', 100),
            'revenue_growth': info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else 0,
        }

        scores = get_snowflake_scores_for_stock(fundamentals)
        return {
            'scores': scores,
            'total': scores.total if scores else 0,
            'value': scores.value if scores else 0,
            'future': scores.future if scores else 0,
            'past': scores.past if scores else 0,
            'health': scores.health if scores else 0,
            'dividend': scores.dividend if scores else 0,
        }
    except Exception:
        return None


def check_snowflake_filter(symbol: str, filters: dict) -> tuple:
    """
    Snowflake 필터 조건 확인
    Returns: (통과 여부, Snowflake 데이터)
    """
    if not filters.get('enabled', False):
        return True, None

    snowflake_data = fetch_snowflake_for_symbol(symbol)

    if not snowflake_data:
        # 데이터 없으면 필터 통과 (선택적)
        return filters.get('allow_no_data', True), None

    scores = snowflake_data

    # 최소 총점 필터
    if filters.get('min_total', 0) > 0:
        if scores['total'] < filters['min_total']:
            return False, snowflake_data

    # 개별 점수 필터
    for key in ['value', 'future', 'past', 'health', 'dividend']:
        min_key = f'min_{key}'
        if filters.get(min_key, 0) > 0:
            if scores.get(key, 0) < filters[min_key]:
                return False, snowflake_data

    return True, snowflake_data


def render_snowflake_filter_ui() -> dict:
    """Snowflake 필터 UI 렌더링"""
    filters = {'enabled': False}

    if not SNOWFLAKE_FILTER_AVAILABLE:
        return filters

    st.subheader("❄️ Snowflake 필터")

    filters['enabled'] = st.checkbox(
        "Snowflake 필터 활성화",
        help="펀더멘털 점수 기반으로 종목을 필터링합니다"
    )

    if filters['enabled']:
        st.caption("최소 점수 조건 (0 = 비활성)")

        filters['min_total'] = st.slider(
            "최소 총점 (6점 만점)",
            0.0, 6.0, 0.0, 0.5,
            help="Snowflake 총점 최소값"
        )

        with st.expander("세부 필터"):
            col1, col2 = st.columns(2)

            with col1:
                filters['min_value'] = st.slider(
                    "가치 (Value)", 0, 6, 0, 1,
                    help="저평가 여부"
                )
                filters['min_future'] = st.slider(
                    "미래 (Future)", 0, 6, 0, 1,
                    help="성장 가능성"
                )
                filters['min_past'] = st.slider(
                    "과거 (Past)", 0, 6, 0, 1,
                    help="과거 실적"
                )

            with col2:
                filters['min_health'] = st.slider(
                    "건전성 (Health)", 0, 6, 0, 1,
                    help="재무 건전성"
                )
                filters['min_dividend'] = st.slider(
                    "배당 (Dividend)", 0, 6, 0, 1,
                    help="배당 매력도"
                )

        filters['allow_no_data'] = st.checkbox(
            "데이터 없는 종목 포함",
            value=True,
            help="Snowflake 데이터가 없는 종목도 백테스트에 포함"
        )

    return filters


def create_equity_chart(equity_curve: pd.Series, title: str = "자산 곡선"):
    """자산 곡선 차트"""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=equity_curve.index,
        y=equity_curve.values,
        mode='lines',
        name='포트폴리오 가치',
        line=dict(color='#2196F3', width=2)
    ))

    fig.update_layout(
        title=title,
        xaxis_title="날짜",
        yaxis_title="가치 ($)",
        height=400,
        margin=dict(l=10, r=10, t=40, b=10),
        hovermode='x unified'
    )

    return fig


def create_drawdown_chart(drawdown_series: pd.Series):
    """낙폭 차트"""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=drawdown_series.index,
        y=drawdown_series.values,
        mode='lines',
        fill='tozeroy',
        name='낙폭',
        line=dict(color='#f44336'),
        fillcolor='rgba(244, 67, 54, 0.3)'
    ))

    fig.update_layout(
        title="낙폭 (Drawdown)",
        xaxis_title="날짜",
        yaxis_title="낙폭 (%)",
        height=250,
        margin=dict(l=10, r=10, t=40, b=10)
    )

    return fig


def create_monthly_returns_heatmap(equity_curve: pd.Series):
    """월별 수익률 히트맵"""
    # 월별 수익률 계산
    monthly = equity_curve.resample('M').last()
    monthly_returns = monthly.pct_change() * 100

    # 피벗 테이블 생성
    returns_df = pd.DataFrame({
        'year': monthly_returns.index.year,
        'month': monthly_returns.index.month,
        'return': monthly_returns.values
    })

    pivot = returns_df.pivot(index='year', columns='month', values='return')

    # 월 이름
    month_names = ['1월', '2월', '3월', '4월', '5월', '6월',
                   '7월', '8월', '9월', '10월', '11월', '12월']

    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=month_names[:len(pivot.columns)],
        y=pivot.index.astype(str),
        colorscale='RdYlGn',
        zmid=0,
        text=np.round(pivot.values, 1),
        texttemplate='%{text}%',
        textfont={"size": 10},
        hovertemplate='%{y}년 %{x}: %{z:.1f}%<extra></extra>'
    ))

    fig.update_layout(
        title="월별 수익률 히트맵",
        height=300,
        margin=dict(l=10, r=10, t=40, b=10)
    )

    return fig


def create_trade_distribution(trades: list):
    """거래 분포 차트"""
    if not trades:
        return None

    pnl_pcts = [t['pnl_pct'] for t in trades]

    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=pnl_pcts,
        nbinsx=30,
        marker_color='#2196F3',
        opacity=0.75
    ))

    fig.add_vline(x=0, line_dash="dash", line_color="red")

    fig.update_layout(
        title="거래 수익률 분포",
        xaxis_title="수익률 (%)",
        yaxis_title="거래 수",
        height=300,
        margin=dict(l=10, r=10, t=40, b=10)
    )

    return fig


def run_sample_backtest(strategy_name: str, symbol: str, params: dict) -> BacktestResult:
    """샘플 백테스트 실행"""
    # 샘플 데이터 생성
    np.random.seed(42)
    dates = pd.date_range(start='2020-01-01', end='2023-12-31', freq='B')
    n = len(dates)

    # 가격 시뮬레이션
    returns = np.random.randn(n) * 0.015
    prices = 100 * np.exp(np.cumsum(returns))

    price_data = pd.DataFrame({
        'Open': prices * (1 + np.random.randn(n) * 0.005),
        'High': prices * (1 + abs(np.random.randn(n) * 0.01)),
        'Low': prices * (1 - abs(np.random.randn(n) * 0.01)),
        'Close': prices,
        'Volume': np.random.randint(1000000, 10000000, n),
    }, index=dates)

    # 엔진 초기화
    engine = BacktestEngine(
        initial_capital=params.get('initial_capital', 100000),
        commission=params.get('commission', 0.001)
    )

    # Multi-level columns for yfinance compatibility
    engine.price_data = pd.DataFrame()
    engine.price_data[('Close', symbol)] = price_data['Close']
    engine.price_data[('Open', symbol)] = price_data['Open']
    engine.price_data[('High', symbol)] = price_data['High']
    engine.price_data[('Low', symbol)] = price_data['Low']
    engine.price_data[('Volume', symbol)] = price_data['Volume']
    engine.price_data.columns = pd.MultiIndex.from_tuples(engine.price_data.columns)
    engine.price_data.index = dates

    # 벤치마크
    engine.benchmark_data = price_data['Close']

    # 전략 선택
    if strategy_name == "바이 앤 홀드":
        strategy = BuyAndHoldStrategy(symbol)
    elif strategy_name == "이동평균 크로스":
        strategy = MovingAverageCrossStrategy(
            symbol,
            fast_period=params.get('fast_ma', 20),
            slow_period=params.get('slow_ma', 50)
        )
    elif strategy_name == "RSI":
        strategy = RSIStrategy(
            symbol,
            period=params.get('rsi_period', 14),
            oversold=params.get('oversold', 30),
            overbought=params.get('overbought', 70)
        )
    elif strategy_name == "모멘텀":
        strategy = MomentumStrategy(
            symbol,
            lookback=params.get('lookback', 20)
        )
    elif strategy_name == "평균 회귀":
        strategy = MeanReversionStrategy(
            symbol,
            period=params.get('period', 20),
            std_dev=params.get('std_dev', 2.0)
        )
    else:
        strategy = BuyAndHoldStrategy(symbol)

    # 백테스트 실행
    result = engine.run(strategy)

    return result


def render_backtest_page():
    """백테스트 페이지 렌더링"""
    st.header("📈 백테스트 시스템")

    # 사이드바 설정
    with st.sidebar:
        st.subheader("백테스트 설정")

        # 전략 선택
        strategy = st.selectbox(
            "전략 선택",
            ["바이 앤 홀드", "이동평균 크로스", "RSI", "모멘텀", "평균 회귀"]
        )

        # 종목
        symbol = st.text_input("종목 코드", "SPY")

        # 기간
        st.subheader("기간")
        start_date = st.date_input("시작일", datetime(2020, 1, 1))
        end_date = st.date_input("종료일", datetime(2023, 12, 31))

        # 자본금
        initial_capital = st.number_input("초기 자본금 ($)", 10000, 10000000, 100000, 10000)

        # 수수료
        commission = st.slider("수수료 (%)", 0.0, 1.0, 0.1, 0.05) / 100

        # 전략별 파라미터
        st.subheader("전략 파라미터")
        params = {
            'initial_capital': initial_capital,
            'commission': commission,
        }

        if strategy == "이동평균 크로스":
            params['fast_ma'] = st.slider("단기 MA", 5, 50, 20)
            params['slow_ma'] = st.slider("장기 MA", 20, 200, 50)

        elif strategy == "RSI":
            params['rsi_period'] = st.slider("RSI 기간", 5, 30, 14)
            params['oversold'] = st.slider("과매도", 10, 40, 30)
            params['overbought'] = st.slider("과매수", 60, 90, 70)

        elif strategy == "모멘텀":
            params['lookback'] = st.slider("Lookback 기간", 5, 60, 20)

        elif strategy == "평균 회귀":
            params['period'] = st.slider("기간", 10, 50, 20)
            params['std_dev'] = st.slider("표준편차", 1.0, 3.0, 2.0, 0.5)

        st.divider()

        # Snowflake 필터 UI
        snowflake_filters = render_snowflake_filter_ui()

        st.divider()

        # 실행 버튼
        run_backtest = st.button("🚀 백테스트 실행", use_container_width=True)

    # 메인 영역
    if run_backtest:
        # Snowflake 필터 체크
        if snowflake_filters.get('enabled', False):
            with st.spinner(f"{symbol} Snowflake 점수 확인 중..."):
                passes_filter, snowflake_data = check_snowflake_filter(symbol, snowflake_filters)

            if not passes_filter:
                st.error(f"❄️ {symbol}이(가) Snowflake 필터 조건을 충족하지 못합니다.")

                if snowflake_data:
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("총점", f"{snowflake_data['total']:.1f}/6")
                    with col2:
                        st.metric("가치", f"{snowflake_data['value']}/6")
                    with col3:
                        st.metric("미래", f"{snowflake_data['future']}/6")

                    col4, col5, col6 = st.columns(3)
                    with col4:
                        st.metric("과거", f"{snowflake_data['past']}/6")
                    with col5:
                        st.metric("건전성", f"{snowflake_data['health']}/6")
                    with col6:
                        st.metric("배당", f"{snowflake_data['dividend']}/6")

                st.info("💡 필터 조건을 완화하거나 다른 종목을 선택하세요.")
                st.stop()

            # 필터 통과 시 Snowflake 정보 표시
            if snowflake_data:
                st.success(f"✅ {symbol} Snowflake 필터 통과 (총점: {snowflake_data['total']:.1f}/6)")

        with st.spinner("백테스트 실행 중..."):
            result = run_sample_backtest(strategy, symbol, params)

        # 결과 표시
        st.success("백테스트 완료!")

        # 요약 지표
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("총 수익률", f"{result.total_return:.2f}%",
                     delta=f"연환산: {result.annualized_return:.2f}%")

        with col2:
            st.metric("샤프 비율", f"{result.sharpe_ratio:.2f}",
                     delta="Good" if result.sharpe_ratio > 1 else "Need Improvement")

        with col3:
            st.metric("최대 낙폭", f"{result.max_drawdown:.2f}%")

        with col4:
            st.metric("승률", f"{result.win_rate:.1f}%",
                     delta=f"손익비: {result.profit_factor:.2f}")

        # 추가 지표
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("소르티노 비율", f"{result.sortino_ratio:.2f}")

        with col2:
            st.metric("칼마 비율", f"{result.calmar_ratio:.2f}")

        with col3:
            st.metric("총 거래 수", f"{result.total_trades}회")

        with col4:
            st.metric("벤치마크 대비", f"{result.alpha:+.2f}%")

        # 차트 섹션
        st.divider()

        # 자산 곡선
        equity_chart = create_equity_chart(result.equity_curve, f"{strategy} 전략 - 자산 곡선")
        st.plotly_chart(equity_chart, use_container_width=True)

        # 낙폭 차트
        drawdown_chart = create_drawdown_chart(result.drawdown_series)
        st.plotly_chart(drawdown_chart, use_container_width=True)

        # 두 열 레이아웃
        col1, col2 = st.columns(2)

        with col1:
            # 월별 히트맵
            heatmap = create_monthly_returns_heatmap(result.equity_curve)
            st.plotly_chart(heatmap, use_container_width=True)

        with col2:
            # 거래 분포
            if result.trades:
                trade_dist = create_trade_distribution(result.trades)
                if trade_dist:
                    st.plotly_chart(trade_dist, use_container_width=True)

        # 거래 내역
        st.subheader("거래 내역")

        if result.trades:
            trades_df = pd.DataFrame(result.trades)
            trades_df['buy_date'] = pd.to_datetime(trades_df['buy_date']).dt.strftime('%Y-%m-%d')
            trades_df['sell_date'] = pd.to_datetime(trades_df['sell_date']).dt.strftime('%Y-%m-%d')
            trades_df['pnl'] = trades_df['pnl'].apply(lambda x: f"${x:,.2f}")
            trades_df['pnl_pct'] = trades_df['pnl_pct'].apply(lambda x: f"{x:+.2f}%")

            trades_df.columns = ['종목', '매수일', '매수가', '매도일', '매도가', '수량', '손익', '수익률', '보유일']

            st.dataframe(trades_df, use_container_width=True, hide_index=True)
        else:
            st.info("거래 내역이 없습니다.")

        # 상세 통계
        with st.expander("📊 상세 통계"):
            st.text(result.summary())

    else:
        # 안내 메시지
        st.info("왼쪽 사이드바에서 전략과 파라미터를 설정한 후 '백테스트 실행' 버튼을 클릭하세요.")

        # 전략 설명
        st.subheader("📖 전략 설명")

        strategies_info = {
            "바이 앤 홀드": "가장 단순한 전략. 초기에 매수하여 끝까지 보유합니다.",
            "이동평균 크로스": "단기 이동평균이 장기 이동평균을 상향 돌파시 매수, 하향 돌파시 매도합니다.",
            "RSI": "RSI가 과매도 구간에서 매수, 과매수 구간에서 매도합니다.",
            "모멘텀": "일정 기간 동안의 가격 모멘텀이 양수면 매수, 음수면 매도합니다.",
            "평균 회귀": "볼린저 밴드 하단에서 매수, 중심선에서 매도하는 평균회귀 전략입니다.",
        }

        for name, desc in strategies_info.items():
            st.markdown(f"**{name}**: {desc}")


if __name__ == "__main__":
    render_backtest_page()
