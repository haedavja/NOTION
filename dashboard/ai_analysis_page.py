"""
AI 분석 대시보드 페이지
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_analysis.gpt_analyzer import GPTAnalyzer
from ai_analysis.market_analyst import AIMarketAnalyst
from ai_analysis.news_summarizer import AINewsSummarizer


def render_ai_analysis_page():
    """AI 분석 페이지 렌더링"""
    st.header("🤖 AI 분석")

    # API 상태 확인
    gpt = GPTAnalyzer()
    market_analyst = AIMarketAnalyst()
    news_summarizer = AINewsSummarizer()

    # 상태 표시
    status_col1, status_col2, status_col3 = st.columns(3)

    with status_col1:
        if gpt.enabled:
            st.success("✅ GPT API 연결됨")
        else:
            st.warning("⚠️ GPT API 미설정")

    with status_col2:
        if news_summarizer.news_api_key:
            st.success("✅ News API 연결됨")
        else:
            st.info("ℹ️ News API 미설정 (RSS 사용)")

    with status_col3:
        st.info(f"모델: {gpt.model}")

    # API 키 설정
    with st.expander("🔑 API 키 설정"):
        openai_key = st.text_input("OpenAI API Key", type="password",
                                   help="GPT 분석을 위해 필요합니다.",
                                   key="openai_api_key_input")
        news_key = st.text_input("News API Key", type="password",
                                 help="더 많은 뉴스 소스를 위해 선택적으로 사용됩니다.",
                                 key="news_api_key_input")

        if st.button("API 키 적용", key="ai_api_apply"):
            if openai_key:
                os.environ['OPENAI_API_KEY'] = openai_key
                st.success("OpenAI API 키가 적용되었습니다.")
                st.rerun()
            if news_key:
                os.environ['NEWS_API_KEY'] = news_key
                st.success("News API 키가 적용되었습니다.")

    st.divider()

    # 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 시장 분석",
        "📰 뉴스 요약",
        "💬 AI 채팅",
        "📋 투자 아이디어"
    ])

    # ========== 탭 1: 시장 분석 ==========
    with tab1:
        st.subheader("AI 시장 분석")

        if st.button("🔄 시장 분석 실행", key="market_analysis"):
            with st.spinner("AI가 시장을 분석하고 있습니다..."):
                if gpt.enabled:
                    result = market_analyst.analyze_market()

                    if result and result.raw_analysis:
                        st.markdown("### 📈 분석 결과")
                        st.markdown(result.raw_analysis)

                        # 요약 정보
                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown("**🎯 기회 요인**")
                            for opp in result.opportunities[:5]:
                                st.write(f"• {opp}")

                        with col2:
                            st.markdown("**📌 권장사항**")
                            for rec in result.recommendations[:5]:
                                st.write(f"• {rec}")
                    else:
                        # 규칙 기반 분석
                        st.info("GPT 분석을 사용할 수 없어 규칙 기반 분석을 표시합니다.")
                        briefing = market_analyst.get_daily_briefing()
                        st.text(briefing)
                else:
                    # 규칙 기반
                    briefing = market_analyst.get_daily_briefing()
                    st.text(briefing)
                    st.info("💡 OpenAI API 키를 설정하면 더 상세한 AI 분석을 받을 수 있습니다.")

        # 개별 종목 분석
        st.divider()
        st.subheader("개별 종목 AI 분석")

        stock_symbol = st.text_input("종목 코드 입력", "AAPL",
                                     help="예: AAPL, MSFT, GOOGL, NVDA")

        if st.button("종목 분석", key="stock_analysis"):
            if gpt.enabled:
                with st.spinner(f"{stock_symbol} 분석 중..."):
                    analysis = market_analyst.analyze_specific_stock(stock_symbol)
                    if analysis:
                        st.markdown(analysis)
                    else:
                        st.error("분석에 실패했습니다.")
            else:
                st.warning("종목 AI 분석을 위해 OpenAI API 키가 필요합니다.")

    # ========== 탭 2: 뉴스 요약 ==========
    with tab2:
        st.subheader("AI 뉴스 요약")

        col1, col2 = st.columns([2, 1])

        with col1:
            news_topic = st.text_input("뉴스 주제 (선택)", "",
                                       help="특정 주제를 입력하거나 비워두면 전체 금융 뉴스를 분석합니다.")

        with col2:
            st.write("")  # 정렬용

        if st.button("📰 뉴스 분석", key="news_analysis"):
            with st.spinner("뉴스를 수집하고 분석하고 있습니다..."):
                if news_topic:
                    summary = news_summarizer.get_topic_news(news_topic)
                else:
                    summary = news_summarizer.summarize()

                # 감정 이모지
                sentiment_emoji = {
                    'bullish': '🟢 긍정적',
                    'bearish': '🔴 부정적',
                    'neutral': '⚪ 중립',
                }

                # 요약 표시
                st.markdown(f"### 시장 심리: {sentiment_emoji.get(summary.sentiment, '⚪')}")
                st.markdown(f"**분석 소스**: {summary.source_count}개 | **분석 시각**: {summary.timestamp.strftime('%Y-%m-%d %H:%M')}")

                st.divider()

                # 주요 헤드라인
                st.markdown("### 📌 주요 헤드라인")
                for i, headline in enumerate(summary.headlines[:5], 1):
                    st.write(f"{i}. {headline}")

                # 핵심 주제
                if summary.key_topics:
                    st.markdown(f"**🔑 핵심 주제**: {', '.join(summary.key_topics)}")

                # 시장 영향
                st.markdown(f"**💹 시장 영향**: {summary.market_impact}")

                # 전체 요약
                st.divider()
                st.markdown("### 📝 분석 요약")
                st.markdown(summary.summary)

        # 일일 다이제스트
        st.divider()
        if st.button("📋 일일 뉴스 다이제스트", key="daily_digest"):
            with st.spinner("다이제스트 생성 중..."):
                digest = news_summarizer.get_daily_digest()
                st.text(digest)

    # ========== 탭 3: AI 채팅 ==========
    with tab3:
        st.subheader("💬 AI 투자 상담")

        if not gpt.enabled:
            st.warning("AI 채팅을 위해 OpenAI API 키를 설정해주세요.")
        else:
            # 역할 선택
            role = st.selectbox(
                "AI 역할 선택",
                [
                    ("market_analyst", "📊 시장 분석가"),
                    ("portfolio_advisor", "💼 포트폴리오 자문가"),
                    ("thesis_evaluator", "🎯 투자 논리 평가자"),
                    ("news_analyst", "📰 뉴스 분석가"),
                ],
                format_func=lambda x: x[1]
            )

            # 채팅 히스토리 (세션 상태)
            if 'chat_history' not in st.session_state:
                st.session_state.chat_history = []

            # 채팅 히스토리 표시
            for msg in st.session_state.chat_history:
                if msg['role'] == 'user':
                    st.chat_message("user").write(msg['content'])
                else:
                    st.chat_message("assistant").write(msg['content'])

            # 사용자 입력
            user_input = st.chat_input("질문을 입력하세요...")

            if user_input:
                # 사용자 메시지 추가
                st.session_state.chat_history.append({
                    'role': 'user',
                    'content': user_input
                })
                st.chat_message("user").write(user_input)

                # AI 응답
                with st.spinner("AI가 답변을 생성하고 있습니다..."):
                    response = gpt.chat(user_input, role=role[0])

                    if response:
                        st.session_state.chat_history.append({
                            'role': 'assistant',
                            'content': response
                        })
                        st.chat_message("assistant").write(response)
                    else:
                        st.error("응답을 생성하지 못했습니다.")

            # 채팅 초기화
            if st.button("🗑️ 대화 초기화"):
                st.session_state.chat_history = []
                st.rerun()

    # ========== 탭 4: 투자 아이디어 ==========
    with tab4:
        st.subheader("💡 AI 투자 아이디어")

        if not gpt.enabled:
            st.warning("투자 아이디어 생성을 위해 OpenAI API 키를 설정해주세요.")
        else:
            # 투자 선호도
            st.markdown("**투자 선호도 설정 (선택)**")

            col1, col2 = st.columns(2)

            with col1:
                risk_tolerance = st.select_slider(
                    "위험 선호도",
                    options=['매우 보수적', '보수적', '중립', '공격적', '매우 공격적'],
                    value='중립'
                )

                investment_horizon = st.selectbox(
                    "투자 기간",
                    ['단기 (1-3개월)', '중기 (3-12개월)', '장기 (1년 이상)']
                )

            with col2:
                sectors = st.multiselect(
                    "관심 섹터",
                    ['기술', '헬스케어', '금융', '에너지', '소비재', '산업', '유틸리티'],
                    default=['기술']
                )

                exclude_sectors = st.multiselect(
                    "제외 섹터",
                    ['기술', '헬스케어', '금융', '에너지', '소비재', '산업', '유틸리티']
                )

            if st.button("💡 아이디어 생성", key="generate_ideas"):
                with st.spinner("AI가 투자 아이디어를 생성하고 있습니다..."):
                    # 시장 데이터 수집
                    market_data = {
                        'user_preferences': {
                            'risk_tolerance': risk_tolerance,
                            'investment_horizon': investment_horizon,
                            'interested_sectors': sectors,
                            'excluded_sectors': exclude_sectors,
                        }
                    }

                    ideas = gpt.get_investment_ideas(
                        market_data,
                        preferences=market_data['user_preferences']
                    )

                    if ideas:
                        st.markdown("### 📋 투자 아이디어")
                        st.markdown(ideas)

                        st.divider()
                        st.warning("⚠️ 본 아이디어는 참고용이며, 투자 결정의 유일한 근거가 되어서는 안 됩니다. "
                                 "투자에 따른 책임은 본인에게 있습니다.")
                    else:
                        st.error("아이디어 생성에 실패했습니다.")

            # 시나리오 분석
            st.divider()
            st.subheader("📊 시나리오 분석")

            if st.button("시나리오 분석 실행", key="scenario_analysis"):
                st.info("포트폴리오를 입력하면 다양한 경제 시나리오에서의 영향을 분석합니다.")

                # 간단한 포트폴리오 입력
                portfolio_text = st.text_area(
                    "포트폴리오 입력 (종목: 비중)",
                    "AAPL: 30%\nMSFT: 25%\nGOOGL: 20%\nNVDA: 15%\nTLT: 10%"
                )

                if portfolio_text and st.button("분석 실행", key="run_scenario"):
                    with st.spinner("시나리오 분석 중..."):
                        scenarios = [
                            {'name': '금리 인상', 'probability': 30, 'description': '연준이 금리를 추가 인상'},
                            {'name': '금리 동결', 'probability': 50, 'description': '현 수준 유지'},
                            {'name': '금리 인하', 'probability': 20, 'description': '경기 둔화로 금리 인하'},
                        ]

                        portfolio = {'holdings': portfolio_text}

                        analysis = gpt.generate_scenario_analysis(scenarios, portfolio)

                        if analysis:
                            st.markdown(analysis)
                        else:
                            st.error("분석에 실패했습니다.")


if __name__ == "__main__":
    render_ai_analysis_page()
