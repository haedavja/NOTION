"""
고급 분석 대시보드
포트폴리오 최적화, 투자 일지, 재무제표, ETF
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# 포트폴리오 최적화
try:
    from portfolio.optimizer import PortfolioOptimizer, portfolio_optimizer
    OPTIMIZER_AVAILABLE = True
except ImportError:
    OPTIMIZER_AVAILABLE = False

# 투자 일지
try:
    from portfolio.journal import (
        InvestmentJournal, investment_journal,
        TradeJournalEntry, GeneralNote, EmotionTag, TradeType, JournalCategory
    )
    JOURNAL_AVAILABLE = True
except ImportError:
    JOURNAL_AVAILABLE = False

# 재무제표
try:
    from analysis.financial_statements import (
        FinancialAnalyzer, financial_analyzer, analyze_financials
    )
    FINANCIAL_AVAILABLE = True
except ImportError:
    FINANCIAL_AVAILABLE = False

# ETF 스크리너
try:
    from analysis.etf_screener import ETFScreener, etf_screener
    ETF_AVAILABLE = True
except ImportError:
    ETF_AVAILABLE = False


def render_portfolio_optimization():
    """포트폴리오 최적화"""
    st.subheader("📊 포트폴리오 최적화 (MPT)")

    if not OPTIMIZER_AVAILABLE:
        st.warning("최적화 모듈을 사용할 수 없습니다.")
        return

    # 종목 입력
    st.markdown("### 종목 입력")
    symbols_input = st.text_area(
        "심볼 (쉼표로 구분)",
        value="AAPL, MSFT, GOOGL, AMZN, NVDA",
        help="예: AAPL, MSFT, GOOGL 또는 005930.KS, 000660.KS"
    )

    col1, col2 = st.columns(2)
    with col1:
        period = st.selectbox("분석 기간", ["1y", "2y", "3y", "5y"], index=1)
    with col2:
        risk_free = st.number_input("무위험 이자율 (%)", value=4.0, step=0.1) / 100

    if st.button("최적화 실행", type="primary"):
        symbols = [s.strip().upper() for s in symbols_input.split(",")]

        if len(symbols) < 2:
            st.error("최소 2개 종목이 필요합니다.")
            return

        with st.spinner("데이터 로드 및 최적화 중..."):
            optimizer = PortfolioOptimizer(risk_free_rate=risk_free)

            if not optimizer.load_data(symbols, period):
                st.error("데이터 로드 실패. 심볼을 확인하세요.")
                return

            # 최적화 실행
            max_sharpe = optimizer.optimize_max_sharpe()
            min_vol = optimizer.optimize_min_volatility()

            # 결과 표시
            st.markdown("---")
            st.markdown("### 최적화 결과")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 🎯 최대 샤프 비율")
                st.metric("예상 수익률", f"{max_sharpe.expected_return*100:.2f}%")
                st.metric("변동성", f"{max_sharpe.volatility*100:.2f}%")
                st.metric("샤프 비율", f"{max_sharpe.sharpe_ratio:.2f}")

                st.markdown("**비중:**")
                for sym, weight in sorted(max_sharpe.weights.items(),
                                          key=lambda x: x[1], reverse=True):
                    if weight > 0.01:
                        st.write(f"  - {sym}: {weight*100:.1f}%")

            with col2:
                st.markdown("#### 🛡️ 최소 변동성")
                st.metric("예상 수익률", f"{min_vol.expected_return*100:.2f}%")
                st.metric("변동성", f"{min_vol.volatility*100:.2f}%")
                st.metric("샤프 비율", f"{min_vol.sharpe_ratio:.2f}")

                st.markdown("**비중:**")
                for sym, weight in sorted(min_vol.weights.items(),
                                          key=lambda x: x[1], reverse=True):
                    if weight > 0.01:
                        st.write(f"  - {sym}: {weight*100:.1f}%")

            # 효율적 프론티어
            st.markdown("### 효율적 프론티어")
            try:
                frontier = optimizer.calculate_efficient_frontier(n_points=30)

                fig = go.Figure()

                # 프론티어 라인
                fig.add_trace(go.Scatter(
                    x=[p.volatility*100 for p in frontier],
                    y=[p.return_*100 for p in frontier],
                    mode='lines',
                    name='효율적 프론티어',
                    line=dict(color='blue', width=2)
                ))

                # 최대 샤프
                fig.add_trace(go.Scatter(
                    x=[max_sharpe.volatility*100],
                    y=[max_sharpe.expected_return*100],
                    mode='markers',
                    name='최대 샤프',
                    marker=dict(color='green', size=15, symbol='star')
                ))

                # 최소 변동성
                fig.add_trace(go.Scatter(
                    x=[min_vol.volatility*100],
                    y=[min_vol.expected_return*100],
                    mode='markers',
                    name='최소 변동성',
                    marker=dict(color='red', size=15, symbol='diamond')
                ))

                fig.update_layout(
                    title='효율적 프론티어',
                    xaxis_title='변동성 (%)',
                    yaxis_title='예상 수익률 (%)',
                    height=400
                )

                st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.warning(f"프론티어 계산 실패: {e}")

            # 상관관계
            st.markdown("### 상관관계 행렬")
            corr = optimizer.get_correlation_matrix()
            if not corr.empty:
                fig = px.imshow(corr, text_auto='.2f', color_continuous_scale='RdBu_r')
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)


def render_investment_journal():
    """투자 일지"""
    st.subheader("📝 투자 일지")

    if not JOURNAL_AVAILABLE:
        st.warning("투자 일지 모듈을 사용할 수 없습니다.")
        return

    tab1, tab2, tab3, tab4 = st.tabs(["📋 매매 일지", "📓 노트", "➕ 새 기록", "📊 분석"])

    with tab1:
        trades = investment_journal.get_trades(limit=30)

        if not trades:
            st.info("매매 기록이 없습니다.")
        else:
            for trade in trades:
                emotion_emoji = {
                    "confident": "💪",
                    "fomo": "😰",
                    "fear": "😨",
                    "greed": "🤑",
                    "calm": "😌"
                }.get(trade.emotion, "😐")

                type_emoji = "🟢" if trade.trade_type in ["buy", "add"] else "🔴"

                result_text = ""
                if trade.actual_result is not None:
                    result_text = f" → {trade.actual_result:+.2f}%"

                with st.expander(
                    f"{type_emoji} [{trade.date}] {trade.name} ({trade.symbol}) "
                    f"{emotion_emoji}{result_text}"
                ):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**유형:** {trade.trade_type}")
                        st.write(f"**수량:** {trade.quantity:,}주")
                        st.write(f"**가격:** ₩{trade.price:,.0f}")
                    with col2:
                        st.write(f"**감정:** {trade.emotion}")
                        st.write(f"**확신도:** {trade.confidence_level}/10")
                        if trade.target_price:
                            st.write(f"**목표가:** ₩{trade.target_price:,.0f}")

                    st.write(f"**매매 이유:** {trade.reason}")
                    if trade.thesis:
                        st.write(f"**투자 논거:** {trade.thesis}")
                    if trade.lessons_learned:
                        st.write(f"**교훈:** {trade.lessons_learned}")

    with tab2:
        notes = investment_journal.get_notes(limit=20)

        if not notes:
            st.info("노트가 없습니다.")
        else:
            for note in notes:
                with st.expander(f"[{note.date}] {note.title} ({note.category})"):
                    st.write(note.content)
                    if note.tags:
                        st.write(f"**태그:** {', '.join(note.tags)}")

    with tab3:
        st.markdown("### 새 매매 기록")

        col1, col2 = st.columns(2)
        with col1:
            new_symbol = st.text_input("심볼", key="j_symbol")
            new_name = st.text_input("종목명", key="j_name")
            new_type = st.selectbox(
                "유형",
                [("매수", "buy"), ("매도", "sell"), ("추가매수", "add"), ("일부매도", "reduce")],
                format_func=lambda x: x[0],
                key="j_type"
            )
        with col2:
            new_qty = st.number_input("수량", min_value=1, value=1, key="j_qty")
            new_price = st.number_input("가격", min_value=0.0, step=100.0, key="j_price")
            new_emotion = st.selectbox(
                "감정 상태",
                [("😌 침착", "calm"), ("💪 확신", "confident"), ("😰 FOMO", "fomo"),
                 ("😨 공포", "fear"), ("🤑 탐욕", "greed")],
                format_func=lambda x: x[0],
                key="j_emotion"
            )

        new_reason = st.text_area("매매 이유", key="j_reason")
        new_confidence = st.slider("확신도", 1, 10, 5, key="j_conf")

        if st.button("기록 추가", key="add_trade"):
            if new_symbol and new_price > 0:
                investment_journal.add_trade(
                    symbol=new_symbol.upper(),
                    name=new_name or new_symbol,
                    trade_type=new_type[1],
                    quantity=new_qty,
                    price=new_price,
                    reason=new_reason,
                    emotion=new_emotion[1],
                    confidence_level=new_confidence
                )
                st.success("기록이 추가되었습니다.")
                st.rerun()

        st.markdown("---")
        st.markdown("### 새 노트")

        note_title = st.text_input("제목", key="n_title")
        note_category = st.selectbox(
            "카테고리",
            [("분석", "analysis"), ("전략", "strategy"), ("아이디어", "idea"), ("학습", "learning")],
            format_func=lambda x: x[0],
            key="n_cat"
        )
        note_content = st.text_area("내용", key="n_content")

        if st.button("노트 추가", key="add_note"):
            if note_title and note_content:
                investment_journal.add_note(
                    title=note_title,
                    category=note_category[1],
                    content=note_content
                )
                st.success("노트가 추가되었습니다.")
                st.rerun()

    with tab4:
        st.markdown("### 감정 분석")
        analysis = investment_journal.get_emotion_analysis(months=6)

        if analysis:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("총 매매 수", analysis.get('total_trades', 0))
                st.metric("평균 확신도", f"{analysis.get('avg_confidence', 0):.1f}/10")

            with col2:
                st.markdown("**감정별 승률:**")
                for emotion, rate in analysis.get('emotion_win_rates', {}).items():
                    st.write(f"  - {emotion}: {rate:.1f}%")
        else:
            st.info("분석할 데이터가 없습니다.")


def render_financial_analysis():
    """재무제표 분석"""
    st.subheader("📈 재무제표 분석")

    if not FINANCIAL_AVAILABLE:
        st.warning("재무 분석 모듈을 사용할 수 없습니다.")
        return

    symbol = st.text_input("심볼 입력", placeholder="AAPL, 005930.KS 등", key="fin_symbol")

    if st.button("분석", key="analyze_fin") and symbol:
        with st.spinner("재무 데이터 분석 중..."):
            result = analyze_financials(symbol.upper())

            if not result:
                st.error("데이터를 찾을 수 없습니다.")
                return

            # 프로필
            st.markdown(f"### {result.name}")
            st.write(f"**섹터:** {result.profile.sector} | **산업:** {result.profile.industry}")
            st.write(f"**시가총액:** ${result.profile.market_cap/1e9:.1f}B")

            # 등급
            col1, col2, col3 = st.columns(3)
            with col1:
                grade_color = {"A": "green", "B": "blue", "C": "orange", "D": "red", "F": "darkred"}
                st.markdown(f"**밸류에이션 등급:** "
                           f"<span style='color:{grade_color.get(result.valuation_grade, 'gray')};font-size:24px;'>"
                           f"{result.valuation_grade}</span>", unsafe_allow_html=True)
            with col2:
                st.metric("재무 건강 점수", f"{result.health_score:.0f}/100")
            with col3:
                st.metric("ROE", f"{result.current_metrics.roe:.1f}%")

            # 지표
            st.markdown("### 주요 지표")
            col1, col2, col3, col4 = st.columns(4)

            m = result.current_metrics
            with col1:
                st.metric("PER", f"{m.per:.1f}")
                st.metric("PBR", f"{m.pbr:.1f}")
            with col2:
                st.metric("PSR", f"{m.psr:.1f}")
                st.metric("EV/EBITDA", f"{m.ev_ebitda:.1f}")
            with col3:
                st.metric("매출성장률", f"{m.revenue_growth:.1f}%")
                st.metric("순이익률", f"{m.net_margin:.1f}%")
            with col4:
                st.metric("부채비율", f"{m.debt_ratio:.0f}%")
                st.metric("배당수익률", f"{m.dividend_yield:.2f}%")

            # 동종업계 비교
            st.markdown("### 동종업계 비교")
            peers_df = financial_analyzer.compare_peers(symbol.upper())
            if not peers_df.empty:
                st.dataframe(peers_df, use_container_width=True, hide_index=True)


def render_etf_screener():
    """ETF 스크리너"""
    st.subheader("🔍 ETF 스크리너")

    if not ETF_AVAILABLE:
        st.warning("ETF 스크리너 모듈을 사용할 수 없습니다.")
        return

    tab1, tab2, tab3 = st.tabs(["🎯 테마별", "📊 비교", "🏆 랭킹"])

    with tab1:
        themes = etf_screener.get_themes()
        selected_theme = st.selectbox("테마 선택", themes)

        if st.button("검색", key="search_theme"):
            with st.spinner("검색 중..."):
                etfs = etf_screener.screen_by_theme(selected_theme)

                if etfs:
                    df = pd.DataFrame([
                        {
                            "심볼": e.symbol,
                            "이름": e.name[:25],
                            "비용(%)": f"{e.expense_ratio:.2f}",
                            "AUM($B)": f"{e.aum/1e9:.1f}",
                            "YTD(%)": f"{e.ytd_return:+.1f}",
                            "1Y(%)": f"{e.one_year_return:+.1f}",
                            "배당(%)": f"{e.yield_:.2f}"
                        }
                        for e in etfs
                    ])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("결과가 없습니다.")

    with tab2:
        etf_input = st.text_area(
            "비교할 ETF (쉼표 구분)",
            value="SPY, QQQ, VTI, IWM",
            key="etf_compare"
        )

        if st.button("비교", key="compare_etfs"):
            symbols = [s.strip().upper() for s in etf_input.split(",")]

            with st.spinner("비교 중..."):
                comparison = etf_screener.compare_etfs(symbols, period="1y")

                if comparison.etfs:
                    # 기본 정보
                    df = pd.DataFrame([
                        {
                            "심볼": e.symbol,
                            "이름": e.name[:20],
                            "비용(%)": f"{e.expense_ratio:.2f}",
                            "YTD(%)": f"{e.ytd_return:+.1f}",
                            "1Y(%)": f"{e.one_year_return:+.1f}"
                        }
                        for e in comparison.etfs
                    ])
                    st.dataframe(df, use_container_width=True, hide_index=True)

                    # 성과 차트
                    if comparison.performance_data is not None:
                        st.markdown("### 성과 비교")
                        fig = px.line(comparison.performance_data, title="누적 수익률 (%)")
                        st.plotly_chart(fig, use_container_width=True)

                    # 상관관계
                    if comparison.correlation_matrix is not None:
                        st.markdown("### 상관관계")
                        fig = px.imshow(comparison.correlation_matrix,
                                        text_auto='.2f', color_continuous_scale='RdBu_r')
                        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        ranking_type = st.selectbox(
            "랭킹 유형",
            [("YTD 수익률", "ytd"), ("1년 수익률", "1y"), ("저비용", "low_cost"), ("고배당", "dividend")],
            format_func=lambda x: x[0],
            key="ranking_type"
        )

        if st.button("랭킹 조회", key="get_ranking"):
            with st.spinner("조회 중..."):
                if ranking_type[1] == "low_cost":
                    etfs = etf_screener.get_low_cost_etfs(limit=15)
                elif ranking_type[1] == "dividend":
                    etfs = etf_screener.get_high_dividend_etfs(limit=15)
                else:
                    etfs = etf_screener.get_best_performers(period=ranking_type[1], limit=15)

                if etfs:
                    df = pd.DataFrame([
                        {
                            "순위": i+1,
                            "심볼": e.symbol,
                            "이름": e.name[:25],
                            "비용(%)": f"{e.expense_ratio:.2f}",
                            "YTD(%)": f"{e.ytd_return:+.1f}",
                            "배당(%)": f"{e.yield_:.2f}"
                        }
                        for i, e in enumerate(etfs)
                    ])
                    st.dataframe(df, use_container_width=True, hide_index=True)


def render_advanced_analysis_page():
    """고급 분석 페이지"""
    st.title("🔬 고급 분석")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 포트폴리오 최적화",
        "📝 투자 일지",
        "📈 재무 분석",
        "🔍 ETF 스크리너"
    ])

    with tab1:
        render_portfolio_optimization()

    with tab2:
        render_investment_journal()

    with tab3:
        render_financial_analysis()

    with tab4:
        render_etf_screener()
