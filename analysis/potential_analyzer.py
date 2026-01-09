"""
잠재적 급등/급락 요인 분석 시스템
Potential Rally/Decline Factor Analyzer

아직 발생하지 않았지만 큰 주가 변동을 일으킬 수 있는 잠재적 요인을 분석합니다.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class CatalystType(Enum):
    """촉매 유형"""
    # 상승 촉매
    EARNINGS_SURPRISE = "실적 서프라이즈 가능성"
    NEW_PRODUCT_LAUNCH = "신제품/서비스 출시"
    MARKET_EXPANSION = "시장 확대/진출"
    REGULATORY_APPROVAL = "규제 승인/인허가"
    PARTNERSHIP_MA = "파트너십/M&A"
    COST_REDUCTION = "비용 절감/효율화"
    SECTOR_TAILWIND = "섹터 수혜/테마"
    UNDERVALUATION = "저평가 해소"
    SHORT_SQUEEZE = "숏스퀴즈 가능성"
    DIVIDEND_INCREASE = "배당 확대"
    BUYBACK = "자사주 매입"
    TURNAROUND = "턴어라운드"

    # 하락 촉매
    EARNINGS_MISS = "실적 미스 가능성"
    COMPETITION_THREAT = "경쟁 심화/점유율 하락"
    REGULATORY_RISK = "규제 리스크"
    DEBT_CONCERN = "부채/유동성 위기"
    DEMAND_SLOWDOWN = "수요 둔화"
    MARGIN_PRESSURE = "마진 압박"
    MANAGEMENT_ISSUE = "경영진/지배구조 이슈"
    SECTOR_HEADWIND = "섹터 역풍"
    OVERVALUATION = "고평가 부담"
    INSIDER_SELLING = "내부자 매도"
    DILUTION_RISK = "주식 희석 리스크"
    MACRO_SENSITIVITY = "매크로 민감도"


class ImpactLevel(Enum):
    """영향도 수준"""
    CRITICAL = ("치명적", 5, "#FF0000")
    HIGH = ("높음", 4, "#FF6B6B")
    MODERATE = ("중간", 3, "#FFB347")
    LOW = ("낮음", 2, "#98D8C8")
    MINIMAL = ("미미", 1, "#87CEEB")

    def __init__(self, korean: str, score: int, color: str):
        self.korean = korean
        self.score = score
        self.color = color


class Probability(Enum):
    """발생 확률"""
    VERY_HIGH = ("매우 높음", 0.9, "#FF0000")
    HIGH = ("높음", 0.7, "#FF6B6B")
    MODERATE = ("중간", 0.5, "#FFB347")
    LOW = ("낮음", 0.3, "#98D8C8")
    VERY_LOW = ("매우 낮음", 0.1, "#87CEEB")

    def __init__(self, korean: str, value: float, color: str):
        self.korean = korean
        self.value = value
        self.color = color


class Timeframe(Enum):
    """예상 시점"""
    IMMINENT = ("임박", "1주 이내", 7)
    SHORT_TERM = ("단기", "1개월 이내", 30)
    MEDIUM_TERM = ("중기", "1-3개월", 90)
    LONG_TERM = ("장기", "3-6개월", 180)
    UNCERTAIN = ("불확실", "시점 미정", 365)

    def __init__(self, korean: str, description: str, days: int):
        self.korean = korean
        self.description = description
        self.days = days


@dataclass
class PotentialCatalyst:
    """잠재적 촉매"""
    catalyst_type: CatalystType
    description: str
    impact: ImpactLevel
    probability: Probability
    timeframe: Timeframe

    # 상세 정보
    evidence: List[str] = field(default_factory=list)  # 근거
    risks: List[str] = field(default_factory=list)  # 리스크
    triggers: List[str] = field(default_factory=list)  # 트리거 조건

    # 예상 영향
    expected_move_pct: Optional[Tuple[float, float]] = None  # (최소, 최대)

    def expected_value(self) -> float:
        """기대값 계산 (영향도 * 확률)"""
        return self.impact.score * self.probability.value


@dataclass
class PotentialAnalysis:
    """잠재적 분석 결과"""
    symbol: str
    name: str
    analysis_date: datetime

    # 촉매 목록
    bullish_catalysts: List[PotentialCatalyst] = field(default_factory=list)
    bearish_catalysts: List[PotentialCatalyst] = field(default_factory=list)

    # 종합 점수
    bullish_score: float = 0.0  # 0-100
    bearish_score: float = 0.0  # 0-100

    # 최종 판단
    overall_bias: str = "중립"  # 강한 상승, 상승, 중립, 하락, 강한 하락
    risk_reward_ratio: float = 1.0
    conviction_level: str = "보통"  # 매우 높음, 높음, 보통, 낮음

    # 요약
    key_thesis: str = ""
    action_recommendation: str = ""
    watch_points: List[str] = field(default_factory=list)


class PotentialCatalystDetector:
    """잠재적 촉매 탐지기"""

    # 상승 촉매 키워드
    BULLISH_KEYWORDS = {
        CatalystType.EARNINGS_SURPRISE: [
            "실적 개선", "흑자 전환", "어닝 서프라이즈", "컨센서스 상회",
            "매출 증가", "이익률 개선", "가이던스 상향"
        ],
        CatalystType.NEW_PRODUCT_LAUNCH: [
            "신제품", "신규 서비스", "출시 예정", "런칭", "신사업",
            "혁신", "차세대", "신기술"
        ],
        CatalystType.MARKET_EXPANSION: [
            "시장 진출", "해외 진출", "점유율 확대", "고객 확보",
            "채널 확대", "신규 시장"
        ],
        CatalystType.REGULATORY_APPROVAL: [
            "승인", "인허가", "FDA", "규제 완화", "허가",
            "인증", "라이선스"
        ],
        CatalystType.PARTNERSHIP_MA: [
            "인수", "합병", "M&A", "파트너십", "전략적 제휴",
            "지분 투자", "조인트벤처"
        ],
        CatalystType.SECTOR_TAILWIND: [
            "수혜주", "테마", "정책 수혜", "트렌드", "성장 섹터"
        ],
        CatalystType.UNDERVALUATION: [
            "저평가", "PER 낮음", "PBR 낮음", "밸류에이션 매력",
            "역사적 저점", "할인 거래"
        ],
        CatalystType.SHORT_SQUEEZE: [
            "공매도", "숏커버", "대차잔고", "숏스퀴즈"
        ],
        CatalystType.TURNAROUND: [
            "턴어라운드", "구조조정", "체질 개선", "회복",
            "정상화", "재도약"
        ]
    }

    # 하락 촉매 키워드
    BEARISH_KEYWORDS = {
        CatalystType.EARNINGS_MISS: [
            "실적 부진", "적자", "어닝 쇼크", "컨센서스 하회",
            "매출 감소", "이익률 하락", "가이던스 하향"
        ],
        CatalystType.COMPETITION_THREAT: [
            "경쟁 심화", "점유율 하락", "가격 경쟁", "신규 진입자",
            "대체재", "경쟁사"
        ],
        CatalystType.REGULATORY_RISK: [
            "규제", "소송", "과징금", "제재", "조사",
            "법적 리스크", "컴플라이언스"
        ],
        CatalystType.DEBT_CONCERN: [
            "부채", "유동성", "차입금", "이자 비용", "신용등급",
            "자금난", "디폴트"
        ],
        CatalystType.DEMAND_SLOWDOWN: [
            "수요 감소", "둔화", "침체", "하락세", "위축",
            "소비 감소"
        ],
        CatalystType.MARGIN_PRESSURE: [
            "마진 축소", "원가 상승", "비용 증가", "수익성 악화",
            "가격 인하"
        ],
        CatalystType.MANAGEMENT_ISSUE: [
            "경영진", "지배구조", "횡령", "배임", "오너 리스크",
            "CEO", "내부 갈등"
        ],
        CatalystType.OVERVALUATION: [
            "고평가", "버블", "밸류에이션 부담", "PER 높음",
            "거품", "과열"
        ],
        CatalystType.INSIDER_SELLING: [
            "내부자 매도", "지분 매각", "블록딜", "오버행",
            "락업 해제"
        ],
        CatalystType.DILUTION_RISK: [
            "유상증자", "전환사채", "CB", "BW", "주식 발행",
            "희석"
        ]
    }

    def detect_catalysts(
        self,
        symbol: str,
        name: str,
        news: List[Dict],
        financial_data: Optional[Dict] = None,
        technical_data: Optional[Dict] = None
    ) -> Tuple[List[PotentialCatalyst], List[PotentialCatalyst]]:
        """잠재적 촉매 탐지"""
        bullish = []
        bearish = []

        # 뉴스 기반 촉매 탐지
        news_bullish, news_bearish = self._detect_from_news(news)
        bullish.extend(news_bullish)
        bearish.extend(news_bearish)

        # 재무 데이터 기반 촉매 탐지
        if financial_data:
            fin_bullish, fin_bearish = self._detect_from_financials(financial_data)
            bullish.extend(fin_bullish)
            bearish.extend(fin_bearish)

        # 기술적 데이터 기반 촉매 탐지
        if technical_data:
            tech_bullish, tech_bearish = self._detect_from_technicals(technical_data)
            bullish.extend(tech_bullish)
            bearish.extend(tech_bearish)

        # 중복 제거 및 정렬
        bullish = self._deduplicate_catalysts(bullish)
        bearish = self._deduplicate_catalysts(bearish)

        # 기대값 기준 정렬
        bullish.sort(key=lambda x: x.expected_value(), reverse=True)
        bearish.sort(key=lambda x: x.expected_value(), reverse=True)

        return bullish, bearish

    def _detect_from_news(
        self,
        news: List[Dict]
    ) -> Tuple[List[PotentialCatalyst], List[PotentialCatalyst]]:
        """뉴스에서 촉매 탐지"""
        bullish = []
        bearish = []

        for article in news:
            title = article.get("title", "")
            content = article.get("content", article.get("summary", ""))
            text = f"{title} {content}"

            # 상승 촉매 탐지
            for catalyst_type, keywords in self.BULLISH_KEYWORDS.items():
                matched_keywords = [kw for kw in keywords if kw in text]
                if matched_keywords:
                    catalyst = PotentialCatalyst(
                        catalyst_type=catalyst_type,
                        description=f"{catalyst_type.value}: {title[:50]}",
                        impact=self._estimate_impact(len(matched_keywords)),
                        probability=Probability.MODERATE,
                        timeframe=Timeframe.MEDIUM_TERM,
                        evidence=[f"뉴스: {title}"],
                        triggers=matched_keywords[:3]
                    )
                    bullish.append(catalyst)

            # 하락 촉매 탐지
            for catalyst_type, keywords in self.BEARISH_KEYWORDS.items():
                matched_keywords = [kw for kw in keywords if kw in text]
                if matched_keywords:
                    catalyst = PotentialCatalyst(
                        catalyst_type=catalyst_type,
                        description=f"{catalyst_type.value}: {title[:50]}",
                        impact=self._estimate_impact(len(matched_keywords)),
                        probability=Probability.MODERATE,
                        timeframe=Timeframe.MEDIUM_TERM,
                        evidence=[f"뉴스: {title}"],
                        risks=matched_keywords[:3]
                    )
                    bearish.append(catalyst)

        return bullish, bearish

    def _detect_from_financials(
        self,
        financial_data: Dict
    ) -> Tuple[List[PotentialCatalyst], List[PotentialCatalyst]]:
        """재무 데이터에서 촉매 탐지"""
        bullish = []
        bearish = []

        # 저평가 탐지
        per = financial_data.get("per", 0)
        pbr = financial_data.get("pbr", 0)

        if 0 < per < 10:
            bullish.append(PotentialCatalyst(
                catalyst_type=CatalystType.UNDERVALUATION,
                description=f"저PER 매력 (PER: {per:.1f})",
                impact=ImpactLevel.MODERATE,
                probability=Probability.MODERATE,
                timeframe=Timeframe.MEDIUM_TERM,
                evidence=[f"PER {per:.1f}배로 업종 평균 대비 저평가"],
                expected_move_pct=(10, 30)
            ))

        if 0 < pbr < 0.7:
            bullish.append(PotentialCatalyst(
                catalyst_type=CatalystType.UNDERVALUATION,
                description=f"저PBR 매력 (PBR: {pbr:.2f})",
                impact=ImpactLevel.MODERATE,
                probability=Probability.MODERATE,
                timeframe=Timeframe.LONG_TERM,
                evidence=[f"PBR {pbr:.2f}배로 자산가치 대비 저평가"],
                expected_move_pct=(15, 50)
            ))

        # 고평가 탐지
        if per > 50:
            bearish.append(PotentialCatalyst(
                catalyst_type=CatalystType.OVERVALUATION,
                description=f"고PER 부담 (PER: {per:.1f})",
                impact=ImpactLevel.MODERATE,
                probability=Probability.MODERATE,
                timeframe=Timeframe.MEDIUM_TERM,
                evidence=[f"PER {per:.1f}배로 밸류에이션 부담"],
                expected_move_pct=(-20, -40)
            ))

        # 부채 리스크 탐지
        debt_ratio = financial_data.get("debt_ratio", 0)
        if debt_ratio > 200:
            bearish.append(PotentialCatalyst(
                catalyst_type=CatalystType.DEBT_CONCERN,
                description=f"높은 부채비율 ({debt_ratio:.0f}%)",
                impact=ImpactLevel.HIGH,
                probability=Probability.MODERATE,
                timeframe=Timeframe.MEDIUM_TERM,
                evidence=[f"부채비율 {debt_ratio:.0f}%로 재무 건전성 우려"],
                risks=["금리 상승 시 이자 부담 증가", "신용등급 하락 가능성"]
            ))

        # 턴어라운드 가능성
        operating_margin = financial_data.get("operating_margin", 0)
        prev_margin = financial_data.get("prev_operating_margin", 0)

        if operating_margin > 0 and prev_margin < 0:
            bullish.append(PotentialCatalyst(
                catalyst_type=CatalystType.TURNAROUND,
                description="흑자 전환 가능성",
                impact=ImpactLevel.HIGH,
                probability=Probability.HIGH,
                timeframe=Timeframe.SHORT_TERM,
                evidence=[f"영업이익률 {prev_margin:.1f}% → {operating_margin:.1f}%"],
                expected_move_pct=(20, 50)
            ))

        return bullish, bearish

    def _detect_from_technicals(
        self,
        technical_data: Dict
    ) -> Tuple[List[PotentialCatalyst], List[PotentialCatalyst]]:
        """기술적 데이터에서 촉매 탐지"""
        bullish = []
        bearish = []

        rsi = technical_data.get("rsi", 50)
        short_interest = technical_data.get("short_interest", 0)
        ma_200_deviation = technical_data.get("ma_200_deviation", 0)

        # 과매도 반등 가능성
        if rsi < 30:
            bullish.append(PotentialCatalyst(
                catalyst_type=CatalystType.UNDERVALUATION,
                description=f"기술적 과매도 (RSI: {rsi:.0f})",
                impact=ImpactLevel.MODERATE,
                probability=Probability.HIGH,
                timeframe=Timeframe.SHORT_TERM,
                evidence=[f"RSI {rsi:.0f}으로 과매도 구간"],
                expected_move_pct=(5, 15)
            ))

        # 숏스퀴즈 가능성
        if short_interest > 15:
            bullish.append(PotentialCatalyst(
                catalyst_type=CatalystType.SHORT_SQUEEZE,
                description=f"높은 공매도 잔고 ({short_interest:.1f}%)",
                impact=ImpactLevel.HIGH,
                probability=Probability.LOW,
                timeframe=Timeframe.UNCERTAIN,
                evidence=[f"공매도 비율 {short_interest:.1f}%"],
                triggers=["긍정적 뉴스", "거래량 급증", "기관 매수"],
                expected_move_pct=(20, 100)
            ))

        # 200일 이평 이격 (과매수)
        if ma_200_deviation > 50:
            bearish.append(PotentialCatalyst(
                catalyst_type=CatalystType.OVERVALUATION,
                description=f"200일선 대비 과도한 이격 (+{ma_200_deviation:.0f}%)",
                impact=ImpactLevel.MODERATE,
                probability=Probability.HIGH,
                timeframe=Timeframe.SHORT_TERM,
                evidence=[f"200일 이평선 대비 {ma_200_deviation:.0f}% 상회"],
                expected_move_pct=(-10, -25)
            ))

        # 200일 이평 이격 (과매도)
        if ma_200_deviation < -30:
            bullish.append(PotentialCatalyst(
                catalyst_type=CatalystType.UNDERVALUATION,
                description=f"200일선 대비 과도한 이격 ({ma_200_deviation:.0f}%)",
                impact=ImpactLevel.MODERATE,
                probability=Probability.HIGH,
                timeframe=Timeframe.MEDIUM_TERM,
                evidence=[f"200일 이평선 대비 {abs(ma_200_deviation):.0f}% 하회"],
                expected_move_pct=(10, 30)
            ))

        return bullish, bearish

    def _estimate_impact(self, keyword_count: int) -> ImpactLevel:
        """키워드 수로 영향도 추정"""
        if keyword_count >= 4:
            return ImpactLevel.HIGH
        elif keyword_count >= 2:
            return ImpactLevel.MODERATE
        else:
            return ImpactLevel.LOW

    def _deduplicate_catalysts(
        self,
        catalysts: List[PotentialCatalyst]
    ) -> List[PotentialCatalyst]:
        """중복 촉매 제거"""
        seen = set()
        unique = []

        for catalyst in catalysts:
            key = catalyst.catalyst_type
            if key not in seen:
                seen.add(key)
                unique.append(catalyst)
            else:
                # 기존 촉매에 근거 추가
                for existing in unique:
                    if existing.catalyst_type == key:
                        existing.evidence.extend(catalyst.evidence)
                        break

        return unique


class PotentialAnalyzer:
    """잠재적 급등/급락 종합 분석기"""

    def __init__(self):
        self.catalyst_detector = PotentialCatalystDetector()

    def analyze(
        self,
        symbol: str,
        name: str,
        news: List[Dict] = None,
        financial_data: Dict = None,
        technical_data: Dict = None
    ) -> PotentialAnalysis:
        """잠재적 급등/급락 요인 종합 분석"""
        news = news or []

        # 촉매 탐지
        bullish_catalysts, bearish_catalysts = self.catalyst_detector.detect_catalysts(
            symbol, name, news, financial_data, technical_data
        )

        # 점수 계산
        bullish_score = self._calculate_score(bullish_catalysts)
        bearish_score = self._calculate_score(bearish_catalysts)

        # 종합 판단
        overall_bias = self._determine_bias(bullish_score, bearish_score)
        risk_reward = self._calculate_risk_reward(bullish_catalysts, bearish_catalysts)
        conviction = self._determine_conviction(bullish_catalysts, bearish_catalysts)

        # 핵심 투자 논리 생성
        key_thesis = self._generate_thesis(
            bullish_catalysts, bearish_catalysts, overall_bias
        )

        # 행동 권고
        action = self._generate_recommendation(
            overall_bias, conviction, risk_reward
        )

        # 관찰 포인트
        watch_points = self._generate_watch_points(
            bullish_catalysts, bearish_catalysts
        )

        return PotentialAnalysis(
            symbol=symbol,
            name=name,
            analysis_date=datetime.now(),
            bullish_catalysts=bullish_catalysts,
            bearish_catalysts=bearish_catalysts,
            bullish_score=bullish_score,
            bearish_score=bearish_score,
            overall_bias=overall_bias,
            risk_reward_ratio=risk_reward,
            conviction_level=conviction,
            key_thesis=key_thesis,
            action_recommendation=action,
            watch_points=watch_points
        )

    def _calculate_score(self, catalysts: List[PotentialCatalyst]) -> float:
        """촉매 점수 계산 (0-100)"""
        if not catalysts:
            return 0.0

        total_ev = sum(c.expected_value() for c in catalysts)
        max_possible = len(catalysts) * 5 * 0.9  # 최대 영향도 * 최대 확률

        score = (total_ev / max(max_possible, 1)) * 100
        return min(score, 100)

    def _determine_bias(self, bullish: float, bearish: float) -> str:
        """종합 방향성 판단"""
        diff = bullish - bearish

        if diff > 40:
            return "강한 상승"
        elif diff > 20:
            return "상승"
        elif diff > -20:
            return "중립"
        elif diff > -40:
            return "하락"
        else:
            return "강한 하락"

    def _calculate_risk_reward(
        self,
        bullish: List[PotentialCatalyst],
        bearish: List[PotentialCatalyst]
    ) -> float:
        """리스크/보상 비율 계산"""
        upside = 0
        downside = 0

        for c in bullish:
            if c.expected_move_pct:
                avg_move = (c.expected_move_pct[0] + c.expected_move_pct[1]) / 2
                upside += avg_move * c.probability.value

        for c in bearish:
            if c.expected_move_pct:
                avg_move = abs((c.expected_move_pct[0] + c.expected_move_pct[1]) / 2)
                downside += avg_move * c.probability.value

        if downside == 0:
            return 10.0 if upside > 0 else 1.0

        return round(upside / downside, 2)

    def _determine_conviction(
        self,
        bullish: List[PotentialCatalyst],
        bearish: List[PotentialCatalyst]
    ) -> str:
        """확신도 판단"""
        # 고확률 촉매 수 계산
        high_prob_bullish = sum(
            1 for c in bullish
            if c.probability in [Probability.HIGH, Probability.VERY_HIGH]
        )
        high_prob_bearish = sum(
            1 for c in bearish
            if c.probability in [Probability.HIGH, Probability.VERY_HIGH]
        )

        total_high_prob = high_prob_bullish + high_prob_bearish
        total_catalysts = len(bullish) + len(bearish)

        if total_catalysts == 0:
            return "낮음"

        ratio = total_high_prob / total_catalysts

        if ratio > 0.6 and total_catalysts >= 3:
            return "매우 높음"
        elif ratio > 0.4 and total_catalysts >= 2:
            return "높음"
        elif ratio > 0.2:
            return "보통"
        else:
            return "낮음"

    def _generate_thesis(
        self,
        bullish: List[PotentialCatalyst],
        bearish: List[PotentialCatalyst],
        bias: str
    ) -> str:
        """핵심 투자 논리 생성"""
        parts = []

        if bullish:
            top_bullish = bullish[0]
            parts.append(f"상승 요인: {top_bullish.catalyst_type.value}")

        if bearish:
            top_bearish = bearish[0]
            parts.append(f"하락 요인: {top_bearish.catalyst_type.value}")

        if not parts:
            return "분석 가능한 촉매 없음"

        direction = "상승 우위" if "상승" in bias else "하락 우위" if "하락" in bias else "방향성 중립"

        return f"{' / '.join(parts)} → {direction}"

    def _generate_recommendation(
        self,
        bias: str,
        conviction: str,
        risk_reward: float
    ) -> str:
        """행동 권고 생성"""
        if bias == "강한 상승" and conviction in ["높음", "매우 높음"]:
            return "적극 매수 고려"
        elif bias == "상승" and conviction in ["높음", "매우 높음"]:
            return "매수 고려"
        elif bias == "상승":
            return "관심 종목으로 모니터링"
        elif bias == "중립":
            return "추가 촉매 대기"
        elif bias == "하락":
            return "리스크 관리 필요"
        elif bias == "강한 하락" and conviction in ["높음", "매우 높음"]:
            return "회피 또는 매도 고려"
        else:
            return "신중한 접근 필요"

    def _generate_watch_points(
        self,
        bullish: List[PotentialCatalyst],
        bearish: List[PotentialCatalyst]
    ) -> List[str]:
        """관찰 포인트 생성"""
        points = []

        for c in bullish[:2]:
            if c.triggers:
                points.append(f"[상승 트리거] {', '.join(c.triggers[:2])}")
            if c.timeframe != Timeframe.UNCERTAIN:
                points.append(f"[시점] {c.catalyst_type.value}: {c.timeframe.description}")

        for c in bearish[:2]:
            if c.risks:
                points.append(f"[하락 리스크] {', '.join(c.risks[:2])}")

        return points[:5]


class PotentialScreener:
    """잠재적 급등/급락 종목 스크리너"""

    def __init__(self):
        self.analyzer = PotentialAnalyzer()

    def screen_for_potential_rallies(
        self,
        stocks: List[Dict],
        min_score: float = 50,
        top_n: int = 10
    ) -> List[PotentialAnalysis]:
        """잠재적 급등 종목 스크리닝"""
        results = []

        for stock in stocks:
            analysis = self.analyzer.analyze(
                symbol=stock.get("symbol", ""),
                name=stock.get("name", ""),
                news=stock.get("news", []),
                financial_data=stock.get("financial_data"),
                technical_data=stock.get("technical_data")
            )

            if analysis.bullish_score >= min_score:
                results.append(analysis)

        # 상승 점수 기준 정렬
        results.sort(key=lambda x: x.bullish_score, reverse=True)
        return results[:top_n]

    def screen_for_potential_declines(
        self,
        stocks: List[Dict],
        min_score: float = 50,
        top_n: int = 10
    ) -> List[PotentialAnalysis]:
        """잠재적 급락 종목 스크리닝"""
        results = []

        for stock in stocks:
            analysis = self.analyzer.analyze(
                symbol=stock.get("symbol", ""),
                name=stock.get("name", ""),
                news=stock.get("news", []),
                financial_data=stock.get("financial_data"),
                technical_data=stock.get("technical_data")
            )

            if analysis.bearish_score >= min_score:
                results.append(analysis)

        # 하락 점수 기준 정렬
        results.sort(key=lambda x: x.bearish_score, reverse=True)
        return results[:top_n]

    def screen_asymmetric_opportunities(
        self,
        stocks: List[Dict],
        min_risk_reward: float = 2.0,
        top_n: int = 10
    ) -> List[PotentialAnalysis]:
        """비대칭 기회 스크리닝 (높은 리스크/보상 비율)"""
        results = []

        for stock in stocks:
            analysis = self.analyzer.analyze(
                symbol=stock.get("symbol", ""),
                name=stock.get("name", ""),
                news=stock.get("news", []),
                financial_data=stock.get("financial_data"),
                technical_data=stock.get("technical_data")
            )

            if analysis.risk_reward_ratio >= min_risk_reward:
                results.append(analysis)

        # 리스크/보상 비율 기준 정렬
        results.sort(key=lambda x: x.risk_reward_ratio, reverse=True)
        return results[:top_n]
