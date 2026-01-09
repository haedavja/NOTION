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

# KRX 데이터 (한국 주식 수급 데이터용)
try:
    from korea.krx_data import get_investor_trading_by_stock, KRXDataCollector
    KRX_AVAILABLE = True
except ImportError:
    KRX_AVAILABLE = False


def fetch_korean_stock_data(code: str) -> dict:
    """한국 주식 데이터 조회 (KRX)"""
    if not KRX_AVAILABLE:
        return {}

    try:
        collector = KRXDataCollector()

        # 종목 정보
        stock_info = collector.get_stock_by_code(code)
        if not stock_info:
            return {}

        # 주가 데이터
        price_df = collector.get_stock_price(code)
        if price_df.empty:
            return {}

        # 기본 정보
        data = {
            'name': stock_info.get('name', code),
            'sector': stock_info.get('market', 'Unknown'),
            'industry': 'Korean Stock',
            'current_price': price_df['Close'].iloc[-1] if not price_df.empty else 0,
            'market': 'KRX',
        }

        # 기술적 데이터
        if len(price_df) >= 50:
            close = price_df['Close']
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

        # 펀더멘털은 KRX에서 제공 안함 - 기본값
        data['fundamentals'] = {
            'per': None,
            'pbr': None,
            'roe': None,
            'dividend_yield': 0,
            'debt_ratio': 100,
            'revenue_growth': 0,
        }

        return data

    except Exception as e:
        st.warning(f"한국 주식 데이터 조회 오류: {e}")
        return {}


def fetch_stock_data(symbol: str) -> dict:
    """주식 데이터 조회 (한국/해외 자동 구분)"""
    # 한국 주식인 경우 (6자리 숫자)
    if is_korean_stock(symbol):
        return fetch_korean_stock_data(symbol)

    # 해외 주식 (yfinance)
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
            'market': 'US',
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


def is_korean_stock(symbol: str) -> bool:
    """한국 주식 여부 확인 (6자리 숫자 코드)"""
    return symbol.isdigit() and len(symbol) == 6


def fetch_supply_demand_data(symbol: str, days: int = 5) -> dict:
    """
    수급 데이터 조회 (한국 주식은 실제 데이터, 해외 주식은 추정)

    Args:
        symbol: 종목 코드
        days: 조회 기간

    Returns:
        수급 데이터 dict {'foreign_net', 'inst_net', 'trend', 'data_source'}
    """
    # 한국 주식인 경우 실제 KRX 데이터 사용
    if is_korean_stock(symbol) and KRX_AVAILABLE:
        try:
            investor_data = get_investor_trading_by_stock(symbol, days)

            foreign_net = investor_data.get('foreign_net', 0)
            inst_net = investor_data.get('inst_net', 0)

            # 수급 추세 판단
            if foreign_net > 0 and inst_net > 0:
                trend = '매집'  # 외국인+기관 동반 매수
            elif foreign_net < 0 and inst_net < 0:
                trend = '이탈'  # 외국인+기관 동반 매도
            elif foreign_net > 0 or inst_net > 0:
                trend = '중립'  # 엇갈림
            else:
                trend = '중립'

            # 금액을 정규화 (억원 단위로 변환 후 -100~100 스케일)
            # 외국인 순매수가 ±500억 이상이면 최대치
            foreign_normalized = max(-100, min(100, foreign_net / 5_000_000_000))
            inst_normalized = max(-100, min(100, inst_net / 3_000_000_000))

            return {
                'foreign_net': foreign_normalized,
                'inst_net': inst_normalized,
                'trend': trend,
                'data_source': 'KRX 실제 데이터',
                'raw_foreign': foreign_net,
                'raw_inst': inst_net,
            }
        except Exception as e:
            st.warning(f"수급 데이터 조회 실패: {e}")

    # 해외 주식 또는 KRX 미사용 시 기술적 분석 기반 추정
    return {
        'foreign_net': 0,
        'inst_net': 0,
        'trend': '중립',
        'data_source': '추정치 (해외 주식)',
    }


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
            value="005930",
            placeholder="한국: 005930 (삼성전자) / 해외: AAPL",
            help="한국 주식은 6자리 코드, 해외 주식은 티커 심볼 입력"
        )

    with col2:
        analyze_btn = st.button("📊 분석 실행", use_container_width=True)

    # 데이터 소스 안내
    if symbol:
        if is_korean_stock(symbol):
            st.caption("🇰🇷 한국 주식 - KRX 데이터 및 실시간 수급 정보 제공")
        else:
            st.caption("🌍 해외 주식 - yfinance 데이터 사용")

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

            # 수급 데이터 (한국 주식은 실제 KRX 데이터 사용)
            supply_demand_data = fetch_supply_demand_data(symbol.upper())

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
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("### 기본 정보")
                st.write(f"**섹터**: {stock_data.get('sector', 'N/A')}")
                st.write(f"**산업**: {stock_data.get('industry', 'N/A')}")
                # 한국 주식은 원화, 해외는 달러
                if stock_data.get('market') == 'KRX':
                    st.write(f"**현재가**: ₩{stock_data.get('current_price', 0):,.0f}")
                else:
                    st.write(f"**현재가**: ${stock_data.get('current_price', 0):,.2f}")

            with col2:
                st.markdown("### 펀더멘털")
                fund = stock_data.get('fundamentals', {})
                st.write(f"**PER**: {fund.get('per', 'N/A'):.2f}" if fund.get('per') else "**PER**: N/A")
                st.write(f"**PBR**: {fund.get('pbr', 'N/A'):.2f}" if fund.get('pbr') else "**PBR**: N/A")
                st.write(f"**ROE**: {fund.get('roe', 'N/A'):.1f}%" if fund.get('roe') else "**ROE**: N/A")

            with col3:
                st.markdown("### 수급 정보")
                st.write(f"**데이터 소스**: {supply_demand_data.get('data_source', 'N/A')}")
                st.write(f"**수급 추세**: {supply_demand_data.get('trend', 'N/A')}")
                # 한국 주식은 실제 금액 표시
                if 'raw_foreign' in supply_demand_data:
                    raw_foreign = supply_demand_data['raw_foreign']
                    raw_inst = supply_demand_data['raw_inst']
                    st.write(f"**외국인**: {raw_foreign/100_000_000:+,.0f}억")
                    st.write(f"**기관**: {raw_inst/100_000_000:+,.0f}억")

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
