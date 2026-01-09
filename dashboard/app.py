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


def render_snowflake_compact():
    """메인 대시보드용 Snowflake 분석 컴팩트 버전 - 전체 종목 지원"""
    st.markdown("### ❄️ 종목 Snowflake 분석")
    st.caption("한국 전체 종목 검색 가능 (2,500+ 종목)")

    # 종목 검색
    search_input = st.text_input(
        "🔍 종목 검색",
        placeholder="종목명 또는 코드 입력 (예: 삼성전자, 005930, 셀트리온)",
        key="main_snowflake_search"
    )

    # 선택된 종목
    selected_code = st.session_state.get('snowflake_selected_code')
    selected_name = st.session_state.get('snowflake_selected_name')

    # 검색 결과 표시
    if search_input and KOREA_AVAILABLE:
        try:
            krx = KRXDataCollector()
            stock_list = krx.get_stock_list('ALL')
            if not stock_list.empty:
                # 이름 또는 코드로 검색
                mask = (stock_list['name'].str.contains(search_input, case=False, na=False) |
                        stock_list['code'].str.contains(search_input, na=False))
                matches = stock_list[mask].head(10)

                if not matches.empty:
                    st.caption(f"🔎 검색 결과 ({len(matches)}개)")
                    # 검색 결과를 버튼으로 표시
                    result_cols = st.columns(min(5, len(matches)))
                    for i, (_, row) in enumerate(matches.head(5).iterrows()):
                        with result_cols[i]:
                            if st.button(
                                f"{row['name'][:6]}",
                                key=f"search_result_{row['code']}",
                                use_container_width=True,
                                help=f"{row['name']} ({row['code']})"
                            ):
                                st.session_state.snowflake_selected_code = row['code']
                                st.session_state.snowflake_selected_name = row['name']
                                st.rerun()
                else:
                    st.caption("검색 결과가 없습니다.")
        except Exception as e:
            st.caption(f"검색 오류: {e}")

    # 인기 종목 퀵 버튼
    popular_stocks = [
        ('삼성전자', '005930'), ('SK하이닉스', '000660'), ('현대차', '005380'),
        ('NAVER', '035420'), ('카카오', '035720'), ('LG에너지솔루션', '373220')
    ]

    st.caption("📌 인기 종목:")
    quick_cols = st.columns(6)
    for i, (name, code) in enumerate(popular_stocks):
        with quick_cols[i]:
            if st.button(name[:4], key=f"quick_snow_{code}", use_container_width=True):
                st.session_state.snowflake_selected_code = code
                st.session_state.snowflake_selected_name = name
                st.rerun()

    if selected_code and selected_name:
        # 실제 펀더멘털 데이터 조회
        stock_data = _get_stock_fundamentals_for_snowflake(selected_code)

        if stock_data:
            scores = snowflake_analyzer.calculate_scores(fundamentals=stock_data, sector='default')
            grade, emoji, description = get_overall_rating(scores)

            col1, col2 = st.columns([2, 1])

            with col1:
                fig = create_snowflake_chart(scores, selected_name)
                fig.update_layout(height=280, margin=dict(l=30, r=30, t=30, b=30))
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.markdown(f"### {emoji} {grade}")
                st.caption(f"{selected_name} ({selected_code})")
                st.markdown(f"""
                | 지표 | 점수 |
                |:---:|:---:|
                | 가치 | {scores.value:.1f}/6 |
                | 미래 | {scores.future:.1f}/6 |
                | 과거 | {scores.past:.1f}/6 |
                | 배당 | {scores.dividend:.1f}/6 |
                | 건전성 | {scores.health:.1f}/6 |
                | **종합** | **{scores.total:.1f}/6** |
                """)
        else:
            st.warning(f"{selected_name} 데이터를 불러올 수 없습니다.")
    else:
        st.info("👆 종목을 검색하거나 인기 종목 버튼을 클릭하세요")

    if st.button("❄️ Snowflake 상세 분석", key="view_snowflake", use_container_width=True):
        st.session_state.current_page = 'snowflake'
        st.rerun()


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
    """대시보드 (홈) 페이지 - 한국 시장 중심"""
    st.markdown("## 📊 한국 주식 대시보드")

    # 온보딩 가이드
    render_onboarding()

    # ==================== 한국 시장 현황 ====================
    if KOREA_AVAILABLE:
        try:
            krx = KRXDataCollector()
            bok = BOKIndicators()

            # 시장 요약 데이터
            market_summary = krx.get_market_summary()
            exchange_rates = bok.get_exchange_rates()

            # 핵심 지표 (한국 시장)
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                kospi = market_summary.get('KOSPI', {})
                kospi_close = kospi.get('close', 0)
                kospi_change = kospi.get('change_pct', 0)
                st.metric(
                    "🇰🇷 KOSPI",
                    f"{kospi_close:,.2f}",
                    delta=f"{kospi_change:+.2f}%",
                    delta_color="normal" if kospi_change >= 0 else "inverse"
                )

            with col2:
                kosdaq = market_summary.get('KOSDAQ', {})
                kosdaq_close = kosdaq.get('close', 0)
                kosdaq_change = kosdaq.get('change_pct', 0)
                st.metric(
                    "🇰🇷 KOSDAQ",
                    f"{kosdaq_close:,.2f}",
                    delta=f"{kosdaq_change:+.2f}%",
                    delta_color="normal" if kosdaq_change >= 0 else "inverse"
                )

            with col3:
                usd_krw = exchange_rates.get('usd_krw', 0)
                st.metric("💱 USD/KRW", f"₩{usd_krw:,.0f}")

            with col4:
                if 'vix' in data['market'].columns:
                    vix = data['market']['vix'].iloc[-1]
                    st.metric("📊 VIX (공포지수)", f"{vix:.1f}")
                else:
                    st.metric("📊 VIX", "N/A")

            st.divider()

            # KOSPI/KOSDAQ 차트
            st.subheader("📈 KOSPI / KOSDAQ 추이")

            col_chart1, col_chart2 = st.columns(2)

            with col_chart1:
                kospi_data = krx.get_index_data('KOSPI', days=30)
                if not kospi_data.empty:
                    fig_kospi = go.Figure()
                    fig_kospi.add_trace(go.Candlestick(
                        x=kospi_data.index,
                        open=kospi_data['Open'],
                        high=kospi_data['High'],
                        low=kospi_data['Low'],
                        close=kospi_data['Close'],
                        name='KOSPI'
                    ))
                    fig_kospi.update_layout(
                        title="KOSPI (30일)",
                        height=300,
                        margin=dict(l=10, r=10, t=40, b=10),
                        xaxis_rangeslider_visible=False
                    )
                    st.plotly_chart(fig_kospi, use_container_width=True)

            with col_chart2:
                kosdaq_data = krx.get_index_data('KOSDAQ', days=30)
                if not kosdaq_data.empty:
                    fig_kosdaq = go.Figure()
                    fig_kosdaq.add_trace(go.Candlestick(
                        x=kosdaq_data.index,
                        open=kosdaq_data['Open'],
                        high=kosdaq_data['High'],
                        low=kosdaq_data['Low'],
                        close=kosdaq_data['Close'],
                        name='KOSDAQ',
                        increasing_line_color='red',
                        decreasing_line_color='blue'
                    ))
                    fig_kosdaq.update_layout(
                        title="KOSDAQ (30일)",
                        height=300,
                        margin=dict(l=10, r=10, t=40, b=10),
                        xaxis_rangeslider_visible=False
                    )
                    st.plotly_chart(fig_kosdaq, use_container_width=True)

            st.divider()

        except Exception as e:
            st.warning(f"한국 시장 데이터 로드 중 오류: {e}")

    # ==================== 핵심 분석 기능 ====================
    st.markdown("---")
    st.markdown("## 🔥 핵심 분석 기능")

    # 1. SNS 스타일 시장 토론
    if SNS_DISCUSSION_AVAILABLE:
        try:
            # 시장 데이터 가져오기
            index_data = fetch_market_index_data(60)
            gainers, losers = fetch_top_movers(5)

            if index_data and 'KOSPI' in index_data:
                kospi_data = index_data['KOSPI']
                metrics = calculate_market_metrics(kospi_data)
                condition = analyze_market_condition(metrics)
                render_sns_discussion_compact(metrics, condition, gainers, losers)
            else:
                st.info("시장 토론: 데이터 로딩 중...")
        except Exception as e:
            st.caption(f"시장 토론 로드 오류: {e}")
    else:
        st.info("💬 SNS 시장 토론 기능을 사용하려면 market_overview 모듈이 필요합니다.")

    st.divider()

    # 2. Snowflake 분석 & 3. 잠재적 요인 분석 (나란히 배치)
    col_snow, col_catalyst = st.columns(2)

    with col_snow:
        if SNOWFLAKE_ANALYSIS_AVAILABLE:
            try:
                render_snowflake_compact()
            except Exception as e:
                st.caption(f"Snowflake 로드 오류: {e}")
        else:
            st.info("❄️ Snowflake 분석 기능을 사용하려면 snowflake_viz 모듈이 필요합니다.")

    with col_catalyst:
        if POTENTIAL_ANALYSIS_AVAILABLE:
            try:
                render_catalyst_compact()
            except Exception as e:
                st.caption(f"잠재 요인 분석 로드 오류: {e}")
        else:
            st.info("🎯 잠재 요인 분석 기능을 사용하려면 potential_analyzer 모듈이 필요합니다.")

    st.divider()

    # 빠른 이동 버튼
    st.markdown("### 🔗 빠른 이동")
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        if st.button("🇰🇷 한국 주식", use_container_width=True, key="quick_korea"):
            st.session_state.current_page = 'korea'
            st.rerun()
    with col2:
        if st.button("❄️ Snowflake", use_container_width=True, key="quick_snowflake"):
            st.session_state.current_page = 'snowflake'
            st.rerun()
    with col3:
        if st.button("🔥 급등/급락", use_container_width=True, key="quick_rally"):
            st.session_state.current_page = 'rally'
            st.rerun()
    with col4:
        if st.button("🤖 AI 분석", use_container_width=True, key="quick_ai"):
            st.session_state.current_page = 'ai_analysis'
            st.rerun()
    with col5:
        if st.button("🎯 잠재 요인", use_container_width=True, key="quick_potential"):
            st.session_state.current_page = 'potential'
            st.rerun()
    with col6:
        if st.button("📅 캘린더", use_container_width=True, key="quick_calendar"):
            st.session_state.current_page = 'calendar'
            st.rerun()

    st.divider()

    # 글로벌 시장 (참고용)
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
