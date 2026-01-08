"""
고급 기능 대시보드 페이지
기술적 지표, 백테스트, 뉴스 모니터링, 성과 추적 통합
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta


def render_technical_analysis():
    """기술적 분석 UI"""
    st.subheader("📊 기술적 분석")

    symbol = st.text_input("종목 코드", value="005930.KS", key="tech_symbol")

    if st.button("분석 실행", key="run_tech"):
        with st.spinner("분석 중..."):
            try:
                from analysis.technical_indicators import SignalAnalyzer, analyze_stock
                import yfinance as yf

                result = analyze_stock(symbol)

                if 'error' in result:
                    st.error(f"분석 실패: {result['error']}")
                    return

                # 종합 시그널
                signal_colors = {
                    'strong_buy': '🟢🟢',
                    'buy': '🟢',
                    'neutral': '⚪',
                    'sell': '🔴',
                    'strong_sell': '🔴🔴'
                }

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("종합 시그널", signal_colors.get(result['signal'], '⚪'))
                with col2:
                    st.metric("신뢰도", f"{result['confidence']:.1f}%")
                with col3:
                    st.metric("현재가", f"{result['last_price']:,.0f}")

                # 개별 지표 시그널
                st.markdown("#### 개별 지표")
                details = result.get('details', {})

                for name, sig in details.items():
                    icon = {'buy': '🟢', 'sell': '🔴', 'neutral': '⚪'}.get(sig.signal, '⚪')
                    strength_bar = '●' * sig.strength + '○' * (5 - sig.strength)
                    st.write(f"{icon} **{sig.name}**: {sig.description} [{strength_bar}]")

                # 차트
                ticker = yf.Ticker(symbol)
                df = ticker.history(period="6mo")

                if not df.empty:
                    analyzer = SignalAnalyzer(df)
                    ind_df = analyzer.get_indicator_df()

                    fig = make_subplots(rows=4, cols=1, shared_xaxes=True,
                                       vertical_spacing=0.05,
                                       row_heights=[0.4, 0.2, 0.2, 0.2])

                    # 가격 + 볼린저밴드
                    fig.add_trace(go.Candlestick(
                        x=ind_df.index, open=ind_df['Open'], high=ind_df['High'],
                        low=ind_df['Low'], close=ind_df['Close'], name='Price'
                    ), row=1, col=1)

                    fig.add_trace(go.Scatter(x=ind_df.index, y=ind_df['BB_Upper'],
                                            line=dict(color='gray', dash='dash'), name='BB Upper'), row=1, col=1)
                    fig.add_trace(go.Scatter(x=ind_df.index, y=ind_df['BB_Lower'],
                                            line=dict(color='gray', dash='dash'), name='BB Lower',
                                            fill='tonexty', fillcolor='rgba(128,128,128,0.1)'), row=1, col=1)

                    # RSI
                    fig.add_trace(go.Scatter(x=ind_df.index, y=ind_df['RSI'],
                                            line=dict(color='purple'), name='RSI'), row=2, col=1)
                    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
                    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

                    # MACD
                    fig.add_trace(go.Scatter(x=ind_df.index, y=ind_df['MACD'],
                                            line=dict(color='blue'), name='MACD'), row=3, col=1)
                    fig.add_trace(go.Scatter(x=ind_df.index, y=ind_df['MACD_Signal'],
                                            line=dict(color='orange'), name='Signal'), row=3, col=1)
                    fig.add_trace(go.Bar(x=ind_df.index, y=ind_df['MACD_Hist'],
                                        name='Histogram'), row=3, col=1)

                    # 스토캐스틱
                    fig.add_trace(go.Scatter(x=ind_df.index, y=ind_df['Stoch_K'],
                                            line=dict(color='blue'), name='%K'), row=4, col=1)
                    fig.add_trace(go.Scatter(x=ind_df.index, y=ind_df['Stoch_D'],
                                            line=dict(color='orange'), name='%D'), row=4, col=1)

                    fig.update_layout(height=800, showlegend=False,
                                     title=f"{symbol} 기술적 분석")
                    fig.update_xaxes(rangeslider_visible=False)

                    st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"오류: {e}")


def render_backtest():
    """백테스트 UI"""
    st.subheader("📈 전략 백테스트")

    col1, col2 = st.columns(2)
    with col1:
        symbol = st.text_input("종목 코드", value="005930.KS", key="bt_symbol")
        strategy = st.selectbox("전략", [
            "이동평균 교차", "RSI", "MACD", "볼린저밴드", "복합전략"
        ])

    with col2:
        period = st.selectbox("기간", ["6개월", "1년", "2년", "3년"])
        initial_cap = st.number_input("초기자금", value=10000000, step=1000000)

    # 전략별 파라미터
    st.markdown("#### 전략 파라미터")
    col1, col2, col3 = st.columns(3)

    with col1:
        if strategy == "이동평균 교차":
            short_ma = st.number_input("단기 MA", value=20, min_value=5)
            long_ma = st.number_input("장기 MA", value=50, min_value=10)
        elif strategy == "RSI":
            rsi_period = st.number_input("RSI 기간", value=14, min_value=5)
            oversold = st.number_input("과매도", value=30, min_value=10, max_value=50)

    with col2:
        if strategy == "이동평균 교차":
            pass
        elif strategy == "RSI":
            overbought = st.number_input("과매수", value=70, min_value=50, max_value=90)
        elif strategy == "MACD":
            macd_fast = st.number_input("Fast", value=12)
            macd_slow = st.number_input("Slow", value=26)

    with col3:
        stop_loss = st.number_input("손절 %", value=-7.0, step=1.0)
        take_profit = st.number_input("익절 %", value=15.0, step=1.0)

    if st.button("백테스트 실행", key="run_bt"):
        with st.spinner("백테스트 실행 중..."):
            try:
                from analysis.backtest_advanced import (
                    AdvancedBacktester, BacktestConfig,
                    MovingAverageCrossStrategy, RSIStrategy,
                    MACDStrategy, BollingerBandStrategy, CombinedStrategy
                )

                period_map = {"6개월": "6mo", "1년": "1y", "2년": "2y", "3년": "3y"}
                days_map = {"6개월": 180, "1년": 365, "2년": 730, "3년": 1095}

                config = BacktestConfig(
                    initial_capital=initial_cap,
                    stop_loss=stop_loss / 100,
                    take_profit=take_profit / 100
                )

                # 전략 선택
                if strategy == "이동평균 교차":
                    strat = MovingAverageCrossStrategy(short_ma, long_ma)
                elif strategy == "RSI":
                    strat = RSIStrategy(rsi_period, oversold, overbought)
                elif strategy == "MACD":
                    strat = MACDStrategy(macd_fast, macd_slow, 9)
                elif strategy == "볼린저밴드":
                    strat = BollingerBandStrategy()
                else:
                    strat = CombinedStrategy([
                        MovingAverageCrossStrategy(),
                        RSIStrategy(),
                        MACDStrategy()
                    ], min_agree=2)

                backtester = AdvancedBacktester(config)
                start = (datetime.now() - timedelta(days=days_map[period])).strftime('%Y-%m-%d')
                result = backtester.run(symbol, strat, start)

                if result:
                    # 결과 표시
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        color = "normal" if result.total_return >= 0 else "inverse"
                        st.metric("총 수익률", f"{result.total_return:.2f}%", delta_color=color)
                    with col2:
                        st.metric("연환산 수익률", f"{result.annual_return:.2f}%")
                    with col3:
                        st.metric("MDD", f"{result.max_drawdown:.2f}%")
                    with col4:
                        st.metric("샤프 비율", f"{result.sharpe_ratio:.2f}")

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("총 거래", f"{result.total_trades}회")
                    with col2:
                        st.metric("승률", f"{result.win_rate:.1f}%")
                    with col3:
                        st.metric("Profit Factor", f"{result.profit_factor:.2f}")
                    with col4:
                        pnl = result.final_value - result.initial_capital
                        st.metric("순이익", f"₩{pnl:,.0f}")

                    # 자산 곡선 차트
                    if result.equity_curve is not None:
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=result.equity_curve['date'],
                            y=result.equity_curve['equity'],
                            mode='lines', name='자산'
                        ))
                        fig.update_layout(title="자산 곡선", height=400)
                        st.plotly_chart(fig, use_container_width=True)

                    # 매매 기록
                    if result.trades:
                        st.markdown("#### 매매 기록")
                        trades_df = pd.DataFrame([{
                            '날짜': t.date.strftime('%Y-%m-%d'),
                            '유형': t.action,
                            '가격': f"{t.price:,.0f}",
                            '수량': f"{t.quantity:.2f}",
                            '수수료': f"{t.fee:,.0f}",
                        } for t in result.trades[:20]])
                        st.dataframe(trades_df, use_container_width=True)
                else:
                    st.warning("백테스트 결과가 없습니다.")

            except Exception as e:
                st.error(f"오류: {e}")


def render_news_monitor():
    """뉴스 모니터링 UI"""
    st.subheader("📰 뉴스 모니터링")

    if 'portfolio' not in st.session_state or not st.session_state.portfolio.positions:
        st.info("포트폴리오에 종목을 추가하면 관련 뉴스를 모니터링합니다.")
        return

    try:
        from alerts.news_monitor import news_monitor

        symbols = [{'symbol': p.symbol, 'name': p.name}
                  for p in st.session_state.portfolio.positions]

        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"**모니터링 종목**: {', '.join([s['name'] for s in symbols[:5]])}")
        with col2:
            if st.button("🔄 새로고침", key="refresh_news"):
                news_monitor._news_cache.clear()

        with st.spinner("뉴스 수집 중..."):
            news_items = news_monitor.get_portfolio_news(symbols)

        if not news_items:
            st.info("최근 뉴스가 없습니다.")
            return

        # 감성별 필터
        sentiment_filter = st.radio("필터", ["전체", "긍정", "부정"], horizontal=True)

        for news in news_items:
            if sentiment_filter == "긍정" and news.sentiment != 'positive':
                continue
            if sentiment_filter == "부정" and news.sentiment != 'negative':
                continue

            icon = {'positive': '📈', 'negative': '📉', 'neutral': '📄'}.get(news.sentiment, '📄')
            color = {'positive': 'green', 'negative': 'red', 'neutral': 'gray'}.get(news.sentiment, 'gray')

            with st.container():
                st.markdown(f"""
                <div style="border-left: 3px solid {color}; padding-left: 10px; margin-bottom: 10px;">
                    <b>{icon} {news.title}</b><br>
                    <small style="color: gray;">{news.source} | {news.published.strftime('%m-%d %H:%M')} | {news.symbol}</small>
                </div>
                """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"뉴스 로드 오류: {e}")


def render_performance():
    """성과 추적 UI"""
    st.subheader("📊 투자 성과")

    try:
        from portfolio.performance_tracker import performance_tracker

        summary = performance_tracker.get_summary()

        if summary.get('status') == 'no_data':
            st.info("아직 기록된 성과 데이터가 없습니다. 포트폴리오 활동 후 표시됩니다.")

            # 수동 스냅샷 기록
            if st.button("현재 성과 기록"):
                if 'portfolio' in st.session_state:
                    snapshot = performance_tracker.record_snapshot(st.session_state.portfolio)
                    st.success(f"성과 기록 완료! 총 평가액: ₩{snapshot.total_value:,.0f}")
                    st.rerun()
            return

        # 성과 요약
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("총 평가액", f"₩{summary['total_value']:,.0f}")
        with col2:
            pnl = summary['total_pnl']
            st.metric("총 손익", f"₩{pnl:,.0f}",
                     delta=f"{summary['total_return']:.2f}%")
        with col3:
            st.metric("MDD", f"{summary['max_drawdown']:.2f}%")
        with col4:
            st.metric("승률", f"{summary['win_rate']:.1f}%")

        # 성과 차트
        df = performance_tracker.get_performance_df(days=90)
        if not df.empty:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                               vertical_spacing=0.1,
                               row_heights=[0.7, 0.3])

            fig.add_trace(go.Scatter(
                x=df['날짜'], y=df['총 평가액'],
                mode='lines', name='평가액', fill='tozeroy'
            ), row=1, col=1)

            fig.add_trace(go.Bar(
                x=df['날짜'], y=df['일간 수익률'],
                name='일간 수익률',
                marker_color=df['일간 수익률'].apply(
                    lambda x: 'green' if x >= 0 else 'red'
                )
            ), row=2, col=1)

            fig.update_layout(height=500, showlegend=False, title="성과 추이")
            st.plotly_chart(fig, use_container_width=True)

        # 최근 매매
        st.markdown("#### 최근 매매 기록")
        trades = performance_tracker.get_trades(days=30)
        if trades:
            for trade in trades[:10]:
                icon = '🟢' if trade.trade_type == 'BUY' else '🔴'
                st.write(f"{icon} **{trade.symbol}** {trade.trade_type} "
                        f"{trade.quantity:.0f}주 @ ₩{trade.price:,.0f} "
                        f"({trade.timestamp.strftime('%m-%d %H:%M')})")
        else:
            st.info("매매 기록이 없습니다.")

    except Exception as e:
        st.error(f"성과 데이터 오류: {e}")


def render_multi_portfolio():
    """다중 포트폴리오 UI"""
    st.subheader("📁 포트폴리오 관리")

    try:
        from portfolio.multi_portfolio import portfolio_manager, PortfolioType

        portfolios = portfolio_manager.list_portfolios()

        # 포트폴리오 선택
        col1, col2 = st.columns([3, 1])
        with col1:
            selected_id = st.selectbox(
                "포트폴리오 선택",
                options=[p.id for p in portfolios],
                format_func=lambda x: next(
                    (f"{p.name} ({p.portfolio_type.value})" for p in portfolios if p.id == x),
                    x
                )
            )
        with col2:
            if st.button("➕ 새 포트폴리오"):
                st.session_state.show_new_portfolio = True

        # 새 포트폴리오 생성
        if st.session_state.get('show_new_portfolio'):
            with st.form("new_portfolio_form"):
                name = st.text_input("이름")
                ptype = st.selectbox("유형", ["실제투자", "모의투자", "관심종목"])
                desc = st.text_area("설명")

                if st.form_submit_button("생성"):
                    type_map = {
                        "실제투자": PortfolioType.REAL,
                        "모의투자": PortfolioType.PAPER,
                        "관심종목": PortfolioType.WATCHLIST
                    }
                    portfolio_manager.create_portfolio(name, type_map[ptype], desc)
                    st.session_state.show_new_portfolio = False
                    st.success("포트폴리오 생성 완료!")
                    st.rerun()

        if not selected_id:
            return

        # 포트폴리오 요약
        summary = portfolio_manager.get_summary(selected_id)
        meta = portfolio_manager.get_meta(selected_id)

        st.divider()

        if summary.get('type') == 'watchlist':
            st.markdown(f"**{meta.name}** - 관심종목 {summary['count']}개")

            watchlist = portfolio_manager.get_watchlist(selected_id)
            for item in watchlist:
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write(f"**{item.name}** ({item.symbol})")
                with col2:
                    if item.target_price:
                        st.write(f"목표가: ₩{item.target_price:,.0f}")
                with col3:
                    if st.button("삭제", key=f"del_{item.symbol}"):
                        portfolio_manager.remove_from_watchlist(selected_id, item.symbol)
                        st.rerun()
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("총 평가액", f"₩{summary.get('total_value', 0):,.0f}")
            with col2:
                st.metric("손익", f"₩{summary.get('pnl', 0):,.0f}")
            with col3:
                st.metric("수익률", f"{summary.get('pnl_pct', 0):.2f}%")

            portfolio = portfolio_manager.get_portfolio(selected_id)
            if portfolio and portfolio.positions:
                st.markdown("#### 보유 종목")
                for pos in portfolio.positions:
                    pnl = (pos.current_price - pos.avg_cost) * pos.quantity
                    pnl_pct = (pos.current_price / pos.avg_cost - 1) * 100 if pos.avg_cost > 0 else 0

                    col1, col2, col3 = st.columns([2, 2, 1])
                    with col1:
                        st.write(f"**{pos.name}** ({pos.symbol})")
                    with col2:
                        color = 'green' if pnl >= 0 else 'red'
                        st.markdown(f"<span style='color:{color}'>₩{pnl:,.0f} ({pnl_pct:+.2f}%)</span>",
                                  unsafe_allow_html=True)
                    with col3:
                        st.write(f"{pos.quantity}주")

    except Exception as e:
        st.error(f"포트폴리오 오류: {e}")


def render_advanced_features():
    """고급 기능 메인 페이지"""
    st.title("🔧 고급 기능")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 기술적 분석", "📈 백테스트", "📰 뉴스", "📊 성과", "📁 포트폴리오"
    ])

    with tab1:
        render_technical_analysis()

    with tab2:
        render_backtest()

    with tab3:
        render_news_monitor()

    with tab4:
        render_performance()

    with tab5:
        render_multi_portfolio()
