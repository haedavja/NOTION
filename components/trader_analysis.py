"""
트레이더 토론 스타일 종목 분석 v2.0
- 지속적인 토론 시스템 (1회성 X)
- 사용자 질문/반론에 트레이더들이 응답
- 트레이더간 상호 반박/동의
- 토론 히스토리 유지
"""

import streamlit as st
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import random
import hashlib


@dataclass
class TraderPersona:
    """트레이더 페르소나"""
    name: str
    style: str
    avatar: str
    color: str
    bias: str
    description: str
    response_patterns: List[str] = field(default_factory=list)


# 6명의 가상 트레이더 (응답 패턴 추가)
STOCK_TRADERS = [
    TraderPersona(
        name="가치투자 김부장",
        style="value",
        avatar="👔",
        color="#2563eb",
        bias="neutral",
        description="PER, PBR, 배당수익률 중심의 가치투자자",
        response_patterns=[
            "밸류에이션 관점에서 보면",
            "내재가치 대비",
            "벤저민 그레이엄이 살아있다면",
            "안전마진 측면에서"
        ]
    ),
    TraderPersona(
        name="성장주 이대리",
        style="growth",
        avatar="🚀",
        color="#16a34a",
        bias="bullish",
        description="매출성장률, 신사업 가능성 중시",
        response_patterns=[
            "성장 스토리로 보면",
            "미래 잠재력 측면에서",
            "피터 린치 스타일로 접근하면",
            "성장률을 고려하면"
        ]
    ),
    TraderPersona(
        name="차트쟁이 박과장",
        style="technical",
        avatar="📊",
        color="#dc2626",
        bias="neutral",
        description="이동평균선, RSI, MACD 기술적 분석가",
        response_patterns=[
            "차트상으로는",
            "기술적 지표를 보면",
            "추세선 관점에서",
            "캔들 패턴이"
        ]
    ),
    TraderPersona(
        name="역발상 최차장",
        style="contrarian",
        avatar="🔄",
        color="#9333ea",
        bias="bearish",
        description="대중과 반대로 가는 역발상 투자자",
        response_patterns=[
            "다들 그렇게 생각하지만",
            "반대로 생각해보면",
            "군중심리와 반대로",
            "워런 버핏 말처럼 공포에 사고"
        ]
    ),
    TraderPersona(
        name="퀀트 정연구원",
        style="quant",
        avatar="🤖",
        color="#0891b2",
        bias="neutral",
        description="데이터와 수치 기반 정량적 분석가",
        response_patterns=[
            "데이터를 보면",
            "수치적으로 분석하면",
            "통계적 관점에서",
            "팩터 분석 결과"
        ]
    ),
    TraderPersona(
        name="모멘텀 한실장",
        style="momentum",
        avatar="⚡",
        color="#ea580c",
        bias="bullish",
        description="수급, 거래량, 모멘텀 추종 트레이더",
        response_patterns=[
            "수급 흐름을 보면",
            "모멘텀 관점에서",
            "외국인/기관 동향이",
            "거래량이 말해주듯"
        ]
    ),
]


def get_trader_by_style(style: str) -> Optional[TraderPersona]:
    """스타일로 트레이더 찾기"""
    for trader in STOCK_TRADERS:
        if trader.style == style:
            return trader
    return None


def analyze_stock_by_trader(
    trader: TraderPersona,
    stock_name: str,
    stock_code: str,
    scores: Dict,
    fundamentals: Dict = None
) -> Dict:
    """트레이더 관점에서 종목 분석"""

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
        'timestamp': datetime.now().strftime("%H:%M"),
        'detailed_reasoning': ''
    }

    # 트레이더 스타일별 분석
    if trader.style == 'value':
        if value_score >= 4.5:
            analysis['stance'] = 'bullish'
            analysis['confidence'] = 75 + random.randint(0, 15)
            analysis['strengths'].append("저평가 매력 높음")
            analysis['key_point'] = "PER/PBR 기준 매력적인 진입 구간"
            analysis['detailed_reasoning'] = f"현재 가치점수 {value_score:.1f}/6으로 저평가 영역입니다. 시장이 이 종목의 본질적 가치를 제대로 반영하지 못하고 있어요."
        elif value_score <= 2.5:
            analysis['stance'] = 'bearish'
            analysis['confidence'] = 65 + random.randint(0, 15)
            analysis['weaknesses'].append("고평가 구간")
            analysis['key_point'] = "현 주가는 펀더멘털 대비 과도"
            analysis['detailed_reasoning'] = f"가치점수가 {value_score:.1f}/6입니다. 현재 주가가 내재가치보다 높게 형성되어 있어 조심해야 합니다."
        else:
            analysis['stance'] = 'neutral'
            analysis['confidence'] = 50 + random.randint(0, 10)
            analysis['key_point'] = "적정 밸류에이션, 관망"
            analysis['detailed_reasoning'] = f"가치점수 {value_score:.1f}/6으로 적정 수준입니다. 확실한 저평가도 고평가도 아닌 상황이에요."

        if dividend_score >= 4.0:
            analysis['strengths'].append("배당수익률 매력적")

    elif trader.style == 'growth':
        if future_score >= 4.5:
            analysis['stance'] = 'bullish'
            analysis['confidence'] = 80 + random.randint(0, 15)
            analysis['strengths'].append("높은 성장 잠재력")
            analysis['key_point'] = "성장 모멘텀 강력, 적극 매수"
            analysis['detailed_reasoning'] = f"미래 성장 점수가 {future_score:.1f}/6으로 매우 높습니다! 이 정도 성장성이면 현재 밸류에이션은 충분히 정당화됩니다."
        elif future_score <= 2.5:
            analysis['stance'] = 'bearish'
            analysis['confidence'] = 60 + random.randint(0, 15)
            analysis['weaknesses'].append("성장성 둔화 우려")
            analysis['key_point'] = "성장 동력 약화"
            analysis['detailed_reasoning'] = f"성장 점수 {future_score:.1f}/6은 우려되는 수준입니다. 성장 스토리가 꺾이면 주가 조정이 불가피해요."
        else:
            analysis['stance'] = 'neutral'
            analysis['confidence'] = 55 + random.randint(0, 10)
            analysis['key_point'] = "성장성 보통, 실적 확인 필요"
            analysis['detailed_reasoning'] = f"미래 성장 점수 {future_score:.1f}/6입니다. 나쁘지 않지만, 분기 실적으로 방향성을 확인해야 합니다."

    elif trader.style == 'technical':
        if total_score >= 4.5:
            analysis['stance'] = 'bullish'
            analysis['confidence'] = 70 + random.randint(0, 15)
            analysis['strengths'].append("상승 추세 진행")
            analysis['key_point'] = "기술적 매수 신호"
            analysis['detailed_reasoning'] = "종합 점수가 높다는 건 펀더멘털이 받쳐준다는 뜻이고, 이런 종목은 기술적으로도 상승 추세를 형성하기 쉽습니다."
        elif total_score <= 2.5:
            analysis['stance'] = 'bearish'
            analysis['confidence'] = 65 + random.randint(0, 15)
            analysis['weaknesses'].append("하락 추세 또는 박스권")
            analysis['key_point'] = "기술적 지지선 이탈 주의"
            analysis['detailed_reasoning'] = "펀더멘털이 약하면 차트도 무너지기 마련입니다. 지지선 이탈 시 손절 대응이 필요해요."
        else:
            analysis['stance'] = 'neutral'
            analysis['confidence'] = 50 + random.randint(0, 15)
            analysis['key_point'] = "방향성 탐색 구간"
            analysis['detailed_reasoning'] = "현재는 뚜렷한 추세가 없습니다. 돌파나 이탈 시점을 기다리는 게 현명해요."

    elif trader.style == 'contrarian':
        if total_score >= 5.0:
            analysis['stance'] = 'bearish'
            analysis['confidence'] = 60 + random.randint(0, 15)
            analysis['weaknesses'].append("과열 신호")
            analysis['key_point'] = "모두가 좋다할 때가 팔 때"
            analysis['detailed_reasoning'] = f"종합 {total_score:.1f}/6? 너무 완벽해 보이죠? 이럴 때가 가장 위험합니다. 좋은 뉴스는 이미 주가에 반영됐을 가능성이 높아요."
        elif total_score <= 2.0:
            analysis['stance'] = 'bullish'
            analysis['confidence'] = 65 + random.randint(0, 15)
            analysis['strengths'].append("공포 극대화 구간")
            analysis['key_point'] = "모두가 외면할 때가 살 때"
            analysis['detailed_reasoning'] = f"점수가 {total_score:.1f}/6으로 최악이네요. 하지만 이런 구간에서 역발상 매수가 큰 수익을 안겨줍니다."
        else:
            analysis['stance'] = 'neutral'
            analysis['confidence'] = 45 + random.randint(0, 10)
            analysis['key_point'] = "극단적 센티먼트 아님"
            analysis['detailed_reasoning'] = "지금은 극단적인 상황이 아니라서 역발상 전략을 쓰기 애매합니다."

    elif trader.style == 'quant':
        avg_score = (value_score + future_score + past_score + health_score + dividend_score) / 5

        if avg_score >= 4.0:
            analysis['stance'] = 'bullish'
            analysis['confidence'] = int(avg_score * 15) + random.randint(0, 10)
            analysis['strengths'].append(f"종합 스코어 상위권")
            analysis['key_point'] = f"퀀트 모델 매수 신호"
            analysis['detailed_reasoning'] = f"5개 팩터 평균 {avg_score:.2f}/6입니다. 통계적으로 이 수준의 종목은 시장 대비 초과수익 확률이 높습니다."
        elif avg_score <= 2.5:
            analysis['stance'] = 'bearish'
            analysis['confidence'] = 60 + random.randint(0, 15)
            analysis['weaknesses'].append("종합 스코어 하위권")
            analysis['key_point'] = "퀀트 모델 매도 신호"
            analysis['detailed_reasoning'] = f"팩터 평균 {avg_score:.2f}/6은 하위 30% 수준입니다. 데이터가 이 종목을 추천하지 않습니다."
        else:
            analysis['stance'] = 'neutral'
            analysis['confidence'] = 50 + random.randint(0, 10)
            analysis['key_point'] = "중립 구간"
            analysis['detailed_reasoning'] = f"평균 스코어 {avg_score:.2f}/6으로 통계적 우위가 없습니다. 다른 팩터를 추가로 검토해야 합니다."

    elif trader.style == 'momentum':
        if future_score >= 4.0 and past_score >= 3.5:
            analysis['stance'] = 'bullish'
            analysis['confidence'] = 75 + random.randint(0, 15)
            analysis['strengths'].append("실적 모멘텀 양호")
            analysis['key_point'] = "상승 모멘텀 탑승"
            analysis['detailed_reasoning'] = f"과거 실적({past_score:.1f}/6)도 좋고 미래 전망({future_score:.1f}/6)도 좋습니다. 이런 종목은 추세를 타면 쭉 갑니다."
        elif future_score <= 2.5:
            analysis['stance'] = 'bearish'
            analysis['confidence'] = 65 + random.randint(0, 10)
            analysis['weaknesses'].append("모멘텀 둔화")
            analysis['key_point'] = "모멘텀 이탈"
            analysis['detailed_reasoning'] = f"미래 전망 점수가 {future_score:.1f}/6입니다. 모멘텀이 꺾이면 빠지는 속도도 빠릅니다."
        else:
            analysis['stance'] = 'neutral'
            analysis['confidence'] = 55 + random.randint(0, 10)
            analysis['key_point'] = "모멘텀 탐색 중"
            analysis['detailed_reasoning'] = "확실한 모멘텀이 형성되지 않았습니다. 거래량 증가와 함께 방향이 정해질 때 진입해도 늦지 않아요."

    # 공통 분석 추가
    if health_score >= 4.5:
        analysis['strengths'].append("탄탄한 재무구조")
    elif health_score <= 2.0:
        analysis['weaknesses'].append("재무 리스크")

    # 추천 생성
    if analysis['stance'] == 'bullish':
        analysis['recommendation'] = random.choice([
            "매수 관점 접근", "분할 매수 권고", "비중 확대 고려"
        ])
    elif analysis['stance'] == 'bearish':
        analysis['recommendation'] = random.choice([
            "신규 진입 자제", "비중 축소 권고", "리스크 관리 필요"
        ])
    else:
        analysis['recommendation'] = random.choice([
            "추가 확인 후 결정", "관망 권고", "방향성 확인 대기"
        ])

    return analysis


def generate_trader_response_to_user(
    trader: TraderPersona,
    user_question: str,
    stock_name: str,
    scores: Dict,
    discussion_history: List[Dict]
) -> str:
    """사용자 질문에 대한 트레이더 응답 생성"""

    q_lower = user_question.lower()
    pattern = random.choice(trader.response_patterns)

    # 키워드 기반 응답 생성
    if trader.style == 'value':
        if any(w in q_lower for w in ['저평가', 'per', 'pbr', '가격', '싸']):
            if scores.get('value', 3) >= 4:
                return f"{pattern}, {stock_name}은 현재 밸류에이션 매력이 있습니다. 가치점수 {scores.get('value', 3):.1f}/6은 저평가 영역이에요."
            else:
                return f"{pattern}, 솔직히 {stock_name}이 저평가라고 보기 어렵습니다. 가치점수가 {scores.get('value', 3):.1f}/6밖에 안 돼요."
        elif any(w in q_lower for w in ['매수', '사도', '들어가']):
            if scores.get('value', 3) >= 4:
                return f"가치투자 관점에서 지금 진입해도 됩니다. 다만 분할 매수로 리스크를 관리하세요."
            else:
                return f"솔직히 지금은 가치투자 매력이 떨어집니다. 더 좋은 가격을 기다리거나 다른 종목을 보세요."
        elif any(w in q_lower for w in ['언제', '시점', '타이밍']):
            return f"가치투자는 타이밍보다 가격입니다. 내재가치 대비 충분한 할인이 있을 때가 적기예요."

    elif trader.style == 'growth':
        if any(w in q_lower for w in ['성장', '미래', '전망', '잠재력']):
            if scores.get('future', 3) >= 4:
                return f"{pattern}, {stock_name}의 성장 잠재력은 높습니다! 미래 점수 {scores.get('future', 3):.1f}/6이면 기대해볼 만해요."
            else:
                return f"{pattern}, 성장 스토리가 약해요. 미래 점수 {scores.get('future', 3):.1f}/6은 아쉽습니다."
        elif any(w in q_lower for w in ['신사업', '확장', '성장동력']):
            return f"성장주 투자의 핵심은 '다음 성장동력'이 있느냐입니다. 이 부분을 IR이나 뉴스로 확인해보세요."
        elif any(w in q_lower for w in ['매수', '들어가']):
            if scores.get('future', 3) >= 4:
                return f"성장 스토리가 살아있다면 지금 들어가도 됩니다. 다만 분기 실적 발표 일정은 체크하세요."
            else:
                return f"솔직히 성장주로서의 매력이 떨어져요. 더 확실한 성장 종목이 있을 겁니다."

    elif trader.style == 'technical':
        if any(w in q_lower for w in ['차트', '추세', '지지', '저항']):
            return f"{pattern}, 현재 종합 점수로 추세를 유추하면 {'상승' if scores.get('total', 3) >= 4 else '하락 또는 횡보'} 국면입니다."
        elif any(w in q_lower for w in ['매수', '진입', '타이밍']):
            return f"{pattern}, 정확한 타이밍은 실제 차트를 봐야 합니다. 펀더멘털 점수만으로는 기술적 진입점을 잡기 어려워요."
        elif any(w in q_lower for w in ['손절', '익절']):
            return f"손절선은 직전 저점 -3~5% 아래, 익절은 목표가 도달 또는 추세 이탈 시 설정하세요."

    elif trader.style == 'contrarian':
        if any(w in q_lower for w in ['다들', '모두', '인기', '핫한']):
            return f"{pattern}, 다들 좋다고 하면 이미 늦은 거예요. 역발상의 기본은 '남들이 무시할 때 사는 것'입니다."
        elif any(w in q_lower for w in ['위험', '리스크', '걱정']):
            if scores.get('total', 3) <= 2.5:
                return f"모두가 걱정할 때가 기회입니다. 공포에 매수하고 탐욕에 매도하세요."
            else:
                return f"지금은 공포 구간이 아니에요. 역발상 전략은 극단적 상황에서 효과적입니다."
        elif any(w in q_lower for w in ['매수', '들어가']):
            if scores.get('total', 3) >= 4.5:
                return f"솔직히 지금은 너무 좋아 보여서 오히려 걱정입니다. 차익실현 타이밍 아닐까요?"
            elif scores.get('total', 3) <= 2:
                return f"역발상 관점에서 흥미로운 구간입니다. 다만 왜 이렇게 싸졌는지 이유는 파악해야 해요."
            else:
                return f"극단적 상황이 아니라서 역발상 전략이 잘 안 맞아요."

    elif trader.style == 'quant':
        if any(w in q_lower for w in ['데이터', '수치', '점수', '팩터']):
            avg = (scores.get('value', 3) + scores.get('future', 3) + scores.get('past', 3) +
                   scores.get('health', 3) + scores.get('dividend', 3)) / 5
            return f"{pattern}, 5개 팩터 평균 {avg:.2f}/6입니다. {'상위 30%' if avg >= 4 else '중위권' if avg >= 3 else '하위권'}에 해당합니다."
        elif any(w in q_lower for w in ['확률', '통계', '백테스트']):
            return f"통계적으로 고팩터 종목이 저팩터 대비 연 3-5%p 초과수익을 보입니다. 단, 모든 상황에 적용되진 않아요."
        elif any(w in q_lower for w in ['매수', '들어가']):
            avg = (scores.get('value', 3) + scores.get('future', 3) + scores.get('past', 3) +
                   scores.get('health', 3) + scores.get('dividend', 3)) / 5
            if avg >= 4:
                return f"퀀트 모델상 매수 신호입니다. 하지만 단일 종목 집중보다 분산 투자를 권합니다."
            else:
                return f"현재 팩터 점수로는 매수 시그널이 아닙니다. 더 높은 점수의 종목을 찾아보세요."

    elif trader.style == 'momentum':
        if any(w in q_lower for w in ['수급', '거래량', '외국인', '기관']):
            return f"{pattern}, 실제 수급 데이터는 별도로 확인해야 합니다. 펀더멘털 점수만으로는 수급을 알 수 없어요."
        elif any(w in q_lower for w in ['모멘텀', '추세', '강세']):
            if scores.get('future', 3) >= 4:
                return f"실적 모멘텀은 살아있어 보입니다. 미래 전망 점수가 {scores.get('future', 3):.1f}/6으로 양호해요."
            else:
                return f"모멘텀이 약해지고 있어요. 미래 점수 {scores.get('future', 3):.1f}/6은 아쉬운 수준입니다."
        elif any(w in q_lower for w in ['매수', '들어가']):
            if scores.get('future', 3) >= 4 and scores.get('past', 3) >= 3.5:
                return f"모멘텀이 살아있을 때 올라타세요! 다만 추세 이탈 시 빠르게 손절해야 합니다."
            else:
                return f"지금은 확실한 모멘텀이 없어서 진입하기 애매해요."

    # 기본 응답
    return f"{pattern}, 좋은 질문입니다. {stock_name}에 대해 더 구체적으로 물어봐 주시면 제 관점에서 분석해드릴게요."


def generate_trader_debate(
    trader1: TraderPersona,
    trader2: TraderPersona,
    topic: str,
    scores: Dict
) -> Dict:
    """두 트레이더 간 토론/반박 생성"""

    debate_responses = {
        'value_vs_growth': {
            'value': "성장성도 중요하지만, 결국 주가는 이익에 수렴합니다. 너무 비싸게 사면 성장해도 수익이 안 나요.",
            'growth': "가치주는 싸지만 '싼 이유'가 있잖아요. 성장하는 기업에 투자해야 복리 효과를 누립니다."
        },
        'technical_vs_value': {
            'technical': "차트는 모든 정보를 반영합니다. 펀더멘털 좋아도 차트가 안 좋으면 안 사요.",
            'value': "차트는 과거일 뿐입니다. 미래의 내재가치를 보고 투자해야죠."
        },
        'momentum_vs_contrarian': {
            'momentum': "추세가 친구입니다. 올라가는 것에 올라타야지, 떨어지는 칼날을 잡으면 안 돼요.",
            'contrarian': "추세 끝에서 사면 물립니다. 남들이 안 볼 때 사야 싸게 살 수 있어요."
        },
        'quant_vs_intuition': {
            'quant': "감이나 경험은 편향을 만듭니다. 데이터 기반 의사결정이 장기적으로 우월해요.",
            'value': "숫자 뒤에 있는 비즈니스를 이해해야 합니다. 퀀트만으로는 한계가 있어요."
        }
    }

    # 스타일 조합에 따른 토론 생성
    combo = f"{trader1.style}_vs_{trader2.style}"
    reverse_combo = f"{trader2.style}_vs_{trader1.style}"

    if combo in debate_responses:
        return {
            'trader1_response': debate_responses[combo].get(trader1.style, "동의하는 부분도 있지만, 제 관점은 다릅니다."),
            'trader2_response': debate_responses[combo].get(trader2.style, "그 관점도 일리가 있네요. 하지만...")
        }
    elif reverse_combo in debate_responses:
        return {
            'trader1_response': debate_responses[reverse_combo].get(trader1.style, "제 생각은 조금 다릅니다."),
            'trader2_response': debate_responses[reverse_combo].get(trader2.style, "네, 이해합니다만...")
        }
    else:
        return {
            'trader1_response': f"{random.choice(trader1.response_patterns)}, 제 분석과는 다른 관점이시네요.",
            'trader2_response': f"{random.choice(trader2.response_patterns)}, 서로 다른 시각이 있을 수 있죠."
        }


def get_discussion_key(stock_code: str) -> str:
    """종목별 토론 키 생성"""
    return f"trader_discussion_{stock_code}"


def init_discussion_state(stock_code: str):
    """토론 상태 초기화"""
    key = get_discussion_key(stock_code)
    if key not in st.session_state:
        st.session_state[key] = {
            'history': [],
            'round': 0,
            'initial_analysis_done': False
        }


def add_to_discussion(stock_code: str, entry: Dict):
    """토론에 항목 추가"""
    key = get_discussion_key(stock_code)
    if key in st.session_state:
        st.session_state[key]['history'].append(entry)


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

    discussions.sort(key=lambda x: x['confidence'], reverse=True)
    return discussions


def render_trader_discussion_ui(
    stock_name: str,
    stock_code: str,
    scores: Dict,
    fundamentals: Dict = None
):
    """지속적 토론 UI 렌더링"""

    # 상태 초기화
    init_discussion_state(stock_code)
    disc_key = get_discussion_key(stock_code)
    disc_state = st.session_state[disc_key]

    st.markdown(f"### 💬 {stock_name} 전문가 토론방")
    st.caption("6명의 전문가와 지속적으로 대화하며 분석을 심화하세요")

    # 초기 분석 (첫 라운드)
    if not disc_state['initial_analysis_done']:
        discussions = generate_trader_discussion(stock_name, stock_code, scores, fundamentals)

        # 의견 요약
        bullish = sum(1 for d in discussions if d['stance'] == 'bullish')
        bearish = sum(1 for d in discussions if d['stance'] == 'bearish')
        neutral = sum(1 for d in discussions if d['stance'] == 'neutral')

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🟢 매수", f"{bullish}명")
        with col2:
            st.metric("🟡 중립", f"{neutral}명")
        with col3:
            st.metric("🔴 매도", f"{bearish}명")

        st.divider()

        # 각 트레이더 초기 의견
        for analysis in discussions:
            _render_trader_message(analysis, is_initial=True)

            # 히스토리에 추가
            add_to_discussion(stock_code, {
                'type': 'initial',
                'trader': analysis['trader'].name,
                'style': analysis['trader'].style,
                'message': analysis['key_point'],
                'stance': analysis['stance'],
                'timestamp': analysis['timestamp']
            })

        disc_state['initial_analysis_done'] = True
        disc_state['initial_discussions'] = discussions

    else:
        # 기존 히스토리 표시
        discussions = disc_state.get('initial_discussions', [])

        # 요약 다시 표시
        bullish = sum(1 for d in discussions if d['stance'] == 'bullish')
        bearish = sum(1 for d in discussions if d['stance'] == 'bearish')
        neutral = sum(1 for d in discussions if d['stance'] == 'neutral')

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🟢 매수", f"{bullish}명")
        with col2:
            st.metric("🟡 중립", f"{neutral}명")
        with col3:
            st.metric("🔴 매도", f"{bearish}명")

        st.divider()

        # 초기 의견
        for analysis in discussions:
            _render_trader_message(analysis, is_initial=True)

        # 후속 대화
        for entry in disc_state['history']:
            if entry['type'] == 'user_question':
                st.markdown(f"""
                <div style='background: #e0f2fe; border-radius: 12px; padding: 0.8rem; margin: 0.5rem 0;
                            border-left: 4px solid #0284c7;'>
                    <div style='font-weight: bold; margin-bottom: 0.3rem;'>🙋 나의 질문</div>
                    <div>{entry['message']}</div>
                </div>
                """, unsafe_allow_html=True)
            elif entry['type'] == 'trader_response':
                trader = get_trader_by_style(entry['style'])
                if trader:
                    st.markdown(f"""
                    <div style='background: white; border: 1px solid #e5e7eb; border-left: 4px solid {trader.color};
                                border-radius: 8px; padding: 0.8rem; margin: 0.3rem 0;'>
                        <div style='display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.3rem;'>
                            <span>{trader.avatar}</span>
                            <span style='font-weight: bold; color: {trader.color};'>{trader.name}</span>
                        </div>
                        <div style='font-size: 0.9rem;'>{entry['message']}</div>
                    </div>
                    """, unsafe_allow_html=True)
            elif entry['type'] == 'debate':
                st.markdown(f"""
                <div style='background: #fef3c7; border-radius: 8px; padding: 0.8rem; margin: 0.5rem 0;'>
                    <div style='font-weight: bold; margin-bottom: 0.5rem;'>⚔️ 트레이더 토론</div>
                    <div style='font-size: 0.9rem;'>{entry['message']}</div>
                </div>
                """, unsafe_allow_html=True)

    st.divider()

    # 사용자 입력 섹션
    st.markdown("### 💭 질문하기 / 토론 이어가기")

    col_input, col_action = st.columns([3, 1])

    with col_input:
        user_input = st.text_input(
            "질문이나 의견을 입력하세요",
            placeholder="예: 지금 매수해도 될까요? / 성장성이 걱정되는데...",
            key=f"user_q_{stock_code}_{disc_state['round']}"
        )

    with col_action:
        ask_trader = st.selectbox(
            "질문 대상",
            ["전체"] + [t.name for t in STOCK_TRADERS],
            key=f"target_{stock_code}"
        )

    col_btn1, col_btn2, col_btn3 = st.columns(3)

    with col_btn1:
        if st.button("💬 질문하기", key=f"ask_{stock_code}", use_container_width=True):
            if user_input.strip():
                # 사용자 질문 추가
                add_to_discussion(stock_code, {
                    'type': 'user_question',
                    'message': user_input,
                    'timestamp': datetime.now().strftime("%H:%M")
                })

                # 트레이더 응답 생성
                if ask_trader == "전체":
                    # 2-3명 랜덤 응답
                    responders = random.sample(STOCK_TRADERS, min(3, len(STOCK_TRADERS)))
                else:
                    responders = [t for t in STOCK_TRADERS if t.name == ask_trader]

                for trader in responders:
                    response = generate_trader_response_to_user(
                        trader, user_input, stock_name, scores, disc_state['history']
                    )
                    add_to_discussion(stock_code, {
                        'type': 'trader_response',
                        'trader': trader.name,
                        'style': trader.style,
                        'message': response,
                        'timestamp': datetime.now().strftime("%H:%M")
                    })

                disc_state['round'] += 1
                st.rerun()

    with col_btn2:
        if st.button("⚔️ 토론 유발", key=f"debate_{stock_code}", use_container_width=True):
            # 서로 다른 의견의 트레이더 선택
            bulls = [d for d in discussions if d['stance'] == 'bullish']
            bears = [d for d in discussions if d['stance'] == 'bearish']

            if bulls and bears:
                # 매수파 vs 매도파 토론
                t1 = random.choice(bulls)['trader']
                t2 = random.choice(bears)['trader']
            else:
                # 의견이 비슷해도 스타일이 다르면 토론 가능
                # 가치 vs 성장, 기술적 vs 펀더멘털, 모멘텀 vs 역발상 등
                debate_pairs = [
                    ('value', 'growth'),      # 가치 vs 성장
                    ('technical', 'value'),   # 차트 vs 펀더멘털
                    ('momentum', 'contrarian'), # 모멘텀 vs 역발상
                    ('quant', 'growth'),      # 퀀트 vs 성장
                ]
                pair = random.choice(debate_pairs)
                t1 = get_trader_by_style(pair[0])
                t2 = get_trader_by_style(pair[1])

            if t1 and t2:
                debate = generate_trader_debate(t1, t2, "stance", scores)

                add_to_discussion(stock_code, {
                    'type': 'debate',
                    'message': f"**{t1.avatar} {t1.name}**: {debate['trader1_response']}\n\n**{t2.avatar} {t2.name}**: {debate['trader2_response']}",
                    'timestamp': datetime.now().strftime("%H:%M")
                })
                disc_state['round'] += 1
                st.rerun()

    with col_btn3:
        if st.button("🔄 토론 초기화", key=f"reset_{stock_code}", use_container_width=True):
            st.session_state[disc_key] = {
                'history': [],
                'round': 0,
                'initial_analysis_done': False
            }
            st.rerun()

    # 토론 깊이 표시
    rounds = disc_state['round']
    if rounds > 0:
        st.caption(f"📊 토론 깊이: {rounds}라운드 | 더 많은 질문으로 분석을 심화하세요")


def _render_trader_message(analysis: Dict, is_initial: bool = False):
    """트레이더 메시지 렌더링"""
    trader = analysis['trader']
    stance = analysis['stance']

    if stance == 'bullish':
        border_color = '#22c55e'
        stance_emoji = '🟢'
        stance_text = '매수'
    elif stance == 'bearish':
        border_color = '#ef4444'
        stance_emoji = '🔴'
        stance_text = '매도'
    else:
        border_color = '#eab308'
        stance_emoji = '🟡'
        stance_text = '중립'

    st.markdown(f"""
    <div style='background: white; border: 1px solid #e5e7eb; border-left: 4px solid {trader.color};
                border-radius: 8px; padding: 0.8rem; margin-bottom: 0.6rem;'>
        <div style='display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.4rem;'>
            <span style='font-size: 1.3rem;'>{trader.avatar}</span>
            <span style='font-weight: bold; color: {trader.color};'>{trader.name}</span>
            <span style='background: {border_color}20; color: {border_color};
                        padding: 2px 6px; border-radius: 10px; font-size: 0.75rem;'>
                {stance_emoji} {stance_text}
            </span>
            <span style='margin-left: auto; font-size: 0.7rem; color: #9ca3af;'>
                신뢰도 {analysis['confidence']}%
            </span>
        </div>
        <div style='font-size: 0.9rem; margin-bottom: 0.3rem;'>
            <strong>{analysis['key_point']}</strong>
        </div>
        <div style='font-size: 0.85rem; color: #4b5563;'>
            {analysis.get('detailed_reasoning', '')}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 상세 분석 (초기 분석일 때만)
    if is_initial and (analysis['strengths'] or analysis['weaknesses']):
        with st.expander(f"📋 {trader.name} 상세 분석", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**💪 강점**")
                for s in analysis['strengths']:
                    st.markdown(f"- {s}")
                if not analysis['strengths']:
                    st.caption("없음")
            with col2:
                st.markdown("**⚠️ 약점**")
                for w in analysis['weaknesses']:
                    st.markdown(f"- {w}")
                if not analysis['weaknesses']:
                    st.caption("없음")


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
        'overall_assessment': '',
        'trader_opinions': []
    }

    thesis_lower = thesis.lower()

    # 키워드 기반 분석
    if any(word in thesis_lower for word in ['저평가', 'per 낮', 'pbr 낮', '싸다', '저렴']):
        if scores.get('value', 3) >= 4:
            result['strengths'].append("✓ 가치지표상 저평가 구간입니다.")
        else:
            result['rebuttals'].append("⚠️ 밸류에이션이 저평가라 보기 어렵습니다.")
            result['limitations'].append("'가치 함정'일 수 있습니다.")

    if any(word in thesis_lower for word in ['성장', '신사업', '확장', '매출 증가']):
        if scores.get('future', 3) >= 4:
            result['strengths'].append("✓ 성장 전망 지표가 양호합니다.")
        else:
            result['rebuttals'].append("⚠️ 성장성 점수가 낮습니다.")
            result['limitations'].append("성장 기대가 과도할 수 있습니다.")

    if any(word in thesis_lower for word in ['배당', '배당금', '배당수익률']):
        if scores.get('dividend', 3) >= 4:
            result['strengths'].append("✓ 배당 매력이 높습니다.")
        else:
            result['rebuttals'].append("⚠️ 배당 매력이 낮습니다.")

    if any(word in thesis_lower for word in ['안정', '튼튼', '재무', '부채']):
        if scores.get('health', 3) >= 4:
            result['strengths'].append("✓ 재무건전성이 양호합니다.")
        else:
            result['rebuttals'].append("⚠️ 재무 리스크가 있습니다.")

    if any(word in thesis_lower for word in ['바닥', '지지', '돌파', '추세']):
        result['limitations'].append("기술적 분석은 펀더멘털 변화에 취약합니다.")
        result['suggestions'].append("펀더멘털 분석과 병행하세요.")

    if any(word in thesis_lower for word in ['테마', '정책', '수혜', '이슈']):
        result['limitations'].append("테마는 일시적일 수 있습니다.")
        result['suggestions'].append("테마 종료 후 펀더멘털을 확인하세요.")

    # 종합 평가
    total = scores.get('total', 3)
    if len(result['strengths']) > len(result['rebuttals']):
        result['overall_assessment'] = f"📊 투자논리가 데이터와 대체로 일치합니다. (점수: {total:.1f}/6)"
    elif len(result['rebuttals']) > len(result['strengths']):
        result['overall_assessment'] = f"⚠️ 재검토가 필요합니다. (점수: {total:.1f}/6)"
    else:
        result['overall_assessment'] = f"📋 추가 검증이 필요합니다. (점수: {total:.1f}/6)"

    if not result['suggestions']:
        result['suggestions'] = ["분할 매수로 리스크 분산", "손절 기준 설정", "정기적 논리 재검토"]

    # 트레이더들의 의견 추가
    for trader in random.sample(STOCK_TRADERS, 2):
        response = generate_trader_response_to_user(trader, thesis, stock_name, scores, [])
        result['trader_opinions'].append({
            'trader': trader,
            'opinion': response
        })

    return result


def render_thesis_analysis_ui(
    stock_name: str,
    stock_code: str,
    scores: Dict,
    fundamentals: Dict = None
):
    """투자논리 분석 UI (지속적 대화 지원)"""

    thesis_key = f"thesis_history_{stock_code}"
    if thesis_key not in st.session_state:
        st.session_state[thesis_key] = []

    st.markdown("### 📝 나의 투자논리 검증")
    st.caption("투자 이유를 적으면 전문가들이 반박/보완해드립니다")

    # 히스토리 표시
    for entry in st.session_state[thesis_key]:
        if entry['type'] == 'thesis':
            st.markdown(f"""
            <div style='background: #dbeafe; border-radius: 8px; padding: 0.8rem; margin: 0.5rem 0;'>
                <strong>📝 나의 논리:</strong> {entry['content']}
            </div>
            """, unsafe_allow_html=True)
        elif entry['type'] == 'analysis':
            st.markdown(f"**{entry['assessment']}**")
            col1, col2 = st.columns(2)
            with col1:
                for s in entry.get('strengths', []):
                    st.success(s)
            with col2:
                for r in entry.get('rebuttals', []):
                    st.warning(r)
            for opinion in entry.get('trader_opinions', []):
                trader = opinion['trader']
                st.markdown(f"""
                <div style='background: white; border-left: 3px solid {trader.color}; padding: 0.5rem; margin: 0.3rem 0;'>
                    {trader.avatar} <strong>{trader.name}</strong>: {opinion['opinion']}
                </div>
                """, unsafe_allow_html=True)

    # 새 입력
    thesis = st.text_area(
        "투자 논리를 입력하세요",
        placeholder="예: 이 종목은 PER이 낮고 배당이 높아서...",
        key=f"thesis_input_{stock_code}",
        height=80
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("🔍 논리 검증", key=f"verify_{stock_code}", use_container_width=True):
            if thesis.strip():
                result = analyze_investment_thesis(thesis, stock_name, scores, fundamentals)

                # 히스토리에 추가
                st.session_state[thesis_key].append({
                    'type': 'thesis',
                    'content': thesis
                })
                st.session_state[thesis_key].append({
                    'type': 'analysis',
                    'assessment': result['overall_assessment'],
                    'strengths': result['strengths'],
                    'rebuttals': result['rebuttals'],
                    'trader_opinions': result['trader_opinions']
                })
                st.rerun()
            else:
                st.warning("논리를 입력해주세요.")

    with col2:
        if st.button("🔄 대화 초기화", key=f"reset_thesis_{stock_code}", use_container_width=True):
            st.session_state[thesis_key] = []
            st.rerun()

    if st.session_state[thesis_key]:
        st.caption(f"💬 {len([e for e in st.session_state[thesis_key] if e['type'] == 'thesis'])}회 검증 완료")
