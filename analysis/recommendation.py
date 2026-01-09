"""
맞춤 추천 모듈
토스 스타일 개인화된 종목 추천
보유 종목/관심 섹터 기반 유사 종목 추천
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np


@dataclass
class StockProfile:
    """종목 프로필"""
    code: str
    name: str
    sector: str
    market_cap: float  # 시가총액
    per: Optional[float]
    pbr: Optional[float]
    dividend_yield: Optional[float]
    roe: Optional[float]
    growth_rate: Optional[float]  # 매출 성장률


@dataclass
class Recommendation:
    """추천 결과"""
    code: str
    name: str
    reason: str
    match_score: float  # 0-100 유사도
    category: str  # 추천 유형
    highlights: List[str]  # 주요 특징


class PersonalizedRecommender:
    """맞춤 추천 엔진"""

    # 섹터 관계 매핑 (관련 섹터)
    RELATED_SECTORS = {
        '반도체': ['IT', '전자부품', '디스플레이', '장비'],
        'IT': ['반도체', '소프트웨어', '인터넷', '게임'],
        '자동차': ['2차전지', '부품', '철강', '화학'],
        '2차전지': ['자동차', '소재', '화학', '에너지'],
        '바이오': ['제약', '헬스케어', '의료기기'],
        '제약': ['바이오', '헬스케어', '화장품'],
        '금융': ['은행', '증권', '보험', '카드'],
        '은행': ['금융', '증권', '보험'],
        '엔터': ['미디어', '게임', '콘텐츠'],
        '미디어': ['엔터', '광고', '콘텐츠'],
        '유통': ['이커머스', '소비재', '식품'],
        '건설': ['부동산', '시멘트', '인테리어'],
        '철강': ['조선', '자동차', '건설'],
        '조선': ['철강', '해운', '기계'],
        '화학': ['정유', '2차전지', '소재'],
    }

    # 투자 스타일 정의
    INVESTMENT_STYLES = {
        'value': {'name': '가치투자', 'per_max': 10, 'pbr_max': 1.0},
        'growth': {'name': '성장투자', 'growth_min': 15},
        'dividend': {'name': '배당투자', 'div_min': 3.0},
        'quality': {'name': '우량주', 'roe_min': 15, 'cap_min': 10_000_000_000_000},
        'momentum': {'name': '모멘텀', 'growth_min': 20},
    }

    # 샘플 종목 데이터베이스
    STOCK_DATABASE = {
        '005930': StockProfile('005930', '삼성전자', '반도체', 430e12, 15.2, 1.3, 2.1, 8.5, 5),
        '000660': StockProfile('000660', 'SK하이닉스', '반도체', 98e12, 8.5, 1.8, 1.2, 21, 25),
        '035420': StockProfile('035420', 'NAVER', 'IT', 45e12, 35, 2.0, 0.3, 6, 10),
        '035720': StockProfile('035720', '카카오', 'IT', 25e12, None, 2.5, 0.1, 3, 5),
        '005380': StockProfile('005380', '현대차', '자동차', 48e12, 6.5, 0.6, 4.5, 10, 8),
        '000270': StockProfile('000270', '기아', '자동차', 38e12, 5.5, 0.8, 5.0, 15, 12),
        '006400': StockProfile('006400', '삼성SDI', '2차전지', 42e12, 25, 2.2, 0.3, 9, 30),
        '373220': StockProfile('373220', 'LG에너지솔루션', '2차전지', 95e12, 80, 5.0, 0, 6, 40),
        '105560': StockProfile('105560', 'KB금융', '은행', 25e12, 5.5, 0.45, 5.5, 9, 3),
        '055550': StockProfile('055550', '신한지주', '은행', 20e12, 5.2, 0.4, 5.8, 8, 2),
        '207940': StockProfile('207940', '삼성바이오로직스', '바이오', 55e12, 70, 6.0, 0, 12, 25),
        '068270': StockProfile('068270', '셀트리온', '바이오', 28e12, 40, 4.5, 0.2, 11, 15),
        '051910': StockProfile('051910', 'LG화학', '화학', 35e12, 15, 1.5, 2.0, 10, 8),
        '096770': StockProfile('096770', 'SK이노베이션', '화학', 15e12, None, 1.2, 1.5, -5, -10),
        '028260': StockProfile('028260', '삼성물산', '건설', 22e12, 12, 0.8, 1.8, 7, 5),
        '034730': StockProfile('034730', 'SK', '지주', 18e12, 8, 0.7, 3.5, 5, 3),
        '015760': StockProfile('015760', '한국전력', '에너지', 12e12, None, 0.3, 0, -15, -20),
        '066570': StockProfile('066570', 'LG전자', '전자', 15e12, 10, 0.9, 2.5, 8, 6),
        '017670': StockProfile('017670', 'SK텔레콤', '통신', 12e12, 9, 0.8, 6.5, 10, 2),
        '030200': StockProfile('030200', 'KT', '통신', 8e12, 7, 0.5, 5.0, 8, 1),
        '003550': StockProfile('003550', 'LG', '지주', 14e12, 11, 0.9, 2.8, 6, 4),
        '018260': StockProfile('018260', '삼성에스디에스', 'IT', 12e12, 18, 2.0, 1.5, 11, 7),
        '032830': StockProfile('032830', '삼성생명', '보험', 16e12, 6, 0.35, 4.0, 6, 2),
        '086790': StockProfile('086790', '하나금융지주', '은행', 15e12, 4.8, 0.38, 6.2, 9, 4),
        '316140': StockProfile('316140', '우리금융지주', '은행', 12e12, 4.5, 0.35, 6.8, 8, 3),
    }

    def __init__(self):
        self.user_portfolio: List[str] = []
        self.watchlist: List[str] = []
        self.preferred_sectors: List[str] = []
        self.investment_style: str = 'balanced'

    def set_user_profile(self,
                        portfolio: List[str] = None,
                        watchlist: List[str] = None,
                        preferred_sectors: List[str] = None,
                        investment_style: str = 'balanced'):
        """
        사용자 프로필 설정

        Args:
            portfolio: 보유 종목 코드 리스트
            watchlist: 관심 종목 코드 리스트
            preferred_sectors: 선호 섹터 리스트
            investment_style: 투자 스타일 (value, growth, dividend, quality, momentum, balanced)
        """
        self.user_portfolio = portfolio or []
        self.watchlist = watchlist or []
        self.preferred_sectors = preferred_sectors or []
        self.investment_style = investment_style

    def get_recommendations(self, limit: int = 5) -> List[Recommendation]:
        """
        맞춤 추천 생성

        Args:
            limit: 추천 개수

        Returns:
            추천 리스트
        """
        recommendations = []

        # 1. 보유 종목 기반 유사 종목 추천
        similar_recs = self._find_similar_stocks()
        recommendations.extend(similar_recs)

        # 2. 선호 섹터 기반 추천
        sector_recs = self._recommend_by_sector()
        recommendations.extend(sector_recs)

        # 3. 투자 스타일 기반 추천
        style_recs = self._recommend_by_style()
        recommendations.extend(style_recs)

        # 4. 배당/가치 특화 추천
        special_recs = self._special_recommendations()
        recommendations.extend(special_recs)

        # 중복 제거 및 정렬
        seen = set()
        unique_recs = []
        for rec in recommendations:
            if rec.code not in seen:
                seen.add(rec.code)
                # 보유/관심 종목 제외
                if rec.code not in self.user_portfolio and rec.code not in self.watchlist:
                    unique_recs.append(rec)

        # 점수순 정렬
        unique_recs.sort(key=lambda x: x.match_score, reverse=True)

        return unique_recs[:limit]

    def _find_similar_stocks(self) -> List[Recommendation]:
        """보유 종목과 유사한 종목 찾기"""
        if not self.user_portfolio:
            return []

        recommendations = []

        for code in self.user_portfolio[:3]:  # 상위 3개 보유 종목 기준
            if code not in self.STOCK_DATABASE:
                continue

            held = self.STOCK_DATABASE[code]

            for candidate_code, candidate in self.STOCK_DATABASE.items():
                if candidate_code == code:
                    continue

                # 유사도 계산
                score, reasons = self._calc_similarity(held, candidate)

                if score >= 60:
                    highlights = []
                    if candidate.dividend_yield and candidate.dividend_yield > 3:
                        highlights.append(f"배당 {candidate.dividend_yield:.1f}%")
                    if candidate.per and candidate.per < 10:
                        highlights.append(f"저PER {candidate.per:.1f}")
                    if candidate.roe and candidate.roe > 15:
                        highlights.append(f"고ROE {candidate.roe:.1f}%")

                    recommendations.append(Recommendation(
                        code=candidate_code,
                        name=candidate.name,
                        reason=f"{held.name} 보유자 추천 - {', '.join(reasons)}",
                        match_score=score,
                        category='similar',
                        highlights=highlights or ['동종 업계']
                    ))

        return recommendations

    def _calc_similarity(self, stock1: StockProfile, stock2: StockProfile) -> Tuple[float, List[str]]:
        """두 종목 간 유사도 계산"""
        score = 0
        reasons = []

        # 같은 섹터
        if stock1.sector == stock2.sector:
            score += 40
            reasons.append('같은 섹터')
        # 관련 섹터
        elif stock2.sector in self.RELATED_SECTORS.get(stock1.sector, []):
            score += 25
            reasons.append('관련 섹터')

        # 시가총액 유사 (0.5x ~ 2x)
        if stock1.market_cap > 0 and stock2.market_cap > 0:
            cap_ratio = stock2.market_cap / stock1.market_cap
            if 0.5 <= cap_ratio <= 2.0:
                score += 15
                reasons.append('유사 규모')

        # PER 유사 (±50%)
        if stock1.per and stock2.per:
            if stock1.per > 0 and stock2.per > 0:
                per_ratio = stock2.per / stock1.per
                if 0.5 <= per_ratio <= 1.5:
                    score += 10
                    reasons.append('유사 PER')

        # 배당 유사
        if stock1.dividend_yield and stock2.dividend_yield:
            div_diff = abs(stock1.dividend_yield - stock2.dividend_yield)
            if div_diff < 2:
                score += 10
                reasons.append('유사 배당')

        # ROE 유사
        if stock1.roe and stock2.roe:
            roe_diff = abs(stock1.roe - stock2.roe)
            if roe_diff < 5:
                score += 10
                reasons.append('유사 수익성')

        return min(100, score), reasons

    def _recommend_by_sector(self) -> List[Recommendation]:
        """섹터 기반 추천"""
        recommendations = []

        # 보유 종목에서 섹터 추출
        sectors = set(self.preferred_sectors)
        for code in self.user_portfolio:
            if code in self.STOCK_DATABASE:
                sectors.add(self.STOCK_DATABASE[code].sector)

        if not sectors:
            return []

        for sector in sectors:
            # 같은 섹터 종목 중 우수 종목
            sector_stocks = [
                (code, s) for code, s in self.STOCK_DATABASE.items()
                if s.sector == sector and code not in self.user_portfolio
            ]

            # ROE 또는 성장률 기준 정렬
            sector_stocks.sort(
                key=lambda x: (x[1].roe or 0) + (x[1].growth_rate or 0),
                reverse=True
            )

            for code, stock in sector_stocks[:2]:  # 섹터당 2개
                highlights = []
                if stock.roe and stock.roe > 10:
                    highlights.append(f"ROE {stock.roe:.1f}%")
                if stock.growth_rate and stock.growth_rate > 10:
                    highlights.append(f"성장률 {stock.growth_rate:.0f}%")
                if stock.dividend_yield and stock.dividend_yield > 2:
                    highlights.append(f"배당 {stock.dividend_yield:.1f}%")

                recommendations.append(Recommendation(
                    code=code,
                    name=stock.name,
                    reason=f"{sector} 섹터 우수 종목",
                    match_score=70 + (stock.roe or 0) / 2,
                    category='sector',
                    highlights=highlights or [f'{sector} 대표주']
                ))

        return recommendations

    def _recommend_by_style(self) -> List[Recommendation]:
        """투자 스타일 기반 추천"""
        recommendations = []
        style = self.investment_style

        for code, stock in self.STOCK_DATABASE.items():
            if code in self.user_portfolio:
                continue

            matches = False
            reason = ""
            highlights = []

            if style == 'value':
                if stock.per and stock.per < 10 and stock.pbr and stock.pbr < 1.0:
                    matches = True
                    reason = "가치투자 적합 - 저PER/PBR"
                    highlights = [f"PER {stock.per:.1f}", f"PBR {stock.pbr:.2f}"]

            elif style == 'growth':
                if stock.growth_rate and stock.growth_rate > 15:
                    matches = True
                    reason = "성장투자 적합 - 높은 성장률"
                    highlights = [f"성장률 {stock.growth_rate:.0f}%"]

            elif style == 'dividend':
                if stock.dividend_yield and stock.dividend_yield > 4:
                    matches = True
                    reason = "배당투자 적합 - 고배당"
                    highlights = [f"배당 {stock.dividend_yield:.1f}%"]

            elif style == 'quality':
                if (stock.roe and stock.roe > 15 and
                    stock.market_cap > 20e12):
                    matches = True
                    reason = "우량주 - 높은 ROE, 대형주"
                    highlights = [f"ROE {stock.roe:.1f}%", "대형주"]

            elif style == 'momentum':
                if stock.growth_rate and stock.growth_rate > 20:
                    matches = True
                    reason = "모멘텀 투자 - 급성장 중"
                    highlights = [f"성장률 {stock.growth_rate:.0f}%"]

            else:  # balanced
                if (stock.roe and stock.roe > 10 and
                    stock.per and stock.per < 20 and
                    stock.dividend_yield and stock.dividend_yield > 1):
                    matches = True
                    reason = "균형 잡힌 종목"
                    highlights = [
                        f"ROE {stock.roe:.1f}%",
                        f"PER {stock.per:.1f}",
                        f"배당 {stock.dividend_yield:.1f}%"
                    ]

            if matches:
                recommendations.append(Recommendation(
                    code=code,
                    name=stock.name,
                    reason=reason,
                    match_score=75,
                    category='style',
                    highlights=highlights
                ))

        return recommendations

    def _special_recommendations(self) -> List[Recommendation]:
        """특별 추천 (배당킹, 저평가 등)"""
        recommendations = []

        # 고배당 종목
        high_div = [(code, s) for code, s in self.STOCK_DATABASE.items()
                    if s.dividend_yield and s.dividend_yield > 5
                    and code not in self.user_portfolio]
        for code, stock in sorted(high_div, key=lambda x: x[1].dividend_yield, reverse=True)[:2]:
            recommendations.append(Recommendation(
                code=code,
                name=stock.name,
                reason="고배당 종목 - 배당수익률 상위",
                match_score=80,
                category='dividend_king',
                highlights=[f"배당 {stock.dividend_yield:.1f}%", "배당 안정성"]
            ))

        # 저PBR 종목 (자산가치 대비 저평가)
        low_pbr = [(code, s) for code, s in self.STOCK_DATABASE.items()
                   if s.pbr and s.pbr < 0.5 and s.roe and s.roe > 5
                   and code not in self.user_portfolio]
        for code, stock in sorted(low_pbr, key=lambda x: x[1].pbr)[:2]:
            recommendations.append(Recommendation(
                code=code,
                name=stock.name,
                reason="자산가치 대비 저평가",
                match_score=75,
                category='undervalued',
                highlights=[f"PBR {stock.pbr:.2f}", f"ROE {stock.roe:.1f}%"]
            ))

        return recommendations

    def get_recommendation_summary(self, recommendations: List[Recommendation]) -> Dict:
        """추천 요약"""
        if not recommendations:
            return {'count': 0, 'categories': {}}

        categories = {}
        for rec in recommendations:
            cat = rec.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(rec.name)

        return {
            'count': len(recommendations),
            'top_pick': recommendations[0].name if recommendations else None,
            'top_reason': recommendations[0].reason if recommendations else None,
            'categories': categories,
            'avg_score': sum(r.match_score for r in recommendations) / len(recommendations)
        }


def get_recommendation_category_name(category: str) -> str:
    """추천 카테고리 한글명"""
    names = {
        'similar': '🔄 유사 종목',
        'sector': '📊 섹터 추천',
        'style': '🎯 스타일 매칭',
        'dividend_king': '👑 배당킹',
        'undervalued': '💎 저평가 발굴',
    }
    return names.get(category, '추천')


def format_recommendation_card(rec: Recommendation) -> str:
    """추천 카드 포맷팅 (텍스트)"""
    category_name = get_recommendation_category_name(rec.category)
    highlights_str = " | ".join(rec.highlights) if rec.highlights else ""

    return f"""
┌─────────────────────────────────────────┐
│ {category_name}
│ {rec.name} ({rec.code})
│ 매칭 점수: {rec.match_score:.0f}점
│ {rec.reason}
│ {highlights_str}
└─────────────────────────────────────────┘
"""


# 싱글톤 인스턴스
recommender = PersonalizedRecommender()
