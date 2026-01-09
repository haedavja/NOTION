"""
분석 결과 쉬운 설명 컴포넌트
비전문가도 이해하기 쉬운 설명 제공
"""

import streamlit as st
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum


class ExplanationLevel(Enum):
    """설명 수준"""
    BEGINNER = "초급"
    INTERMEDIATE = "중급"
    EXPERT = "전문가"


@dataclass
class EasyExplanation:
    """쉬운 설명 데이터"""
    title: str
    simple_summary: str  # 한 줄 요약
    what_it_means: str  # 의미
    what_to_do: str  # 행동 지침
    emoji: str = "💡"


# 지표별 쉬운 설명 템플릿
METRIC_EXPLANATIONS = {
    # Snowflake 지표
    'value': {
        'name': '가치(Value)',
        'description': '현재 주가가 기업 가치 대비 저평가/고평가 정도',
        'high': '주가가 저평가되어 있어요. 싸게 살 기회일 수 있어요!',
        'low': '주가가 비싼 편이에요. 이미 많이 올랐을 수 있어요.',
        'icon': '💰'
    },
    'future': {
        'name': '미래(Future)',
        'description': '향후 성장 가능성과 수익 전망',
        'high': '성장 전망이 밝아요. 앞으로 더 커질 가능성이 높아요!',
        'low': '성장 전망이 불투명해요. 신중한 접근이 필요해요.',
        'icon': '🚀'
    },
    'past': {
        'name': '과거(Past)',
        'description': '과거 수익률과 성과',
        'high': '과거 성과가 좋았어요. 꾸준히 수익을 낸 기업이에요!',
        'low': '과거 성과가 부진했어요. 회복 중인지 확인이 필요해요.',
        'icon': '📊'
    },
    'health': {
        'name': '건강(Health)',
        'description': '재무 안정성과 부채 상태',
        'high': '재무상태가 튼튼해요. 위기에도 버틸 힘이 있어요!',
        'low': '재무상태가 걱정돼요. 부채가 많거나 자금 사정이 어려울 수 있어요.',
        'icon': '🏥'
    },
    'dividend': {
        'name': '배당(Dividend)',
        'description': '주주에게 돌려주는 배당금 수준',
        'high': '배당을 잘 주는 기업이에요. 꾸준한 현금 수입을 기대할 수 있어요!',
        'low': '배당이 적거나 없어요. 성장에 재투자하는 기업일 수 있어요.',
        'icon': '💵'
    },

    # 기술적 지표
    'rsi': {
        'name': 'RSI (상대강도지수)',
        'description': '최근 주가가 얼마나 많이 올랐는지/떨어졌는지',
        'high': '과매수 상태예요. 너무 많이 올라서 쉬어갈 수 있어요.',
        'low': '과매도 상태예요. 너무 떨어져서 반등할 수 있어요.',
        'icon': '📈'
    },
    'macd': {
        'name': 'MACD',
        'description': '추세의 방향과 강도',
        'high': '상승 추세가 강해요. 오름세가 계속될 가능성이 높아요!',
        'low': '하락 추세예요. 더 떨어질 수 있으니 주의하세요.',
        'icon': '〽️'
    },
    'moving_average': {
        'name': '이동평균선',
        'description': '일정 기간 평균 주가',
        'above': '평균보다 위에 있어요. 상승 추세일 가능성이 높아요!',
        'below': '평균보다 아래에 있어요. 약세장일 수 있어요.',
        'icon': '📉'
    },

    # 수급 지표
    'foreign_net': {
        'name': '외국인 순매수',
        'description': '외국인 투자자들의 매매 동향',
        'positive': '외국인이 사고 있어요. 기관 투자자들이 좋게 보고 있어요!',
        'negative': '외국인이 팔고 있어요. 왜 파는지 살펴볼 필요가 있어요.',
        'icon': '🌍'
    },
    'inst_net': {
        'name': '기관 순매수',
        'description': '국내 기관 투자자들의 매매 동향',
        'positive': '기관이 사고 있어요. 전문가들이 관심을 가지고 있어요!',
        'negative': '기관이 팔고 있어요. 단기 조정을 예상할 수 있어요.',
        'icon': '🏦'
    },

    # 상관관계
    'correlation': {
        'name': '상관관계',
        'description': '두 종목이 얼마나 같이 움직이는지',
        'high_positive': '두 종목이 함께 움직여요. 하나만 투자해도 될 수 있어요.',
        'low': '각자 다르게 움직여요. 분산 투자 효과를 얻을 수 있어요!',
        'high_negative': '반대로 움직여요. 리스크 분산에 아주 좋아요!',
        'icon': '🔗'
    },

    # 성과 지표
    'alpha': {
        'name': '알파',
        'description': '시장 평균 대비 초과 수익',
        'positive': '시장보다 더 벌었어요. 실력 있는 투자예요! 👍',
        'negative': '시장보다 못 벌었어요. 그냥 지수 투자가 나았을 수 있어요.',
        'icon': '🎯'
    },
    'beta': {
        'name': '베타',
        'description': '시장 변동에 얼마나 민감한지',
        'high': '시장보다 변동이 커요. 오르면 더 오르고, 떨어지면 더 떨어져요.',
        'low': '시장보다 안정적이에요. 변동폭이 작아서 마음이 편해요.',
        'icon': '🎢'
    },
    'sharpe_ratio': {
        'name': '샤프 비율',
        'description': '위험 대비 수익 효율성',
        'high': '위험 대비 수익이 좋아요. 효율적인 투자예요! 🏆',
        'low': '위험 대비 수익이 낮아요. 더 좋은 투자처를 찾아볼까요?',
        'icon': '⚖️'
    },
    'max_drawdown': {
        'name': '최대 낙폭',
        'description': '가장 많이 떨어졌던 적이 얼마인지',
        'high': '한번 크게 떨어진 적이 있어요. 멘탈 관리가 필요해요.',
        'low': '크게 떨어진 적이 없어요. 비교적 안정적인 투자예요.',
        'icon': '📉'
    }
}


def get_score_explanation(score: float, metric_type: str = 'value') -> EasyExplanation:
    """
    점수에 대한 쉬운 설명 생성

    Args:
        score: 점수 (0-100 또는 -1~1 범위)
        metric_type: 지표 유형

    Returns:
        EasyExplanation
    """
    info = METRIC_EXPLANATIONS.get(metric_type, {})
    name = info.get('name', metric_type)
    emoji = info.get('icon', '📊')

    # 점수 범위에 따른 설명
    if score >= 70:
        level = '높음'
        explanation = info.get('high', '점수가 높습니다.')
        action = '긍정적인 신호입니다.'
    elif score >= 40:
        level = '보통'
        explanation = '평균적인 수준입니다.'
        action = '다른 지표도 함께 확인하세요.'
    else:
        level = '낮음'
        explanation = info.get('low', '점수가 낮습니다.')
        action = '주의가 필요한 신호입니다.'

    return EasyExplanation(
        title=f"{emoji} {name}",
        simple_summary=f"{name} 점수: {score:.0f}점 ({level})",
        what_it_means=explanation,
        what_to_do=action,
        emoji=emoji
    )


def get_grade_explanation(grade: str) -> EasyExplanation:
    """등급에 대한 쉬운 설명"""
    grade_info = {
        'A+': ('최고 수준', '매우 좋은 종목이에요! 다만 이미 가격에 반영됐을 수 있어요.', '장기 투자 고려', '🥇'),
        'A': ('우수', '좋은 종목이에요. 꾸준히 관찰하면서 매수 시점을 찾아보세요.', '적극 검토', '🥈'),
        'A-': ('양호', '괜찮은 종목이에요. 장점과 단점을 비교해보세요.', '관심 종목으로 등록', '🥉'),
        'B+': ('평균 이상', '무난한 종목이에요. 특별한 강점을 찾아보세요.', '추가 분석 필요', '👍'),
        'B': ('평균', '평균적인 종목이에요. 왜 이 종목인지 이유가 필요해요.', '신중히 검토', '👌'),
        'B-': ('평균 이하', '조금 부족한 점이 있어요. 더 좋은 대안을 찾아보세요.', '비교 분석 권장', '🤔'),
        'C+': ('주의', '부족한 점이 많아요. 투자 전 충분한 검토가 필요해요.', '신중 접근', '⚠️'),
        'C': ('경계', '리스크가 있어요. 투기적 접근만 가능해요.', '투자 자제 권장', '🚨'),
        'C-': ('위험', '위험 신호가 많아요. 피하는 것이 좋아요.', '투자 비권장', '🛑'),
        'D': ('매우 위험', '심각한 문제가 있을 수 있어요. 절대 피하세요.', '투자 금지', '❌'),
    }

    info = grade_info.get(grade, ('알 수 없음', '등급 정보를 확인할 수 없습니다.', '추가 확인 필요', '❓'))

    return EasyExplanation(
        title=f"{info[3]} 종합 등급: {grade}",
        simple_summary=f"{info[0]} 수준의 종목입니다.",
        what_it_means=info[1],
        what_to_do=info[2],
        emoji=info[3]
    )


def get_market_phase_explanation(phase: str) -> EasyExplanation:
    """시장 국면에 대한 쉬운 설명"""
    phase_info = {
        '초기 확장': (
            '경기가 살아나기 시작해요',
            '경제가 회복되면서 기업 실적이 좋아지고 있어요. 성장주와 경기민감주가 유리해요!',
            'IT, 반도체, 자동차, 건설 섹터에 관심을 가져보세요.',
            '🌱'
        ),
        '후기 확장': (
            '경기가 정점에 가까워요',
            '경제가 활발하지만 곧 꺾일 수 있어요. 원자재와 에너지가 강세를 보여요.',
            '에너지, 철강, 화학 섹터를 주목하되, 출구 전략을 준비하세요.',
            '🔥'
        ),
        '초기 수축': (
            '경기가 둔화되기 시작해요',
            '경제가 냉각되면서 안전자산 선호가 높아져요. 방어적 투자가 유리해요.',
            '은행, 바이오, 유틸리티 등 방어주로 이동을 고려하세요.',
            '🍂'
        ),
        '후기 수축': (
            '경기 침체 국면이에요',
            '경제가 어려운 시기예요. 현금 비중을 높이고 방어적으로 대응하세요.',
            '유틸리티, 필수소비재, 통신 등 안정적인 섹터에 집중하세요.',
            '❄️'
        ),
        '회복': (
            '바닥을 찍고 반등 중이에요',
            '최악의 시기는 지났어요. 용기 있게 좋은 종목을 담을 기회예요!',
            '2차전지, IT, 반도체, 건설 등 성장주를 선점하세요.',
            '🌅'
        ),
    }

    info = phase_info.get(phase, ('판단 어려움', '시장 상황을 파악하기 어렵습니다.', '관망을 권장합니다.', '🤷'))

    return EasyExplanation(
        title=f"{info[3]} 현재 시장: {phase}",
        simple_summary=info[0],
        what_it_means=info[1],
        what_to_do=info[2],
        emoji=info[3]
    )


def render_easy_explanation(explanation: EasyExplanation, expanded: bool = False):
    """쉬운 설명 UI 렌더링"""
    with st.expander(f"{explanation.emoji} 쉽게 이해하기", expanded=expanded):
        st.markdown(f"### {explanation.title}")

        # 한 줄 요약
        st.info(f"**요약**: {explanation.simple_summary}")

        # 의미
        st.markdown(f"**이게 무슨 뜻이에요?**")
        st.write(explanation.what_it_means)

        # 행동 지침
        st.markdown(f"**그래서 어떻게 해야 해요?**")
        st.success(f"👉 {explanation.what_to_do}")


def render_metric_tooltip(metric_type: str, value: float) -> str:
    """지표에 대한 툴팁 텍스트 생성"""
    info = METRIC_EXPLANATIONS.get(metric_type, {})
    name = info.get('name', metric_type)
    description = info.get('description', '')

    return f"{name}: {description} (현재 값: {value:.2f})"


def get_investment_summary(
    grade: str,
    snowflake_scores: Dict[str, float],
    technical_signal: str = None,
    supply_demand: str = None
) -> str:
    """
    종합 투자 요약 생성 (비전문가용)

    Args:
        grade: 종합 등급
        snowflake_scores: Snowflake 점수들
        technical_signal: 기술적 신호 ('매수'/'매도'/'중립')
        supply_demand: 수급 신호 ('긍정'/'부정'/'중립')

    Returns:
        쉬운 언어로 된 투자 요약
    """
    # 등급별 기본 평가
    if grade.startswith('A'):
        base = "이 종목은 전반적으로 좋은 평가를 받고 있어요."
        recommendation = "관심을 가지고 지켜볼 만해요."
    elif grade.startswith('B'):
        base = "이 종목은 평균적인 수준이에요."
        recommendation = "더 자세한 분석 후에 결정하세요."
    else:
        base = "이 종목은 주의가 필요해요."
        recommendation = "투자에 신중해야 해요."

    # 강점/약점 분석
    strengths = []
    weaknesses = []

    for metric, score in snowflake_scores.items():
        name = METRIC_EXPLANATIONS.get(metric, {}).get('name', metric)
        if score >= 70:
            strengths.append(name)
        elif score <= 30:
            weaknesses.append(name)

    summary_parts = [base]

    if strengths:
        summary_parts.append(f"특히 {', '.join(strengths)} 측면이 강점이에요.")

    if weaknesses:
        summary_parts.append(f"반면 {', '.join(weaknesses)} 부분은 보완이 필요해요.")

    # 기술적 신호
    if technical_signal:
        if technical_signal == '매수':
            summary_parts.append("차트상으로는 사기 좋은 타이밍이에요. 📈")
        elif technical_signal == '매도':
            summary_parts.append("차트상으로는 조금 기다리는 게 좋아요. 📉")

    # 수급 신호
    if supply_demand:
        if supply_demand == '긍정':
            summary_parts.append("외국인과 기관이 사고 있어서 긍정적이에요. 🌍")
        elif supply_demand == '부정':
            summary_parts.append("외국인과 기관이 팔고 있어서 주의가 필요해요. ⚠️")

    summary_parts.append(recommendation)

    return " ".join(summary_parts)


def render_beginner_mode_toggle() -> bool:
    """초보자 모드 토글"""
    return st.toggle(
        "🔰 초보자 모드",
        value=st.session_state.get('beginner_mode', True),
        help="켜면 모든 분석 결과에 쉬운 설명이 추가됩니다."
    )


def show_quick_tip(tip_key: str):
    """퀵 팁 표시"""
    tips = {
        'diversification': "💡 **분산 투자란?** 여러 종목에 나눠 투자해서 위험을 줄이는 방법이에요. 달걀을 한 바구니에 담지 말라는 말과 같아요!",
        'long_term': "💡 **장기 투자가 왜 좋아요?** 단기적으로는 오르락내리락해도, 좋은 기업은 장기적으로 성장해요. 복리의 마법이 작동하려면 시간이 필요해요!",
        'timing': "💡 **매수 타이밍이 중요할까요?** 완벽한 타이밍은 아무도 몰라요. 좋은 기업을 적정 가격에 사는 것이 더 중요해요!",
        'risk': "💡 **리스크 관리란?** 잃어도 되는 돈만 투자하고, 한 종목에 올인하지 않는 것이에요. 투자는 마라톤이지 단거리 경주가 아니에요!",
        'fee': "💡 **수수료도 중요해요!** 자주 사고팔면 수수료가 쌓여요. 장기 투자자가 유리한 이유 중 하나예요.",
    }

    tip = tips.get(tip_key, "")
    if tip:
        st.info(tip)


class EasyModeContext:
    """쉬운 모드 컨텍스트 매니저"""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def explain_metric(self, metric_type: str, value: float):
        """지표 설명 (쉬운 모드일 때만)"""
        if self.enabled:
            explanation = get_score_explanation(value, metric_type)
            render_easy_explanation(explanation)

    def show_tip(self, tip_key: str):
        """팁 표시 (쉬운 모드일 때만)"""
        if self.enabled:
            show_quick_tip(tip_key)

    def summarize(self, grade: str, scores: Dict[str, float], **kwargs):
        """투자 요약 (쉬운 모드일 때만)"""
        if self.enabled:
            summary = get_investment_summary(grade, scores, **kwargs)
            st.markdown("---")
            st.markdown("### 📝 쉽게 정리하면...")
            st.write(summary)
