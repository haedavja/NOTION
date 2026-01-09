"""
기능 통합 유틸리티
Snowflake와 추천 기능을 기존 페이지에 쉽게 통합하기 위한 헬퍼 함수들
"""

import streamlit as st
from typing import Dict, Optional, List, Tuple

try:
    from analysis.snowflake_viz import (
        SnowflakeAnalyzer, SnowflakeScores,
        create_snowflake_chart, get_score_interpretation,
        get_overall_rating, snowflake_analyzer
    )
    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SNOWFLAKE_AVAILABLE = False

try:
    from analysis.recommendation import (
        PersonalizedRecommender, Recommendation,
        get_recommendation_category_name, recommender,
        StockProfile
    )
    RECOMMENDATION_AVAILABLE = True
except ImportError:
    RECOMMENDATION_AVAILABLE = False


def convert_fundamentals_to_snowflake_data(fundamentals) -> Dict:
    """
    StockFundamentals 또는 dict를 Snowflake 분석용 데이터로 변환

    Args:
        fundamentals: StockFundamentals dataclass 또는 dict

    Returns:
        Snowflake 분석에 사용할 dict
    """
    if hasattr(fundamentals, '__dict__'):
        # dataclass인 경우
        return {
            'per': getattr(fundamentals, 'per', None),
            'pbr': getattr(fundamentals, 'pbr', None),
            'roe': getattr(fundamentals, 'roe', None),
            'dividend_yield': getattr(fundamentals, 'dividend_yield', None),
            # 추가 필드들 (없으면 기본값)
            'debt_ratio': getattr(fundamentals, 'debt_ratio', 100),
            'current_ratio': getattr(fundamentals, 'current_ratio', 1.5),
            'revenue_growth': getattr(fundamentals, 'revenue_growth', 0),
            'operating_margin': getattr(fundamentals, 'operating_margin', 10),
        }
    elif isinstance(fundamentals, dict):
        return fundamentals
    else:
        return {}


def render_mini_snowflake(fundamentals, name: str = "종목",
                          sector: str = "default", show_details: bool = True):
    """
    미니 Snowflake 차트 렌더링 (기존 페이지에 쉽게 삽입 가능)

    Args:
        fundamentals: 펀더멘털 데이터 (dict 또는 dataclass)
        name: 종목명
        sector: 섹터 (PER 평균 참조용)
        show_details: 상세 해석 표시 여부
    """
    if not SNOWFLAKE_AVAILABLE:
        st.info("Snowflake 분석을 사용하려면 plotly가 필요합니다.")
        return

    data = convert_fundamentals_to_snowflake_data(fundamentals)
    if not data:
        st.warning("Snowflake 분석에 필요한 데이터가 부족합니다.")
        return

    scores = snowflake_analyzer.calculate_scores(
        fundamentals=data,
        sector=sector
    )

    # 차트 렌더링
    fig = create_snowflake_chart(scores, name, show_benchmark=True)
    fig.update_layout(height=350)  # 미니 버전
    st.plotly_chart(fig, use_container_width=True)

    # 등급
    grade, emoji, description = get_overall_rating(scores)
    st.markdown(f"**{emoji} 종합 등급: {grade}** - {description}")

    # 상세 해석
    if show_details:
        with st.expander("📋 상세 해석", expanded=False):
            interpretations = get_score_interpretation(scores)
            for category, interp in interpretations.items():
                st.markdown(f"**{category}**: {interp}")

    return scores


def render_similar_recommendations(
    current_code: str,
    current_sector: str = None,
    limit: int = 3,
    exclude_codes: List[str] = None
):
    """
    유사 종목 추천 렌더링

    Args:
        current_code: 현재 종목 코드
        current_sector: 현재 종목 섹터
        limit: 추천 개수
        exclude_codes: 제외할 종목 코드 리스트
    """
    if not RECOMMENDATION_AVAILABLE:
        return

    st.markdown("### 🔄 유사 종목 추천")

    # 추천 엔진 설정
    recommender.set_user_profile(
        portfolio=[current_code],
        preferred_sectors=[current_sector] if current_sector else [],
        investment_style='balanced'
    )

    # 추천 생성
    recommendations = recommender.get_recommendations(limit=limit + 2)

    # 현재 종목 및 제외 종목 필터링
    exclude = set([current_code] + (exclude_codes or []))
    filtered_recs = [r for r in recommendations if r.code not in exclude][:limit]

    if not filtered_recs:
        st.info("유사한 종목을 찾을 수 없습니다.")
        return

    # 추천 표시
    cols = st.columns(len(filtered_recs))
    for i, rec in enumerate(filtered_recs):
        with cols[i]:
            category_name = get_recommendation_category_name(rec.category)
            highlights = " | ".join(rec.highlights[:2]) if rec.highlights else ""

            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #3498db, #2ecc71);
                        padding: 0.8rem; border-radius: 8px; color: white; text-align: center;'>
                <div style='font-size: 0.75em; opacity: 0.8;'>{category_name}</div>
                <div style='font-size: 1.1em; font-weight: bold;'>{rec.name}</div>
                <div style='font-size: 0.8em;'>{rec.code}</div>
                <div style='font-size: 0.75em; margin-top: 4px;'>{highlights}</div>
            </div>
            """, unsafe_allow_html=True)

    return filtered_recs


def get_snowflake_scores_for_stock(fundamentals, sector: str = "default") -> Optional[SnowflakeScores]:
    """
    종목의 Snowflake 점수 계산 (차트 없이 점수만)

    Args:
        fundamentals: 펀더멘털 데이터
        sector: 섹터

    Returns:
        SnowflakeScores 또는 None
    """
    if not SNOWFLAKE_AVAILABLE:
        return None

    data = convert_fundamentals_to_snowflake_data(fundamentals)
    if not data:
        return None

    return snowflake_analyzer.calculate_scores(
        fundamentals=data,
        sector=sector
    )


def render_snowflake_summary_row(
    stocks: List[Tuple[str, str, Dict, str]],
    title: str = "종목별 Snowflake 요약"
):
    """
    여러 종목의 Snowflake 요약을 한 줄로 표시

    Args:
        stocks: [(코드, 이름, fundamentals, sector), ...] 리스트
        title: 섹션 제목
    """
    if not SNOWFLAKE_AVAILABLE:
        return

    st.markdown(f"### {title}")

    cols = st.columns(min(len(stocks), 5))

    for i, (code, name, fundamentals, sector) in enumerate(stocks[:5]):
        with cols[i]:
            scores = get_snowflake_scores_for_stock(fundamentals, sector)
            if scores:
                grade, emoji, _ = get_overall_rating(scores)
                st.markdown(f"""
                <div style='text-align: center; padding: 0.5rem;
                            border: 1px solid #ddd; border-radius: 8px;'>
                    <div style='font-size: 0.9em; font-weight: bold;'>{name}</div>
                    <div style='font-size: 2em;'>{emoji}</div>
                    <div style='font-size: 1.2em; font-weight: bold;'>{grade}</div>
                    <div style='font-size: 0.8em; color: gray;'>
                        총점 {scores.total:.1f}/6
                    </div>
                </div>
                """, unsafe_allow_html=True)


def get_investment_insight(scores: SnowflakeScores) -> str:
    """
    Snowflake 점수 기반 투자 인사이트 생성

    Args:
        scores: SnowflakeScores

    Returns:
        인사이트 텍스트
    """
    insights = []

    # 강점 분석
    strengths = []
    if scores.value >= 4.0:
        strengths.append("저평가 매력")
    if scores.future >= 4.0:
        strengths.append("성장 기대")
    if scores.past >= 4.0:
        strengths.append("견실한 실적")
    if scores.dividend >= 4.0:
        strengths.append("배당 매력")
    if scores.health >= 4.0:
        strengths.append("재무 안정성")

    # 약점 분석
    weaknesses = []
    if scores.value < 2.5:
        weaknesses.append("고평가 우려")
    if scores.future < 2.5:
        weaknesses.append("성장 둔화")
    if scores.past < 2.5:
        weaknesses.append("실적 부진")
    if scores.dividend < 2.5:
        weaknesses.append("낮은 배당")
    if scores.health < 2.5:
        weaknesses.append("재무 리스크")

    if strengths:
        insights.append(f"**강점**: {', '.join(strengths)}")
    if weaknesses:
        insights.append(f"**약점**: {', '.join(weaknesses)}")

    # 종합 평가
    total = scores.total
    if total >= 4.5:
        insights.append("→ 전반적으로 우수한 투자 후보입니다.")
    elif total >= 3.5:
        insights.append("→ 양호하나 일부 약점에 주의가 필요합니다.")
    elif total >= 2.5:
        insights.append("→ 평균 수준이며 개선 여지가 있습니다.")
    else:
        insights.append("→ 투자 전 신중한 검토가 필요합니다.")

    return "\n".join(insights)


# 섹터 매핑 (한국어 -> 영어 키)
SECTOR_MAPPING = {
    '반도체': '반도체',
    'IT': 'IT',
    '소프트웨어': 'IT',
    '인터넷': 'IT',
    '자동차': '자동차',
    '2차전지': '2차전지',
    '배터리': '2차전지',
    '바이오': '바이오',
    '제약': '제약',
    '금융': '금융',
    '은행': '은행',
    '보험': '보험',
    '증권': '금융',
    '건설': '건설',
    '화학': '화학',
    '철강': '철강',
    '조선': '조선',
    '유통': '유통',
    '미디어': '미디어',
    '엔터': '엔터',
    '통신': '통신',
    '에너지': '에너지',
    '전자': 'IT',
    '기계': '기계',
    '지주': '지주',
}


def normalize_sector(sector: str) -> str:
    """섹터명 정규화"""
    if not sector:
        return 'default'
    return SECTOR_MAPPING.get(sector, sector)
