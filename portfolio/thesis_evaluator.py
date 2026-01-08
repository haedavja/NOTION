"""
투자 논리 평가 모듈
사용자의 매수 이유를 객관적으로 분석하고 평가합니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

from .portfolio import Position, InvestmentThesis


class ThesisRating(Enum):
    """논리 평가 등급"""
    STRONG = "매우 긍정"      # 논리가 현재 데이터와 강하게 일치
    POSITIVE = "긍정"         # 논리가 현재 데이터와 일치
    NEUTRAL = "중립"          # 판단 보류
    NEGATIVE = "부정"         # 논리와 현재 상황 불일치
    WEAK = "매우 부정"        # 논리가 현재 데이터와 크게 불일치


@dataclass
class ThesisEvaluation:
    """논리 평가 결과"""
    position: Position
    rating: ThesisRating
    score: float                    # -1 ~ 1
    confidence: float               # 0 ~ 1

    # 분석 결과
    fundamental_check: Dict         # 펀더멘털 체크
    technical_check: Dict           # 기술적 체크
    macro_alignment: Dict           # 거시경제 정합성
    risk_assessment: Dict           # 리스크 평가

    # 종합 의견
    strengths: List[str]            # 강점
    weaknesses: List[str]           # 약점
    recommendations: List[str]       # 권고사항
    probability_assessment: Dict     # 확률적 평가


class ThesisEvaluator:
    """투자 논리 평가 클래스"""

    # 논리 유형별 체크 포인트
    THESIS_CHECKPOINTS = {
        InvestmentThesis.GROWTH: [
            'revenue_growth',      # 매출 성장률
            'earnings_growth',     # 이익 성장률
            'market_expansion',    # 시장 확대
            'competitive_moat',    # 경쟁 해자
            'price_momentum',      # 가격 모멘텀
        ],
        InvestmentThesis.VALUE: [
            'pe_ratio',            # PER
            'pb_ratio',            # PBR
            'dividend_yield',      # 배당 수익률
            'fcf_yield',           # FCF 수익률
            'margin_of_safety',    # 안전 마진
        ],
        InvestmentThesis.DIVIDEND: [
            'dividend_yield',
            'dividend_growth',     # 배당 성장
            'payout_ratio',        # 배당 성향
            'dividend_consistency', # 배당 지속성
        ],
        InvestmentThesis.MOMENTUM: [
            'price_trend',         # 가격 추세
            'relative_strength',   # 상대 강도
            'volume_trend',        # 거래량 추세
            'breakout_status',     # 돌파 여부
        ],
        InvestmentThesis.MACRO: [
            'interest_rate_sensitivity',  # 금리 민감도
            'inflation_hedge',            # 인플레 헷지
            'economic_cycle',             # 경기 사이클
            'sector_outlook',             # 섹터 전망
        ],
        InvestmentThesis.SECTOR_ROTATION: [
            'sector_momentum',     # 섹터 모멘텀
            'relative_performance', # 상대 성과
            'cycle_position',      # 사이클 위치
        ],
        InvestmentThesis.TECHNICAL: [
            'trend_direction',
            'support_resistance',
            'momentum_indicators',
            'volume_analysis',
        ],
    }

    # 키워드 분석용 (투자 논리 텍스트에서 추출)
    POSITIVE_KEYWORDS = {
        'growth': ['성장', '확대', '증가', '급증', 'growth', 'expansion', 'increase'],
        'value': ['저평가', '할인', '저렴', 'undervalued', 'cheap', 'discount'],
        'dividend': ['배당', '수익률', 'dividend', 'yield', 'income'],
        'moat': ['독점', '해자', '경쟁력', 'monopoly', 'moat', 'competitive'],
        'catalyst': ['촉매', '이벤트', '발표', 'catalyst', 'event', 'announcement'],
    }

    RISK_KEYWORDS = {
        'high_valuation': ['고평가', '버블', 'overvalued', 'expensive', 'bubble'],
        'competition': ['경쟁', '위협', 'competition', 'threat', 'disrupt'],
        'regulation': ['규제', '법률', 'regulation', 'legal', 'antitrust'],
        'macro_risk': ['금리', '인플레', '경기침체', 'interest', 'inflation', 'recession'],
    }

    def __init__(self):
        """초기화"""
        self.cache = {}

    def get_stock_data(self, symbol: str, period: str = '1y') -> Optional[pd.DataFrame]:
        """주가 데이터 조회"""
        if not YFINANCE_AVAILABLE:
            return None

        cache_key = f"{symbol}_{period}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            self.cache[cache_key] = data
            return data
        except Exception as e:
            print(f"데이터 조회 실패 ({symbol}): {e}")
            return None

    def get_fundamental_data(self, symbol: str) -> Dict:
        """펀더멘털 데이터 조회"""
        if not YFINANCE_AVAILABLE:
            return {}

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            return {
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'pb_ratio': info.get('priceToBook'),
                'ps_ratio': info.get('priceToSalesTrailing12Months'),
                'dividend_yield': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
                'payout_ratio': info.get('payoutRatio', 0) * 100 if info.get('payoutRatio') else 0,
                'revenue_growth': info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else 0,
                'earnings_growth': info.get('earningsGrowth', 0) * 100 if info.get('earningsGrowth') else 0,
                'profit_margin': info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 0,
                'roe': info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0,
                'debt_to_equity': info.get('debtToEquity'),
                'current_ratio': info.get('currentRatio'),
                'market_cap': info.get('marketCap'),
                'beta': info.get('beta'),
                '52w_high': info.get('fiftyTwoWeekHigh'),
                '52w_low': info.get('fiftyTwoWeekLow'),
                'avg_volume': info.get('averageVolume'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
            }
        except Exception as e:
            print(f"펀더멘털 조회 실패 ({symbol}): {e}")
            return {}

    def analyze_thesis_keywords(self, thesis_description: str) -> Dict:
        """투자 논리 키워드 분석"""
        text_lower = thesis_description.lower()

        positive_found = []
        risk_found = []

        for category, keywords in self.POSITIVE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    positive_found.append({'category': category, 'keyword': keyword})

        for category, keywords in self.RISK_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    risk_found.append({'category': category, 'keyword': keyword})

        return {
            'positive_factors': positive_found,
            'risk_factors': risk_found,
            'positive_count': len(positive_found),
            'risk_count': len(risk_found),
        }

    def check_fundamental_alignment(self, position: Position, fundamentals: Dict) -> Dict:
        """펀더멘털 정합성 체크"""
        checks = {
            'passed': [],
            'failed': [],
            'warnings': [],
            'score': 0,
        }

        thesis_type = position.thesis_type

        # 성장주 체크
        if thesis_type == InvestmentThesis.GROWTH:
            revenue_growth = fundamentals.get('revenue_growth', 0)
            earnings_growth = fundamentals.get('earnings_growth', 0)

            if revenue_growth > 15:
                checks['passed'].append(f"매출 성장률 양호: {revenue_growth:.1f}%")
            elif revenue_growth > 0:
                checks['warnings'].append(f"매출 성장률 보통: {revenue_growth:.1f}%")
            else:
                checks['failed'].append(f"매출 역성장: {revenue_growth:.1f}%")

            if earnings_growth > 15:
                checks['passed'].append(f"이익 성장률 양호: {earnings_growth:.1f}%")
            elif earnings_growth > 0:
                checks['warnings'].append(f"이익 성장률 보통: {earnings_growth:.1f}%")
            else:
                checks['failed'].append(f"이익 역성장: {earnings_growth:.1f}%")

            # PEG 비율 체크
            pe = fundamentals.get('forward_pe', 0)
            if pe and earnings_growth > 0:
                peg = pe / earnings_growth
                if peg < 1:
                    checks['passed'].append(f"PEG 비율 양호: {peg:.2f}")
                elif peg < 2:
                    checks['warnings'].append(f"PEG 비율 보통: {peg:.2f}")
                else:
                    checks['failed'].append(f"PEG 비율 높음: {peg:.2f}")

        # 가치주 체크
        elif thesis_type == InvestmentThesis.VALUE:
            pe = fundamentals.get('pe_ratio')
            pb = fundamentals.get('pb_ratio')

            if pe:
                if pe < 15:
                    checks['passed'].append(f"PER 저평가: {pe:.1f}")
                elif pe < 25:
                    checks['warnings'].append(f"PER 적정: {pe:.1f}")
                else:
                    checks['failed'].append(f"PER 고평가: {pe:.1f}")

            if pb:
                if pb < 1.5:
                    checks['passed'].append(f"PBR 저평가: {pb:.2f}")
                elif pb < 3:
                    checks['warnings'].append(f"PBR 적정: {pb:.2f}")
                else:
                    checks['failed'].append(f"PBR 고평가: {pb:.2f}")

        # 배당주 체크
        elif thesis_type == InvestmentThesis.DIVIDEND:
            div_yield = fundamentals.get('dividend_yield', 0)
            payout = fundamentals.get('payout_ratio', 0)

            if div_yield > 3:
                checks['passed'].append(f"배당 수익률 양호: {div_yield:.2f}%")
            elif div_yield > 1.5:
                checks['warnings'].append(f"배당 수익률 보통: {div_yield:.2f}%")
            else:
                checks['failed'].append(f"배당 수익률 낮음: {div_yield:.2f}%")

            if 30 < payout < 70:
                checks['passed'].append(f"배당 성향 적정: {payout:.1f}%")
            elif payout > 90:
                checks['failed'].append(f"배당 성향 과다: {payout:.1f}%")

        # 점수 계산
        total_checks = len(checks['passed']) + len(checks['failed']) + len(checks['warnings'])
        if total_checks > 0:
            score = (len(checks['passed']) - len(checks['failed']) * 0.5) / total_checks
            checks['score'] = max(min(score, 1), -1)

        return checks

    def check_technical_alignment(self, position: Position, price_data: pd.DataFrame) -> Dict:
        """기술적 분석 정합성 체크"""
        checks = {
            'passed': [],
            'failed': [],
            'warnings': [],
            'indicators': {},
            'score': 0,
        }

        if price_data is None or price_data.empty:
            return checks

        close = price_data['Close']
        current_price = close.iloc[-1]

        # 이동평균
        ma_20 = close.rolling(20).mean().iloc[-1]
        ma_50 = close.rolling(50).mean().iloc[-1]
        ma_200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None

        checks['indicators']['ma_20'] = ma_20
        checks['indicators']['ma_50'] = ma_50
        checks['indicators']['ma_200'] = ma_200

        # 추세 체크
        if current_price > ma_20 > ma_50:
            checks['passed'].append("단기 상승 추세 (가격 > MA20 > MA50)")
        elif current_price < ma_20 < ma_50:
            checks['failed'].append("단기 하락 추세 (가격 < MA20 < MA50)")
        else:
            checks['warnings'].append("혼조세")

        if ma_200 and current_price > ma_200:
            checks['passed'].append("장기 상승 추세 (200일선 위)")
        elif ma_200:
            checks['failed'].append("장기 하락 추세 (200일선 아래)")

        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]

        checks['indicators']['rsi'] = current_rsi

        if 30 < current_rsi < 70:
            checks['passed'].append(f"RSI 중립 구간: {current_rsi:.1f}")
        elif current_rsi > 70:
            checks['warnings'].append(f"RSI 과매수: {current_rsi:.1f}")
        else:
            checks['warnings'].append(f"RSI 과매도: {current_rsi:.1f}")

        # 52주 고저점 대비
        high_52w = close.tail(252).max() if len(close) >= 252 else close.max()
        low_52w = close.tail(252).min() if len(close) >= 252 else close.min()

        from_high = (current_price / high_52w - 1) * 100
        from_low = (current_price / low_52w - 1) * 100

        checks['indicators']['from_52w_high'] = from_high
        checks['indicators']['from_52w_low'] = from_low

        if from_high > -10:
            checks['passed'].append(f"52주 고점 근처 ({from_high:.1f}%)")
        elif from_high < -30:
            checks['failed'].append(f"52주 고점 대비 크게 하락 ({from_high:.1f}%)")

        # 수익률 분석
        returns_1m = (current_price / close.iloc[-21] - 1) * 100 if len(close) >= 21 else 0
        returns_3m = (current_price / close.iloc[-63] - 1) * 100 if len(close) >= 63 else 0

        checks['indicators']['return_1m'] = returns_1m
        checks['indicators']['return_3m'] = returns_3m

        # 모멘텀 투자 논리일 경우
        if position.thesis_type == InvestmentThesis.MOMENTUM:
            if returns_1m > 5 and returns_3m > 10:
                checks['passed'].append("강한 모멘텀 확인")
            elif returns_1m < 0 and returns_3m < 0:
                checks['failed'].append("모멘텀 약화")

        # 점수 계산
        total = len(checks['passed']) + len(checks['failed']) + len(checks['warnings'])
        if total > 0:
            score = (len(checks['passed']) - len(checks['failed']) * 0.5) / total
            checks['score'] = max(min(score, 1), -1)

        return checks

    def assess_risk(self, position: Position, fundamentals: Dict, price_data: pd.DataFrame) -> Dict:
        """리스크 평가"""
        risk_assessment = {
            'overall_risk': 'medium',
            'risk_score': 0.5,  # 0 (낮음) ~ 1 (높음)
            'risks': [],
            'mitigants': [],
        }

        # 변동성 리스크
        if price_data is not None and not price_data.empty:
            returns = price_data['Close'].pct_change()
            volatility = returns.std() * np.sqrt(252) * 100

            if volatility > 40:
                risk_assessment['risks'].append(f"높은 변동성: {volatility:.1f}%")
                risk_assessment['risk_score'] += 0.2
            elif volatility < 20:
                risk_assessment['mitigants'].append(f"낮은 변동성: {volatility:.1f}%")

        # 밸류에이션 리스크
        pe = fundamentals.get('pe_ratio')
        if pe and pe > 40:
            risk_assessment['risks'].append(f"높은 밸류에이션 (PER: {pe:.1f})")
            risk_assessment['risk_score'] += 0.15

        # 부채 리스크
        debt_equity = fundamentals.get('debt_to_equity')
        if debt_equity and debt_equity > 2:
            risk_assessment['risks'].append(f"높은 부채 비율: {debt_equity:.2f}")
            risk_assessment['risk_score'] += 0.15

        # 베타 리스크
        beta = fundamentals.get('beta')
        if beta and beta > 1.5:
            risk_assessment['risks'].append(f"높은 시장 민감도 (Beta: {beta:.2f})")
            risk_assessment['risk_score'] += 0.1
        elif beta and beta < 0.8:
            risk_assessment['mitigants'].append(f"낮은 시장 민감도 (Beta: {beta:.2f})")

        # 손절가 대비 현재가
        if position.stop_loss and position.current_price:
            downside = (position.stop_loss / position.current_price - 1) * 100
            if downside > -5:
                risk_assessment['risks'].append(f"손절가 근접: {abs(downside):.1f}% 하락 시 손절")
                risk_assessment['risk_score'] += 0.2

        # 목표가 대비 현재가
        if position.target_price and position.current_price:
            upside = (position.target_price / position.current_price - 1) * 100
            if upside < 5:
                risk_assessment['warnings'] = ["목표가 근접 - 출구 전략 검토 필요"]

        # 전체 리스크 레벨
        if risk_assessment['risk_score'] > 0.7:
            risk_assessment['overall_risk'] = 'high'
        elif risk_assessment['risk_score'] < 0.3:
            risk_assessment['overall_risk'] = 'low'

        return risk_assessment

    def calculate_probability_assessment(self, position: Position,
                                         fundamental_check: Dict,
                                         technical_check: Dict,
                                         risk_assessment: Dict) -> Dict:
        """확률적 평가"""
        # 목표가 도달 확률 추정
        target_probability = 0.5
        stop_probability = 0.5

        # 펀더멘털 점수 반영
        fundamental_score = fundamental_check.get('score', 0)
        target_probability += fundamental_score * 0.15

        # 기술적 점수 반영
        technical_score = technical_check.get('score', 0)
        target_probability += technical_score * 0.15

        # 리스크 반영
        risk_score = risk_assessment.get('risk_score', 0.5)
        stop_probability = 0.2 + risk_score * 0.3

        # 기대값 계산
        if position.target_price and position.stop_loss and position.current_price:
            upside = (position.target_price / position.current_price - 1) * 100
            downside = (position.stop_loss / position.current_price - 1) * 100

            expected_return = (target_probability * upside) + (stop_probability * downside)
            risk_reward_ratio = abs(upside / downside) if downside != 0 else 0

            return {
                'target_probability': min(max(target_probability, 0.1), 0.9) * 100,
                'stop_probability': min(max(stop_probability, 0.1), 0.5) * 100,
                'upside_potential': upside,
                'downside_risk': downside,
                'expected_return': expected_return,
                'risk_reward_ratio': risk_reward_ratio,
                'kelly_fraction': (target_probability * risk_reward_ratio - (1 - target_probability)) / risk_reward_ratio if risk_reward_ratio > 0 else 0,
            }

        return {
            'target_probability': target_probability * 100,
            'stop_probability': stop_probability * 100,
        }

    def evaluate(self, position: Position, macro_data: Optional[Dict] = None) -> ThesisEvaluation:
        """종합 평가 실행"""
        # 데이터 수집
        price_data = self.get_stock_data(position.symbol)
        fundamentals = self.get_fundamental_data(position.symbol)

        # 키워드 분석
        keyword_analysis = self.analyze_thesis_keywords(position.thesis_description)

        # 펀더멘털 체크
        fundamental_check = self.check_fundamental_alignment(position, fundamentals)

        # 기술적 체크
        technical_check = self.check_technical_alignment(position, price_data)

        # 리스크 평가
        risk_assessment = self.assess_risk(position, fundamentals, price_data)

        # 확률 평가
        probability_assessment = self.calculate_probability_assessment(
            position, fundamental_check, technical_check, risk_assessment
        )

        # 종합 점수 계산
        scores = [
            fundamental_check.get('score', 0),
            technical_check.get('score', 0),
            -risk_assessment.get('risk_score', 0.5) + 0.5,  # 리스크 점수 반전
        ]
        overall_score = np.mean(scores)

        # 등급 결정
        if overall_score > 0.4:
            rating = ThesisRating.STRONG
        elif overall_score > 0.15:
            rating = ThesisRating.POSITIVE
        elif overall_score > -0.15:
            rating = ThesisRating.NEUTRAL
        elif overall_score > -0.4:
            rating = ThesisRating.NEGATIVE
        else:
            rating = ThesisRating.WEAK

        # 강점/약점/권고사항 정리
        strengths = fundamental_check['passed'] + technical_check['passed'] + risk_assessment.get('mitigants', [])
        weaknesses = fundamental_check['failed'] + technical_check['failed'] + risk_assessment['risks']
        warnings = fundamental_check['warnings'] + technical_check['warnings']

        recommendations = []
        if overall_score > 0.3:
            recommendations.append("투자 논리가 현재 데이터와 잘 부합합니다. 보유 유지 권장.")
        elif overall_score > 0:
            recommendations.append("투자 논리가 어느 정도 유효합니다. 모니터링 필요.")
        elif overall_score > -0.3:
            recommendations.append("투자 논리에 대한 재검토가 필요합니다.")
        else:
            recommendations.append("투자 논리가 현재 상황과 맞지 않습니다. 포지션 축소 검토.")

        if risk_assessment['overall_risk'] == 'high':
            recommendations.append("리스크가 높습니다. 손절가 준수 및 비중 조절 고려.")

        if warnings:
            recommendations.extend([f"주의: {w}" for w in warnings[:2]])

        return ThesisEvaluation(
            position=position,
            rating=rating,
            score=overall_score,
            confidence=0.7,  # 데이터 가용성에 따라 조정

            fundamental_check=fundamental_check,
            technical_check=technical_check,
            macro_alignment={'status': 'not_checked'},  # 거시경제 정합성은 별도 분석
            risk_assessment=risk_assessment,

            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            probability_assessment=probability_assessment,
        )

    def evaluate_portfolio(self, positions: List[Position]) -> List[ThesisEvaluation]:
        """포트폴리오 전체 평가"""
        evaluations = []

        for position in positions:
            try:
                evaluation = self.evaluate(position)
                evaluations.append(evaluation)
            except Exception as e:
                print(f"평가 실패 ({position.symbol}): {e}")

        return evaluations

    def get_summary_report(self, evaluations: List[ThesisEvaluation]) -> Dict:
        """평가 요약 리포트"""
        if not evaluations:
            return {'error': 'No evaluations'}

        # 등급별 분포
        rating_dist = {}
        for e in evaluations:
            rating = e.rating.value
            rating_dist[rating] = rating_dist.get(rating, 0) + 1

        # 평균 점수
        avg_score = np.mean([e.score for e in evaluations])

        # 가장 강한/약한 포지션
        sorted_evals = sorted(evaluations, key=lambda x: x.score, reverse=True)
        strongest = sorted_evals[0] if sorted_evals else None
        weakest = sorted_evals[-1] if sorted_evals else None

        # 전체 권고사항
        all_recommendations = []
        for e in evaluations:
            all_recommendations.extend(e.recommendations)

        return {
            'total_positions': len(evaluations),
            'rating_distribution': rating_dist,
            'average_score': avg_score,
            'strongest_position': {
                'symbol': strongest.position.symbol,
                'score': strongest.score,
                'rating': strongest.rating.value,
            } if strongest else None,
            'weakest_position': {
                'symbol': weakest.position.symbol,
                'score': weakest.score,
                'rating': weakest.rating.value,
            } if weakest else None,
            'key_recommendations': list(set(all_recommendations))[:5],
        }
