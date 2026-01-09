"""
Decline Analyzer - 하락 종목/섹터 논리 평가 시스템

[기능]
1. 하락 종목/섹터 감지 (DeclineDetector)
2. 하락 논리(Thesis) 추출 (DeclineThesisExtractor)
3. 과매도 여부 평가 (OversoldEvaluator)
4. 반등 가능성 평가 (RecoveryAnalyzer)

[평가 기준]
- 하락 정당성: 실적 악화, 악재 등 근거 있는 하락인지
- 과매도 수준: RSI, 이격도 등 기술적 과매도
- 반등 가능성: 수급 전환, 밸류에이션 매력도
- 리스크: 추가 하락 가능성
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
import pandas as pd

logger = logging.getLogger(__name__)


class DeclineType(Enum):
    """하락 논리 유형"""
    EARNINGS_MISS = "실적 부진"
    GUIDANCE_CUT = "가이던스 하향"
    SECTOR_WEAKNESS = "섹터 약세"
    MACRO_RISK = "거시경제 악재"
    COMPANY_SPECIFIC = "기업 고유 이슈"
    SUPPLY_PRESSURE = "수급 악화"
    VALUATION_CONCERN = "밸류에이션 부담"
    TECHNICAL_BREAKDOWN = "기술적 이탈"
    THEME_FADE = "테마 소멸"
    REGULATORY_RISK = "규제 리스크"
    PROFIT_TAKING = "차익 실현"
    MARKET_SENTIMENT = "시장 심리 악화"
    UNKNOWN = "불명확"


class OversoldLevel(Enum):
    """과매도 수준"""
    EXTREME = "극심한 과매도"
    SEVERE = "심한 과매도"
    MODERATE = "보통 과매도"
    MILD = "약한 과매도"
    NEUTRAL = "중립"
    OVERBOUGHT = "과매수 영역"


class RecoveryPotential(Enum):
    """반등 가능성"""
    VERY_HIGH = "매우 높음"
    HIGH = "높음"
    MEDIUM = "보통"
    LOW = "낮음"
    VERY_LOW = "매우 낮음"
    AVOID = "회피 권장"


@dataclass
class DeclineInfo:
    """하락 정보"""
    symbol: str
    name: str
    sector: str
    current_price: float
    change_1d: float  # 1일 변동률
    change_5d: float  # 5일 변동률
    change_1m: float  # 1개월 변동률
    change_from_high: float  # 고점 대비 하락률
    volume_ratio: float  # 평균 거래량 대비
    foreign_net_sell: float  # 외국인 순매도
    inst_net_sell: float  # 기관 순매도
    rsi: float  # RSI 지표
    detected_at: datetime = field(default_factory=datetime.now)
    # 펀더멘털 데이터 (Snowflake 통합용)
    per: Optional[float] = None
    pbr: Optional[float] = None
    roe: Optional[float] = None
    dividend_yield: Optional[float] = None
    debt_ratio: Optional[float] = None
    revenue_growth: Optional[float] = None


@dataclass
class DeclineClaim:
    """하락 논리 주장"""
    claim_type: DeclineType
    description: str
    source: str
    severity: str  # 심각도: high, medium, low
    source_date: Optional[datetime] = None
    evidence: List[str] = field(default_factory=list)
    is_temporary: bool = False  # 일시적 요인 여부


@dataclass
class DeclineValidation:
    """하락 논리 검증 결과"""
    claim: DeclineClaim
    is_justified: bool  # 하락이 정당한지
    confidence: float
    validation_details: str
    reversal_potential: float  # 반전 가능성 0~1
    additional_downside: float  # 추가 하락 여지 %


@dataclass
class OversoldAnalysis:
    """과매도 분석 결과"""
    level: OversoldLevel
    rsi_score: float  # RSI 기반 점수
    price_deviation: float  # 이동평균 이격도
    volume_capitulation: bool  # 거래량 급증 (투매)
    support_level: float  # 지지선 가격
    technical_score: float  # 종합 기술적 점수


@dataclass
class RecoveryAnalysis:
    """반등 분석 결과"""
    potential: RecoveryPotential
    score: float  # 0~100
    catalysts: List[str]  # 반등 촉매
    risks: List[str]  # 리스크 요인
    target_price: Optional[float]  # 목표가
    time_horizon: str  # 예상 기간


@dataclass
class DeclineReport:
    """하락 분석 리포트"""
    decline_info: DeclineInfo
    decline_claims: List[DeclineClaim]
    validations: List[DeclineValidation]
    oversold: OversoldAnalysis
    recovery: RecoveryAnalysis
    summary: str
    recommendation: str
    warnings: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)


class DeclineDetector:
    """하락 종목/섹터 감지기"""

    def __init__(self):
        self.min_decline_1d = -3.0  # 1일 최소 하락률
        self.min_decline_5d = -10.0  # 5일 최소 하락률
        self.min_volume_ratio = 1.5  # 최소 거래량 비율

    def detect_declining_stocks(
        self,
        market: str = 'ALL',
        top_n: int = 20,
        period: str = '5d'
    ) -> List[DeclineInfo]:
        """하락 종목 감지"""
        declines = []

        try:
            from korea.krx_data import KRXDataCollector
            krx = KRXDataCollector()

            stock_list = krx.get_stock_list(market)

            for _, row in stock_list.head(100).iterrows():
                code = row['code']
                name = row['name']

                try:
                    price_data = krx.get_stock_price(code)
                    if price_data.empty or len(price_data) < 5:
                        continue

                    current_price = float(price_data['Close'].iloc[-1])

                    # 변동률 계산
                    if len(price_data) >= 2:
                        prev_price = float(price_data['Close'].iloc[-2])
                        change_1d = ((current_price - prev_price) / prev_price) * 100
                    else:
                        change_1d = 0

                    if len(price_data) >= 5:
                        price_5d_ago = float(price_data['Close'].iloc[-5])
                        change_5d = ((current_price - price_5d_ago) / price_5d_ago) * 100
                    else:
                        change_5d = 0

                    if len(price_data) >= 20:
                        price_1m_ago = float(price_data['Close'].iloc[-20])
                        change_1m = ((current_price - price_1m_ago) / price_1m_ago) * 100
                    else:
                        change_1m = 0

                    # 고점 대비 하락률
                    high_52w = float(price_data['High'].max())
                    change_from_high = ((current_price - high_52w) / high_52w) * 100

                    # 거래량 비율
                    if len(price_data) >= 20:
                        avg_volume = float(price_data['Volume'].iloc[-20:].mean())
                        current_volume = float(price_data['Volume'].iloc[-1])
                        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
                    else:
                        volume_ratio = 1.0

                    # RSI 계산
                    rsi = self._calculate_rsi(price_data['Close'])

                    # 필터링 조건
                    if period == '1d' and change_1d > self.min_decline_1d:
                        continue
                    elif period == '5d' and change_5d > self.min_decline_5d:
                        continue

                    # 수급 데이터 조회
                    try:
                        investor_data = krx.get_investor_trading_by_stock(code, 5)
                        # 순매도 = -순매수
                        foreign_net_sell = -investor_data.get('foreign_net', 0)
                        inst_net_sell = -investor_data.get('inst_net', 0)
                    except Exception:
                        foreign_net_sell = 0
                        inst_net_sell = 0

                    # 펀더멘털 데이터 조회
                    fundamentals = self._fetch_fundamentals(krx, code)

                    decline = DeclineInfo(
                        symbol=code,
                        name=name,
                        sector=row.get('sector', '기타'),
                        current_price=current_price,
                        change_1d=change_1d,
                        change_5d=change_5d,
                        change_1m=change_1m,
                        change_from_high=change_from_high,
                        volume_ratio=volume_ratio,
                        foreign_net_sell=foreign_net_sell if foreign_net_sell > 0 else 0,
                        inst_net_sell=inst_net_sell if inst_net_sell > 0 else 0,
                        rsi=rsi,
                        per=fundamentals.get('per'),
                        pbr=fundamentals.get('pbr'),
                        roe=fundamentals.get('roe'),
                        dividend_yield=fundamentals.get('dividend_yield'),
                        debt_ratio=fundamentals.get('debt_ratio'),
                        revenue_growth=fundamentals.get('revenue_growth'),
                    )
                    declines.append(decline)

                except Exception as e:
                    logger.debug(f"종목 분석 오류 ({code}): {e}")
                    continue

        except Exception as e:
            logger.error(f"하락 종목 감지 오류: {e}")

        # 하락률 기준 정렬 (가장 많이 하락한 순)
        if period == '1d':
            declines.sort(key=lambda x: x.change_1d)
        else:
            declines.sort(key=lambda x: x.change_5d)

        return declines[:top_n]

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """RSI 계산"""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

            # ZeroDivisionError 방지
            loss_adj = loss.replace(0, 1e-10)
            rs = gain / loss_adj
            rsi = 100 - (100 / (1 + rs))

            return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0
        except Exception:
            return 50.0

    def _fetch_fundamentals(self, krx, code: str) -> Dict:
        """펀더멘털 데이터 조회"""
        try:
            # KRX에서 펀더멘털 데이터 조회 시도
            if hasattr(krx, 'get_stock_fundamentals'):
                fund_data = krx.get_stock_fundamentals(code)
                if fund_data:
                    return {
                        'per': fund_data.get('PER'),
                        'pbr': fund_data.get('PBR'),
                        'roe': fund_data.get('ROE'),
                        'dividend_yield': fund_data.get('DIV'),
                        'debt_ratio': fund_data.get('debt_ratio', 100),
                        'revenue_growth': fund_data.get('revenue_growth', 0),
                    }

            # 폴백: 기본값 반환
            return {
                'per': None,
                'pbr': None,
                'roe': None,
                'dividend_yield': None,
                'debt_ratio': 100,
                'revenue_growth': 0,
            }
        except Exception as e:
            logger.debug(f"펀더멘털 조회 오류 ({code}): {e}")
            return {}

    def detect_sector_declines(self, top_n: int = 5) -> List[Dict]:
        """섹터별 하락 감지"""
        sectors = []

        sector_etfs = {
            '반도체': '091160',
            '2차전지': '305720',
            '바이오': '244580',
            '은행': '091170',
            '자동차': '091180',
            '철강': '139260',
            '건설': '139220',
            '화학': '139250',
            '미디어': '228790',  # TIGER 미디어컨텐츠
            '에너지': '117460',
        }

        try:
            from korea.krx_data import KRXDataCollector
            krx = KRXDataCollector()

            for sector_name, etf_code in sector_etfs.items():
                try:
                    price_data = krx.get_stock_price(etf_code)
                    if price_data.empty:
                        continue

                    current_price = float(price_data['Close'].iloc[-1])

                    if len(price_data) >= 5:
                        price_5d_ago = float(price_data['Close'].iloc[-5])
                        change_5d = ((current_price - price_5d_ago) / price_5d_ago) * 100
                    else:
                        change_5d = 0

                    sectors.append({
                        'sector': sector_name,
                        'etf_code': etf_code,
                        'change_5d': change_5d,
                        'current_price': current_price,
                    })

                except Exception:
                    continue

        except Exception as e:
            logger.error(f"섹터 분석 오류: {e}")

        # 하락률 기준 정렬
        sectors.sort(key=lambda x: x['change_5d'])
        return sectors[:top_n]


class DeclineThesisExtractor:
    """하락 논리 추출기"""

    def __init__(self):
        self.decline_keywords = {
            DeclineType.EARNINGS_MISS: ['실적 부진', '적자', '이익 감소', '매출 감소', '어닝쇼크'],
            DeclineType.GUIDANCE_CUT: ['가이던스 하향', '전망 하향', '목표 하향', '실적 경고'],
            DeclineType.SECTOR_WEAKNESS: ['섹터 약세', '업종 하락', '동반 하락'],
            DeclineType.MACRO_RISK: ['금리 인상', '인플레이션', '경기 침체', '불황'],
            DeclineType.COMPANY_SPECIFIC: ['소송', '리콜', '횡령', '분식', '사고'],
            DeclineType.SUPPLY_PRESSURE: ['외국인 매도', '기관 매도', '대주주 매도', '블록딜'],
            DeclineType.VALUATION_CONCERN: ['고평가', '버블', '밸류에이션 부담'],
            DeclineType.TECHNICAL_BREAKDOWN: ['지지선 이탈', '하락 추세', '데드크로스'],
            DeclineType.THEME_FADE: ['테마 소멸', '관심 감소', '모멘텀 약화'],
            DeclineType.REGULATORY_RISK: ['규제', '과징금', '제재', '법적'],
            DeclineType.PROFIT_TAKING: ['차익 실현', '이익 실현', '고점 매도'],
            DeclineType.MARKET_SENTIMENT: ['공포', '패닉', '투매', '악재'],
        }

    def extract_thesis(
        self,
        decline_info: DeclineInfo,
        news_articles: List[Dict] = None,
    ) -> List[DeclineClaim]:
        """하락 논리 추출"""
        claims = []

        # 1. 수급 기반 하락
        if decline_info.foreign_net_sell > 0:
            claims.append(DeclineClaim(
                claim_type=DeclineType.SUPPLY_PRESSURE,
                description=f"외국인 순매도 {decline_info.foreign_net_sell:,.0f}원",
                source="거래소 데이터",
                severity="high" if decline_info.foreign_net_sell > 10_000_000_000 else "medium",
                evidence=[f"외국인 {decline_info.foreign_net_sell:,.0f}원 순매도"],
                is_temporary=True,
            ))

        # 2. 거래량 급증 (투매)
        if decline_info.volume_ratio > 3.0 and decline_info.change_1d < -5:
            claims.append(DeclineClaim(
                claim_type=DeclineType.MARKET_SENTIMENT,
                description=f"거래량 {decline_info.volume_ratio:.1f}배 급증 (투매 가능성)",
                source="거래 데이터",
                severity="high",
                evidence=[f"평균 대비 거래량 {decline_info.volume_ratio:.1f}배, 급락"],
                is_temporary=True,
            ))

        # 3. 기술적 이탈 (RSI 과매도)
        if decline_info.rsi < 30:
            claims.append(DeclineClaim(
                claim_type=DeclineType.TECHNICAL_BREAKDOWN,
                description=f"RSI {decline_info.rsi:.1f} - 과매도 영역",
                source="기술적 분석",
                severity="medium",
                evidence=[f"RSI {decline_info.rsi:.1f}"],
                is_temporary=True,
            ))

        # 4. 고점 대비 대폭 하락
        if decline_info.change_from_high < -30:
            severity = "high" if decline_info.change_from_high < -50 else "medium"
            claims.append(DeclineClaim(
                claim_type=DeclineType.TECHNICAL_BREAKDOWN,
                description=f"고점 대비 {decline_info.change_from_high:.1f}% 하락",
                source="가격 데이터",
                severity=severity,
                evidence=[f"52주 고점 대비 {decline_info.change_from_high:.1f}% 하락"],
            ))

        # 5. 뉴스 기반
        if news_articles:
            news_claims = self._extract_from_news(news_articles)
            claims.extend(news_claims)

        # 6. 논리가 없으면 불명확
        if not claims:
            claims.append(DeclineClaim(
                claim_type=DeclineType.UNKNOWN,
                description="명확한 하락 원인 파악 어려움",
                source="분석 결과",
                severity="medium",
            ))

        return claims

    def _extract_from_news(self, articles: List[Dict]) -> List[DeclineClaim]:
        """뉴스에서 하락 논리 추출"""
        claims = []

        for article in articles:
            title = article.get('title', '')
            content = article.get('content', '')
            source = article.get('source', '뉴스')
            text = f"{title} {content}"

            for decline_type, keywords in self.decline_keywords.items():
                for keyword in keywords:
                    if keyword in text:
                        claims.append(DeclineClaim(
                            claim_type=decline_type,
                            description=title[:100],
                            source=source,
                            severity="medium",
                            evidence=[f"뉴스: {title[:50]}..."],
                        ))
                        break

        return claims


class OversoldEvaluator:
    """과매도 평가기"""

    def evaluate(self, decline_info: DeclineInfo) -> OversoldAnalysis:
        """과매도 수준 평가"""

        # RSI 점수 (낮을수록 과매도)
        rsi = decline_info.rsi
        if rsi < 20:
            rsi_score = 100
        elif rsi < 30:
            rsi_score = 80
        elif rsi < 40:
            rsi_score = 60
        elif rsi < 50:
            rsi_score = 40
        else:
            rsi_score = 20

        # 이격도 (고점 대비 하락률 기반)
        price_deviation = abs(decline_info.change_from_high)

        # 거래량 급증 (투매 여부)
        volume_capitulation = (
            decline_info.volume_ratio > 3.0 and
            decline_info.change_1d < -5
        )

        # 종합 점수
        technical_score = (
            rsi_score * 0.4 +
            min(price_deviation, 50) * 2 * 0.3 +  # 최대 100점
            (30 if volume_capitulation else 0) * 0.3
        )

        # 과매도 레벨 결정
        if technical_score >= 80:
            level = OversoldLevel.EXTREME
        elif technical_score >= 65:
            level = OversoldLevel.SEVERE
        elif technical_score >= 50:
            level = OversoldLevel.MODERATE
        elif technical_score >= 35:
            level = OversoldLevel.MILD
        elif technical_score >= 20:
            level = OversoldLevel.NEUTRAL
        else:
            level = OversoldLevel.OVERBOUGHT

        # 지지선 추정 (단순화)
        support_level = decline_info.current_price * 0.95

        return OversoldAnalysis(
            level=level,
            rsi_score=rsi_score,
            price_deviation=price_deviation,
            volume_capitulation=volume_capitulation,
            support_level=support_level,
            technical_score=technical_score,
        )


class RecoveryAnalyzer:
    """반등 가능성 분석기"""

    def analyze(
        self,
        decline_info: DeclineInfo,
        validations: List[DeclineValidation],
        oversold: OversoldAnalysis,
    ) -> RecoveryAnalysis:
        """반등 가능성 분석"""

        catalysts = []
        risks = []
        score = 50  # 기본점수

        # 1. 과매도 수준에 따른 점수
        if oversold.level in [OversoldLevel.EXTREME, OversoldLevel.SEVERE]:
            score += 20
            catalysts.append("기술적 과매도 - 반등 가능성")
        elif oversold.level == OversoldLevel.MODERATE:
            score += 10
            catalysts.append("보통 수준 과매도")

        # 2. 하락 논리 검증 결과
        temporary_count = sum(1 for v in validations if v.claim.is_temporary)
        permanent_count = len(validations) - temporary_count

        if temporary_count > permanent_count:
            score += 15
            catalysts.append("일시적 요인 위주 - 회복 가능")
        else:
            score -= 10
            risks.append("구조적 악재 - 회복 지연 우려")

        # 3. RSI 과매도
        if decline_info.rsi < 25:
            score += 15
            catalysts.append(f"극단적 RSI ({decline_info.rsi:.0f}) - 기술적 반등")
        elif decline_info.rsi < 35:
            score += 10

        # 4. 거래량 급증 (투매 후 반등)
        if oversold.volume_capitulation:
            score += 10
            catalysts.append("거래량 급증 (투매) - 단기 반등 기대")

        # 5. 리스크 요인
        for v in validations:
            if v.additional_downside > 10:
                risks.append(f"추가 하락 여지 {v.additional_downside:.0f}%")
                score -= 10

        if decline_info.change_from_high < -50:
            risks.append("고점 대비 50% 이상 하락 - 장기 회복 필요")

        # 점수 정규화
        score = max(0, min(100, score))

        # 반등 가능성 레벨
        if score >= 75:
            potential = RecoveryPotential.VERY_HIGH
        elif score >= 60:
            potential = RecoveryPotential.HIGH
        elif score >= 45:
            potential = RecoveryPotential.MEDIUM
        elif score >= 30:
            potential = RecoveryPotential.LOW
        elif score >= 15:
            potential = RecoveryPotential.VERY_LOW
        else:
            potential = RecoveryPotential.AVOID

        # 목표가 추정 (단순화)
        if potential in [RecoveryPotential.VERY_HIGH, RecoveryPotential.HIGH]:
            target_price = decline_info.current_price * 1.15  # 15% 반등
            time_horizon = "1-2주"
        elif potential == RecoveryPotential.MEDIUM:
            target_price = decline_info.current_price * 1.10  # 10% 반등
            time_horizon = "2-4주"
        else:
            target_price = None
            time_horizon = "불확실"

        return RecoveryAnalysis(
            potential=potential,
            score=score,
            catalysts=catalysts,
            risks=risks,
            target_price=target_price,
            time_horizon=time_horizon,
        )


class DeclineAnalyzer:
    """하락 분석기 (통합 인터페이스)"""

    def __init__(self):
        self.detector = DeclineDetector()
        self.extractor = DeclineThesisExtractor()
        self.oversold_evaluator = OversoldEvaluator()
        self.recovery_analyzer = RecoveryAnalyzer()

    def analyze_decline(
        self,
        symbol: str,
        name: str = None,
        news: List[Dict] = None,
    ) -> Optional[DeclineReport]:
        """단일 종목 하락 분석"""

        try:
            from korea.krx_data import KRXDataCollector
            krx = KRXDataCollector()

            price_data = krx.get_stock_price(symbol)
            if price_data.empty:
                return None

            current_price = float(price_data['Close'].iloc[-1])

            # 변동률 계산
            change_1d = change_5d = change_1m = 0
            volume_ratio = 1.0
            rsi = 50.0

            if len(price_data) >= 2:
                prev_price = float(price_data['Close'].iloc[-2])
                change_1d = ((current_price - prev_price) / prev_price) * 100

            if len(price_data) >= 5:
                price_5d_ago = float(price_data['Close'].iloc[-5])
                change_5d = ((current_price - price_5d_ago) / price_5d_ago) * 100

            if len(price_data) >= 20:
                price_1m_ago = float(price_data['Close'].iloc[-20])
                change_1m = ((current_price - price_1m_ago) / price_1m_ago) * 100
                avg_volume = float(price_data['Volume'].iloc[-20:].mean())
                current_volume = float(price_data['Volume'].iloc[-1])
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0

            # RSI
            rsi = self.detector._calculate_rsi(price_data['Close'])

            # 고점 대비
            high_52w = float(price_data['High'].max())
            change_from_high = ((current_price - high_52w) / high_52w) * 100

            decline_info = DeclineInfo(
                symbol=symbol,
                name=name or symbol,
                sector='',
                current_price=current_price,
                change_1d=change_1d,
                change_5d=change_5d,
                change_1m=change_1m,
                change_from_high=change_from_high,
                volume_ratio=volume_ratio,
                foreign_net_sell=0,
                inst_net_sell=0,
                rsi=rsi,
            )

            # 하락 논리 추출
            claims = self.extractor.extract_thesis(decline_info, news)

            # 논리 검증
            validations = []
            for claim in claims:
                validation = self._validate_claim(claim, decline_info)
                validations.append(validation)

            # 과매도 평가
            oversold = self.oversold_evaluator.evaluate(decline_info)

            # 반등 가능성 분석
            recovery = self.recovery_analyzer.analyze(decline_info, validations, oversold)

            # 요약 생성
            summary = self._generate_summary(decline_info, validations, oversold, recovery)
            recommendation = self._generate_recommendation(oversold, recovery)
            warnings = self._collect_warnings(validations, oversold, recovery)

            return DeclineReport(
                decline_info=decline_info,
                decline_claims=claims,
                validations=validations,
                oversold=oversold,
                recovery=recovery,
                summary=summary,
                recommendation=recommendation,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"하락 분석 오류 ({symbol}): {e}")
            return None

    def _validate_claim(self, claim: DeclineClaim, decline_info: DeclineInfo) -> DeclineValidation:
        """하락 논리 검증"""

        is_justified = True
        confidence = 0.5
        reversal_potential = 0.5
        additional_downside = 10.0

        if claim.claim_type == DeclineType.SUPPLY_PRESSURE:
            is_justified = True
            confidence = 0.8
            reversal_potential = 0.6  # 수급은 전환 가능
            additional_downside = 5.0

        elif claim.claim_type == DeclineType.EARNINGS_MISS:
            is_justified = True
            confidence = 0.9
            reversal_potential = 0.3  # 실적은 바로 회복 어려움
            additional_downside = 15.0

        elif claim.claim_type == DeclineType.TECHNICAL_BREAKDOWN:
            is_justified = True
            confidence = 0.6
            reversal_potential = 0.7 if decline_info.rsi < 30 else 0.4
            additional_downside = 10.0

        elif claim.claim_type == DeclineType.MARKET_SENTIMENT:
            is_justified = True
            confidence = 0.7
            reversal_potential = 0.7  # 심리는 빠르게 변화
            additional_downside = 5.0

        elif claim.claim_type == DeclineType.UNKNOWN:
            is_justified = False
            confidence = 0.3
            reversal_potential = 0.5
            additional_downside = 15.0

        return DeclineValidation(
            claim=claim,
            is_justified=is_justified,
            confidence=confidence,
            validation_details=f"{claim.claim_type.value} 확인",
            reversal_potential=reversal_potential,
            additional_downside=additional_downside,
        )

    def analyze_top_declines(self, top_n: int = 10) -> List[DeclineReport]:
        """상위 하락 종목 분석"""
        reports = []
        declines = self.detector.detect_declining_stocks(top_n=top_n)

        for decline in declines:
            report = self.analyze_decline(decline.symbol, decline.name)
            if report:
                reports.append(report)

        return reports

    def _generate_summary(
        self,
        decline_info: DeclineInfo,
        validations: List[DeclineValidation],
        oversold: OversoldAnalysis,
        recovery: RecoveryAnalysis,
    ) -> str:
        """분석 요약 생성"""
        lines = []
        lines.append(f"📉 {decline_info.name} ({decline_info.symbol})")
        lines.append(f"현재가: {decline_info.current_price:,.0f}원")
        lines.append(f"변동률: 1일 {decline_info.change_1d:+.1f}% / 5일 {decline_info.change_5d:+.1f}%")
        lines.append(f"고점대비: {decline_info.change_from_high:+.1f}%")
        lines.append("")
        lines.append(f"📊 과매도 수준: {oversold.level.value} (RSI: {decline_info.rsi:.0f})")
        lines.append(f"🔄 반등 가능성: {recovery.potential.value} ({recovery.score:.0f}점)")
        lines.append("")
        lines.append("🔍 하락 원인:")
        for v in validations:
            icon = "⚠️" if v.claim.severity == "high" else "ℹ️"
            lines.append(f"  {icon} {v.claim.claim_type.value}: {v.claim.description}")

        return "\n".join(lines)

    def _generate_recommendation(
        self,
        oversold: OversoldAnalysis,
        recovery: RecoveryAnalysis,
    ) -> str:
        """투자 의견 생성"""

        if oversold.level == OversoldLevel.EXTREME and recovery.potential in [
            RecoveryPotential.VERY_HIGH, RecoveryPotential.HIGH
        ]:
            return "🟢 극심한 과매도 + 반등 가능성 높음. 분할 매수 고려"
        elif oversold.level in [OversoldLevel.EXTREME, OversoldLevel.SEVERE]:
            return "🟡 과매도 영역. 추가 확인 후 신중한 접근"
        elif recovery.potential in [RecoveryPotential.LOW, RecoveryPotential.VERY_LOW]:
            return "🟠 반등 모멘텀 부족. 관망 권장"
        elif recovery.potential == RecoveryPotential.AVOID:
            return "🔴 구조적 악재. 접근 비권장"
        else:
            return "🟡 중립. 추가 분석 필요"

    def _collect_warnings(
        self,
        validations: List[DeclineValidation],
        oversold: OversoldAnalysis,
        recovery: RecoveryAnalysis,
    ) -> List[str]:
        """경고 수집"""
        warnings = []

        # 리스크 요인
        warnings.extend(recovery.risks)

        # 추가 하락 경고
        for v in validations:
            if v.additional_downside > 15:
                warnings.append(f"⚠️ 추가 하락 가능성 {v.additional_downside:.0f}%")

        # 구조적 악재
        structural_types = {
            DeclineType.EARNINGS_MISS,
            DeclineType.REGULATORY_RISK,
            DeclineType.COMPANY_SPECIFIC
        }
        for v in validations:
            if v.claim.claim_type in structural_types:
                warnings.append(f"⚠️ 구조적 악재: {v.claim.claim_type.value}")

        return list(set(warnings))


# 편의 함수
def analyze_stock_decline(symbol: str, name: str = None) -> Optional[DeclineReport]:
    """단일 종목 하락 분석 (간편 함수)"""
    analyzer = DeclineAnalyzer()
    return analyzer.analyze_decline(symbol, name)


def get_top_declines(top_n: int = 10) -> List[DeclineReport]:
    """상위 하락 종목 분석 (간편 함수)"""
    analyzer = DeclineAnalyzer()
    return analyzer.analyze_top_declines(top_n)
