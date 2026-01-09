"""
거시경제 기반 시장 예측 대시보드
사이드바 네비게이션 v2.0
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
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
    KOREA_AVAILABLE = True
except ImportError:
    pass

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
def render_dashboard_page(data, prediction, scenario_summary):
    """대시보드 (홈) 페이지"""
    st.markdown("## 📊 대시보드")

    # 온보딩 가이드
    render_onboarding()

    # 핵심 지표 요약
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        prob = prediction.probability * 100
        delta_color = "normal" if prob > 50 else "inverse"
        st.metric("상승 확률", f"{prob:.1f}%",
                  delta=f"{prob - 50:.1f}%p", delta_color=delta_color)

    with col2:
        st.metric("신뢰도", f"{prediction.confidence*100:.0f}%",
                  delta="높음" if prediction.confidence > 0.7 else "보통")

    with col3:
        most_likely = scenario_summary.get('most_likely_scenario', {})
        st.metric("주요 시나리오", most_likely.get('name', 'N/A'),
                  delta=f"{most_likely.get('probability', 0):.0f}%")

    with col4:
        if 'vix' in data['market'].columns:
            vix = data['market']['vix'].iloc[-1]
            st.metric("VIX", f"{vix:.1f}")
        else:
            st.metric("VIX", "N/A")

    st.divider()

    # 빠른 이동 버튼
    st.markdown("### 🔗 빠른 이동")
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        if st.button("❄️ Snowflake", use_container_width=True, key="quick_snowflake"):
            st.session_state.current_page = 'snowflake'
            st.rerun()
    with col2:
        if st.button("🔥 급등/급락", use_container_width=True, key="quick_rally"):
            st.session_state.current_page = 'rally'
            st.rerun()
    with col3:
        if st.button("🇰🇷 한국 주식", use_container_width=True, key="quick_korea"):
            st.session_state.current_page = 'korea'
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

    # 시장 현황 요약
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 시장 지수")
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
        st.subheader("🎯 권장 자산 배분")
        allocation = scenario_summary.get('recommended_allocation', {})
        if allocation:
            alloc_chart = create_allocation_chart(allocation)
            st.plotly_chart(alloc_chart, use_container_width=True)


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
        'prediction': True,
        'macro': True,
        'fund_flow': True,
        'sentiment': True,
        'technical': True,
        'korea': KOREA_AVAILABLE,
        'snowflake': SNOWFLAKE_AVAILABLE,
        'rally': RALLY_ANALYZER_AVAILABLE,
        'potential': POTENTIAL_ANALYZER_AVAILABLE,
        'portfolio': True,
        'backtest': BACKTEST_AVAILABLE,
        'tools': TOOLS_AVAILABLE,
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

    # 도구 카테고리
    elif current_page == 'tools':
        if TOOLS_AVAILABLE:
            render_tools_page()
        else:
            render_unavailable_page("투자 도구")

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
