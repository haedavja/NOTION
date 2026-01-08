"""
거시경제 기반 시장 예측 대시보드
Streamlit을 사용한 인터랙티브 대시보드
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

# 새로운 모듈들 (선택적 import)
try:
    from dashboard.backtest_page import render_backtest_page
    BACKTEST_AVAILABLE = True
except ImportError:
    BACKTEST_AVAILABLE = False

try:
    from dashboard.ai_analysis_page import render_ai_analysis_page
    AI_ANALYSIS_AVAILABLE = True
except ImportError:
    AI_ANALYSIS_AVAILABLE = False

try:
    from dashboard.korea_page import render_korea_page
    KOREA_AVAILABLE = True
except ImportError:
    KOREA_AVAILABLE = False

try:
    from dashboard.advanced_features import render_advanced_features
    from dashboard.alert_settings import render_alert_settings
    ADVANCED_AVAILABLE = True
except ImportError:
    ADVANCED_AVAILABLE = False


# 페이지 설정
st.set_page_config(
    page_title="거시경제 시장 예측 시스템",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일 (반응형 포함)
st.markdown("""
<style>
    /* 기본 스타일 */
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
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

    /* 모바일 반응형 (768px 이하) */
    @media (max-width: 768px) {
        .main-header {
            font-size: 1.5rem;
            margin-bottom: 1rem;
        }

        /* 사이드바 숨김 기본 */
        [data-testid="stSidebar"] {
            min-width: 0px !important;
            max-width: 0px !important;
            padding: 0 !important;
        }
        [data-testid="stSidebar"][aria-expanded="true"] {
            min-width: 250px !important;
            max-width: 250px !important;
        }

        /* 컬럼 세로 배치 */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
        }

        /* 메트릭 카드 작게 */
        [data-testid="stMetric"] {
            padding: 0.5rem !important;
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.8rem !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.2rem !important;
        }

        /* 차트 높이 조정 */
        .js-plotly-plot {
            max-height: 250px !important;
        }

        /* 버튼 풀 너비 */
        .stButton > button {
            width: 100% !important;
            margin: 0.2rem 0 !important;
        }

        /* 테이블 스크롤 */
        [data-testid="stDataFrame"] {
            overflow-x: auto !important;
        }

        /* 탭 작게 */
        .stTabs [data-baseweb="tab"] {
            font-size: 0.8rem !important;
            padding: 0.3rem 0.5rem !important;
        }

        /* 폼 요소 */
        .stTextInput input, .stSelectbox select {
            font-size: 16px !important; /* iOS 줌 방지 */
        }
    }

    /* 태블릿 (769px ~ 1024px) */
    @media (min-width: 769px) and (max-width: 1024px) {
        .main-header {
            font-size: 2rem;
        }

        [data-testid="stSidebar"] {
            min-width: 200px !important;
            max-width: 200px !important;
        }
    }

    /* 터치 디바이스 개선 */
    @media (hover: none) and (pointer: coarse) {
        .stButton > button {
            min-height: 44px !important;
            min-width: 44px !important;
        }

        a, button, [role="button"] {
            min-height: 44px;
            min-width: 44px;
        }
    }

    /* 다크 모드 지원 */
    @media (prefers-color-scheme: dark) {
        .metric-card {
            background-color: #262730;
        }
    }
</style>
""", unsafe_allow_html=True)


# yfinance import
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


def get_minimal_macro_data():
    """최소 거시경제 데이터 생성 (실시간 데이터 보완용)"""
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
    return [
        {'title': 'Market Update', 'source': 'System', 'published_at': datetime.now().isoformat(), 'description': '실시간 데이터 사용 중'},
    ]


@st.cache_data(ttl=300)  # 5분 캐시
def load_realtime_data():
    """yfinance로 실시간 데이터 로드"""
    if not YFINANCE_AVAILABLE:
        return None

    try:
        # 주요 지수/ETF 심볼
        symbols = {
            'sp500': '^GSPC',
            'nasdaq': '^IXIC',
            'dow': '^DJI',
            'vix': '^VIX',
            'gold': 'GC=F',
            'oil': 'CL=F',
            'usd_index': 'DX-Y.NYB',
            'us10y': '^TNX',
        }

        # 데이터 다운로드 (6개월)
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

        # 매크로 데이터 (기본 데이터 + 실시간 VIX/금리)
        macro_data = get_minimal_macro_data()

        # VIX 최신값 반영
        if 'vix' in market_data.columns and not market_data['vix'].empty:
            latest_vix = market_data['vix'].iloc[-1]
            if 'vix' in macro_data.columns:
                macro_data.loc[macro_data.index[-1], 'vix'] = latest_vix

        # 10년물 금리 반영
        if 'us10y' in market_data.columns and not market_data['us10y'].empty:
            latest_10y = market_data['us10y'].iloc[-1]
            if 'interest_rate' in macro_data.columns:
                macro_data.loc[macro_data.index[-1], 'interest_rate'] = latest_10y

        return {
            'macro': macro_data,
            'market': market_data,
            'fund_flow': get_minimal_fund_flow(),
            'news': get_minimal_news(),
            'realtime': True,
        }

    except Exception as e:
        st.error(f"실시간 데이터 로드 실패: {e}")
        return None


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
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': value
            }
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
        x=probs,
        y=names,
        orientation='h',
        marker_color=['#2ecc71', '#3498db', '#e74c3c', '#f39c12', '#9b59b6'][:len(names)]
    ))

    fig.update_layout(
        title="시나리오별 확률",
        xaxis_title="확률 (%)",
        yaxis_title="",
        height=300,
        margin=dict(l=10, r=10, t=40, b=10)
    )

    return fig


def create_allocation_chart(allocation: dict):
    """자산 배분 파이 차트"""
    labels = list(allocation.keys())
    values = list(allocation.values())

    # 한글 레이블
    label_kr = {
        'equities': '주식',
        'bonds': '채권',
        'gold': '금',
        'cash': '현금'
    }
    labels = [label_kr.get(l, l) for l in labels]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=.4,
        marker_colors=['#3498db', '#2ecc71', '#f1c40f', '#95a5a6']
    )])

    fig.update_layout(
        title="권장 자산 배분",
        height=300,
        margin=dict(l=10, r=10, t=40, b=10)
    )

    return fig


def create_sector_heatmap(sector_data: dict):
    """섹터 히트맵"""
    if not sector_data:
        return None

    sectors = list(sector_data.keys())
    scores = list(sector_data.values())

    fig = go.Figure(data=go.Heatmap(
        z=[scores],
        x=sectors,
        y=['점수'],
        colorscale='RdYlGn',
        zmid=0
    ))

    fig.update_layout(
        title="섹터 점수",
        height=150,
        margin=dict(l=10, r=10, t=40, b=10)
    )

    return fig


def create_time_series_chart(data: pd.DataFrame, columns: list, title: str):
    """시계열 차트"""
    fig = go.Figure()

    for col in columns:
        if col in data.columns:
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data[col],
                mode='lines',
                name=col
            ))

    fig.update_layout(
        title=title,
        xaxis_title="날짜",
        yaxis_title="값",
        height=400,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig


def main():
    """메인 대시보드"""
    st.markdown('<h1 class="main-header">📊 거시경제 기반 시장 예측 시스템</h1>', unsafe_allow_html=True)

    # 사이드바
    st.sidebar.title("⚙️ 설정")

    # 분석 기간
    analysis_period = st.sidebar.selectbox(
        "분석 기간",
        ["1개월", "3개월", "6개월", "1년", "2년"]
    )

    # 가중치 설정
    st.sidebar.subheader("분석 가중치")
    macro_weight = st.sidebar.slider("거시경제", 0.0, 1.0, 0.30, 0.05)
    flow_weight = st.sidebar.slider("자금흐름", 0.0, 1.0, 0.25, 0.05)
    sentiment_weight = st.sidebar.slider("센티먼트", 0.0, 1.0, 0.20, 0.05)
    technical_weight = st.sidebar.slider("기술적", 0.0, 1.0, 0.25, 0.05)

    # 실시간 데이터 로드
    if YFINANCE_AVAILABLE:
        with st.spinner("실시간 데이터 로딩 중..."):
            data = load_realtime_data()
        if data:
            st.sidebar.success("✅ 실시간 데이터")
        else:
            st.sidebar.warning("⏳ 데이터 로드 중...")
    else:
        st.sidebar.error("yfinance 설치 필요: pip install yfinance")
        st.stop()

    if not data:
        st.error("데이터를 불러올 수 없습니다. 페이지를 새로고침해주세요.")
        st.stop()

    # 분석기 초기화
    macro_analyzer = MacroAnalyzer()
    flow_analyzer = FlowAnalyzer()
    sentiment_analyzer = SentimentAnalyzer(use_ml=False)
    technical_analyzer = TechnicalAnalyzer()
    prob_model = ProbabilityModel()
    scenario_analyzer = ScenarioAnalyzer()

    # 분석 실행
    macro_analysis = macro_analyzer.get_summary(data['macro'])
    flow_analysis = flow_analyzer.get_flow_summary(data['market'])
    sentiment_analysis = sentiment_analyzer.get_summary(data['news'])

    # 기술적 분석 (S&P 500 기준)
    if 'sp500' in data['market'].columns:
        technical_analysis = technical_analyzer.get_technical_summary(data['market']['sp500'])
    else:
        technical_analysis = {}

    # 확률 예측
    prediction = prob_model.predict_probability(
        macro_analysis=macro_analysis,
        flow_analysis=flow_analysis,
        sentiment_analysis=sentiment_analysis,
        technical_analysis=technical_analysis
    )

    # 시나리오 분석
    scenario_summary = scenario_analyzer.get_summary(
        macro_analysis, flow_analysis, sentiment_analysis
    )

    # ========== 메인 대시보드 ==========

    # 상단 요약
    st.header("📈 시장 전망 요약")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        direction_color = "bullish" if prediction.probability > 0.55 else ("bearish" if prediction.probability < 0.45 else "neutral")
        st.metric(
            label="예측 방향",
            value=prediction.direction.value,
            delta=f"확률: {prediction.probability*100:.1f}%"
        )

    with col2:
        st.metric(
            label="신뢰도",
            value=f"{prediction.confidence*100:.0f}%",
            delta="높음" if prediction.confidence > 0.7 else ("보통" if prediction.confidence > 0.5 else "낮음")
        )

    with col3:
        most_likely = scenario_summary.get('most_likely_scenario', {})
        st.metric(
            label="주요 시나리오",
            value=most_likely.get('name', 'N/A'),
            delta=f"{most_likely.get('probability', 0):.0f}%"
        )

    with col4:
        risk_regime = flow_analysis.get('risk_regime', 'N/A')
        st.metric(
            label="위험 선호도",
            value=risk_regime,
            delta=f"점수: {flow_analysis.get('risk_score', 0.5)*100:.0f}"
        )

    # 구분선
    st.divider()

    # 탭 구성 (동적으로 탭 추가)
    tab_names = [
        "🎯 종합 예측",
        "🌐 거시경제",
        "💹 자금흐름",
        "📰 센티먼트",
        "📊 기술적 분석",
        "💼 포트폴리오 분석",
        "📈 백테스트",
        "🤖 AI 분석",
        "🇰🇷 한국 주식",
        "🔧 고급 기능"
    ]
    tabs = st.tabs(tab_names)
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = tabs

    # ========== 탭 1: 종합 예측 ==========
    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("시장 방향 확률")
            gauge = create_gauge_chart(
                prediction.probability * 100,
                "상승 확률 (%)"
            )
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

    # ========== 탭 2: 거시경제 ==========
    with tab2:
        st.subheader("경기 사이클")
        cycle = macro_analysis.get('economic_cycle', 'N/A')
        st.info(f"현재 경기 단계: **{cycle}**")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("주요 거시경제 지표")

            # 거시경제 차트
            macro_chart = create_time_series_chart(
                data['macro'],
                ['fed_funds_rate', 'cpi', 'unemployment_rate'],
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
        if 'treasury_10y' in data['macro'].columns and 'yield_spread' in data['macro'].columns:
            yield_chart = create_time_series_chart(
                data['macro'],
                ['treasury_10y', 'yield_spread'],
                "금리 및 스프레드"
            )
            st.plotly_chart(yield_chart, use_container_width=True)

    # ========== 탭 3: 자금흐름 ==========
    with tab3:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("자금흐름 현황")

            st.markdown("**유입 자산**")
            for asset in flow_analysis.get('inflows', [])[:5]:
                st.write(f"📈 {asset}")

            st.markdown("**유출 자산**")
            for asset in flow_analysis.get('outflows', [])[:5]:
                st.write(f"📉 {asset}")

        with col2:
            st.subheader("시장 폭 지표")

            breadth = flow_analysis.get('market_breadth', {})

            metrics = [
                ("50일 MA 상위", breadth.get('pct_above_ma_50', 0)),
                ("200일 MA 상위", breadth.get('pct_above_ma_200', 0)),
                ("건강도 점수", breadth.get('health_score', 0) * 100),
            ]

            for label, value in metrics:
                st.metric(label, f"{value:.1f}%")

        # 자금흐름 차트
        st.subheader("섹터별 자금흐름")
        fund_flow_chart = create_time_series_chart(
            data['fund_flow'],
            list(data['fund_flow'].columns)[:5],
            "섹터별 누적 자금흐름"
        )
        st.plotly_chart(fund_flow_chart, use_container_width=True)

    # ========== 탭 4: 센티먼트 ==========
    with tab4:
        overall = sentiment_analysis.get('overall_analysis', {})

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("뉴스 센티먼트")

            dist = overall.get('sentiment_distribution', {})
            sentiment_df = pd.DataFrame({
                '센티먼트': ['긍정', '중립', '부정'],
                '건수': [
                    dist.get('positive', 0),
                    dist.get('neutral', 0),
                    dist.get('negative', 0)
                ]
            })

            fig = px.pie(sentiment_df, values='건수', names='센티먼트',
                        color='센티먼트',
                        color_discrete_map={'긍정': 'green', '중립': 'gray', '부정': 'red'})
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("센티먼트 점수")

            composite = overall.get('composite_score', 0)
            gauge = create_gauge_chart(
                (composite + 1) * 50,  # -1~1을 0~100으로
                "종합 센티먼트",
                0, 100
            )
            st.plotly_chart(gauge, use_container_width=True)

        # 주요 키워드
        st.subheader("주요 키워드")
        keywords = overall.get('top_keywords', [])
        if keywords:
            keyword_df = pd.DataFrame(keywords, columns=['키워드', '빈도'])
            st.bar_chart(keyword_df.set_index('키워드')['빈도'])

        # 최신 뉴스
        st.subheader("주요 뉴스")
        for news in data['news'][:5]:
            with st.expander(news.get('title', 'No Title')):
                st.write(f"**출처**: {news.get('source', 'N/A')}")
                st.write(f"**날짜**: {news.get('published_at', 'N/A')}")
                st.write(news.get('description', ''))

    # ========== 탭 5: 기술적 분석 ==========
    with tab5:
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

            st.metric("RSI", f"{momentum.get('rsi', 50):.1f}",
                     delta=momentum.get('rsi_signal', ''))

            st.metric("MACD", f"{momentum.get('macd', 0):.4f}",
                     delta=momentum.get('macd_cross', ''))

        # 가격 차트
        st.subheader("가격 및 이동평균")

        if 'sp500' in data['market'].columns:
            price_data = data['market'][['sp500']].copy()
            price_data['MA50'] = price_data['sp500'].rolling(50).mean()
            price_data['MA200'] = price_data['sp500'].rolling(200).mean()

            price_chart = create_time_series_chart(
                price_data,
                ['sp500', 'MA50', 'MA200'],
                "S&P 500 가격 및 이동평균"
            )
            st.plotly_chart(price_chart, use_container_width=True)

        # 지지/저항
        st.subheader("지지/저항선")
        sr = technical_analysis.get('support_resistance', {})

        col1, col2 = st.columns(2)
        with col1:
            st.metric("최근접 저항선", f"{sr.get('nearest_resistance', 'N/A')}")
            st.caption(f"거리: {sr.get('distance_to_resistance', 'N/A')}%")

        with col2:
            st.metric("최근접 지지선", f"{sr.get('nearest_support', 'N/A')}")
            st.caption(f"거리: {sr.get('distance_to_support', 'N/A')}%")

    # ========== 탭 6: 포트폴리오 분석 ==========
    with tab6:
        from dashboard.portfolio_page import render_portfolio_page
        render_portfolio_page()

    # ========== 탭 7: 백테스트 ==========
    with tab7:
        if BACKTEST_AVAILABLE:
            render_backtest_page()
        else:
            st.warning("백테스트 모듈을 사용할 수 없습니다.")
            st.info("backtest 패키지가 올바르게 설치되었는지 확인하세요.")

    # ========== 탭 8: AI 분석 ==========
    with tab8:
        if AI_ANALYSIS_AVAILABLE:
            render_ai_analysis_page()
        else:
            st.warning("AI 분석 모듈을 사용할 수 없습니다.")
            st.info("ai_analysis 패키지가 올바르게 설치되었는지 확인하세요.")
            st.markdown("""
            **필요한 패키지:**
            - openai (GPT API용)
            - feedparser (뉴스 수집용)
            """)

    # ========== 탭 9: 한국 주식 ==========
    with tab9:
        if KOREA_AVAILABLE:
            render_korea_page()
        else:
            st.warning("한국 주식 모듈을 사용할 수 없습니다.")
            st.info("korea 패키지가 올바르게 설치되었는지 확인하세요.")
            st.markdown("""
            **필요한 패키지:**
            - pykrx (KRX 데이터용)
            """)

    # ========== 탭 10: 고급 기능 ==========
    with tab10:
        if ADVANCED_AVAILABLE:
            render_advanced_features()
        else:
            st.warning("고급 기능 모듈을 사용할 수 없습니다.")
            st.info("advanced_features 모듈을 확인하세요.")

    # 푸터
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: gray;'>
        <p>⚠️ 본 시스템의 예측은 참고용이며, 투자 결정의 유일한 근거가 되어서는 안 됩니다.</p>
        <p>투자에 따른 책임은 본인에게 있습니다.</p>
        <p>마지막 업데이트: {}</p>
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), unsafe_allow_html=True)


if __name__ == "__main__":
    main()
