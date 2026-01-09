"""
AI 어시스턴트 & 소셜 센티먼트 대시보드 페이지
"""

import streamlit as st
from datetime import datetime


def render_ai_chat():
    """AI 채팅 UI"""
    st.subheader("🤖 AI 투자 어시스턴트")

    try:
        from ai_analysis.ai_assistant import ai_assistant

        if not ai_assistant.is_available():
            st.warning("OpenAI API 키가 설정되지 않았습니다.")
            st.info("`.env` 파일에 `OPENAI_API_KEY`를 설정하세요.")

            with st.expander("API 키 직접 입력"):
                api_key = st.text_input("OpenAI API Key", type="password")
                if api_key and st.button("연결"):
                    ai_assistant.api_key = api_key
                    from openai import OpenAI
                    ai_assistant.client = OpenAI(api_key=api_key)
                    st.success("API 연결 완료!")
                    st.rerun()
            return

        # 대화 이력 초기화
        if 'ai_messages' not in st.session_state:
            st.session_state.ai_messages = []

        # 대화 이력 표시
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.ai_messages:
                if msg['role'] == 'user':
                    st.chat_message("user").write(msg['content'])
                else:
                    st.chat_message("assistant").write(msg['content'])

        # 빠른 질문 버튼
        st.markdown("#### 빠른 질문")
        col1, col2, col3 = st.columns(3)

        quick_questions = [
            ("📊 포트폴리오 분석", "현재 포트폴리오를 분석해주세요."),
            ("📈 시장 전망", "현재 시장 전망은 어떤가요?"),
            ("💡 투자 조언", "지금 어떤 투자 전략이 좋을까요?"),
        ]

        for i, (label, question) in enumerate(quick_questions):
            col = [col1, col2, col3][i]
            with col:
                if st.button(label, key=f"quick_{i}"):
                    st.session_state.pending_question = question

        # 입력창
        user_input = st.chat_input("투자에 대해 질문하세요...")

        # 빠른 질문 처리
        if hasattr(st.session_state, 'pending_question'):
            user_input = st.session_state.pending_question
            del st.session_state.pending_question

        if user_input:
            # 사용자 메시지 추가
            st.session_state.ai_messages.append({
                'role': 'user',
                'content': user_input
            })

            # 컨텍스트 구성
            context = {}
            if 'portfolio' in st.session_state and st.session_state.portfolio.positions:
                portfolio = st.session_state.portfolio
                total_value = sum(p.current_price * p.quantity for p in portfolio.positions)
                context = {
                    'portfolio_value': total_value,
                    'positions': len(portfolio.positions)
                }

            # AI 응답
            with st.spinner("생각 중..."):
                response = ai_assistant.chat(user_input, context)

            # 응답 추가
            st.session_state.ai_messages.append({
                'role': 'assistant',
                'content': response
            })

            st.rerun()

        # 초기화 버튼
        if st.session_state.ai_messages:
            if st.button("대화 초기화"):
                st.session_state.ai_messages = []
                ai_assistant.clear_history()
                st.rerun()

    except Exception as e:
        st.error(f"AI 어시스턴트 오류: {e}")


def render_stock_analysis():
    """AI 종목 분석 UI"""
    st.subheader("📈 AI 종목 분석")

    try:
        from ai_analysis.ai_assistant import ai_assistant

        if not ai_assistant.is_available():
            st.warning("OpenAI API 키가 필요합니다.")
            return

        symbol = st.text_input("종목 코드", value="005930.KS", key="ai_stock")

        if st.button("AI 분석 요청"):
            with st.spinner("AI가 분석 중..."):
                # 기본 데이터 수집
                try:
                    import yfinance as yf
                    ticker = yf.Ticker(symbol)
                    info = ticker.info

                    stock_data = {
                        'name': info.get('shortName', symbol),
                        'price': info.get('currentPrice', 0),
                        'per': info.get('trailingPE', 0),
                        'pbr': info.get('priceToBook', 0),
                        'roe': (info.get('returnOnEquity', 0) or 0) * 100,
                        'operating_margin': (info.get('operatingMargins', 0) or 0) * 100,
                        'debt_ratio': info.get('debtToEquity', 0),
                    }
                except Exception:
                    stock_data = {'name': symbol}

                result = ai_assistant.analyze_stock(symbol, stock_data)

            # 결과 표시
            st.markdown("---")
            st.markdown(f"### {result.symbol} 분석 결과")

            col1, col2 = st.columns([2, 1])
            with col1:
                st.markdown("**요약**")
                st.write(result.summary)

            with col2:
                rec_color = {
                    '매수': 'green',
                    '매도': 'red',
                    '중립': 'gray'
                }.get(result.recommendation, 'gray')
                st.markdown(f"**투자 의견**: <span style='color:{rec_color};font-size:1.5em'>{result.recommendation}</span>",
                           unsafe_allow_html=True)
                st.metric("신뢰도", f"{result.confidence:.0f}%")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**💪 강점**")
                for s in result.strengths:
                    st.write(f"✅ {s}")

            with col2:
                st.markdown("**⚠️ 약점/리스크**")
                for w in result.weaknesses:
                    st.write(f"❌ {w}")

    except Exception as e:
        st.error(f"종목 분석 오류: {e}")


def render_social_sentiment():
    """소셜 센티먼트 UI"""
    st.subheader("📱 소셜 센티먼트")

    try:
        from analysis.social_sentiment import social_analyzer

        # 단일 종목 분석
        col1, col2 = st.columns([2, 1])
        with col1:
            stock_code = st.text_input("종목 코드 (6자리)", value="005930", key="social_code")
            stock_name = st.text_input("종목명", value="삼성전자", key="social_name")
        with col2:
            st.write("")
            st.write("")
            analyze_btn = st.button("센티먼트 분석")

        if analyze_btn:
            with st.spinner("소셜 데이터 수집 중..."):
                result = social_analyzer.analyze_stock_sentiment(stock_code, stock_name)

            # 결과 표시
            st.markdown("---")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("총 게시글", f"{result.total_posts}개")
            with col2:
                color = "normal" if result.sentiment_score >= 0 else "inverse"
                st.metric("센티먼트 점수", f"{result.sentiment_score:+.1f}",
                         delta_color=color)
            with col3:
                trend_icon = {'rising': '📈', 'falling': '📉', 'stable': '➡️'}.get(result.trend, '➡️')
                st.metric("트렌드", trend_icon)
            with col4:
                bias = social_analyzer.get_bullish_bearish_ratio(stock_code)
                st.metric("강세/약세", bias['bias'])

            # 감성 분포
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**감성 분포**")
                st.progress(result.positive_ratio / 100, text=f"🟢 긍정 {result.positive_ratio:.1f}%")
                st.progress(result.neutral_ratio / 100, text=f"⚪ 중립 {result.neutral_ratio:.1f}%")
                st.progress(result.negative_ratio / 100, text=f"🔴 부정 {result.negative_ratio:.1f}%")

            with col2:
                st.markdown("**핫 키워드**")
                if result.hot_keywords:
                    for kw in result.hot_keywords[:10]:
                        st.write(f"#{kw}")
                else:
                    st.info("키워드 없음")

        # 포트폴리오 전체 분석
        st.markdown("---")
        st.markdown("#### 포트폴리오 센티먼트")

        if 'portfolio' in st.session_state and st.session_state.portfolio.positions:
            if st.button("전체 종목 분석"):
                positions = [{'symbol': p.symbol, 'name': p.name}
                            for p in st.session_state.portfolio.positions]

                with st.spinner("포트폴리오 센티먼트 분석 중..."):
                    results = social_analyzer.analyze_portfolio_sentiment(positions)

                for r in results:
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.write(f"**{r.name}**")
                    with col2:
                        score_color = 'green' if r.sentiment_score > 0 else ('red' if r.sentiment_score < 0 else 'gray')
                        st.markdown(f"<span style='color:{score_color}'>{r.sentiment_score:+.1f}</span>",
                                   unsafe_allow_html=True)
                    with col3:
                        trend_icon = {'rising': '📈', 'falling': '📉', 'stable': '➡️'}.get(r.trend, '➡️')
                        st.write(trend_icon)
        else:
            st.info("포트폴리오에 종목을 추가하면 전체 분석이 가능합니다.")

        # 시장 분위기
        st.markdown("---")
        st.markdown("#### 시장 전반 분위기")

        if st.button("시장 분위기 조회"):
            with st.spinner("시장 데이터 수집 중..."):
                mood = social_analyzer.get_market_mood()

            st.metric("전반적 관심도", mood['overall_interest'].upper())

            for detail in mood['details']:
                col1, col2 = st.columns([1, 3])
                with col1:
                    interest_icon = {'high': '🔥', 'medium': '📊', 'low': '💤'}.get(detail['interest'], '📊')
                    st.write(f"{interest_icon} **{detail['keyword']}**")
                with col2:
                    if detail['related']:
                        st.write(f"연관: {', '.join(detail['related'])}")

    except Exception as e:
        st.error(f"센티먼트 분석 오류: {e}")


def render_news_summary():
    """뉴스 요약 UI"""
    st.subheader("📰 AI 뉴스 요약")

    try:
        from ai_analysis.ai_assistant import ai_assistant
        from alerts.news_monitor import news_monitor

        if not ai_assistant.is_available():
            st.warning("OpenAI API 키가 필요합니다.")
            return

        if 'portfolio' not in st.session_state or not st.session_state.portfolio.positions:
            st.info("포트폴리오에 종목을 추가하면 관련 뉴스를 요약합니다.")
            return

        if st.button("뉴스 수집 및 요약"):
            symbols = [{'symbol': p.symbol, 'name': p.name}
                      for p in st.session_state.portfolio.positions]

            with st.spinner("뉴스 수집 중..."):
                news_items = news_monitor.get_portfolio_news(symbols)

            if not news_items:
                st.info("최근 뉴스가 없습니다.")
                return

            # 뉴스 목록 표시
            st.markdown("**수집된 뉴스**")
            news_data = [{'title': n.title, 'source': n.source}
                        for n in news_items[:10]]

            for item in news_data:
                st.write(f"• {item['title']} ({item['source']})")

            # AI 요약
            with st.spinner("AI가 뉴스를 분석 중..."):
                summary = ai_assistant.summarize_news(news_data)

            st.markdown("---")
            st.markdown("**AI 뉴스 요약**")
            st.write(summary)

    except Exception as e:
        st.error(f"뉴스 요약 오류: {e}")


def render_ai_sentiment_page():
    """AI & 센티먼트 메인 페이지"""
    st.title("🧠 AI & 센티먼트 분석")

    tab1, tab2, tab3, tab4 = st.tabs([
        "💬 AI 채팅", "📈 종목 분석", "📱 소셜 센티먼트", "📰 뉴스 요약"
    ])

    with tab1:
        render_ai_chat()

    with tab2:
        render_stock_analysis()

    with tab3:
        render_social_sentiment()

    with tab4:
        render_news_summary()
