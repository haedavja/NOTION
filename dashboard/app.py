"""
거시경제 기반 시장 예측 대시보드
사이드바 네비게이션 v2.0
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional, Dict
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys
import os

# 상위 디렉토리 import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.macro_indicators import MacroIndicators
from data.market_data import MarketData
from data.fund_flow import FundFlowTracker
from data.news_collector import NewsCollector
from analysis.macro_analysis import MacroAnalyzer
from analysis.flow_analysis import FlowAnalyzer
from analysis.sentiment import SentimentAnalyzer
from analysis.technical import TechnicalAnalyzer
from prediction.probability_model import ProbabilityModel
from prediction.scenarios import ScenarioAnalyzer

# 포트폴리오 모듈
from portfolio.portfolio import Portfolio, Position
from portfolio.analyzer import PortfolioAnalyzer
from portfolio.thesis_evaluator import ThesisEvaluator, ThesisRating

# 네비게이션 모듈
from dashboard.navigation import (
    init_navigation_state, render_sidebar, render_onboarding,
    get_page_title, MENU_STRUCTURE
)

# ==================== 모듈 가용성 체크 ====================
BACKTEST_AVAILABLE = False
AI_ANALYSIS_AVAILABLE = False
KOREA_AVAILABLE = False
ADVANCED_AVAILABLE = False
TOOLS_AVAILABLE = False
AI_CHAT_AVAILABLE = False
CALENDAR_AVAILABLE = False
ADVANCED_ANALYSIS_AVAILABLE = False
NOTIFICATION_AVAILABLE = False
RALLY_ANALYZER_AVAILABLE = False
POTENTIAL_ANALYZER_AVAILABLE = False
SHORTCUTS_AVAILABLE = False

try:
    from dashboard.backtest_page import render_backtest_page
    BACKTEST_AVAILABLE = True
except ImportError:
    pass

try:
    from dashboard.ai_analysis_page import render_ai_analysis_page
    AI_ANALYSIS_AVAILABLE = True
except ImportError:
    pass

try:
    from dashboard.korea_page import render_korea_page
    from korea.krx_data import KRXDataCollector
    from korea.bok_indicators import BOKIndicators
    KOREA_AVAILABLE = True
except ImportError:
    KOREA_AVAILABLE = False

try:
    from dashboard.advanced_features import render_advanced_features
    from dashboard.alert_settings import render_alert_settings
    ADVANCED_AVAILABLE = True
except ImportError:
    pass

try:
    from dashboard.tools_page import render_tools_page
    TOOLS_AVAILABLE = True
except ImportError:
    pass

try:
    from dashboard.ai_chat_page import render_ai_sentiment_page
    AI_CHAT_AVAILABLE = True
except ImportError:
    pass

try:
    from dashboard.calendar_page import render_calendar_watchlist_page
    CALENDAR_AVAILABLE = True
except ImportError:
    pass

try:
    from dashboard.advanced_analysis_page import render_advanced_analysis_page
    ADVANCED_ANALYSIS_AVAILABLE = True
except ImportError:
    pass

try:
    from dashboard.notification_page import render_notification_dashboard
    NOTIFICATION_AVAILABLE = True
except ImportError:
    pass

try:
    from dashboard.rally_page import render_rally_dashboard
    RALLY_ANALYZER_AVAILABLE = True
except ImportError:
    pass

try:
    from dashboard.potential_page import render_potential_dashboard
    POTENTIAL_ANALYZER_AVAILABLE = True
except ImportError:
    pass

try:
    from dashboard.keyboard_shortcuts import inject_keyboard_shortcuts, add_shortcut_indicator
    SHORTCUTS_AVAILABLE = True
except ImportError:
    pass

try:
    from dashboard.snowflake_page import render_snowflake_page
    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SNOWFLAKE_AVAILABLE = False

try:
    from dashboard.scorecard_page import render_scorecard_page
    SCORECARD_AVAILABLE = True
except ImportError:
    SCORECARD_AVAILABLE = False

try:
    from dashboard.benchmark_page import render_benchmark_page
    BENCHMARK_AVAILABLE = True
except ImportError:
    BENCHMARK_AVAILABLE = False

try:
    from dashboard.correlation_page import render_correlation_page
    CORRELATION_AVAILABLE = True
except ImportError:
    CORRELATION_AVAILABLE = False

try:
    from dashboard.sector_rotation_page import render_sector_rotation_page
    SECTOR_ROTATION_AVAILABLE = True
except ImportError:
    SECTOR_ROTATION_AVAILABLE = False

try:
    from dashboard.market_overview_page import render_market_overview_page
    MARKET_OVERVIEW_AVAILABLE = True
except ImportError:
    MARKET_OVERVIEW_AVAILABLE = False

# SNS 토론 기능
try:
    from dashboard.market_overview_page import (
        generate_sns_market_discussion,
        calculate_market_metrics,
        analyze_market_condition,
        fetch_market_index_data,
        fetch_top_movers,
        TRADER_PERSONAS
    )
    SNS_DISCUSSION_AVAILABLE = True
except ImportError:
    SNS_DISCUSSION_AVAILABLE = False

# Snowflake 분석
try:
    from analysis.snowflake_viz import (
        snowflake_analyzer, create_snowflake_chart,
        get_overall_rating, SnowflakeScores
    )
    SNOWFLAKE_ANALYSIS_AVAILABLE = True
except ImportError:
    SNOWFLAKE_ANALYSIS_AVAILABLE = False

# 잠재적 요인 분석
try:
    from analysis.potential_analyzer import PotentialAnalyzer
    POTENTIAL_ANALYSIS_AVAILABLE = True
except ImportError:
    POTENTIAL_ANALYSIS_AVAILABLE = False

try:
    from components.watchlist import render_watchlist_manager
    WATCHLIST_AVAILABLE = True
except ImportError:
    WATCHLIST_AVAILABLE = False

try:
    from components.price_alert import render_alert_list
    PRICE_ALERT_AVAILABLE = True
except ImportError:
    PRICE_ALERT_AVAILABLE = False

# yfinance
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


# ==================== 페이지 설정 ====================
st.set_page_config(
    page_title="NOTION - 시장 예측 시스템",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CSS 스타일 ====================
st.markdown("""
<style>
    /* 기본 스타일 */
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem;
    }
    .bullish { color: #00c853; font-weight: bold; }
    .bearish { color: #ff1744; font-weight: bold; }
    .neutral { color: #ffc107; font-weight: bold; }

    /* 사이드바 스타일 */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
    }
    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        text-align: left;
        padding: 0.5rem 1rem;
        margin: 0.1rem 0;
    }

    /* 모바일 반응형 */
    @media (max-width: 768px) {
        .main-header { font-size: 1.5rem; }
        [data-testid="stSidebar"] {
            min-width: 0px !important;
            max-width: 0px !important;
        }
        [data-testid="stSidebar"][aria-expanded="true"] {
            min-width: 280px !important;
            max-width: 280px !important;
        }
    }

    /* 다크 모드 */
    @media (prefers-color-scheme: dark) {
        .metric-card { background-color: #262730; }
    }
</style>
""", unsafe_allow_html=True)


# ==================== 데이터 로드 함수 ====================
def get_minimal_macro_data():
    """최소 거시경제 데이터 생성"""
    dates = pd.date_range(end=datetime.now(), periods=180, freq='D')
    return pd.DataFrame({
        'fed_funds_rate': np.linspace(5.25, 5.5, 180),
        'cpi': np.linspace(3.0, 3.2, 180) + np.random.randn(180) * 0.1,
        'unemployment_rate': np.linspace(3.7, 3.9, 180) + np.random.randn(180) * 0.05,
        'gdp_growth': np.linspace(2.0, 2.5, 180) + np.random.randn(180) * 0.2,
        'interest_rate': np.linspace(4.0, 4.5, 180),
        'treasury_10y': np.linspace(4.0, 4.5, 180),
        'yield_spread': np.linspace(-0.5, 0.5, 180),
        'vix': np.linspace(15, 20, 180) + np.random.randn(180) * 2,
    }, index=dates)


def get_minimal_fund_flow():
    """최소 자금흐름 데이터 생성"""
    dates = pd.date_range(end=datetime.now(), periods=180, freq='D')
    return pd.DataFrame({
        'Technology': np.cumsum(np.random.randn(180) * 0.5),
        'Healthcare': np.cumsum(np.random.randn(180) * 0.3),
        'Financials': np.cumsum(np.random.randn(180) * 0.4),
        'Energy': np.cumsum(np.random.randn(180) * 0.3),
        'Consumer': np.cumsum(np.random.randn(180) * 0.2),
    }, index=dates)


def get_minimal_news():
    """최소 뉴스 데이터 생성"""
    return [{'title': 'Market Update', 'source': 'System',
             'published_at': datetime.now().isoformat(),
             'description': '실시간 데이터 사용 중'}]


@st.cache_data(ttl=300)
def load_realtime_data():
    """yfinance로 실시간 데이터 로드"""
    if not YFINANCE_AVAILABLE:
        return None

    try:
        symbols = {
            'sp500': '^GSPC', 'nasdaq': '^IXIC', 'dow': '^DJI',
            'vix': '^VIX', 'gold': 'GC=F', 'oil': 'CL=F',
            'usd_index': 'DX-Y.NYB', 'us10y': '^TNX',
        }

        end_date = datetime.now()
        start_date = end_date - timedelta(days=180)
        market_data = pd.DataFrame()

        for name, symbol in symbols.items():
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(start=start_date, end=end_date)
                if not hist.empty:
                    market_data[name] = hist['Close']
            except Exception:
                pass

        if market_data.empty:
            return None

        macro_data = get_minimal_macro_data()

        if 'vix' in market_data.columns and not market_data['vix'].empty:
            macro_data.loc[macro_data.index[-1], 'vix'] = market_data['vix'].iloc[-1]

        if 'us10y' in market_data.columns and not market_data['us10y'].empty:
            macro_data.loc[macro_data.index[-1], 'interest_rate'] = market_data['us10y'].iloc[-1]

        return {
            'macro': macro_data,
            'market': market_data,
            'fund_flow': get_minimal_fund_flow(),
            'news': get_minimal_news(),
            'realtime': True,
        }

    except Exception as e:
        return None


# ==================== 차트 함수 ====================
def create_gauge_chart(value: float, title: str, min_val: float = 0, max_val: float = 100):
    """게이지 차트 생성"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': title},
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={
            'axis': {'range': [min_val, max_val]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 33], 'color': "#ff6b6b"},
                {'range': [33, 66], 'color': "#ffd93d"},
                {'range': [66, 100], 'color': "#6bcb77"}
            ],
        }
    ))
    fig.update_layout(height=250, margin=dict(l=10, r=10, t=50, b=10))
    return fig


def create_scenario_chart(scenarios: list):
    """시나리오 확률 차트"""
    if not scenarios:
        return None

    names = [s['name'] for s in scenarios]
    probs = [s['probability'] for s in scenarios]

    fig = go.Figure(go.Bar(
        x=probs, y=names, orientation='h',
        marker_color=['#2ecc71', '#3498db', '#e74c3c', '#f39c12', '#9b59b6'][:len(names)]
    ))
    fig.update_layout(title="시나리오별 확률", xaxis_title="확률 (%)", height=300,
                      margin=dict(l=10, r=10, t=40, b=10))
    return fig


def create_allocation_chart(allocation: dict):
    """자산 배분 파이 차트"""
    labels = list(allocation.keys())
    values = list(allocation.values())
    label_kr = {'equities': '주식', 'bonds': '채권', 'gold': '금', 'cash': '현금'}
    labels = [label_kr.get(l, l) for l in labels]

    fig = go.Figure(data=[go.Pie(
        labels=labels, values=values, hole=.4,
        marker_colors=['#3498db', '#2ecc71', '#f1c40f', '#95a5a6']
    )])
    fig.update_layout(title="권장 자산 배분", height=300, margin=dict(l=10, r=10, t=40, b=10))
    return fig


def create_time_series_chart(data: pd.DataFrame, columns: list, title: str):
    """시계열 차트"""
    fig = go.Figure()
    for col in columns:
        if col in data.columns:
            fig.add_trace(go.Scatter(x=data.index, y=data[col], mode='lines', name=col))
    fig.update_layout(title=title, xaxis_title="날짜", yaxis_title="값", height=400,
                      margin=dict(l=10, r=10, t=40, b=10),
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig


# ==================== 페이지 렌더링 함수 ====================
def render_sns_discussion_compact(metrics: dict, condition: dict, gainers: list, losers: list):
    """메인 대시보드용 SNS 토론 컴팩트 버전"""
    st.markdown("### 💬 트레이더들의 시장 토론")
    st.caption("6명의 전문가가 현재 시장을 분석합니다")

    posts = generate_sns_market_discussion(metrics, condition, gainers, losers, None)

    # 상위 3개 의견만 표시
    for post in posts[:3]:
        persona = post['persona']
        confidence = post.get('confidence')

        # 신뢰도 색상
        if confidence is not None:
            conf_color = '#22c55e' if confidence >= 70 else '#eab308' if confidence >= 50 else '#ef4444'
        else:
            conf_color = '#6b7280'

        st.markdown(f"""
        <div style='background: white; border: 1px solid #e5e7eb; border-left: 4px solid {persona["color"]};
                    border-radius: 8px; padding: 0.8rem; margin-bottom: 0.5rem;'>
            <div style='display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.3rem;'>
                <span style='font-size: 1.3rem;'>{persona["avatar"]}</span>
                <span style='font-weight: bold; color: {persona["color"]};'>{persona["name"]}</span>
                <span style='font-size: 0.75rem; color: #9ca3af;'>{post["timestamp"]}</span>
            </div>
            <div style='font-size: 0.9rem; line-height: 1.5; margin-bottom: 0.3rem;'>
                {post["message"][:150]}{"..." if len(post["message"]) > 150 else ""}
            </div>
            <div style='display: flex; gap: 1rem; font-size: 0.8rem; color: #6b7280;'>
                <span>❤️ {post["likes"]}</span>
                <span>💬 {post["comments"]}</span>
                {"<span style='background: " + conf_color + "20; color: " + conf_color + "; padding: 2px 6px; border-radius: 10px;'>신뢰도 " + str(confidence) + "%</span>" if confidence else ""}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 더보기 버튼
    if st.button("💬 전체 토론 보기", key="view_all_discussion", use_container_width=True):
        st.session_state.current_page = 'market_overview'
        st.rerun()


def render_integrated_stock_analysis():
    """통합 종목 분석 - Snowflake + 트레이더 토론 + 투자논리 검증"""

    # 자동완성 검색 컴포넌트
    try:
        from components.stock_search import render_stock_autocomplete

        selected = render_stock_autocomplete(
            key="main_stock_search",
            label="🔍 종목 검색 (2,400+ 종목)",
            placeholder="종목명 또는 코드 (예: 삼성, 다날, 005930)",
            show_popular=True,
            default_code=st.session_state.get('main_selected_code'),
            default_name=st.session_state.get('main_selected_name')
        )

        if selected:
            st.session_state.main_selected_code = selected['code']
            st.session_state.main_selected_name = selected['name']

    except ImportError:
        search_input = st.text_input(
            "🔍 종목 검색",
            placeholder="종목명 또는 코드 입력",
            key="fallback_search"
        )
        if search_input and KOREA_AVAILABLE:
            try:
                krx = KRXDataCollector()
                stock_list = krx.get_stock_list('ALL')
                if not stock_list.empty:
                    mask = (stock_list['name'].str.contains(search_input, case=False, na=False) |
                            stock_list['code'].str.contains(search_input, na=False))
                    matches = stock_list[mask].head(5)
                    if not matches.empty:
                        cols = st.columns(len(matches))
                        for i, (_, row) in enumerate(matches.iterrows()):
                            with cols[i]:
                                if st.button(row['name'][:6], key=f"sr_{row['code']}", use_container_width=True):
                                    st.session_state.main_selected_code = row['code']
                                    st.session_state.main_selected_name = row['name']
                                    st.rerun()
            except Exception:
                pass

    # 선택된 종목 분석
    selected_code = st.session_state.get('main_selected_code')
    selected_name = st.session_state.get('main_selected_name')

    if selected_code and selected_name:
        st.divider()

        # 펀더멘털 데이터 조회
        stock_data = _get_stock_fundamentals_for_snowflake(selected_code)

        if stock_data and SNOWFLAKE_ANALYSIS_AVAILABLE:
            scores = snowflake_analyzer.calculate_scores(fundamentals=stock_data, sector='default')
            grade, emoji, description = get_overall_rating(scores)

            # 종목 헤더
            st.markdown(f"## {emoji} {selected_name} ({selected_code})")
            st.caption(f"종합 등급: **{grade}** | {description}")

            # 탭으로 분석 영역 구분
            tab1, tab2, tab3 = st.tabs(["❄️ Snowflake 분석", "💬 전문가 토론", "📝 투자논리 검증"])

            with tab1:
                # Snowflake 차트
                col1, col2 = st.columns([2, 1])

                with col1:
                    fig = create_snowflake_chart(scores, selected_name)
                    fig.update_layout(height=350, margin=dict(l=30, r=30, t=30, b=30))
                    st.plotly_chart(fig, use_container_width=True)

                with col2:
                    st.markdown("### 📊 점수 상세")
                    st.markdown(f"""
                    | 지표 | 점수 | 평가 |
                    |:---:|:---:|:---:|
                    | 💰 가치 | {scores.value:.1f}/6 | {"✅" if scores.value >= 4 else "⚠️" if scores.value >= 2.5 else "❌"} |
                    | 🚀 미래 | {scores.future:.1f}/6 | {"✅" if scores.future >= 4 else "⚠️" if scores.future >= 2.5 else "❌"} |
                    | 📈 과거 | {scores.past:.1f}/6 | {"✅" if scores.past >= 4 else "⚠️" if scores.past >= 2.5 else "❌"} |
                    | 💵 배당 | {scores.dividend:.1f}/6 | {"✅" if scores.dividend >= 4 else "⚠️" if scores.dividend >= 2.5 else "❌"} |
                    | 🏥 건전성 | {scores.health:.1f}/6 | {"✅" if scores.health >= 4 else "⚠️" if scores.health >= 2.5 else "❌"} |
                    | **🎯 종합** | **{scores.total:.1f}/6** | **{emoji}** |
                    """)

                    # 평가 기호 범례
                    with st.expander("ℹ️ 평가 기호 설명", expanded=False):
                        st.markdown("""
                        | 기호 | 점수 범위 | 의미 |
                        |:---:|:---:|:---|
                        | ✅ | 4.0 이상 | **양호** - 해당 지표가 우수함 |
                        | ⚠️ | 2.5 ~ 4.0 | **보통** - 평균 수준, 주시 필요 |
                        | ❌ | 2.5 미만 | **주의** - 개선이 필요한 영역 |

                        ---
                        **종합 등급 기준**
                        | 등급 | 점수 | 의미 |
                        |:---:|:---:|:---|
                        | ⭐ A+ | 5.0+ | 최우량 |
                        | 🟢 A | 4.0+ | 우량 |
                        | 🔵 B | 3.5+ | 양호 |
                        | 🟡 C | 3.0+ | 보통 |
                        | 🟠 D | 2.5+ | 주의 |
                        | 🔴 F | 2.5 미만 | 위험 |
                        """)

                    # 핵심 요약
                    st.markdown("### 💡 핵심 요약")
                    if scores.total >= 4.5:
                        st.success("우량 종목으로 평가됩니다")
                    elif scores.total >= 3.5:
                        st.info("양호한 편이나 일부 개선 필요")
                    elif scores.total >= 2.5:
                        st.warning("투자 전 추가 검토 권장")
                    else:
                        st.error("리스크 요인 다수 존재")

            with tab2:
                # 트레이더 토론
                try:
                    from components.trader_analysis import render_trader_discussion_ui
                    scores_dict = {
                        'total': scores.total,
                        'value': scores.value,
                        'future': scores.future,
                        'past': scores.past,
                        'dividend': scores.dividend,
                        'health': scores.health
                    }
                    render_trader_discussion_ui(selected_name, selected_code, scores_dict, stock_data)
                except ImportError as e:
                    st.warning(f"트레이더 토론 모듈 로드 실패: {e}")

            with tab3:
                # 투자논리 검증
                try:
                    from components.trader_analysis import render_thesis_analysis_ui
                    scores_dict = {
                        'total': scores.total,
                        'value': scores.value,
                        'future': scores.future,
                        'past': scores.past,
                        'dividend': scores.dividend,
                        'health': scores.health
                    }
                    render_thesis_analysis_ui(selected_name, selected_code, scores_dict, stock_data)
                except ImportError as e:
                    st.warning(f"투자논리 분석 모듈 로드 실패: {e}")

        else:
            st.warning(f"{selected_name} 분석 데이터를 불러올 수 없습니다.")
    else:
        st.info("👆 종목을 검색하거나 인기 종목 버튼을 클릭하세요")


def render_snowflake_compact():
    """메인 대시보드용 Snowflake 분석 컴팩트 버전 - 전체 종목 지원 (레거시 호환)"""
    render_integrated_stock_analysis()


def _get_stock_fundamentals_for_snowflake(code: str) -> Optional[Dict]:
    """Snowflake 분석용 펀더멘털 데이터 조회"""
    try:
        from korea.korean_stocks import KoreanStockAnalyzer
        analyzer = KoreanStockAnalyzer()
        fundamentals = analyzer.get_fundamentals(code)

        if fundamentals:
            return {
                'per': fundamentals.per or 15,
                'pbr': fundamentals.pbr or 1.5,
                'roe': fundamentals.roe or 10,
                'dividend_yield': fundamentals.dividend_yield or 1.0,
                'debt_ratio': 50,  # 기본값 (별도 API 필요)
                'current_ratio': 1.5,
                'revenue_growth': 5,
                'earnings_growth': 8,
                'operating_margin': 10,
                'net_margin': 8,
            }
    except Exception as e:
        pass

    # 폴백: 기본 데이터
    return {
        'per': 15, 'pbr': 1.5, 'roe': 10, 'dividend_yield': 1.5,
        'debt_ratio': 50, 'current_ratio': 1.5, 'revenue_growth': 5,
        'earnings_growth': 8, 'operating_margin': 10, 'net_margin': 8
    }


def render_catalyst_compact():
    """메인 대시보드용 잠재적 요인 분석 컴팩트 버전"""
    st.markdown("### 🎯 잠재적 급등/급락 요인")
    st.caption("발생 전 선제적으로 파악하는 핵심 촉매")

    analyzer = PotentialAnalyzer()

    # 샘플 분석 (실제로는 실시간 데이터)
    sample_analyses = [
        {"symbol": "005930", "name": "삼성전자", "type": "bullish",
         "catalyst": "AI반도체 수요 급증", "probability": "높음", "impact": "상", "timeframe": "3개월 내"},
        {"symbol": "000660", "name": "SK하이닉스", "type": "bullish",
         "catalyst": "HBM3E 양산 본격화", "probability": "매우높음", "impact": "상", "timeframe": "1개월 내"},
        {"symbol": "035720", "name": "카카오", "type": "bearish",
         "catalyst": "규제 리스크 지속", "probability": "중간", "impact": "중", "timeframe": "6개월 내"},
    ]

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**🚀 상승 촉매**")
        for item in [a for a in sample_analyses if a['type'] == 'bullish'][:2]:
            st.markdown(f"""
            <div style='background: #dcfce7; padding: 0.6rem; border-radius: 8px;
                        border-left: 3px solid #22c55e; margin-bottom: 0.4rem;'>
                <div style='font-weight: bold; color: #166534;'>{item['name']}</div>
                <div style='font-size: 0.85rem;'>{item['catalyst']}</div>
                <div style='font-size: 0.75rem; color: #4ade80;'>
                    확률: {item['probability']} | 영향: {item['impact']} | {item['timeframe']}
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown("**⚠️ 하락 촉매**")
        for item in [a for a in sample_analyses if a['type'] == 'bearish'][:2]:
            st.markdown(f"""
            <div style='background: #fee2e2; padding: 0.6rem; border-radius: 8px;
                        border-left: 3px solid #ef4444; margin-bottom: 0.4rem;'>
                <div style='font-weight: bold; color: #991b1b;'>{item['name']}</div>
                <div style='font-size: 0.85rem;'>{item['catalyst']}</div>
                <div style='font-size: 0.75rem; color: #f87171;'>
                    확률: {item['probability']} | 영향: {item['impact']} | {item['timeframe']}
                </div>
            </div>
            """, unsafe_allow_html=True)

    if st.button("🎯 잠재 요인 상세 분석", key="view_potential", use_container_width=True):
        st.session_state.current_page = 'potential'
        st.rerun()


def render_dashboard_page(data, prediction, scenario_summary):
    """메인 대시보드 - 한국 주식 통합 화면"""

    # ==================== 상단: 시장 지수 + 실시간 키워드 ====================
    if KOREA_AVAILABLE:
        try:
            krx = KRXDataCollector()
            bok = BOKIndicators()
            market_summary = krx.get_market_summary()
            exchange_rates = bok.get_exchange_rates()

            # 핵심 지표 바 (고정 상단)
            st.markdown("""
            <style>
            .market-bar {
                background: linear-gradient(90deg, #1e3a5f 0%, #2d5a87 100%);
                padding: 0.8rem 1rem;
                border-radius: 10px;
                margin-bottom: 1rem;
            }
            </style>
            """, unsafe_allow_html=True)

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                kospi = market_summary.get('KOSPI', {})
                kospi_close = kospi.get('close', 0)
                kospi_change = kospi.get('change_pct', 0)
                delta_color = "normal" if kospi_change >= 0 else "inverse"
                st.metric("🔵 KOSPI", f"{kospi_close:,.2f}", f"{kospi_change:+.2f}%", delta_color=delta_color)

            with col2:
                kosdaq = market_summary.get('KOSDAQ', {})
                kosdaq_close = kosdaq.get('close', 0)
                kosdaq_change = kosdaq.get('change_pct', 0)
                delta_color = "normal" if kosdaq_change >= 0 else "inverse"
                st.metric("🟢 KOSDAQ", f"{kosdaq_close:,.2f}", f"{kosdaq_change:+.2f}%", delta_color=delta_color)

            with col3:
                usd_krw = exchange_rates.get('usd_krw', 0)
                st.metric("💱 원/달러", f"₩{usd_krw:,.0f}")

            with col4:
                if 'vix' in data['market'].columns:
                    vix = data['market']['vix'].iloc[-1]
                    vix_status = "🟢" if vix < 20 else "🟡" if vix < 30 else "🔴"
                    st.metric(f"{vix_status} VIX", f"{vix:.1f}")
                else:
                    st.metric("📊 VIX", "N/A")

            with col5:
                # 시장 상태 요약
                avg_change = (kospi_change + kosdaq_change) / 2
                if avg_change > 1:
                    st.metric("📈 시장", "강세", f"{avg_change:+.1f}%")
                elif avg_change < -1:
                    st.metric("📉 시장", "약세", f"{avg_change:+.1f}%")
                else:
                    st.metric("➡️ 시장", "보합", f"{avg_change:+.1f}%")

            # 실시간 인기 키워드
            st.markdown("---")
            try:
                from korea.market_keywords import get_realtime_keywords, get_fallback_keywords
                keywords_data = get_realtime_keywords()
                if not keywords_data or not keywords_data.get('popular_stocks'):
                    keywords_data = get_fallback_keywords()

                popular = keywords_data.get('popular_stocks', [])[:8]
                themes = keywords_data.get('themes', [])[:5]

                col_kw1, col_kw2 = st.columns([2, 1])

                with col_kw1:
                    st.markdown("#### 🔥 실시간 인기 종목")
                    if popular:
                        kw_cols = st.columns(min(len(popular), 8))
                        for i, stock in enumerate(popular[:8]):
                            with kw_cols[i]:
                                name = stock.get('name', '')[:5]
                                change = stock.get('change', '')
                                if st.button(f"{i+1}. {name}", key=f"hot_{i}", use_container_width=True):
                                    # 인기 종목 클릭 시 검색
                                    st.session_state.main_selected_name = stock.get('name', '')
                                    # 코드 찾기
                                    try:
                                        from korea.krx_data import search_korean_stock
                                        results = search_korean_stock(stock.get('name', ''))
                                        if results:
                                            st.session_state.main_selected_code = results[0].get('code', '')
                                    except:
                                        pass
                                    st.rerun()
                    else:
                        st.caption("인기 종목 로딩 중...")

                with col_kw2:
                    st.markdown("#### 📌 테마")
                    if themes:
                        for theme in themes[:4]:
                            theme_name = theme.get('name', '') if isinstance(theme, dict) else str(theme)
                            st.markdown(f"<span style='background:#f0f9ff; padding:3px 8px; border-radius:12px; font-size:0.85rem;'>{theme_name}</span>", unsafe_allow_html=True)
                    else:
                        st.caption("테마 로딩 중...")

            except ImportError:
                st.caption("실시간 키워드: 모듈 없음")
            except Exception as e:
                st.caption(f"키워드 로드 오류")

            st.divider()

            # KOSPI/KOSDAQ 미니 차트
            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                kospi_data = krx.get_index_data('KOSPI', days=20)
                if not kospi_data.empty:
                    fig_kospi = go.Figure()
                    fig_kospi.add_trace(go.Candlestick(
                        x=kospi_data.index,
                        open=kospi_data['Open'],
                        high=kospi_data['High'],
                        low=kospi_data['Low'],
                        close=kospi_data['Close'],
                        name='KOSPI',
                        increasing_line_color='#ef4444',
                        decreasing_line_color='#3b82f6'
                    ))
                    fig_kospi.update_layout(
                        title="KOSPI",
                        height=220,
                        margin=dict(l=5, r=5, t=30, b=5),
                        xaxis_rangeslider_visible=False,
                        showlegend=False
                    )
                    st.plotly_chart(fig_kospi, use_container_width=True)

            with col_chart2:
                kosdaq_data = krx.get_index_data('KOSDAQ', days=20)
                if not kosdaq_data.empty:
                    fig_kosdaq = go.Figure()
                    fig_kosdaq.add_trace(go.Candlestick(
                        x=kosdaq_data.index,
                        open=kosdaq_data['Open'],
                        high=kosdaq_data['High'],
                        low=kosdaq_data['Low'],
                        close=kosdaq_data['Close'],
                        name='KOSDAQ',
                        increasing_line_color='#ef4444',
                        decreasing_line_color='#3b82f6'
                    ))
                    fig_kosdaq.update_layout(
                        title="KOSDAQ",
                        height=220,
                        margin=dict(l=5, r=5, t=30, b=5),
                        xaxis_rangeslider_visible=False,
                        showlegend=False
                    )
                    st.plotly_chart(fig_kosdaq, use_container_width=True)

        except Exception as e:
            st.warning(f"시장 데이터 로드 오류: {e}")
    else:
        st.warning("한국 시장 모듈을 사용할 수 없습니다. `pykrx` 패키지를 설치하세요.")

    st.divider()

    # ==================== 핵심: 통합 종목 분석 ====================
    st.markdown("## 🔍 종목 분석")
    st.caption("종목을 검색하면 Snowflake 분석 + 전문가 토론 + 투자논리 검증이 한번에!")

    if SNOWFLAKE_ANALYSIS_AVAILABLE:
        try:
            render_integrated_stock_analysis()
        except Exception as e:
            st.error(f"종목 분석 로드 오류: {e}")
    else:
        st.info("Snowflake 분석 모듈을 사용할 수 없습니다.")

    st.divider()

    # ==================== 하단: 추가 기능 (접이식) ====================
    with st.expander("💬 시장 토론 (트레이더들의 의견)", expanded=False):
        if SNS_DISCUSSION_AVAILABLE:
            try:
                index_data = fetch_market_index_data(60)
                gainers, losers = fetch_top_movers(5)
                if index_data and 'KOSPI' in index_data:
                    kospi_data_sns = index_data['KOSPI']
                    metrics = calculate_market_metrics(kospi_data_sns)
                    condition = analyze_market_condition(metrics)
                    render_sns_discussion_compact(metrics, condition, gainers, losers)
            except Exception as e:
                st.caption(f"시장 토론 로드 오류: {e}")
        else:
            st.info("시장 토론 모듈이 필요합니다.")

    with st.expander("🎯 잠재적 급등/급락 요인", expanded=False):
        if POTENTIAL_ANALYSIS_AVAILABLE:
            try:
                render_catalyst_compact()
            except Exception as e:
                st.caption(f"잠재 요인 분석 로드 오류: {e}")
        else:
            st.info("잠재 요인 분석 모듈이 필요합니다.")

    with st.expander("🌍 글로벌 시장 현황", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**미국 지수**")
            if 'sp500' in data['market'].columns:
                market_df = pd.DataFrame({
                    '지수': ['S&P 500', 'NASDAQ', 'DOW'],
                    '현재가': [
                        f"{data['market']['sp500'].iloc[-1]:,.0f}" if 'sp500' in data['market'].columns else 'N/A',
                        f"{data['market']['nasdaq'].iloc[-1]:,.0f}" if 'nasdaq' in data['market'].columns else 'N/A',
                        f"{data['market']['dow'].iloc[-1]:,.0f}" if 'dow' in data['market'].columns else 'N/A',
                    ]
                })
                st.dataframe(market_df, use_container_width=True, hide_index=True)
        with col2:
            st.markdown("**시장 예측**")
            prob = prediction.probability * 100
            st.metric("상승 확률", f"{prob:.1f}%", delta=f"{prob - 50:.1f}%p")

    # 빠른 이동 버튼
    st.markdown("### 🔗 더 많은 기능")
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        if st.button("🔥 급등/급락", use_container_width=True, key="quick_rally"):
            st.session_state.current_page = 'rally'
            st.rerun()
    with col2:
        if st.button("🤖 AI 분석", use_container_width=True, key="quick_ai"):
            st.session_state.current_page = 'ai_analysis'
            st.rerun()
    with col3:
        if st.button("📊 포트폴리오", use_container_width=True, key="quick_portfolio"):
            st.session_state.current_page = 'portfolio'
            st.rerun()
    with col4:
        if st.button("📅 캘린더", use_container_width=True, key="quick_calendar"):
            st.session_state.current_page = 'calendar'
            st.rerun()
    with col5:
        if st.button("⚙️ 더보기", use_container_width=True, key="quick_more"):
            st.session_state.current_page = 'tools'
            st.rerun()


def render_prediction_page(data, prediction, scenario_summary):
    """종합 예측 페이지"""
    st.markdown("## 🎯 종합 예측")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("시장 방향 확률")
        gauge = create_gauge_chart(prediction.probability * 100, "상승 확률 (%)")
        st.plotly_chart(gauge, use_container_width=True)

        st.subheader("시나리오 분석")
        scenario_chart = create_scenario_chart(scenario_summary.get('all_scenarios', []))
        if scenario_chart:
            st.plotly_chart(scenario_chart, use_container_width=True)

    with col2:
        st.subheader("권장 자산 배분")
        allocation = scenario_summary.get('recommended_allocation', {})
        if allocation:
            alloc_chart = create_allocation_chart(allocation)
            st.plotly_chart(alloc_chart, use_container_width=True)

        st.subheader("기대 수익률")
        expected_returns = scenario_summary.get('expected_returns', {})
        if expected_returns:
            return_df = pd.DataFrame({
                '자산': ['주식', '채권', '금', '현금'],
                '기대수익률(%)': [
                    expected_returns.get('equities', 0),
                    expected_returns.get('bonds', 0),
                    expected_returns.get('gold', 0),
                    expected_returns.get('cash', 0),
                ]
            })
            st.dataframe(return_df, use_container_width=True, hide_index=True)

    # 섹터 추천
    st.subheader("섹터 추천")
    sector_recs = scenario_summary.get('sector_recommendations', {})
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**✅ 비중 확대**")
        for sector in sector_recs.get('overweight', []):
            st.write(f"• {sector}")
    with col2:
        st.markdown("**➖ 중립**")
        for sector in sector_recs.get('neutral', []):
            st.write(f"• {sector}")
    with col3:
        st.markdown("**❌ 비중 축소**")
        for sector in sector_recs.get('underweight', []):
            st.write(f"• {sector}")

    # 리스크 요인
    st.subheader("⚠️ 주요 리스크 요인")
    for risk in scenario_summary.get('risk_factors', []):
        st.warning(risk)


def render_macro_page(data, macro_analysis):
    """거시경제 페이지"""
    st.markdown("## 🌐 거시경제 분석")

    cycle = macro_analysis.get('economic_cycle', 'N/A')
    st.info(f"현재 경기 단계: **{cycle}**")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("주요 거시경제 지표")
        macro_chart = create_time_series_chart(
            data['macro'], ['fed_funds_rate', 'cpi', 'unemployment_rate'],
            "거시경제 지표 추이"
        )
        st.plotly_chart(macro_chart, use_container_width=True)

    with col2:
        st.subheader("거시경제 신호")
        signals = macro_analysis.get('signals', [])
        for signal in signals:
            indicator = signal.get('indicator', '')
            sig_type = signal.get('signal', '')
            description = signal.get('description', '')

            if sig_type == 'bullish':
                st.success(f"🟢 **{indicator}**: {description}")
            elif sig_type == 'bearish':
                st.error(f"🔴 **{indicator}**: {description}")
            else:
                st.warning(f"🟡 **{indicator}**: {description}")

    # 수익률 곡선
    st.subheader("수익률 곡선")
    if 'treasury_10y' in data['macro'].columns:
        yield_chart = create_time_series_chart(
            data['macro'], ['treasury_10y', 'yield_spread'],
            "금리 및 스프레드"
        )
        st.plotly_chart(yield_chart, use_container_width=True)


def render_fund_flow_page(data, flow_analysis):
    """자금흐름 페이지"""
    st.markdown("## 💹 자금흐름 분석")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("자금흐름 현황")
        st.markdown("**📈 유입 자산**")
        for asset in flow_analysis.get('inflows', [])[:5]:
            st.write(f"• {asset}")
        st.markdown("**📉 유출 자산**")
        for asset in flow_analysis.get('outflows', [])[:5]:
            st.write(f"• {asset}")

    with col2:
        st.subheader("시장 폭 지표")
        breadth = flow_analysis.get('market_breadth', {})
        for label, key in [("50일 MA 상위", 'pct_above_ma_50'),
                           ("200일 MA 상위", 'pct_above_ma_200'),
                           ("건강도 점수", 'health_score')]:
            value = breadth.get(key, 0)
            if key == 'health_score':
                value *= 100
            st.metric(label, f"{value:.1f}%")

    st.subheader("섹터별 자금흐름")
    fund_flow_chart = create_time_series_chart(
        data['fund_flow'], list(data['fund_flow'].columns)[:5],
        "섹터별 누적 자금흐름"
    )
    st.plotly_chart(fund_flow_chart, use_container_width=True)


def render_sentiment_page(data, sentiment_analysis):
    """센티먼트 페이지"""
    st.markdown("## 📰 센티먼트 분석")

    overall = sentiment_analysis.get('overall_analysis', {})

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("뉴스 센티먼트")
        dist = overall.get('sentiment_distribution', {})
        sentiment_df = pd.DataFrame({
            '센티먼트': ['긍정', '중립', '부정'],
            '건수': [dist.get('positive', 0), dist.get('neutral', 0), dist.get('negative', 0)]
        })
        fig = px.pie(sentiment_df, values='건수', names='센티먼트',
                    color='센티먼트',
                    color_discrete_map={'긍정': 'green', '중립': 'gray', '부정': 'red'})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("센티먼트 점수")
        composite = overall.get('composite_score', 0)
        gauge = create_gauge_chart((composite + 1) * 50, "종합 센티먼트", 0, 100)
        st.plotly_chart(gauge, use_container_width=True)

    # 최신 뉴스
    st.subheader("주요 뉴스")
    for news in data['news'][:5]:
        with st.expander(news.get('title', 'No Title')):
            st.write(f"**출처**: {news.get('source', 'N/A')}")
            st.write(f"**날짜**: {news.get('published_at', 'N/A')}")
            st.write(news.get('description', ''))


def render_technical_page(data, technical_analysis):
    """기술적 분석 페이지"""
    st.markdown("## 📊 기술적 분석")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("이동평균")
        trend_analysis = technical_analysis.get('trend_analysis', {})
        st.metric("현재 추세", trend_analysis.get('trend', 'N/A'))

        ma_data = {
            'MA20': trend_analysis.get('ma_20', 0),
            'MA50': trend_analysis.get('ma_50', 0),
            'MA200': trend_analysis.get('ma_200', 0),
        }
        for ma, value in ma_data.items():
            above = "✅" if trend_analysis.get(f'above_{ma.lower()}', False) else "❌"
            st.write(f"{ma}: {value:.2f} {above}")

    with col2:
        st.subheader("모멘텀 지표")
        momentum = technical_analysis.get('momentum_analysis', {})
        st.metric("RSI", f"{momentum.get('rsi', 50):.1f}", delta=momentum.get('rsi_signal', ''))
        st.metric("MACD", f"{momentum.get('macd', 0):.4f}", delta=momentum.get('macd_cross', ''))

    # 가격 차트
    st.subheader("가격 및 이동평균")
    if 'sp500' in data['market'].columns:
        price_data = data['market'][['sp500']].copy()
        price_data['MA50'] = price_data['sp500'].rolling(50).mean()
        price_data['MA200'] = price_data['sp500'].rolling(200).mean()
        price_chart = create_time_series_chart(price_data, ['sp500', 'MA50', 'MA200'],
                                               "S&P 500 가격 및 이동평균")
        st.plotly_chart(price_chart, use_container_width=True)


def render_unavailable_page(page_name: str, description: str = ""):
    """사용 불가 페이지 렌더링"""
    st.warning(f"{page_name} 모듈을 사용할 수 없습니다.")
    st.info("관련 패키지가 올바르게 설치되었는지 확인하세요.")
    if description:
        st.markdown(description)


# ==================== 메인 함수 ====================
def main():
    """메인 대시보드"""
    # 네비게이션 상태 초기화
    init_navigation_state()

    # 모듈 가용성 맵
    availability = {
        'dashboard': True,
        'market_overview': MARKET_OVERVIEW_AVAILABLE,
        'prediction': True,
        'macro': True,
        'fund_flow': True,
        'sentiment': True,
        'technical': True,
        'sector_rotation': SECTOR_ROTATION_AVAILABLE,
        'korea': KOREA_AVAILABLE,
        'snowflake': SNOWFLAKE_AVAILABLE,
        'scorecard': SCORECARD_AVAILABLE,
        'rally': RALLY_ANALYZER_AVAILABLE,
        'potential': POTENTIAL_ANALYZER_AVAILABLE,
        'portfolio': True,
        'backtest': BACKTEST_AVAILABLE,
        'benchmark': BENCHMARK_AVAILABLE,
        'correlation': CORRELATION_AVAILABLE,
        'tools': TOOLS_AVAILABLE,
        'watchlist': WATCHLIST_AVAILABLE,
        'alerts': PRICE_ALERT_AVAILABLE,
        'calendar': CALENDAR_AVAILABLE,
        'advanced': ADVANCED_AVAILABLE,
        'advanced_analysis': ADVANCED_ANALYSIS_AVAILABLE,
        'ai_analysis': AI_ANALYSIS_AVAILABLE,
        'ai_chat': AI_CHAT_AVAILABLE,
        'notifications': NOTIFICATION_AVAILABLE,
    }

    # 사이드바 렌더링
    render_sidebar(availability)

    # 데이터 로드
    if not YFINANCE_AVAILABLE:
        st.error("yfinance 설치 필요: `pip install yfinance`")
        st.stop()

    with st.spinner("데이터 로딩 중..."):
        data = load_realtime_data()

    if not data:
        st.error("데이터를 불러올 수 없습니다. 페이지를 새로고침해주세요.")
        st.stop()

    # 분석기 초기화 및 분석 실행
    macro_analyzer = MacroAnalyzer()
    flow_analyzer = FlowAnalyzer()
    sentiment_analyzer = SentimentAnalyzer(use_ml=False)
    technical_analyzer = TechnicalAnalyzer()
    prob_model = ProbabilityModel()
    scenario_analyzer = ScenarioAnalyzer()

    macro_analysis = macro_analyzer.get_summary(data['macro'])
    flow_analysis = flow_analyzer.get_flow_summary(data['market'])
    sentiment_analysis = sentiment_analyzer.get_summary(data['news'])

    if 'sp500' in data['market'].columns:
        technical_analysis = technical_analyzer.get_technical_summary(data['market']['sp500'])
    else:
        technical_analysis = {}

    prediction = prob_model.predict_probability(
        macro_analysis=macro_analysis,
        flow_analysis=flow_analysis,
        sentiment_analysis=sentiment_analysis,
        technical_analysis=technical_analysis
    )

    scenario_summary = scenario_analyzer.get_summary(
        macro_analysis, flow_analysis, sentiment_analysis
    )

    # 키보드 단축키
    if SHORTCUTS_AVAILABLE:
        inject_keyboard_shortcuts()
        add_shortcut_indicator()

    # ==================== 페이지 라우팅 ====================
    current_page = st.session_state.current_page

    # 홈 카테고리
    if current_page == 'dashboard':
        render_dashboard_page(data, prediction, scenario_summary)

    elif current_page == 'market_overview':
        if MARKET_OVERVIEW_AVAILABLE:
            render_market_overview_page()
        else:
            render_unavailable_page("시장 종합 현황")

    elif current_page == 'prediction':
        render_prediction_page(data, prediction, scenario_summary)

    # 시장 분석 카테고리
    elif current_page == 'macro':
        render_macro_page(data, macro_analysis)

    elif current_page == 'fund_flow':
        render_fund_flow_page(data, flow_analysis)

    elif current_page == 'sentiment':
        render_sentiment_page(data, sentiment_analysis)

    elif current_page == 'technical':
        render_technical_page(data, technical_analysis)

    # 종목 분석 카테고리
    elif current_page == 'korea':
        if KOREA_AVAILABLE:
            render_korea_page()
        else:
            render_unavailable_page("한국 주식", "필요한 패키지: `pykrx`")

    elif current_page == 'snowflake':
        if SNOWFLAKE_AVAILABLE:
            render_snowflake_page()
        else:
            render_unavailable_page("Snowflake 분석", "필요한 패키지: `plotly`")

    elif current_page == 'scorecard':
        if SCORECARD_AVAILABLE:
            render_scorecard_page()
        else:
            render_unavailable_page("종합 스코어카드")

    elif current_page == 'rally':
        if RALLY_ANALYZER_AVAILABLE:
            render_rally_dashboard()
        else:
            render_unavailable_page("급등/급락 분석")

    elif current_page == 'potential':
        if POTENTIAL_ANALYZER_AVAILABLE:
            render_potential_dashboard()
        else:
            render_unavailable_page("잠재 요인 분석")

    # 포트폴리오 카테고리
    elif current_page == 'portfolio':
        try:
            from dashboard.portfolio_page import render_portfolio_page
            render_portfolio_page()
        except ImportError:
            render_unavailable_page("포트폴리오 분석")

    elif current_page == 'backtest':
        if BACKTEST_AVAILABLE:
            render_backtest_page()
        else:
            render_unavailable_page("백테스트")

    elif current_page == 'benchmark':
        if BENCHMARK_AVAILABLE:
            render_benchmark_page()
        else:
            render_unavailable_page("벤치마크 비교")

    elif current_page == 'correlation':
        if CORRELATION_AVAILABLE:
            render_correlation_page()
        else:
            render_unavailable_page("상관관계 분석")

    elif current_page == 'sector_rotation':
        if SECTOR_ROTATION_AVAILABLE:
            render_sector_rotation_page()
        else:
            render_unavailable_page("섹터 회전 분석")

    # 도구 카테고리
    elif current_page == 'tools':
        if TOOLS_AVAILABLE:
            render_tools_page()
        else:
            render_unavailable_page("투자 도구")

    elif current_page == 'watchlist':
        if WATCHLIST_AVAILABLE:
            st.header("⭐ 관심 종목 관리")
            render_watchlist_manager()
        else:
            render_unavailable_page("관심 종목")

    elif current_page == 'alerts':
        if PRICE_ALERT_AVAILABLE:
            st.header("🔔 가격 알림 관리")
            render_alert_list()
        else:
            render_unavailable_page("가격 알림")

    elif current_page == 'calendar':
        if CALENDAR_AVAILABLE:
            render_calendar_watchlist_page()
        else:
            render_unavailable_page("캘린더/워치리스트")

    elif current_page == 'advanced':
        if ADVANCED_AVAILABLE:
            render_advanced_features()
        else:
            render_unavailable_page("고급 기능")

    elif current_page == 'advanced_analysis':
        if ADVANCED_ANALYSIS_AVAILABLE:
            render_advanced_analysis_page()
        else:
            render_unavailable_page("고급 분석")

    # AI 카테고리
    elif current_page == 'ai_analysis':
        if AI_ANALYSIS_AVAILABLE:
            render_ai_analysis_page()
        else:
            render_unavailable_page("AI 분석", "필요한 패키지: `openai`")

    elif current_page == 'ai_chat':
        if AI_CHAT_AVAILABLE:
            render_ai_sentiment_page()
        else:
            render_unavailable_page("AI 어시스턴트", "필요한 설정: `OPENAI_API_KEY` 환경변수")

    # 설정 카테고리
    elif current_page == 'notifications':
        if NOTIFICATION_AVAILABLE:
            render_notification_dashboard()
        else:
            render_unavailable_page("알림")

    else:
        # 기본 페이지
        render_dashboard_page(data, prediction, scenario_summary)

    # 푸터
    st.divider()
    st.markdown(f"""
    <div style='text-align: center; color: gray; font-size: 0.8rem;'>
        <p>⚠️ 본 시스템의 예측은 참고용이며, 투자 결정의 유일한 근거가 되어서는 안 됩니다.</p>
        <p>마지막 업데이트: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
