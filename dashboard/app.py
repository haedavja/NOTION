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

from data.macro_indicators import MacroIndicators, get_sample_macro_data
from data.market_data import MarketData, get_sample_market_data
from data.fund_flow import FundFlowTracker, get_sample_fund_flow
from data.news_collector import NewsCollector, get_sample_news
from analysis.macro_analysis import MacroAnalyzer
from analysis.flow_analysis import FlowAnalyzer
from analysis.sentiment import SentimentAnalyzer
from analysis.technical import TechnicalAnalyzer
from prediction.probability_model import ProbabilityModel
from prediction.scenarios import ScenarioAnalyzer


# 페이지 설정
st.set_page_config(
    page_title="거시경제 시장 예측 시스템",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS 스타일
st.markdown("""
<style>
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
    .bullish {
        color: #00c853;
        font-weight: bold;
    }
    .bearish {
        color: #ff1744;
        font-weight: bold;
    }
    .neutral {
        color: #ffc107;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600)
def load_sample_data():
    """샘플 데이터 로드 (캐시됨)"""
    return {
        'macro': get_sample_macro_data(),
        'market': get_sample_market_data(),
        'fund_flow': get_sample_fund_flow(),
        'news': get_sample_news(),
    }


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

    # 데이터 소스 선택
    data_source = st.sidebar.radio(
        "데이터 소스",
        ["샘플 데이터", "실시간 데이터 (API 필요)"]
    )

    # API 키 입력 (실시간 데이터 선택 시)
    if data_source == "실시간 데이터 (API 필요)":
        st.sidebar.subheader("API 키 설정")
        fred_key = st.sidebar.text_input("FRED API Key", type="password")
        news_key = st.sidebar.text_input("News API Key", type="password")

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

    # 데이터 로드
    if data_source == "샘플 데이터":
        data = load_sample_data()
    else:
        st.warning("실시간 데이터는 API 키가 필요합니다. 샘플 데이터를 사용합니다.")
        data = load_sample_data()

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

    # 탭 구성
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🎯 종합 예측",
        "🌐 거시경제",
        "💹 자금흐름",
        "📰 센티먼트",
        "📊 기술적 분석"
    ])

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
