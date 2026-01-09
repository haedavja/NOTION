"""
종합 스코어카드 모듈
여러 분석 결과를 통합하여 하나의 종합 점수로 제공
"""

import streamlit as st
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from enum import Enum


class ScoreCategory(Enum):
    """점수 카테고리"""
    SNOWFLAKE = "펀더멘털"
    TECHNICAL = "기술적"
    SUPPLY_DEMAND = "수급"
    POTENTIAL = "잠재 요인"
    RALLY_CREDIBILITY = "상승 신뢰도"


@dataclass
class CategoryScore:
    """카테고리별 점수"""
    category: ScoreCategory
    score: float  # 0-100
    grade: str  # A, B+, B, C, D, F
    summary: str
    details: Dict[str, float] = field(default_factory=dict)


@dataclass
class ComprehensiveScorecard:
    """종합 스코어카드"""
    symbol: str
    name: str
    overall_score: float  # 0-100
    overall_grade: str
    overall_rating: int  # 1-5 stars
    recommendation: str  # 매수/보유/매도
    categories: List[CategoryScore] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    key_insight: str = ""


class ScorecardGenerator:
    """스코어카드 생성기"""

    def __init__(self):
        # 카테고리별 가중치
        self.weights = {
            ScoreCategory.SNOWFLAKE: 0.30,
            ScoreCategory.TECHNICAL: 0.20,
            ScoreCategory.SUPPLY_DEMAND: 0.20,
            ScoreCategory.POTENTIAL: 0.15,
            ScoreCategory.RALLY_CREDIBILITY: 0.15,
        }

    def generate(
        self,
        symbol: str,
        name: str,
        snowflake_scores=None,
        technical_data: Dict = None,
        supply_demand_data: Dict = None,
        potential_analysis=None,
        rally_credibility=None,
    ) -> ComprehensiveScorecard:
        """종합 스코어카드 생성"""
        categories = []
        total_weighted_score = 0
        total_weight = 0

        # 1. Snowflake (펀더멘털) 점수
        if snowflake_scores:
            score = (snowflake_scores.total / 6) * 100
            grade = self._get_grade(score)
            categories.append(CategoryScore(
                category=ScoreCategory.SNOWFLAKE,
                score=score,
                grade=grade,
                summary=self._get_snowflake_summary(snowflake_scores),
                details={
                    'value': snowflake_scores.value,
                    'future': snowflake_scores.future,
                    'past': snowflake_scores.past,
                    'dividend': snowflake_scores.dividend,
                    'health': snowflake_scores.health,
                }
            ))
            total_weighted_score += score * self.weights[ScoreCategory.SNOWFLAKE]
            total_weight += self.weights[ScoreCategory.SNOWFLAKE]

        # 2. 기술적 분석 점수
        if technical_data:
            score = self._calculate_technical_score(technical_data)
            grade = self._get_grade(score)
            categories.append(CategoryScore(
                category=ScoreCategory.TECHNICAL,
                score=score,
                grade=grade,
                summary=self._get_technical_summary(technical_data),
                details=technical_data,
            ))
            total_weighted_score += score * self.weights[ScoreCategory.TECHNICAL]
            total_weight += self.weights[ScoreCategory.TECHNICAL]

        # 3. 수급 점수
        if supply_demand_data:
            score = self._calculate_supply_demand_score(supply_demand_data)
            grade = self._get_grade(score)
            categories.append(CategoryScore(
                category=ScoreCategory.SUPPLY_DEMAND,
                score=score,
                grade=grade,
                summary=self._get_supply_demand_summary(supply_demand_data),
                details=supply_demand_data,
            ))
            total_weighted_score += score * self.weights[ScoreCategory.SUPPLY_DEMAND]
            total_weight += self.weights[ScoreCategory.SUPPLY_DEMAND]

        # 4. 잠재 요인 점수
        if potential_analysis:
            bullish = getattr(potential_analysis, 'bullish_score', 50)
            bearish = getattr(potential_analysis, 'bearish_score', 50)
            score = max(0, min(100, 50 + (bullish - bearish)))
            grade = self._get_grade(score)
            categories.append(CategoryScore(
                category=ScoreCategory.POTENTIAL,
                score=score,
                grade=grade,
                summary=f"상승 {bullish:.0f}점 / 하락 {bearish:.0f}점",
                details={'bullish': bullish, 'bearish': bearish},
            ))
            total_weighted_score += score * self.weights[ScoreCategory.POTENTIAL]
            total_weight += self.weights[ScoreCategory.POTENTIAL]

        # 5. 상승 신뢰도 점수
        if rally_credibility:
            score = getattr(rally_credibility, 'overall', 50)
            grade = self._get_grade(score)
            categories.append(CategoryScore(
                category=ScoreCategory.RALLY_CREDIBILITY,
                score=score,
                grade=grade,
                summary=getattr(rally_credibility, 'level', 'N/A').value if hasattr(rally_credibility.level, 'value') else 'N/A',
                details={},
            ))
            total_weighted_score += score * self.weights[ScoreCategory.RALLY_CREDIBILITY]
            total_weight += self.weights[ScoreCategory.RALLY_CREDIBILITY]

        # 종합 점수 계산
        if total_weight > 0:
            overall_score = total_weighted_score / total_weight
        else:
            overall_score = 50

        overall_grade = self._get_grade(overall_score)
        overall_rating = self._get_star_rating(overall_score)
        recommendation = self._get_recommendation(overall_score, categories)

        # 강점/약점 분석
        strengths, weaknesses = self._analyze_strengths_weaknesses(categories)

        # 핵심 인사이트
        key_insight = self._generate_key_insight(overall_score, categories, strengths, weaknesses)

        return ComprehensiveScorecard(
            symbol=symbol,
            name=name,
            overall_score=overall_score,
            overall_grade=overall_grade,
            overall_rating=overall_rating,
            recommendation=recommendation,
            categories=categories,
            strengths=strengths,
            weaknesses=weaknesses,
            key_insight=key_insight,
        )

    def _get_grade(self, score: float) -> str:
        """점수를 등급으로 변환"""
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B+"
        elif score >= 60:
            return "B"
        elif score >= 50:
            return "C"
        elif score >= 40:
            return "D"
        else:
            return "F"

    def _get_star_rating(self, score: float) -> int:
        """점수를 별점으로 변환 (1-5)"""
        if score >= 80:
            return 5
        elif score >= 65:
            return 4
        elif score >= 50:
            return 3
        elif score >= 35:
            return 2
        else:
            return 1

    def _get_recommendation(self, score: float, categories: List[CategoryScore]) -> str:
        """투자 권고 생성"""
        if score >= 70:
            return "적극 매수"
        elif score >= 60:
            return "매수"
        elif score >= 50:
            return "보유"
        elif score >= 40:
            return "비중 축소"
        else:
            return "매도 검토"

    def _calculate_technical_score(self, data: Dict) -> float:
        """기술적 분석 점수 계산"""
        score = 50  # 기본 점수

        # RSI
        rsi = data.get('rsi', 50)
        if 40 <= rsi <= 60:
            score += 10
        elif rsi < 30:
            score += 15  # 과매도 = 매수 기회
        elif rsi > 70:
            score -= 10  # 과매수 = 주의

        # 추세
        trend = data.get('trend', '')
        if trend == '상승':
            score += 15
        elif trend == '하락':
            score -= 15

        # 이동평균
        ma_signal = data.get('ma_signal', '')
        if '골든크로스' in str(ma_signal):
            score += 10
        elif '데드크로스' in str(ma_signal):
            score -= 10

        return max(0, min(100, score))

    def _calculate_supply_demand_score(self, data: Dict) -> float:
        """수급 점수 계산"""
        score = 50

        foreign = data.get('foreign_net', 0)
        inst = data.get('inst_net', 0)

        if foreign > 0:
            score += 15
        elif foreign < 0:
            score -= 10

        if inst > 0:
            score += 10
        elif inst < 0:
            score -= 5

        trend = data.get('trend', '')
        if trend == '매집':
            score += 15
        elif trend == '이탈':
            score -= 15

        return max(0, min(100, score))

    def _get_snowflake_summary(self, scores) -> str:
        """Snowflake 요약"""
        total = scores.total
        if total >= 4.5:
            return "우수한 펀더멘털"
        elif total >= 3.5:
            return "양호한 펀더멘털"
        elif total >= 2.5:
            return "평균적 펀더멘털"
        else:
            return "취약한 펀더멘털"

    def _get_technical_summary(self, data: Dict) -> str:
        """기술적 분석 요약"""
        trend = data.get('trend', '중립')
        rsi = data.get('rsi', 50)
        if rsi < 30:
            return f"{trend} 추세, 과매도 구간"
        elif rsi > 70:
            return f"{trend} 추세, 과매수 구간"
        else:
            return f"{trend} 추세"

    def _get_supply_demand_summary(self, data: Dict) -> str:
        """수급 요약"""
        trend = data.get('trend', '중립')
        return f"수급 {trend}"

    def _analyze_strengths_weaknesses(self, categories: List[CategoryScore]):
        """강점/약점 분석"""
        strengths = []
        weaknesses = []

        for cat in categories:
            if cat.score >= 70:
                strengths.append(f"{cat.category.value}: {cat.summary}")
            elif cat.score < 40:
                weaknesses.append(f"{cat.category.value}: {cat.summary}")

        return strengths, weaknesses

    def _generate_key_insight(
        self,
        score: float,
        categories: List[CategoryScore],
        strengths: List[str],
        weaknesses: List[str]
    ) -> str:
        """핵심 인사이트 생성"""
        if score >= 70:
            if len(strengths) >= 3:
                return "여러 영역에서 강점을 보이는 우수한 투자 후보입니다."
            else:
                return "전반적으로 양호하며 투자 매력이 있습니다."
        elif score >= 50:
            if weaknesses:
                weak_areas = [w.split(':')[0] for w in weaknesses[:2]]
                return f"보통 수준이며, {', '.join(weak_areas)} 개선이 필요합니다."
            else:
                return "평균적인 수준으로, 추가 분석이 권장됩니다."
        else:
            if len(weaknesses) >= 2:
                return "여러 약점이 존재하여 투자에 주의가 필요합니다."
            else:
                return "현재 투자 매력이 낮습니다."


def render_comprehensive_scorecard(scorecard: ComprehensiveScorecard):
    """종합 스코어카드 렌더링"""
    st.markdown(f"## 📊 {scorecard.name} ({scorecard.symbol}) 종합 스코어카드")

    # 상단 요약
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        stars = "⭐" * scorecard.overall_rating
        st.metric(
            "종합 점수",
            f"{scorecard.overall_score:.0f}점",
            f"{scorecard.overall_grade} 등급"
        )
        st.markdown(f"**{stars}**")

    with col2:
        # 투자 권고 색상
        rec_colors = {
            '적극 매수': '#22c55e',
            '매수': '#4ade80',
            '보유': '#facc15',
            '비중 축소': '#fb923c',
            '매도 검토': '#ef4444',
        }
        color = rec_colors.get(scorecard.recommendation, '#888')
        st.markdown(f"""
        <div style='background: {color}; padding: 1rem; border-radius: 8px;
                    text-align: center; color: white;'>
            <div style='font-size: 0.8em;'>투자 권고</div>
            <div style='font-size: 1.5em; font-weight: bold;'>{scorecard.recommendation}</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        if scorecard.strengths:
            st.markdown("**💪 강점**")
            for s in scorecard.strengths[:2]:
                st.markdown(f"✅ {s}")

    with col4:
        if scorecard.weaknesses:
            st.markdown("**⚠️ 약점**")
            for w in scorecard.weaknesses[:2]:
                st.markdown(f"⚠️ {w}")

    # 핵심 인사이트
    st.info(f"💡 **핵심 인사이트**: {scorecard.key_insight}")

    st.divider()

    # 카테고리별 점수
    st.markdown("### 📋 영역별 분석")

    cols = st.columns(len(scorecard.categories)) if scorecard.categories else []

    for i, cat in enumerate(scorecard.categories):
        with cols[i]:
            # 점수에 따른 색상
            if cat.score >= 70:
                color = '#22c55e'
            elif cat.score >= 50:
                color = '#facc15'
            else:
                color = '#ef4444'

            st.markdown(f"""
            <div style='text-align: center; padding: 0.5rem;
                        border: 2px solid {color}; border-radius: 8px;'>
                <div style='font-size: 0.9em; color: {color};'>{cat.category.value}</div>
                <div style='font-size: 2em; font-weight: bold; color: {color};'>{cat.score:.0f}</div>
                <div style='font-size: 1.2em;'>{cat.grade}</div>
                <div style='font-size: 0.75em; color: gray;'>{cat.summary}</div>
            </div>
            """, unsafe_allow_html=True)


# 싱글톤 인스턴스
scorecard_generator = ScorecardGenerator()
