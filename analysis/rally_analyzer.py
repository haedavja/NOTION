"""
Rally Analyzer - 상승 종목/섹터 논리 평가 시스템

[기능]
1. 상승 종목/섹터 감지 (RallyDetector)
2. 상승 논리(Thesis) 추출 (ThesisExtractor)
3. 논리 검증 및 신뢰도 평가 (ThesisValidator)
4. 종합 리포트 생성 (RallyReport)

[평가 기준]
- 펀더멘털 근거: 실적, 매출, 이익 등 실제 데이터
- 수급 근거: 외국인/기관 매수, 거래량 등
- 기술적 근거: 차트 패턴, 추세 등
- 테마/모멘텀: 뉴스, 정책, 시장 트렌드
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
import pandas as pd

logger = logging.getLogger(__name__)


class ThesisType(Enum):
    """상승 논리 유형"""
    EARNINGS = "실적 개선"
    GUIDANCE = "가이던스 상향"
    NEW_PRODUCT = "신제품/신사업"
    POLICY = "정책 수혜"
    SECTOR_ROTATION = "섹터 로테이션"
    SUPPLY_DEMAND = "수급 개선"
    VALUATION = "저평가 해소"
    TECHNICAL = "기술적 반등"
    THEME = "테마/모멘텀"
    M_AND_A = "M&A/구조조정"
    MACRO = "거시경제 요인"
    UNKNOWN = "불명확"


class CredibilityLevel(Enum):
    """신뢰도 수준"""
    VERY_HIGH = "매우 높음"
    HIGH = "높음"
    MEDIUM = "보통"
    LOW = "낮음"
    VERY_LOW = "매우 낮음"
    SPECULATIVE = "투기적"


@dataclass
class RallyInfo:
    """상승 정보"""
    symbol: str
    name: str
    sector: str
    current_price: float
    change_1d: float  # 1일 변동률
    change_5d: float  # 5일 변동률
    change_1m: float  # 1개월 변동률
    volume_ratio: float  # 평균 거래량 대비
    foreign_net_buy: float  # 외국인 순매수
    inst_net_buy: float  # 기관 순매수
    market_cap: float
    detected_at: datetime = field(default_factory=datetime.now)


@dataclass
class ThesisClaim:
    """상승 논리 주장"""
    claim_type: ThesisType
    description: str
    source: str  # 출처 (뉴스, 리포트, 공시 등)
    source_date: Optional[datetime] = None
    evidence: List[str] = field(default_factory=list)
    counter_evidence: List[str] = field(default_factory=list)


@dataclass
class ThesisValidation:
    """논리 검증 결과"""
    claim: ThesisClaim
    is_valid: bool
    confidence: float  # 0.0 ~ 1.0
    validation_details: str
    data_support: Dict = field(default_factory=dict)
    risks: List[str] = field(default_factory=list)


@dataclass
class CredibilityScore:
    """신뢰도 점수"""
    overall: float  # 0 ~ 100
    level: CredibilityLevel
    fundamental_score: float  # 펀더멘털 근거 점수
    supply_demand_score: float  # 수급 근거 점수
    technical_score: float  # 기술적 근거 점수
    narrative_score: float  # 스토리/테마 점수
    risk_score: float  # 리스크 점수 (낮을수록 좋음)
    breakdown: Dict[str, float] = field(default_factory=dict)


@dataclass
class RallyReport:
    """상승 분석 리포트"""
    rally_info: RallyInfo
    thesis_claims: List[ThesisClaim]
    validations: List[ThesisValidation]
    credibility: CredibilityScore
    summary: str
    recommendation: str
    warnings: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)


class RallyDetector:
    """상승 종목/섹터 감지기"""

    def __init__(self):
        self.min_change_1d = 3.0  # 1일 최소 상승률
        self.min_change_5d = 10.0  # 5일 최소 상승률
        self.min_volume_ratio = 2.0  # 최소 거래량 비율

    def detect_rallying_stocks(
        self,
        market: str = 'ALL',
        top_n: int = 20,
        period: str = '5d'
    ) -> List[RallyInfo]:
        """상승 종목 감지"""
        rallies = []

        try:
            # pykrx 또는 yfinance로 데이터 조회
            from korea.krx_data import KRXDataCollector
            krx = KRXDataCollector()

            # 종목 리스트 조회
            stock_list = krx.get_stock_list(market)

            for _, row in stock_list.head(100).iterrows():  # 상위 100개만 분석
                code = row['code']
                name = row['name']

                try:
                    # 가격 데이터 조회
                    price_data = krx.get_stock_price(code)
                    if price_data.empty:
                        continue

                    # 변동률 계산
                    current_price = float(price_data['Close'].iloc[-1])

                    # 1일 변동률
                    if len(price_data) >= 2:
                        prev_price = float(price_data['Close'].iloc[-2])
                        change_1d = ((current_price - prev_price) / prev_price) * 100
                    else:
                        change_1d = 0

                    # 5일 변동률
                    if len(price_data) >= 5:
                        price_5d_ago = float(price_data['Close'].iloc[-5])
                        change_5d = ((current_price - price_5d_ago) / price_5d_ago) * 100
                    else:
                        change_5d = 0

                    # 1개월 변동률
                    if len(price_data) >= 20:
                        price_1m_ago = float(price_data['Close'].iloc[-20])
                        change_1m = ((current_price - price_1m_ago) / price_1m_ago) * 100
                    else:
                        change_1m = 0

                    # 거래량 비율
                    if len(price_data) >= 20:
                        avg_volume = float(price_data['Volume'].iloc[-20:].mean())
                        current_volume = float(price_data['Volume'].iloc[-1])
                        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
                    else:
                        volume_ratio = 1.0

                    # 필터링 조건
                    if period == '1d' and change_1d < self.min_change_1d:
                        continue
                    elif period == '5d' and change_5d < self.min_change_5d:
                        continue

                    rally = RallyInfo(
                        symbol=code,
                        name=name,
                        sector=row.get('sector', '기타'),
                        current_price=current_price,
                        change_1d=change_1d,
                        change_5d=change_5d,
                        change_1m=change_1m,
                        volume_ratio=volume_ratio,
                        foreign_net_buy=0,  # 별도 조회 필요
                        inst_net_buy=0,
                        market_cap=0,
                    )
                    rallies.append(rally)

                except Exception as e:
                    logger.debug(f"종목 분석 오류 ({code}): {e}")
                    continue

        except Exception as e:
            logger.error(f"상승 종목 감지 오류: {e}")

        # 상승률 기준 정렬
        if period == '1d':
            rallies.sort(key=lambda x: x.change_1d, reverse=True)
        else:
            rallies.sort(key=lambda x: x.change_5d, reverse=True)

        return rallies[:top_n]

    def detect_sector_rallies(self, top_n: int = 5) -> List[Dict]:
        """섹터별 상승 감지"""
        sectors = []

        # 섹터 ETF 기반 분석
        sector_etfs = {
            '반도체': '091160',
            '2차전지': '305720',
            '바이오': '244580',
            '은행': '091170',
            '자동차': '091180',
            '철강': '117700',
            '건설': '117700',
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

                    # 변동률 계산
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

        sectors.sort(key=lambda x: x['change_5d'], reverse=True)
        return sectors[:top_n]


class ThesisExtractor:
    """상승 논리 추출기"""

    def __init__(self):
        # 논리 유형별 키워드
        self.thesis_keywords = {
            ThesisType.EARNINGS: ['실적', '영업이익', '순이익', '매출', '흑자', '어닝서프라이즈'],
            ThesisType.GUIDANCE: ['가이던스', '전망', '목표', '상향', '컨센서스'],
            ThesisType.NEW_PRODUCT: ['신제품', '신사업', '출시', '개발', '수주', '계약'],
            ThesisType.POLICY: ['정책', '정부', '지원', '규제', '법안', '세제'],
            ThesisType.SECTOR_ROTATION: ['섹터', '순환', '로테이션', '선호', '비중'],
            ThesisType.SUPPLY_DEMAND: ['외국인', '기관', '순매수', '수급', '매집'],
            ThesisType.VALUATION: ['저평가', 'PER', 'PBR', '밸류에이션', '저점'],
            ThesisType.TECHNICAL: ['돌파', '지지', '저항', '반등', '골든크로스'],
            ThesisType.THEME: ['테마', '트렌드', 'AI', '전기차', '메타버스'],
            ThesisType.M_AND_A: ['인수', '합병', 'M&A', '구조조정', '분할'],
            ThesisType.MACRO: ['금리', '환율', '유가', '인플레이션', '경기'],
        }

    def extract_thesis(
        self,
        rally_info: RallyInfo,
        news_articles: List[Dict] = None,
        analyst_reports: List[Dict] = None,
    ) -> List[ThesisClaim]:
        """상승 논리 추출"""
        claims = []

        # 1. 수급 기반 논리 (데이터에서 직접 추출)
        if rally_info.foreign_net_buy > 0:
            claims.append(ThesisClaim(
                claim_type=ThesisType.SUPPLY_DEMAND,
                description=f"외국인 순매수 {rally_info.foreign_net_buy:,.0f}원",
                source="거래소 데이터",
                evidence=[f"외국인 {rally_info.foreign_net_buy:,.0f}원 순매수"]
            ))

        if rally_info.inst_net_buy > 0:
            claims.append(ThesisClaim(
                claim_type=ThesisType.SUPPLY_DEMAND,
                description=f"기관 순매수 {rally_info.inst_net_buy:,.0f}원",
                source="거래소 데이터",
                evidence=[f"기관 {rally_info.inst_net_buy:,.0f}원 순매수"]
            ))

        # 2. 거래량 급증 기반 논리
        if rally_info.volume_ratio > 3.0:
            claims.append(ThesisClaim(
                claim_type=ThesisType.SUPPLY_DEMAND,
                description=f"거래량 {rally_info.volume_ratio:.1f}배 급증",
                source="거래 데이터",
                evidence=[f"평균 대비 거래량 {rally_info.volume_ratio:.1f}배"]
            ))

        # 3. 뉴스 기반 논리 추출
        if news_articles:
            news_claims = self._extract_from_news(news_articles)
            claims.extend(news_claims)

        # 4. 애널리스트 리포트 기반
        if analyst_reports:
            report_claims = self._extract_from_reports(analyst_reports)
            claims.extend(report_claims)

        # 5. 논리가 없으면 불명확으로 표시
        if not claims:
            claims.append(ThesisClaim(
                claim_type=ThesisType.UNKNOWN,
                description="명확한 상승 논리를 찾지 못함",
                source="분석 결과",
            ))

        return claims

    def _extract_from_news(self, articles: List[Dict]) -> List[ThesisClaim]:
        """뉴스에서 논리 추출"""
        claims = []

        for article in articles:
            title = article.get('title', '')
            content = article.get('content', '')
            source = article.get('source', '뉴스')
            date = article.get('date')
            text = f"{title} {content}"

            # 키워드 매칭으로 논리 유형 판단
            for thesis_type, keywords in self.thesis_keywords.items():
                for keyword in keywords:
                    if keyword in text:
                        claims.append(ThesisClaim(
                            claim_type=thesis_type,
                            description=title[:100],
                            source=source,
                            source_date=date,
                            evidence=[f"뉴스: {title[:50]}..."]
                        ))
                        break

        return claims

    def _extract_from_reports(self, reports: List[Dict]) -> List[ThesisClaim]:
        """애널리스트 리포트에서 논리 추출"""
        claims = []

        for report in reports:
            title = report.get('title', '')
            target_price = report.get('target_price')
            rating = report.get('rating')
            source = report.get('analyst', '애널리스트')

            if target_price:
                claims.append(ThesisClaim(
                    claim_type=ThesisType.VALUATION,
                    description=f"목표가 {target_price:,}원 ({rating})",
                    source=source,
                    evidence=[f"목표가: {target_price:,}원"]
                ))

        return claims


class ThesisValidator:
    """논리 검증기"""

    def __init__(self):
        self.validation_weights = {
            ThesisType.EARNINGS: 0.9,  # 실적은 검증 가능
            ThesisType.GUIDANCE: 0.7,
            ThesisType.NEW_PRODUCT: 0.6,
            ThesisType.POLICY: 0.5,
            ThesisType.SECTOR_ROTATION: 0.4,
            ThesisType.SUPPLY_DEMAND: 0.8,  # 수급은 데이터로 확인
            ThesisType.VALUATION: 0.7,
            ThesisType.TECHNICAL: 0.5,
            ThesisType.THEME: 0.3,  # 테마는 주관적
            ThesisType.M_AND_A: 0.8,
            ThesisType.MACRO: 0.5,
            ThesisType.UNKNOWN: 0.1,
        }

    def validate_thesis(
        self,
        claim: ThesisClaim,
        rally_info: RallyInfo,
        financial_data: Dict = None,
    ) -> ThesisValidation:
        """논리 검증"""

        is_valid = True
        confidence = self.validation_weights.get(claim.claim_type, 0.5)
        validation_details = ""
        data_support = {}
        risks = []

        # 논리 유형별 검증
        if claim.claim_type == ThesisType.EARNINGS:
            result = self._validate_earnings(claim, financial_data)
            is_valid = result['valid']
            confidence *= result['confidence']
            validation_details = result['details']
            data_support = result.get('data', {})
            risks = result.get('risks', [])

        elif claim.claim_type == ThesisType.SUPPLY_DEMAND:
            result = self._validate_supply_demand(claim, rally_info)
            is_valid = result['valid']
            confidence *= result['confidence']
            validation_details = result['details']

        elif claim.claim_type == ThesisType.VALUATION:
            result = self._validate_valuation(claim, rally_info, financial_data)
            is_valid = result['valid']
            confidence *= result['confidence']
            validation_details = result['details']
            risks = result.get('risks', [])

        elif claim.claim_type == ThesisType.THEME:
            # 테마는 검증이 어려움
            is_valid = True
            confidence *= 0.5
            validation_details = "테마/모멘텀은 객관적 검증이 어려움"
            risks = ["테마 소멸 시 급락 가능성", "펀더멘털 뒷받침 부재"]

        elif claim.claim_type == ThesisType.UNKNOWN:
            is_valid = False
            confidence = 0.1
            validation_details = "상승 논리 불명확 - 투기적 상승 가능성"
            risks = ["논리 없는 급등은 급락 위험", "고점 매수 주의"]

        return ThesisValidation(
            claim=claim,
            is_valid=is_valid,
            confidence=min(confidence, 1.0),
            validation_details=validation_details,
            data_support=data_support,
            risks=risks,
        )

    def _validate_earnings(self, claim: ThesisClaim, financial_data: Dict) -> Dict:
        """실적 논리 검증"""
        if not financial_data:
            return {
                'valid': False,
                'confidence': 0.3,
                'details': "실적 데이터 없음",
                'risks': ["실적 확인 필요"]
            }

        # 실적 데이터 확인
        revenue_growth = financial_data.get('revenue_growth', 0)
        profit_growth = financial_data.get('profit_growth', 0)

        if profit_growth > 20:
            return {
                'valid': True,
                'confidence': 0.9,
                'details': f"이익 {profit_growth:.1f}% 성장으로 실적 개선 확인",
                'data': {'profit_growth': profit_growth},
                'risks': []
            }
        elif profit_growth > 0:
            return {
                'valid': True,
                'confidence': 0.7,
                'details': f"이익 {profit_growth:.1f}% 성장 (양호)",
                'data': {'profit_growth': profit_growth},
                'risks': ["성장세 둔화 가능성"]
            }
        else:
            return {
                'valid': False,
                'confidence': 0.3,
                'details': f"이익 {profit_growth:.1f}% 감소 - 실적 개선 주장과 불일치",
                'risks': ["실적 부진 지속 가능성"]
            }

    def _validate_supply_demand(self, claim: ThesisClaim, rally_info: RallyInfo) -> Dict:
        """수급 논리 검증"""
        foreign_net = rally_info.foreign_net_buy
        inst_net = rally_info.inst_net_buy
        volume_ratio = rally_info.volume_ratio

        if foreign_net > 0 and inst_net > 0:
            return {
                'valid': True,
                'confidence': 0.9,
                'details': f"외국인+기관 동반 순매수 확인"
            }
        elif foreign_net > 0 or inst_net > 0:
            return {
                'valid': True,
                'confidence': 0.7,
                'details': f"기관 투자자 매수세 확인"
            }
        elif volume_ratio > 2.0:
            return {
                'valid': True,
                'confidence': 0.5,
                'details': f"거래량 급증 ({volume_ratio:.1f}배) - 관심 증가"
            }
        else:
            return {
                'valid': False,
                'confidence': 0.3,
                'details': "수급 개선 근거 부족"
            }

    def _validate_valuation(
        self,
        claim: ThesisClaim,
        rally_info: RallyInfo,
        financial_data: Dict
    ) -> Dict:
        """밸류에이션 논리 검증"""
        if not financial_data:
            return {
                'valid': False,
                'confidence': 0.3,
                'details': "재무 데이터 없음",
                'risks': ["밸류에이션 확인 필요"]
            }

        per = financial_data.get('per', 0)
        pbr = financial_data.get('pbr', 0)
        industry_per = financial_data.get('industry_per', 15)

        if per > 0 and per < industry_per * 0.7:
            return {
                'valid': True,
                'confidence': 0.8,
                'details': f"PER {per:.1f}배 - 업종 평균 대비 저평가",
                'risks': []
            }
        elif per > 0 and per < industry_per:
            return {
                'valid': True,
                'confidence': 0.6,
                'details': f"PER {per:.1f}배 - 적정 수준",
                'risks': ["추가 상승 여력 제한적"]
            }
        else:
            return {
                'valid': False,
                'confidence': 0.3,
                'details': f"PER {per:.1f}배 - 고평가 영역",
                'risks': ["밸류에이션 부담", "실적 뒷받침 필요"]
            }


class CredibilityScorer:
    """신뢰도 평가기"""

    def calculate_credibility(
        self,
        rally_info: RallyInfo,
        validations: List[ThesisValidation],
    ) -> CredibilityScore:
        """종합 신뢰도 계산"""

        # 1. 펀더멘털 점수 (실적, 밸류에이션 기반)
        fundamental_score = self._calc_fundamental_score(validations)

        # 2. 수급 점수
        supply_demand_score = self._calc_supply_demand_score(rally_info, validations)

        # 3. 기술적 점수
        technical_score = self._calc_technical_score(rally_info)

        # 4. 내러티브 점수 (스토리 일관성)
        narrative_score = self._calc_narrative_score(validations)

        # 5. 리스크 점수 (낮을수록 좋음)
        risk_score = self._calc_risk_score(validations)

        # 종합 점수 계산 (가중 평균)
        overall = (
            fundamental_score * 0.30 +
            supply_demand_score * 0.25 +
            technical_score * 0.15 +
            narrative_score * 0.20 +
            (100 - risk_score) * 0.10
        )

        # 신뢰도 레벨 결정
        if overall >= 80:
            level = CredibilityLevel.VERY_HIGH
        elif overall >= 65:
            level = CredibilityLevel.HIGH
        elif overall >= 50:
            level = CredibilityLevel.MEDIUM
        elif overall >= 35:
            level = CredibilityLevel.LOW
        elif overall >= 20:
            level = CredibilityLevel.VERY_LOW
        else:
            level = CredibilityLevel.SPECULATIVE

        return CredibilityScore(
            overall=overall,
            level=level,
            fundamental_score=fundamental_score,
            supply_demand_score=supply_demand_score,
            technical_score=technical_score,
            narrative_score=narrative_score,
            risk_score=risk_score,
            breakdown={
                'fundamental': fundamental_score,
                'supply_demand': supply_demand_score,
                'technical': technical_score,
                'narrative': narrative_score,
                'risk': risk_score,
            }
        )

    def _calc_fundamental_score(self, validations: List[ThesisValidation]) -> float:
        """펀더멘털 점수 계산"""
        fundamental_types = {ThesisType.EARNINGS, ThesisType.VALUATION, ThesisType.GUIDANCE}

        relevant = [v for v in validations if v.claim.claim_type in fundamental_types]
        if not relevant:
            return 40  # 기본점수

        valid_count = sum(1 for v in relevant if v.is_valid)
        avg_confidence = sum(v.confidence for v in relevant) / len(relevant)

        return min(100, (valid_count / len(relevant)) * 50 + avg_confidence * 50)

    def _calc_supply_demand_score(
        self,
        rally_info: RallyInfo,
        validations: List[ThesisValidation]
    ) -> float:
        """수급 점수 계산"""
        score = 50  # 기본점수

        # 외국인 순매수
        if rally_info.foreign_net_buy > 0:
            score += 20
        elif rally_info.foreign_net_buy < 0:
            score -= 10

        # 기관 순매수
        if rally_info.inst_net_buy > 0:
            score += 15
        elif rally_info.inst_net_buy < 0:
            score -= 10

        # 거래량
        if rally_info.volume_ratio > 3:
            score += 15
        elif rally_info.volume_ratio > 2:
            score += 10

        return min(100, max(0, score))

    def _calc_technical_score(self, rally_info: RallyInfo) -> float:
        """기술적 점수 계산"""
        score = 50

        # 상승 추세 확인
        if rally_info.change_1m > rally_info.change_5d > rally_info.change_1d > 0:
            score += 20  # 건전한 상승 추세
        elif rally_info.change_1d > 10:
            score -= 10  # 급등 (과열 우려)

        # 거래량 동반
        if rally_info.volume_ratio > 1.5:
            score += 10

        return min(100, max(0, score))

    def _calc_narrative_score(self, validations: List[ThesisValidation]) -> float:
        """내러티브 점수 계산"""
        if not validations:
            return 20

        # 검증된 주장이 많을수록 높음
        valid_count = sum(1 for v in validations if v.is_valid)
        total = len(validations)

        # UNKNOWN 유형이 있으면 감점
        unknown_count = sum(1 for v in validations
                           if v.claim.claim_type == ThesisType.UNKNOWN)

        base_score = (valid_count / total) * 80 if total > 0 else 20
        penalty = unknown_count * 20

        return max(0, base_score - penalty)

    def _calc_risk_score(self, validations: List[ThesisValidation]) -> float:
        """리스크 점수 계산 (낮을수록 좋음)"""
        total_risks = 0
        for v in validations:
            total_risks += len(v.risks)

        # 리스크가 많을수록 점수 높음
        return min(100, total_risks * 15)


class RallyAnalyzer:
    """상승 분석기 (통합 인터페이스)"""

    def __init__(self):
        self.detector = RallyDetector()
        self.extractor = ThesisExtractor()
        self.validator = ThesisValidator()
        self.scorer = CredibilityScorer()

    def analyze_rally(
        self,
        symbol: str,
        name: str = None,
        news: List[Dict] = None,
        reports: List[Dict] = None,
        financial_data: Dict = None,
    ) -> Optional[RallyReport]:
        """단일 종목 상승 분석"""

        try:
            # 1. 종목 정보 조회
            from korea.krx_data import KRXDataCollector
            krx = KRXDataCollector()

            price_data = krx.get_stock_price(symbol)
            if price_data.empty:
                return None

            current_price = float(price_data['Close'].iloc[-1])

            # 변동률 계산
            change_1d = 0
            change_5d = 0
            change_1m = 0
            volume_ratio = 1.0

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

            rally_info = RallyInfo(
                symbol=symbol,
                name=name or symbol,
                sector='',
                current_price=current_price,
                change_1d=change_1d,
                change_5d=change_5d,
                change_1m=change_1m,
                volume_ratio=volume_ratio,
                foreign_net_buy=0,
                inst_net_buy=0,
                market_cap=0,
            )

            # 2. 논리 추출
            claims = self.extractor.extract_thesis(rally_info, news, reports)

            # 3. 논리 검증
            validations = []
            for claim in claims:
                validation = self.validator.validate_thesis(claim, rally_info, financial_data)
                validations.append(validation)

            # 4. 신뢰도 평가
            credibility = self.scorer.calculate_credibility(rally_info, validations)

            # 5. 요약 및 추천 생성
            summary = self._generate_summary(rally_info, validations, credibility)
            recommendation = self._generate_recommendation(credibility)
            warnings = self._collect_warnings(validations, credibility)

            return RallyReport(
                rally_info=rally_info,
                thesis_claims=claims,
                validations=validations,
                credibility=credibility,
                summary=summary,
                recommendation=recommendation,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"상승 분석 오류 ({symbol}): {e}")
            return None

    def analyze_top_rallies(self, top_n: int = 10) -> List[RallyReport]:
        """상위 상승 종목 분석"""
        reports = []

        # 상승 종목 감지
        rallies = self.detector.detect_rallying_stocks(top_n=top_n)

        for rally in rallies:
            report = self.analyze_rally(
                symbol=rally.symbol,
                name=rally.name,
            )
            if report:
                reports.append(report)

        return reports

    def _generate_summary(
        self,
        rally_info: RallyInfo,
        validations: List[ThesisValidation],
        credibility: CredibilityScore,
    ) -> str:
        """분석 요약 생성"""
        lines = []

        lines.append(f"📈 {rally_info.name} ({rally_info.symbol})")
        lines.append(f"현재가: {rally_info.current_price:,.0f}원")
        lines.append(f"변동률: 1일 {rally_info.change_1d:+.1f}% / 5일 {rally_info.change_5d:+.1f}% / 1개월 {rally_info.change_1m:+.1f}%")
        lines.append("")
        lines.append(f"📊 신뢰도: {credibility.overall:.0f}점 ({credibility.level.value})")
        lines.append("")
        lines.append("🔍 상승 논리:")

        for v in validations:
            status = "✅" if v.is_valid else "❌"
            lines.append(f"  {status} {v.claim.claim_type.value}: {v.claim.description}")
            if v.validation_details:
                lines.append(f"     └ {v.validation_details}")

        return "\n".join(lines)

    def _generate_recommendation(self, credibility: CredibilityScore) -> str:
        """투자 의견 생성"""
        if credibility.level == CredibilityLevel.VERY_HIGH:
            return "🟢 상승 논리가 견고함. 추세 추종 가능"
        elif credibility.level == CredibilityLevel.HIGH:
            return "🟢 논리적 근거 있음. 선별적 접근 권장"
        elif credibility.level == CredibilityLevel.MEDIUM:
            return "🟡 논리 일부 확인. 신중한 접근 필요"
        elif credibility.level == CredibilityLevel.LOW:
            return "🟠 논리 불충분. 추가 확인 후 판단"
        elif credibility.level == CredibilityLevel.VERY_LOW:
            return "🔴 논리 근거 부족. 투자 주의"
        else:
            return "⚫ 투기적 상승. 참여 비권장"

    def _collect_warnings(
        self,
        validations: List[ThesisValidation],
        credibility: CredibilityScore,
    ) -> List[str]:
        """경고 수집"""
        warnings = []

        # 검증에서 수집된 리스크
        for v in validations:
            warnings.extend(v.risks)

        # 신뢰도 기반 경고
        if credibility.risk_score > 50:
            warnings.append("⚠️ 리스크 요인이 다수 존재")

        if credibility.fundamental_score < 40:
            warnings.append("⚠️ 펀더멘털 근거 부족")

        if credibility.level in [CredibilityLevel.VERY_LOW, CredibilityLevel.SPECULATIVE]:
            warnings.append("⚠️ 급락 위험 높음")

        return list(set(warnings))  # 중복 제거


# 편의 함수
def analyze_stock_rally(symbol: str, name: str = None) -> Optional[RallyReport]:
    """단일 종목 상승 분석 (간편 함수)"""
    analyzer = RallyAnalyzer()
    return analyzer.analyze_rally(symbol, name)


def get_top_rallies(top_n: int = 10) -> List[RallyReport]:
    """상위 상승 종목 분석 (간편 함수)"""
    analyzer = RallyAnalyzer()
    return analyzer.analyze_top_rallies(top_n)
