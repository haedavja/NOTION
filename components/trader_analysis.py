"""
트레이더 토론 스타일 종목 분석
- 가상의 전문가들이 종목의 강점/약점을 토론
- 차트 분석 포함
- 사용자 투자논리 반박/분석 기능
"""

import streamlit as st
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import random


@dataclass
class TraderPersona:
    """트레이더 페르소나"""
    name: str
    style: str  # value, growth, technical, contrarian, quant, momentum
    avatar: str
    color: str
    bias: str  # bullish, bearish, neutral
    description: str


# 6명의 가상 트레이더
STOCK_TRADERS = [
    TraderPersona(
        name="가치투자 김부장",
        style="value",
        avatar="👔",
        color="#2563eb",
        bias="neutral",
        description="PER, PBR, 배당수익률 중심의 가치투자자"
    ),
    TraderPersona(
        name="성장주 이대리",
        style="growth",
        avatar="🚀",
        color="#16a34a",
        bias="bullish",
        description="매출성장률, 신사업 가능성 중시"
    ),
    TraderPersona(
        name="차트쟁이 박과장",
        style="technical",
        avatar="📊",
        color="#dc2626",
        bias="neutral",
        description="이동평균선, RSI, MACD 기술적 분석가"
    ),
    TraderPersona(
        name="역발상 최차장",
        style="contrarian",
        avatar="🔄",
        color="#9333ea",
        bias="bearish",
        description="대중과 반대로 가는 역발상 투자자"
    ),
    TraderPersona(
        name="퀀트 정연구원",
        style="quant",
        avatar="🤖",
        color="#0891b2",
        bias="neutral",
        description="데이터와 수치 기반 정량적 분석가"
    ),
    TraderPersona(
        name="모멘텀 한실장",
        style="momentum",
        avatar="⚡",
        color="#ea580c",
        bias="bullish",
        description="수급, 거래량, 모멘텀 추종 트레이더"
    ),
]


def analyze_stock_by_trader(
    trader: TraderPersona,
    stock_name: str,
    stock_code: str,
    scores: Dict,
    fundamentals: Dict = None
) -> Dict:
    """트레이더 관점에서 종목 분석"""

    # 점수 기반 분석
    total_score = scores.get('total', 3.0)
    value_score = scores.get('value', 3.0)
    future_score = scores.get('future', 3.0)
    health_score = scores.get('health', 3.0)
    dividend_score = scores.get('dividend', 3.0)
    past_score = scores.get('past', 3.0)

    analysis = {
        'trader': trader,
        'stance': 'neutral',
        'confidence': 50,
        'strengths': [],
        'weaknesses': [],
        'key_point': '',
        'recommendation': '',
        'timestamp': datetime.now().strftime("%H:%M")
    }

    # 트레이더 스타일별 분석
    if trader.style == 'value':
        # 가치투자자 - PER, PBR, 배당 중시
        if value_score >= 4.5:
            analysis['stance'] = 'bullish'
            analysis['confidence'] = 75 + random.randint(0, 15)
            analysis['strengths'].append("저평가 매력 높음 (가치지표 우수)")
            analysis['key_point'] = f"PER/PBR 기준 매력적인 진입 구간"
        elif value_score <= 2.5:
            analysis['stance'] = 'bearish'
            analysis['confidence'] = 65 + random.randint(0, 15)
            analysis['weaknesses'].append("고평가 구간 (밸류에이션 부담)")
            analysis['key_point'] = "현 주가는 펀더멘털 대비 과도"
        else:
            analysis['stance'] = 'neutral'
            analysis['confidence'] = 50 + random.randint(0, 10)
            analysis['key_point'] = "적정 밸류에이션, 관망 권고"

        if dividend_score >= 4.0:
            analysis['strengths'].append(f"배당수익률 매력적")
        elif dividend_score <= 2.0:
            analysis['weaknesses'].append("배당 매력 낮음")

    elif trader.style == 'growth':
        # 성장투자자 - 미래성장성 중시
        if future_score >= 4.5:
            analysis['stance'] = 'bullish'
            analysis['confidence'] = 80 + random.randint(0, 15)
            analysis['strengths'].append("높은 성장 잠재력")
            analysis['key_point'] = "성장 모멘텀 강력, 적극 매수 고려"
        elif future_score <= 2.5:
            analysis['stance'] = 'bearish'
            analysis['confidence'] = 60 + random.randint(0, 15)
            analysis['weaknesses'].append("성장성 둔화 우려")
            analysis['key_point'] = "성장 동력 약화, 비중 축소 권고"
        else:
            analysis['stance'] = 'neutral'
            analysis['confidence'] = 55 + random.randint(0, 10)
            analysis['key_point'] = "성장성은 보통, 실적 확인 필요"

        if past_score >= 4.0:
            analysis['strengths'].append("과거 실적 트랙레코드 우수")

    elif trader.style == 'technical':
        # 기술적 분석가 - 차트/추세 중시
        # 종합점수로 추세 판단 (실제로는 기술적 지표 필요)
        if total_score >= 4.5:
            analysis['stance'] = 'bullish'
            analysis['confidence'] = 70 + random.randint(0, 15)
            analysis['strengths'].append("상승 추세 진행 중")
            analysis['key_point'] = "기술적 매수 신호 포착"
        elif total_score <= 2.5:
            analysis['stance'] = 'bearish'
            analysis['confidence'] = 65 + random.randint(0, 15)
            analysis['weaknesses'].append("하락 추세 또는 박스권")
            analysis['key_point'] = "기술적 지지선 이탈 주의"
        else:
            analysis['stance'] = 'neutral'
            analysis['confidence'] = 50 + random.randint(0, 15)
            analysis['key_point'] = "방향성 탐색 구간, 돌파 대기"

    elif trader.style == 'contrarian':
        # 역발상 투자자 - 대중과 반대
        if total_score >= 5.0:
            # 너무 좋으면 오히려 경계
            analysis['stance'] = 'bearish'
            analysis['confidence'] = 60 + random.randint(0, 15)
            analysis['weaknesses'].append("과열 신호, 차익실현 구간")
            analysis['key_point'] = "모두가 좋다할 때가 팔 때"
        elif total_score <= 2.0:
            # 너무 나쁘면 기회
            analysis['stance'] = 'bullish'
            analysis['confidence'] = 65 + random.randint(0, 15)
            analysis['strengths'].append("공포 극대화 구간, 역발상 매수 기회")
            analysis['key_point'] = "모두가 외면할 때가 살 때"
        else:
            analysis['stance'] = 'neutral'
            analysis['confidence'] = 45 + random.randint(0, 10)
            analysis['key_point'] = "극단적 센티먼트 아님, 관망"

    elif trader.style == 'quant':
        # 퀀트 분석가 - 수치 기반
        avg_score = (value_score + future_score + past_score + health_score + dividend_score) / 5

        if avg_score >= 4.0:
            analysis['stance'] = 'bullish'
            analysis['confidence'] = int(avg_score * 15) + random.randint(0, 10)
            analysis['strengths'].append(f"종합 스코어 {avg_score:.1f}/6 (상위권)")
            analysis['key_point'] = f"퀀트 모델 매수 신호 (Score: {avg_score:.2f})"
        elif avg_score <= 2.5:
            analysis['stance'] = 'bearish'
            analysis['confidence'] = 60 + random.randint(0, 15)
            analysis['weaknesses'].append(f"종합 스코어 {avg_score:.1f}/6 (하위권)")
            analysis['key_point'] = f"퀀트 모델 매도 신호 (Score: {avg_score:.2f})"
        else:
            analysis['stance'] = 'neutral'
            analysis['confidence'] = 50 + random.randint(0, 10)
            analysis['key_point'] = f"중립 구간 (Score: {avg_score:.2f})"

        if health_score >= 4.5:
            analysis['strengths'].append("재무건전성 우수")
        elif health_score <= 2.0:
            analysis['weaknesses'].append("재무 리스크 존재")

    elif trader.style == 'momentum':
        # 모멘텀 트레이더 - 수급/거래량 중시
        if future_score >= 4.0 and past_score >= 3.5:
            analysis['stance'] = 'bullish'
            analysis['confidence'] = 75 + random.randint(0, 15)
            analysis['strengths'].append("실적 모멘텀 양호")
            analysis['key_point'] = "상승 모멘텀 탑승 권고"
        elif future_score <= 2.5:
            analysis['stance'] = 'bearish'
            analysis['confidence'] = 65 + random.randint(0, 10)
            analysis['weaknesses'].append("모멘텀 둔화")
            analysis['key_point'] = "모멘텀 이탈, 리스크 관리 필요"
        else:
            analysis['stance'] = 'neutral'
            analysis['confidence'] = 55 + random.randint(0, 10)
            analysis['key_point'] = "모멘텀 방향 탐색 중"

    # 공통 분석 추가
    if health_score >= 4.5 and 'health' not in str(analysis['strengths']):
        analysis['strengths'].append("탄탄한 재무구조")
    if health_score <= 2.0 and 'health' not in str(analysis['weaknesses']):
        analysis['weaknesses'].append("부채비율 또는 유동성 우려")

    # 추천 생성
    if analysis['stance'] == 'bullish':
        analysis['recommendation'] = random.choice([
            "매수 관점 접근 가능",
            "분할 매수 전략 권고",
            "비중 확대 고려",
            "긍정적 시각 유지"
        ])
    elif analysis['stance'] == 'bearish':
        analysis['recommendation'] = random.choice([
            "신규 진입 자제",
            "비중 축소 권고",
            "리스크 관리 필요",
            "관망 또는 매도 고려"
        ])
    else:
        analysis['recommendation'] = random.choice([
            "추가 정보 확인 후 결정",
            "중립, 관망 권고",
            "분할 접근 전략 고려",
            "방향성 확인 후 대응"
        ])

    return analysis


def generate_trader_discussion(
    stock_name: str,
    stock_code: str,
    scores: Dict,
    fundamentals: Dict = None
) -> List[Dict]:
    """6명의 트레이더 토론 생성"""
    discussions = []

    for trader in STOCK_TRADERS:
        analysis = analyze_stock_by_trader(
            trader, stock_name, stock_code, scores, fundamentals
        )
        discussions.append(analysis)

    # 신뢰도 순으로 정렬
    discussions.sort(key=lambda x: x['confidence'], reverse=True)

    return discussions


def analyze_investment_thesis(
    thesis: str,
    stock_name: str,
    scores: Dict,
    fundamentals: Dict = None
) -> Dict:
    """사용자 투자논리 분석 및 반박"""

    result = {
        'original_thesis': thesis,
        'strengths': [],
        'weaknesses': [],
        'rebuttals': [],
        'limitations': [],
        'suggestions': [],
        'overall_assessment': ''
    }

    thesis_lower = thesis.lower()

    # 키워드 기반 분석

    # 저평가 관련
    if any(word in thesis_lower for word in ['저평가', 'per 낮', 'pbr 낮', '싸다', '저렴']):
        if scores.get('value', 3) >= 4:
            result['strengths'].append("✓ 맞습니다. 가치지표상 저평가 구간입니다.")
        else:
            result['rebuttals'].append("⚠️ 현재 밸류에이션은 저평가라 보기 어렵습니다. 가치점수가 평균 이하입니다.")
            result['limitations'].append("저평가처럼 보이는 것이 '가치 함정(Value Trap)'일 수 있습니다.")

    # 성장 관련
    if any(word in thesis_lower for word in ['성장', '신사업', '확장', '매출 증가', '시장 확대']):
        if scores.get('future', 3) >= 4:
            result['strengths'].append("✓ 성장 전망 지표가 양호합니다.")
        else:
            result['rebuttals'].append("⚠️ 미래 성장성 점수가 높지 않습니다. 성장 기대가 과도할 수 있습니다.")
            result['limitations'].append("성장 스토리만으로 투자하면 실적 미달 시 급락 위험이 있습니다.")

    # 배당 관련
    if any(word in thesis_lower for word in ['배당', '배당금', '배당수익률', '인컴']):
        if scores.get('dividend', 3) >= 4:
            result['strengths'].append("✓ 배당 매력이 실제로 높습니다.")
        else:
            result['rebuttals'].append("⚠️ 배당수익률이 기대만큼 높지 않거나 지속성이 불확실합니다.")
            result['limitations'].append("배당은 실적에 따라 삭감될 수 있습니다.")

    # 안정성 관련
    if any(word in thesis_lower for word in ['안정', '튼튼', '재무', '부채 낮', '현금']):
        if scores.get('health', 3) >= 4:
            result['strengths'].append("✓ 재무건전성이 양호합니다.")
        else:
            result['rebuttals'].append("⚠️ 재무건전성 지표가 우려됩니다. 부채비율이나 유동성을 확인하세요.")

    # 실적 관련
    if any(word in thesis_lower for word in ['실적', '이익', '흑자', '영업이익', 'eps']):
        if scores.get('past', 3) >= 4:
            result['strengths'].append("✓ 과거 실적 트랙레코드가 우수합니다.")
        else:
            result['rebuttals'].append("⚠️ 과거 실적이 불안정하거나 개선이 필요합니다.")

    # 차트/기술적 분석 관련
    if any(word in thesis_lower for word in ['바닥', '지지', '돌파', '상승 추세', '이평선']):
        result['limitations'].append("기술적 분석은 후행적이며, 펀더멘털 변화에 취약합니다.")
        result['suggestions'].append("기술적 분석과 펀더멘털 분석을 병행하세요.")

    # 테마/이슈 관련
    if any(word in thesis_lower for word in ['테마', '정책', '수혜', '모멘텀', '이슈']):
        result['limitations'].append("테마/이슈는 일시적일 수 있으며, 과열 시 급락 위험이 있습니다.")
        result['suggestions'].append("테마 종료 후에도 펀더멘털이 지지되는지 확인하세요.")

    # 전반적인 평가
    total_score = scores.get('total', 3)

    if len(result['strengths']) > len(result['rebuttals']):
        result['overall_assessment'] = f"📊 투자논리가 대체로 데이터와 일치합니다. (종합점수: {total_score:.1f}/6)"
    elif len(result['rebuttals']) > len(result['strengths']):
        result['overall_assessment'] = f"⚠️ 투자논리에 재검토가 필요한 부분이 있습니다. (종합점수: {total_score:.1f}/6)"
    else:
        result['overall_assessment'] = f"📋 투자논리가 부분적으로 맞지만, 추가 검증이 필요합니다. (종합점수: {total_score:.1f}/6)"

    # 일반적인 제안 추가
    if not result['suggestions']:
        result['suggestions'] = [
            "분할 매수로 리스크를 분산하세요.",
            "손절 기준을 미리 정해두세요.",
            "정기적으로 투자논리를 재검토하세요."
        ]

    return result


def render_trader_discussion_ui(
    stock_name: str,
    stock_code: str,
    scores: Dict,
    fundamentals: Dict = None
):
    """트레이더 토론 UI 렌더링"""

    st.markdown(f"### 💬 전문가들의 {stock_name} 토론")
    st.caption("6명의 가상 트레이더가 이 종목을 분석합니다")

    discussions = generate_trader_discussion(stock_name, stock_code, scores, fundamentals)

    # 의견 요약
    bullish_count = sum(1 for d in discussions if d['stance'] == 'bullish')
    bearish_count = sum(1 for d in discussions if d['stance'] == 'bearish')
    neutral_count = sum(1 for d in discussions if d['stance'] == 'neutral')

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🟢 매수 의견", f"{bullish_count}명")
    with col2:
        st.metric("🟡 중립 의견", f"{neutral_count}명")
    with col3:
        st.metric("🔴 매도 의견", f"{bearish_count}명")

    st.divider()

    # 각 트레이더 의견 표시
    for analysis in discussions:
        trader = analysis['trader']
        stance = analysis['stance']

        # 스탠스별 색상
        if stance == 'bullish':
            border_color = '#22c55e'
            stance_emoji = '🟢'
            stance_text = '매수 관점'
        elif stance == 'bearish':
            border_color = '#ef4444'
            stance_emoji = '🔴'
            stance_text = '매도 관점'
        else:
            border_color = '#eab308'
            stance_emoji = '🟡'
            stance_text = '중립 관점'

        st.markdown(f"""
        <div style='background: white; border: 1px solid #e5e7eb; border-left: 4px solid {trader.color};
                    border-radius: 8px; padding: 1rem; margin-bottom: 0.8rem;'>
            <div style='display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;'>
                <span style='font-size: 1.5rem;'>{trader.avatar}</span>
                <span style='font-weight: bold; color: {trader.color};'>{trader.name}</span>
                <span style='background: {border_color}20; color: {border_color};
                            padding: 2px 8px; border-radius: 12px; font-size: 0.8rem;'>
                    {stance_emoji} {stance_text}
                </span>
                <span style='margin-left: auto; font-size: 0.75rem; color: #9ca3af;'>
                    신뢰도 {analysis['confidence']}%
                </span>
            </div>
            <div style='font-size: 0.85rem; color: #6b7280; margin-bottom: 0.5rem;'>
                {trader.description}
            </div>
            <div style='font-size: 0.95rem; margin-bottom: 0.5rem;'>
                <strong>핵심 포인트:</strong> {analysis['key_point']}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 강점/약점 표시 (확장 가능)
        with st.expander(f"📋 {trader.name}의 상세 분석", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**💪 강점**")
                for s in analysis['strengths']:
                    st.markdown(f"- {s}")
                if not analysis['strengths']:
                    st.caption("특별히 언급할 강점 없음")
            with col2:
                st.markdown("**⚠️ 약점/리스크**")
                for w in analysis['weaknesses']:
                    st.markdown(f"- {w}")
                if not analysis['weaknesses']:
                    st.caption("특별히 언급할 약점 없음")

            st.info(f"💡 추천: {analysis['recommendation']}")


def render_thesis_analysis_ui(
    stock_name: str,
    stock_code: str,
    scores: Dict,
    fundamentals: Dict = None
):
    """투자논리 분석 UI"""

    st.markdown("### 📝 나의 투자논리 검증")
    st.caption("투자 이유를 적으면 AI가 반박, 한계, 장점을 분석해드립니다")

    thesis_key = f"thesis_{stock_code}"

    thesis = st.text_area(
        "투자 논리를 입력하세요",
        placeholder="예: 이 종목은 PER이 낮고 배당수익률이 높아서 저평가라고 생각합니다. 신사업 진출로 성장 가능성도 있고...",
        key=thesis_key,
        height=100
    )

    if st.button("🔍 투자논리 분석", key=f"analyze_{stock_code}", use_container_width=True):
        if thesis.strip():
            with st.spinner("투자논리 분석 중..."):
                result = analyze_investment_thesis(thesis, stock_name, scores, fundamentals)

            # 결과 표시
            st.markdown("---")
            st.markdown(f"**{result['overall_assessment']}**")

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### ✅ 논리의 강점")
                if result['strengths']:
                    for s in result['strengths']:
                        st.success(s)
                else:
                    st.caption("입력한 논리에서 데이터로 확인된 강점이 없습니다.")

            with col2:
                st.markdown("#### ⚠️ 반박 및 한계")
                if result['rebuttals']:
                    for r in result['rebuttals']:
                        st.warning(r)
                if result['limitations']:
                    for l in result['limitations']:
                        st.error(l)
                if not result['rebuttals'] and not result['limitations']:
                    st.caption("특별한 반박점이 없습니다.")

            st.markdown("#### 💡 제안")
            for suggestion in result['suggestions']:
                st.info(suggestion)
        else:
            st.warning("투자 논리를 입력해주세요.")
