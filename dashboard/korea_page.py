"""
한국 주식 대시보드 페이지
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from korea.krx_data import KRXDataCollector
from korea.korean_stocks import KoreanStockAnalyzer
from korea.bok_indicators import BOKIndicators


def create_candlestick_chart(df: pd.DataFrame, title: str):
    """캔들스틱 차트"""
    fig = go.Figure(data=[go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name='가격'
    )])

    # 이동평균 추가
    if len(df) >= 20:
        ma20 = df['Close'].rolling(20).mean()
        fig.add_trace(go.Scatter(
            x=df.index, y=ma20,
            mode='lines', name='MA20',
            line=dict(color='orange', width=1)
        ))

    if len(df) >= 60:
        ma60 = df['Close'].rolling(60).mean()
        fig.add_trace(go.Scatter(
            x=df.index, y=ma60,
            mode='lines', name='MA60',
            line=dict(color='purple', width=1)
        ))

    fig.update_layout(
        title=title,
        yaxis_title='가격',
        xaxis_title='날짜',
        height=400,
        xaxis_rangeslider_visible=False
    )

    return fig


def create_volume_chart(df: pd.DataFrame):
    """거래량 차트"""
    colors = ['red' if df['Close'].iloc[i] < df['Open'].iloc[i] else 'green'
              for i in range(len(df))]

    fig = go.Figure(data=[go.Bar(
        x=df.index,
        y=df['Volume'],
        marker_color=colors,
        name='거래량'
    )])

    fig.update_layout(
        title='거래량',
        yaxis_title='거래량',
        height=200
    )

    return fig


def render_korea_page():
    """한국 주식 페이지 렌더링"""
    st.header("🇰🇷 한국 주식")

    # 모듈 초기화
    krx = KRXDataCollector()
    analyzer = KoreanStockAnalyzer()
    bok = BOKIndicators()

    # 상태 표시
    col1, col2, col3 = st.columns(3)

    with col1:
        if krx.enabled:
            st.success("✅ KRX 데이터 연결됨")
        else:
            st.warning("⚠️ pykrx 미설치 (샘플 데이터 사용)")

    with col2:
        if bok.enabled:
            st.success("✅ BOK API 연결됨")
        else:
            st.info("ℹ️ BOK API 미설정")

    with col3:
        st.info(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    st.divider()

    # 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 시장 현황",
        "🔍 종목 분석",
        "💹 경제 지표",
        "📋 종목 비교"
    ])

    # ========== 탭 1: 시장 현황 ==========
    with tab1:
        st.subheader("시장 현황")

        # 지수 요약
        market_summary = krx.get_market_summary()

        col1, col2 = st.columns(2)

        with col1:
            for market, data in market_summary.items():
                change_emoji = '🔺' if data['change'] > 0 else ('🔻' if data['change'] < 0 else '➖')
                delta_color = "normal" if data['change'] >= 0 else "inverse"

                st.metric(
                    label=market,
                    value=f"{data['close']:,.2f}",
                    delta=f"{data['change_pct']:+.2f}%",
                    delta_color=delta_color
                )

        with col2:
            # 지수 차트
            index_name = st.selectbox("지수 선택", ['KOSPI', 'KOSDAQ', 'KOSPI200'])
            index_data = krx.get_index_data(index_name, days=60)

            if not index_data.empty:
                chart = create_candlestick_chart(index_data, f"{index_name} 차트")
                st.plotly_chart(chart, use_container_width=True)

        st.divider()

        # 섹터 성과
        st.subheader("섹터별 성과 (1개월)")
        sector_perf = krx.get_sector_performance()

        if sector_perf:
            sector_df = pd.DataFrame([
                {'섹터': name, '수익률': data['change_1m']}
                for name, data in sector_perf.items()
            ])
            sector_df = sector_df.sort_values('수익률', ascending=False)

            # 막대 차트
            colors = ['green' if x > 0 else 'red' for x in sector_df['수익률']]

            fig = go.Figure(data=[go.Bar(
                x=sector_df['섹터'],
                y=sector_df['수익률'],
                marker_color=colors
            )])

            fig.update_layout(
                title='섹터별 월간 수익률',
                yaxis_title='수익률 (%)',
                height=300
            )

            st.plotly_chart(fig, use_container_width=True)

        # 외국인 매매 동향
        st.subheader("외국인 매매 동향")
        foreign_df = krx.get_foreign_investor_trading()

        if not foreign_df.empty:
            st.dataframe(foreign_df.head(10), use_container_width=True)

    # ========== 탭 2: 종목 분석 ==========
    with tab2:
        st.subheader("종목 분석")

        # 종목 검색
        col1, col2 = st.columns([2, 1])

        with col1:
            search_query = st.text_input("종목 검색 (코드 또는 이름)", "삼성전자")

        with col2:
            if st.button("🔍 검색"):
                results = krx.search_stock(search_query)
                if results:
                    st.session_state.search_results = results

        # 검색 결과
        if 'search_results' in st.session_state and st.session_state.search_results:
            selected = st.selectbox(
                "종목 선택",
                st.session_state.search_results,
                format_func=lambda x: f"{x['name']} ({x['code']}) - {x['market']}"
            )

            if selected:
                stock_code = selected['code']
            else:
                stock_code = '005930'  # 삼성전자 기본값
        else:
            stock_code = st.text_input("종목 코드 직접 입력", "005930")

        if st.button("📊 분석 실행", key="analyze_stock"):
            with st.spinner("종목 분석 중..."):
                analysis = analyzer.analyze_stock(stock_code)

                # 기본 정보
                st.markdown(f"### {analysis.name} ({analysis.code})")

                # 점수 표시
                score_color = 'green' if analysis.score >= 60 else ('orange' if analysis.score >= 40 else 'red')
                st.markdown(f"**종합 점수**: <span style='color:{score_color}; font-size:24px;'>{analysis.score}/100</span> | **추천**: {analysis.recommendation}", unsafe_allow_html=True)

                st.divider()

                # 3열 레이아웃
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown("**📊 펀더멘털**")
                    fund = analysis.fundamentals
                    st.metric("현재가", f"{fund.price:,.0f}원")
                    st.metric("시가총액", f"{fund.market_cap/1e12:.1f}조원")
                    st.metric("PER", f"{fund.per:.1f}" if fund.per else "N/A")
                    st.metric("PBR", f"{fund.pbr:.2f}" if fund.pbr else "N/A")
                    st.metric("배당수익률", f"{fund.dividend_yield:.1f}%" if fund.dividend_yield else "N/A")

                with col2:
                    st.markdown("**📈 기술적 분석**")
                    tech = analysis.technical
                    st.metric("추세", tech.get('trend', 'N/A'))
                    st.metric("RSI", f"{tech.get('rsi', 0):.1f}")
                    st.metric("MA20", f"{tech.get('ma_20', 0):,.0f}원")
                    st.metric("1주 수익률", f"{tech.get('change_1w', 0):+.1f}%")
                    st.metric("1개월 수익률", f"{tech.get('change_1m', 0):+.1f}%")

                with col3:
                    st.markdown("**💹 수급 동향**")
                    inv = analysis.foreign_trend
                    st.metric("수급 상태", inv.get('trend', 'N/A'))

                    foreign_5d = inv.get('foreign_5d', 0)
                    inst_5d = inv.get('institution_5d', 0)

                    st.metric("외국인 5일",
                             f"{foreign_5d/1e8:+,.0f}억원" if foreign_5d else "N/A")
                    st.metric("기관 5일",
                             f"{inst_5d/1e8:+,.0f}억원" if inst_5d else "N/A")

                # 신호
                st.markdown("**🚦 기술적 신호**")
                signals = tech.get('signals', [])
                for signal in signals:
                    if '매수' in signal or '과매도' in signal:
                        st.success(f"🟢 {signal}")
                    elif '매도' in signal or '과매수' in signal:
                        st.error(f"🔴 {signal}")
                    else:
                        st.info(f"🟡 {signal}")

                # 차트
                st.divider()
                st.subheader("가격 차트")

                price_data = krx.get_stock_price(stock_code)
                if not price_data.empty:
                    chart = create_candlestick_chart(price_data.tail(60), f"{analysis.name} 일봉")
                    st.plotly_chart(chart, use_container_width=True)

                    vol_chart = create_volume_chart(price_data.tail(60))
                    st.plotly_chart(vol_chart, use_container_width=True)

    # ========== 탭 3: 경제 지표 ==========
    with tab3:
        st.subheader("한국 경제 지표")

        # API 키 설정
        with st.expander("🔑 한국은행 API 키 설정"):
            bok_key = st.text_input("BOK API Key", type="password",
                                    help="한국은행 경제통계시스템에서 발급받을 수 있습니다.",
                                    key="bok_api_key_input")
            if st.button("API 키 적용", key="bok_api_apply"):
                if bok_key:
                    os.environ['BOK_API_KEY'] = bok_key
                    st.success("BOK API 키가 적용되었습니다.")
                    st.rerun()

        if st.button("📊 경제 리포트 생성", key="bok_report_btn"):
            with st.spinner("경제 지표를 분석하고 있습니다..."):
                report = bok.get_korean_economy_report()
                st.text(report)

        st.divider()

        # 개별 지표 조회
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📈 주요 경제 지표")
            summary = bok.get_economic_summary()

            for name, indicator in summary.items():
                trend_emoji = '🔺' if indicator.trend == '상승' else ('🔻' if indicator.trend == '하락' else '➖')
                st.metric(
                    label=indicator.name,
                    value=f"{indicator.value:,.2f}{indicator.unit}",
                    delta=f"{indicator.change:+.2f}" if indicator.change else None
                )

        with col2:
            st.subheader("💱 환율")
            rates = bok.get_exchange_rates()

            for key, value in rates.items():
                currency_names = {
                    'usd_krw': '🇺🇸 USD/KRW',
                    'eur_krw': '🇪🇺 EUR/KRW',
                    'jpy_krw': '🇯🇵 JPY/KRW (100엔)',
                    'cny_krw': '🇨🇳 CNY/KRW',
                }
                st.metric(currency_names.get(key, key), f"{value:,.2f}원")

        st.divider()

        # 상세 분석
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("물가 분석")
            inflation = bok.get_inflation_analysis()

            st.metric("CPI (전년비)", f"{inflation['cpi_yoy']:+.1f}%")
            st.metric("CPI (전월비)", f"{inflation['cpi_mom']:+.1f}%")
            st.metric("PPI (전년비)", f"{inflation['ppi_yoy']:+.1f}%")
            st.info(f"**추세**: {inflation['trend']}")
            st.write(f"**전망**: {inflation['outlook']}")

        with col2:
            st.subheader("금리 분석")
            rates_analysis = bok.get_interest_rate_analysis()

            st.metric("기준금리", f"{rates_analysis['base_rate']}%")
            st.metric("국고채 3년", f"{rates_analysis['treasury_3y']}%")
            st.metric("국고채 10년", f"{rates_analysis['treasury_10y']}%")
            st.metric("장단기 스프레드", f"{rates_analysis['spread_10y_3y']:+.2f}%p")

            curve_color = 'red' if rates_analysis['curve_shape'] == '역전' else 'green'
            st.markdown(f"**수익률 곡선**: <span style='color:{curve_color}'>{rates_analysis['curve_shape']}</span>", unsafe_allow_html=True)
            st.write(f"**신호**: {rates_analysis['curve_signal']}")

        # 경기 사이클
        st.divider()
        st.subheader("🔄 경기 사이클")
        cycle = bok.get_economic_cycle_indicator()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("선행지수", f"{cycle['leading_index']:.1f}",
                     delta=f"{cycle['leading_trend']:+.1f}%")

        with col2:
            st.metric("동행지수", f"{cycle['coincident_index']:.1f}",
                     delta=f"{cycle['coincident_trend']:+.1f}%")

        with col3:
            phase_colors = {
                '확장': 'green',
                '회복': 'lightgreen',
                '후퇴': 'orange',
                '수축': 'red',
                '전환': 'gray'
            }
            st.markdown(f"**경기 국면**: <span style='color:{phase_colors.get(cycle['phase'], 'gray')}; font-size:20px;'>{cycle['phase']}</span>", unsafe_allow_html=True)
            st.write(cycle['description'])

    # ========== 탭 4: 종목 비교 ==========
    with tab4:
        st.subheader("종목 비교 분석")

        # 종목 입력
        stocks_input = st.text_area(
            "비교할 종목 코드 (쉼표로 구분)",
            "005930, 000660, 035420, 035720, 051910",
            help="예: 005930, 000660, 035420"
        )

        if st.button("📊 비교 분석", key="compare_stocks"):
            codes = [c.strip() for c in stocks_input.split(',')]

            with st.spinner("종목 비교 분석 중..."):
                comparison_df = analyzer.compare_stocks(codes)

                # 테이블 표시
                st.dataframe(comparison_df, use_container_width=True, hide_index=True)

                # 점수 차트
                fig = go.Figure(data=[go.Bar(
                    x=comparison_df['종목명'],
                    y=comparison_df['점수'],
                    marker_color=['green' if s >= 60 else 'orange' if s >= 40 else 'red'
                                 for s in comparison_df['점수']]
                )])

                fig.update_layout(
                    title='종목별 종합 점수',
                    yaxis_title='점수',
                    height=300
                )

                st.plotly_chart(fig, use_container_width=True)

        # 일일 리포트
        st.divider()
        st.subheader("📋 일일 리포트")

        watchlist = st.text_input(
            "관심 종목 코드",
            "005930, 000660, 035420",
            help="일일 리포트를 받을 종목 코드"
        )

        if st.button("📝 리포트 생성", key="daily_report"):
            codes = [c.strip() for c in watchlist.split(',')]

            with st.spinner("리포트 생성 중..."):
                report = analyzer.get_daily_report(codes)
                st.text(report)


if __name__ == "__main__":
    render_korea_page()
