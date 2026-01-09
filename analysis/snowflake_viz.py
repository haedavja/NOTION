"""
Snowflake 시각화 모듈
Simply Wall St 스타일 5축 레이더 차트
가치(Value), 미래(Future), 과거(Past), 배당(Dividend), 건전성(Health)
"""

import plotly.graph_objects as go
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np

# 중앙화된 설정 사용
try:
    from config.constants import SNOWFLAKE
    _USE_CENTRAL_CONFIG = True
except ImportError:
    _USE_CENTRAL_CONFIG = False


@dataclass
class SnowflakeScores:
    """Snowflake 5축 점수"""
    value: float  # 가치 (저평가 정도)
    future: float  # 미래 (성장 전망)
    past: float  # 과거 (실적 일관성)
    dividend: float  # 배당 (배당 매력)
    health: float  # 건전성 (재무 안정성)

    @property
    def total(self) -> float:
        """종합 점수 (가중 평균) - 건전성/가치 비중 높임"""
        # 중앙화된 설정 사용 (config.constants.SNOWFLAKE)
        if _USE_CENTRAL_CONFIG:
            weights = SNOWFLAKE.weights
        else:
            # 폴백: 기본 가중치
            weights = {'value': 0.25, 'future': 0.20, 'past': 0.20,
                       'dividend': 0.10, 'health': 0.25}
        return (self.value * weights['value'] +
                self.future * weights['future'] +
                self.past * weights['past'] +
                self.dividend * weights['dividend'] +
                self.health * weights['health'])

    @property
    def total_simple(self) -> float:
        """종합 점수 (단순 평균)"""
        return (self.value + self.future + self.past +
                self.dividend + self.health) / 5

    @property
    def min_score(self) -> float:
        """최저 점수 (약점 파악용)"""
        return min(self.value, self.future, self.past, self.dividend, self.health)

    def to_dict(self) -> Dict[str, float]:
        return {
            '가치': self.value,
            '미래': self.future,
            '과거': self.past,
            '배당': self.dividend,
            '건전성': self.health
        }


class SnowflakeAnalyzer:
    """Snowflake 분석기"""

    # 섹터별 평균 PER - 중앙화된 설정 사용
    @property
    def SECTOR_AVG_PER(self) -> Dict[str, float]:
        if _USE_CENTRAL_CONFIG:
            return SNOWFLAKE.sector_per
        else:
            # 폴백: 기본값
            return {
                '반도체': 20, '소프트웨어': 30, 'IT': 25,
                '금융': 10, '은행': 8, '보험': 12,
                '바이오': 50, '제약': 25, '헬스케어': 22,
                '자동차': 10, '철강': 8, '화학': 12,
                '유통': 15, '미디어': 18, '엔터': 25,
                '건설': 10, '조선': 15, '기계': 12,
                '식품': 15, '음료': 20, 'default': 15
            }

    def calculate_scores(self,
                        fundamentals: Dict,
                        technical: Dict = None,
                        historical: Dict = None,
                        sector: str = 'default') -> SnowflakeScores:
        """
        Snowflake 점수 계산

        Args:
            fundamentals: 펀더멘털 데이터 (PER, PBR, ROE, 배당 등)
            technical: 기술적 분석 데이터
            historical: 과거 실적 데이터
            sector: 섹터 (평균 PER 참조용)

        Returns:
            SnowflakeScores
        """
        value_score = self._calc_value_score(fundamentals, sector)
        future_score = self._calc_future_score(fundamentals, technical)
        past_score = self._calc_past_score(fundamentals, historical)
        dividend_score = self._calc_dividend_score(fundamentals)
        health_score = self._calc_health_score(fundamentals)

        return SnowflakeScores(
            value=value_score,
            future=future_score,
            past=past_score,
            dividend=dividend_score,
            health=health_score
        )

    def _calc_value_score(self, data: Dict, sector: str) -> float:
        """
        가치 점수 (0-6)
        - PER: 섹터 평균 대비 저평가 정도
        - PBR: 1 미만이면 가점
        - PEG: 1 미만이면 가점
        """
        score = 3.0  # 기본 점수

        # PER 평가
        per = data.get('per') or data.get('PER')
        if per and per > 0:
            avg_per = self.SECTOR_AVG_PER.get(sector, 15)
            per_ratio = per / avg_per

            if per_ratio < 0.5:
                score += 1.5  # 크게 저평가
            elif per_ratio < 0.8:
                score += 1.0  # 저평가
            elif per_ratio < 1.0:
                score += 0.5  # 약간 저평가
            elif per_ratio > 2.0:
                score -= 1.5  # 크게 고평가
            elif per_ratio > 1.5:
                score -= 1.0  # 고평가

        # PBR 평가
        pbr = data.get('pbr') or data.get('PBR')
        if pbr and pbr > 0:
            if pbr < 0.7:
                score += 1.0
            elif pbr < 1.0:
                score += 0.5
            elif pbr > 3.0:
                score -= 0.5

        # PSR 평가 (있는 경우)
        psr = data.get('psr') or data.get('PSR')
        if psr and psr > 0:
            if psr < 1.0:
                score += 0.5
            elif psr > 5.0:
                score -= 0.5

        return max(0, min(6, score))

    def _calc_future_score(self, data: Dict, technical: Dict = None) -> float:
        """
        미래 점수 (0-6)
        - 매출 성장률
        - 이익 성장률
        - 애널리스트 컨센서스
        - 추세 (기술적)
        """
        score = 3.0

        # 매출 성장률
        rev_growth = data.get('revenue_growth') or data.get('매출성장률', 0)
        if rev_growth > 20:
            score += 1.5
        elif rev_growth > 10:
            score += 1.0
        elif rev_growth > 5:
            score += 0.5
        elif rev_growth < -10:
            score -= 1.0
        elif rev_growth < 0:
            score -= 0.5

        # 이익 성장률
        earn_growth = data.get('earnings_growth') or data.get('이익성장률', 0)
        if earn_growth > 30:
            score += 1.0
        elif earn_growth > 15:
            score += 0.5
        elif earn_growth < -20:
            score -= 1.0
        elif earn_growth < 0:
            score -= 0.5

        # 기술적 추세
        if technical:
            trend = technical.get('trend', '')
            if trend == '상승':
                score += 0.5
            elif trend == '하락':
                score -= 0.5

        return max(0, min(6, score))

    def _calc_past_score(self, data: Dict, historical: Dict = None) -> float:
        """
        과거 점수 (0-6)
        - ROE 일관성
        - 수익성 트렌드
        - 실적 서프라이즈 이력
        """
        score = 3.0

        # ROE 평가
        roe = data.get('roe') or data.get('ROE', 0)
        if roe > 20:
            score += 1.5
        elif roe > 15:
            score += 1.0
        elif roe > 10:
            score += 0.5
        elif roe < 5:
            score -= 0.5
        elif roe < 0:
            score -= 1.5

        # 영업이익률
        op_margin = data.get('operating_margin') or data.get('영업이익률', 0)
        if op_margin > 20:
            score += 1.0
        elif op_margin > 10:
            score += 0.5
        elif op_margin < 0:
            score -= 1.0

        # 순이익률
        net_margin = data.get('net_margin') or data.get('순이익률', 0)
        if net_margin > 15:
            score += 0.5
        elif net_margin < 0:
            score -= 0.5

        return max(0, min(6, score))

    def _calc_dividend_score(self, data: Dict) -> float:
        """
        배당 점수 (0-6)
        - 배당수익률
        - 배당성향
        - 배당 성장 이력
        """
        score = 3.0

        # 배당수익률
        div_yield = data.get('dividend_yield') or data.get('배당수익률', 0)
        if div_yield > 5:
            score += 1.5  # 고배당 (최대 1.5점으로 조정)
        elif div_yield > 3:
            score += 1.0
        elif div_yield > 2:
            score += 0.7
        elif div_yield > 1:
            score += 0.3
        elif div_yield == 0:
            score -= 0.3  # 무배당 (성장주는 배당 없는 것이 정상, 페널티 완화)

        # 배당성향 (적정 수준 30-60%가 좋음)
        payout = data.get('payout_ratio') or data.get('배당성향', 0)
        if 30 <= payout <= 60:
            score += 0.5
        elif payout > 90:
            score -= 0.5  # 지속 가능성 우려

        return max(0, min(6, score))

    def _calc_health_score(self, data: Dict) -> float:
        """
        건전성 점수 (0-6)
        - 부채비율
        - 유동비율
        - 이자보상배율
        """
        score = 3.0

        # 부채비율
        debt_ratio = data.get('debt_ratio') or data.get('부채비율', 100)
        if debt_ratio < 50:
            score += 1.5
        elif debt_ratio < 100:
            score += 1.0
        elif debt_ratio < 150:
            score += 0.5
        elif debt_ratio > 300:
            score -= 1.5  # 매우 높은 부채
        elif debt_ratio > 200:
            score -= 1.0  # 높은 부채

        # 유동비율
        current_ratio = data.get('current_ratio') or data.get('유동비율', 1)
        if current_ratio > 2:
            score += 1.0
        elif current_ratio > 1.5:
            score += 0.5
        elif current_ratio < 1:
            score -= 1.0

        # 당좌비율 (있는 경우)
        quick_ratio = data.get('quick_ratio') or data.get('당좌비율')
        if quick_ratio:
            if quick_ratio > 1.5:
                score += 0.5
            elif quick_ratio < 0.5:
                score -= 0.5

        return max(0, min(6, score))


def create_snowflake_chart(scores: SnowflakeScores,
                          name: str = "종목",
                          show_benchmark: bool = True) -> go.Figure:
    """
    Snowflake 레이더 차트 생성

    Args:
        scores: SnowflakeScores 객체
        name: 종목명
        show_benchmark: 벤치마크(평균) 표시 여부

    Returns:
        Plotly Figure
    """
    categories = ['가치', '미래', '과거', '배당', '건전성']
    values = [scores.value, scores.future, scores.past,
              scores.dividend, scores.health]

    # 차트 닫기 위해 첫 값 추가
    values_closed = values + [values[0]]
    categories_closed = categories + [categories[0]]

    fig = go.Figure()

    # 벤치마크 (평균 = 3)
    if show_benchmark:
        benchmark = [3, 3, 3, 3, 3, 3]
        fig.add_trace(go.Scatterpolar(
            r=benchmark,
            theta=categories_closed,
            fill='toself',
            fillcolor='rgba(128, 128, 128, 0.1)',
            line=dict(color='gray', width=1, dash='dash'),
            name='평균 기준'
        ))

    # 메인 차트
    # 점수에 따른 색상 결정
    total = scores.total
    if total >= 4.5:
        color = 'rgb(0, 200, 83)'  # 녹색 - 우수
        fill_color = 'rgba(0, 200, 83, 0.3)'
    elif total >= 3.5:
        color = 'rgb(0, 176, 255)'  # 파랑 - 양호
        fill_color = 'rgba(0, 176, 255, 0.3)'
    elif total >= 2.5:
        color = 'rgb(255, 193, 7)'  # 노랑 - 보통
        fill_color = 'rgba(255, 193, 7, 0.3)'
    else:
        color = 'rgb(255, 82, 82)'  # 빨강 - 주의
        fill_color = 'rgba(255, 82, 82, 0.3)'

    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill='toself',
        fillcolor=fill_color,
        line=dict(color=color, width=2),
        name=name,
        text=[f'{v:.1f}/6' for v in values_closed],
        hovertemplate='%{theta}: %{r:.1f}/6<extra></extra>'
    ))

    # 레이아웃
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 6],
                tickvals=[1, 2, 3, 4, 5, 6],
                ticktext=['1', '2', '3', '4', '5', '6'],
                tickfont=dict(size=10),
                gridcolor='rgba(128, 128, 128, 0.3)'
            ),
            angularaxis=dict(
                tickfont=dict(size=12, color='white'),
                gridcolor='rgba(128, 128, 128, 0.3)'
            ),
            bgcolor='rgba(0, 0, 0, 0)'
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        title=dict(
            text=f'{name} Snowflake 분석',
            x=0.5,
            font=dict(size=16)
        ),
        paper_bgcolor='rgba(0, 0, 0, 0)',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        margin=dict(l=80, r=80, t=80, b=80),
        height=400
    )

    return fig


def create_comparison_snowflake(stocks: List[Tuple[str, SnowflakeScores]]) -> go.Figure:
    """
    여러 종목 비교 Snowflake 차트

    Args:
        stocks: [(종목명, SnowflakeScores), ...] 리스트

    Returns:
        Plotly Figure
    """
    categories = ['가치', '미래', '과거', '배당', '건전성']
    categories_closed = categories + [categories[0]]

    colors = [
        'rgb(0, 176, 255)',   # 파랑
        'rgb(255, 82, 82)',    # 빨강
        'rgb(0, 200, 83)',     # 녹색
        'rgb(255, 193, 7)',    # 노랑
        'rgb(156, 39, 176)'    # 보라
    ]

    fig = go.Figure()

    for i, (name, scores) in enumerate(stocks[:5]):  # 최대 5개
        values = [scores.value, scores.future, scores.past,
                  scores.dividend, scores.health]
        values_closed = values + [values[0]]

        color = colors[i % len(colors)]
        fill_color = color.replace('rgb', 'rgba').replace(')', ', 0.15)')

        fig.add_trace(go.Scatterpolar(
            r=values_closed,
            theta=categories_closed,
            fill='toself',
            fillcolor=fill_color,
            line=dict(color=color, width=2),
            name=f'{name} ({scores.total:.1f}점)',
            hovertemplate=f'{name}<br>%{{theta}}: %{{r:.1f}}/6<extra></extra>'
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 6],
                tickvals=[1, 2, 3, 4, 5, 6],
                gridcolor='rgba(128, 128, 128, 0.3)'
            ),
            angularaxis=dict(
                tickfont=dict(size=12),
                gridcolor='rgba(128, 128, 128, 0.3)'
            ),
            bgcolor='rgba(0, 0, 0, 0)'
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5
        ),
        title=dict(
            text='종목 비교 Snowflake',
            x=0.5,
            font=dict(size=16)
        ),
        paper_bgcolor='rgba(0, 0, 0, 0)',
        plot_bgcolor='rgba(0, 0, 0, 0)',
        margin=dict(l=80, r=80, t=80, b=100),
        height=450
    )

    return fig


def get_score_interpretation(scores: SnowflakeScores) -> Dict[str, str]:
    """
    점수 해석 제공

    Args:
        scores: SnowflakeScores

    Returns:
        각 축별 해석 텍스트
    """
    interpretations = {}

    # 가치
    if scores.value >= 4.5:
        interpretations['가치'] = "🟢 크게 저평가됨 - 매력적인 진입 기회"
    elif scores.value >= 3.5:
        interpretations['가치'] = "🔵 적정~저평가 - 밸류에이션 양호"
    elif scores.value >= 2.5:
        interpretations['가치'] = "🟡 적정 수준 - 섹터 평균"
    else:
        interpretations['가치'] = "🔴 고평가 우려 - 진입 시 주의"

    # 미래
    if scores.future >= 4.5:
        interpretations['미래'] = "🟢 높은 성장 전망 - 강한 모멘텀"
    elif scores.future >= 3.5:
        interpretations['미래'] = "🔵 성장 기대 - 양호한 전망"
    elif scores.future >= 2.5:
        interpretations['미래'] = "🟡 안정적 - 큰 변화 없음"
    else:
        interpretations['미래'] = "🔴 성장 둔화 - 구조적 문제 가능"

    # 과거
    if scores.past >= 4.5:
        interpretations['과거'] = "🟢 뛰어난 실적 - 꾸준한 수익성"
    elif scores.past >= 3.5:
        interpretations['과거'] = "🔵 양호한 실적 - 안정적 운영"
    elif scores.past >= 2.5:
        interpretations['과거'] = "🟡 평균 수준 - 개선 여지"
    else:
        interpretations['과거'] = "🔴 부진한 실적 - 턴어라운드 필요"

    # 배당
    if scores.dividend >= 4.5:
        interpretations['배당'] = "🟢 높은 배당 - 인컴 투자 적합"
    elif scores.dividend >= 3.5:
        interpretations['배당'] = "🔵 적절한 배당 - 균형 잡힌 정책"
    elif scores.dividend >= 2.5:
        interpretations['배당'] = "🟡 낮은 배당 - 성장에 재투자"
    else:
        interpretations['배당'] = "🔴 무배당/미흡 - 인컴 기대 어려움"

    # 건전성
    if scores.health >= 4.5:
        interpretations['건전성'] = "🟢 매우 건전 - 낮은 재무 리스크"
    elif scores.health >= 3.5:
        interpretations['건전성'] = "🔵 양호 - 안정적 재무구조"
    elif scores.health >= 2.5:
        interpretations['건전성'] = "🟡 보통 - 모니터링 필요"
    else:
        interpretations['건전성'] = "🔴 주의 - 재무 리스크 존재"

    return interpretations


def get_overall_rating(scores: SnowflakeScores) -> Tuple[str, str, str]:
    """
    종합 등급 및 설명 반환 - 중앙화된 설정 사용

    Returns:
        (등급, 이모지, 설명)
    """
    total = scores.total

    # 중앙화된 등급 기준 사용
    if _USE_CENTRAL_CONFIG:
        grade_a_plus = SNOWFLAKE.grade_a_plus
        grade_a = SNOWFLAKE.grade_a
        grade_b = SNOWFLAKE.grade_b
        grade_c = SNOWFLAKE.grade_c
        grade_d = SNOWFLAKE.grade_d
    else:
        # 폴백: 기본값
        grade_a_plus = 5.0
        grade_a = 4.0
        grade_b = 3.5
        grade_c = 3.0
        grade_d = 2.5

    if total >= grade_a_plus:
        return "A+", "⭐", "최우수 - 모든 지표가 뛰어남"
    elif total >= grade_a + 0.5:  # 4.5
        return "A", "🟢", "우수 - 대부분의 지표가 양호"
    elif total >= grade_a:  # 4.0
        return "B+", "🔵", "양호 - 전반적으로 괜찮음"
    elif total >= grade_b:  # 3.5
        return "B", "🔵", "보통 이상 - 일부 강점 보유"
    elif total >= grade_c:  # 3.0
        return "C+", "🟡", "보통 - 평균 수준"
    elif total >= grade_d:  # 2.5
        return "C", "🟡", "보통 이하 - 개선 필요"
    elif total >= 2.0:
        return "D", "🟠", "주의 - 여러 약점 존재"
    else:
        return "F", "🔴", "위험 - 투자 주의 필요"


# 싱글톤 인스턴스
snowflake_analyzer = SnowflakeAnalyzer()
