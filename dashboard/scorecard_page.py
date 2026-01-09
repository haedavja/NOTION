"""
종합 스코어카드 페이지
여러 분석 결과를 통합하여 종합 투자 평가 제공
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 스코어카드 모듈
from analysis.scorecard import (
    ScorecardGenerator, ComprehensiveScorecard,
    render_comprehensive_scorecard, ScoreCategory
)

# Snowflake 통합 (선택적)
try:
    from analysis.integration_utils import get_snowflake_scores_for_stock
    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SNOWFLAKE_AVAILABLE = False

# yfinance (선택적)
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


def fetch_stock_data(symbol: str) -> dict:
    """주식 데이터 조회"""
    if not YFINANCE_AVAILABLE:
        return {}

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        hist = ticker.history(period="6mo")

        if hist.empty:
            return {}

        # 기본 정보
        data = {
            'name': info.get('shortName', symbol),
            'sector': info.get('sector', 'Unknown'),
            'industry': info.get('industry', 'Unknown'),
            'current_price': hist['Close'].iloc[-1] if not hist.empty else 0,
        }

        # 펀더멘털 데이터
        data['fundamentals'] = {
            'per': info.get('trailingPE'),
            'pbr': info.get('priceToBook'),
            'roe': info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else None,
            'dividend_yield': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
            'debt_ratio': info.get('debtToEquity', 100),
            'revenue_growth': info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else 0,
        }

        # 기술적 데이터
        if len(hist) >= 50:
            close = hist['Close']
            ma20 = close.rolling(20).mean().iloc[-1]
            ma50 = close.rolling(50).mean().iloc[-1]

            # RSI 계산
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            data['technical'] = {
                'rsi': rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50,
                'ma20': ma20,
                'ma50': ma50,
                'trend': '상승' if close.iloc[-1] > ma50 else '하락',
                'ma_signal': '골든크로스' if ma20 > ma50 else '데드크로스',
            }
        else:
            data['technical'] = {'rsi': 50, 'trend': '중립', 'ma_signal': ''}

        return data

    except Exception as e:
        st.error(f"데이터 조회 오류: {e}")
        return {}


def calculate_snowflake_from_fundamentals(fundamentals: dict) -> object:
    """펀더멘털 데이터에서 Snowflake 점수 계산"""
    if not SNOWFLAKE_AVAILABLE:
        return None

    try:
        scores = get_snowflake_scores_for_stock(fundamentals)
        return scores
    except Exception:
        return None


class MockPotentialAnalysis:
    """잠재 요인 분석 모의 객체"""
    def __init__(self, bullish: float = 50, bearish: float = 50):
        self.bullish_score = bullish
        self.bearish_score = bearish


class MockRallyCredibility:
    """상승 신뢰도 모의 객체"""
    def __init__(self, overall: float = 50):
        self.overall = overall
        self.level = type('Level', (), {'value': self._get_level()})()

    def _get_level(self):
        if self.overall >= 70:
            return "높음"
        elif self.overall >= 50:
            return "보통"
        else:
            return "낮음"


def render_scorecard_page():
    """종합 스코어카드 페이지 렌더링"""
    st.header("📋 종합 스코어카드")
    st.markdown("여러 분석 지표를 종합하여 투자 평가를 제공합니다.")

    # 종목 입력
    col1, col2 = st.columns([3, 1])

    with col1:
        symbol = st.text_input(
            "종목 코드",
            value="AAPL",
            placeholder="예: AAPL, MSFT, GOOGL",
            help="분석할 종목의 티커 심볼을 입력하세요"
        )

    with col2:
        analyze_btn = st.button("📊 분석 실행", use_container_width=True)

    # 분석 실행
    if analyze_btn and symbol:
        with st.spinner(f"{symbol} 분석 중..."):
            # 데이터 조회
            stock_data = fetch_stock_data(symbol.upper())

            if not stock_data:
                st.error(f"{symbol}에 대한 데이터를 찾을 수 없습니다.")
                return

            # 스코어카드 생성기
            generator = ScorecardGenerator()

            # Snowflake 점수 계산
            snowflake_scores = None
            if SNOWFLAKE_AVAILABLE and stock_data.get('fundamentals'):
                snowflake_scores = calculate_snowflake_from_fundamentals(
                    stock_data['fundamentals']
                )

            # 기술적 데이터
            technical_data = stock_data.get('technical', {})

            # 수급 데이터 (모의 - 실제 연결 시 교체)
            supply_demand_data = {
                'foreign_net': np.random.randint(-100, 100),
                'inst_net': np.random.randint(-50, 50),
                'trend': np.random.choice(['매집', '중립', '이탈']),
            }

            # 잠재 요인 (기술적 분석 기반으로 추정)
            rsi = technical_data.get('rsi', 50)
            if rsi < 30:
                bullish, bearish = 70, 30
            elif rsi > 70:
                bullish, bearish = 30, 70
            else:
                bullish, bearish = 50, 50

            potential_analysis = MockPotentialAnalysis(bullish, bearish)

            # 상승 신뢰도 (추세 기반)
            trend = technical_data.get('trend', '중립')
            ma_signal = technical_data.get('ma_signal', '')

            rally_score = 50
            if trend == '상승':
                rally_score += 15
            elif trend == '하락':
                rally_score -= 15
            if '골든크로스' in ma_signal:
                rally_score += 10
            elif '데드크로스' in ma_signal:
                rally_score -= 10

            rally_credibility = MockRallyCredibility(max(0, min(100, rally_score)))

            # 스코어카드 생성
            scorecard = generator.generate(
                symbol=symbol.upper(),
                name=stock_data.get('name', symbol),
                snowflake_scores=snowflake_scores,
                technical_data=technical_data,
                supply_demand_data=supply_demand_data,
                potential_analysis=potential_analysis,
                rally_credibility=rally_credibility,
            )

            # 세션에 저장
            if 'scorecard_history' not in st.session_state:
                st.session_state.scorecard_history = []

            st.session_state.scorecard_history.append({
                'symbol': symbol.upper(),
                'scorecard': scorecard,
                'timestamp': datetime.now(),
            })

            # 최근 10개만 유지
            st.session_state.scorecard_history = st.session_state.scorecard_history[-10:]

        # 스코어카드 렌더링
        render_comprehensive_scorecard(scorecard)

        # 추가 정보
        with st.expander("📈 상세 정보"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### 기본 정보")
                st.write(f"**섹터**: {stock_data.get('sector', 'N/A')}")
                st.write(f"**산업**: {stock_data.get('industry', 'N/A')}")
                st.write(f"**현재가**: ${stock_data.get('current_price', 0):,.2f}")

            with col2:
                st.markdown("### 펀더멘털")
                fund = stock_data.get('fundamentals', {})
                st.write(f"**PER**: {fund.get('per', 'N/A'):.2f}" if fund.get('per') else "**PER**: N/A")
                st.write(f"**PBR**: {fund.get('pbr', 'N/A'):.2f}" if fund.get('pbr') else "**PBR**: N/A")
                st.write(f"**ROE**: {fund.get('roe', 'N/A'):.1f}%" if fund.get('roe') else "**ROE**: N/A")

        # 카테고리별 점수 상세
        with st.expander("📊 카테고리별 점수 상세"):
            for cat in scorecard.categories:
                st.markdown(f"#### {cat.category.value}")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("점수", f"{cat.score:.1f}")
                with col2:
                    st.metric("등급", cat.grade)
                with col3:
                    st.write(f"**요약**: {cat.summary}")

                if cat.details:
                    st.json(cat.details)
                st.divider()

    # 분석 이력
    if 'scorecard_history' in st.session_state and st.session_state.scorecard_history:
        st.divider()
        st.subheader("📜 최근 분석 이력")

        history_df = pd.DataFrame([
            {
                '종목': h['symbol'],
                '종합점수': f"{h['scorecard'].overall_score:.0f}",
                '등급': h['scorecard'].overall_grade,
                '권고': h['scorecard'].recommendation,
                '분석시간': h['timestamp'].strftime('%H:%M:%S'),
            }
            for h in reversed(st.session_state.scorecard_history)
        ])

        st.dataframe(history_df, use_container_width=True, hide_index=True)

        # 비교 기능
        if len(st.session_state.scorecard_history) >= 2:
            st.subheader("📊 종목 비교")

            symbols = [h['symbol'] for h in st.session_state.scorecard_history]
            selected = st.multiselect(
                "비교할 종목 선택",
                symbols,
                default=symbols[:2] if len(symbols) >= 2 else symbols
            )

            if len(selected) >= 2:
                compare_data = []
                for symbol in selected:
                    for h in st.session_state.scorecard_history:
                        if h['symbol'] == symbol:
                            sc = h['scorecard']
                            compare_data.append({
                                '종목': symbol,
                                '종합점수': sc.overall_score,
                                '등급': sc.overall_grade,
                                '별점': '⭐' * sc.overall_rating,
                                '권고': sc.recommendation,
                            })
                            break

                compare_df = pd.DataFrame(compare_data)
                st.dataframe(compare_df, use_container_width=True, hide_index=True)

    # 사용 가이드
    with st.expander("ℹ️ 사용 가이드"):
        st.markdown("""
        ### 종합 스코어카드 해석 가이드

        **점수 구성**
        - **펀더멘털 (30%)**: PER, PBR, ROE, 배당, 부채 등 기본 지표
        - **기술적 (20%)**: RSI, 이동평균, 추세 등 차트 분석
        - **수급 (20%)**: 외국인/기관 매매 동향
        - **잠재 요인 (15%)**: 상승/하락 요인 분석
        - **상승 신뢰도 (15%)**: 현재 추세의 지속 가능성

        **등급 체계**
        - A+ (90점 이상): 매우 우수
        - A (80점 이상): 우수
        - B+ (70점 이상): 양호
        - B (60점 이상): 보통
        - C (50점 이상): 평균 이하
        - D (40점 이상): 취약
        - F (40점 미만): 매우 취약

        **투자 권고**
        - 적극 매수: 70점 이상
        - 매수: 60점 이상
        - 보유: 50점 이상
        - 비중 축소: 40점 이상
        - 매도 검토: 40점 미만
        """)


if __name__ == "__main__":
    render_scorecard_page()
