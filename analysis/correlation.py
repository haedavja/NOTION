"""
상관관계 분석 모듈
종목 간 상관관계 및 공분산 분석
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class CorrelationResult:
    """상관관계 분석 결과"""
    stock1: str
    stock2: str
    stock1_name: str
    stock2_name: str
    correlation: float
    covariance: float
    beta: Optional[float] = None
    interpretation: str = ""


@dataclass
class CorrelationMatrix:
    """상관관계 매트릭스"""
    stocks: List[str]
    stock_names: Dict[str, str]
    matrix: pd.DataFrame
    analysis_period: int
    analysis_date: datetime = field(default_factory=datetime.now)


class CorrelationAnalyzer:
    """상관관계 분석기"""

    def __init__(self):
        self.correlation_thresholds = {
            'very_high': 0.8,
            'high': 0.6,
            'moderate': 0.4,
            'low': 0.2
        }

    def calculate_correlation(
        self,
        prices1: pd.Series,
        prices2: pd.Series,
        stock1: str = "Stock1",
        stock2: str = "Stock2",
        stock1_name: str = "",
        stock2_name: str = ""
    ) -> CorrelationResult:
        """
        두 종목 간 상관관계 계산

        Args:
            prices1: 첫 번째 종목 가격 시계열
            prices2: 두 번째 종목 가격 시계열
            stock1: 첫 번째 종목 코드
            stock2: 두 번째 종목 코드
            stock1_name: 첫 번째 종목명
            stock2_name: 두 번째 종목명

        Returns:
            CorrelationResult
        """
        # 길이 맞춤
        min_len = min(len(prices1), len(prices2))
        prices1 = prices1.tail(min_len)
        prices2 = prices2.tail(min_len)

        # 수익률 계산
        returns1 = prices1.pct_change().dropna()
        returns2 = prices2.pct_change().dropna()

        # 상관계수
        correlation = returns1.corr(returns2)

        # 공분산
        covariance = np.cov(returns1, returns2)[0, 1]

        # 베타 (stock2를 기준으로 stock1의 베타)
        beta = None
        if np.var(returns2) > 0:
            beta = covariance / np.var(returns2)

        # 해석
        interpretation = self._interpret_correlation(correlation)

        return CorrelationResult(
            stock1=stock1,
            stock2=stock2,
            stock1_name=stock1_name or stock1,
            stock2_name=stock2_name or stock2,
            correlation=correlation,
            covariance=covariance,
            beta=beta,
            interpretation=interpretation
        )

    def _interpret_correlation(self, correlation: float) -> str:
        """상관계수 해석"""
        abs_corr = abs(correlation)
        direction = "양의" if correlation > 0 else "음의"

        if abs_corr >= self.correlation_thresholds['very_high']:
            strength = "매우 강한"
            advice = "동일 방향 움직임, 분산 효과 미미"
        elif abs_corr >= self.correlation_thresholds['high']:
            strength = "강한"
            advice = "유사한 움직임 경향"
        elif abs_corr >= self.correlation_thresholds['moderate']:
            strength = "보통"
            advice = "어느 정도 분산 효과 기대"
        elif abs_corr >= self.correlation_thresholds['low']:
            strength = "약한"
            advice = "분산 투자에 적합"
        else:
            strength = "매우 약한"
            advice = "독립적 움직임, 최적의 분산 효과"

        if correlation < 0:
            advice = "역방향 움직임, 헤징에 유용"

        return f"{strength} {direction} 상관관계 ({advice})"

    def calculate_correlation_matrix(
        self,
        price_data: Dict[str, pd.Series],
        stock_names: Dict[str, str] = None
    ) -> CorrelationMatrix:
        """
        여러 종목의 상관관계 매트릭스 계산

        Args:
            price_data: {종목코드: 가격시계열} 딕셔너리
            stock_names: {종목코드: 종목명} 딕셔너리

        Returns:
            CorrelationMatrix
        """
        stocks = list(price_data.keys())
        stock_names = stock_names or {s: s for s in stocks}

        # 길이 맞춤
        min_len = min(len(prices) for prices in price_data.values())

        # 수익률 데이터프레임 생성
        returns_df = pd.DataFrame()
        for code, prices in price_data.items():
            returns = prices.tail(min_len).pct_change().dropna()
            returns_df[code] = returns

        # 상관관계 매트릭스
        corr_matrix = returns_df.corr()

        return CorrelationMatrix(
            stocks=stocks,
            stock_names=stock_names,
            matrix=corr_matrix,
            analysis_period=min_len
        )

    def find_diversification_candidates(
        self,
        base_stock: str,
        price_data: Dict[str, pd.Series],
        max_correlation: float = 0.3,
        min_correlation: float = -1.0
    ) -> List[Tuple[str, float]]:
        """
        분산 투자에 적합한 종목 찾기

        Args:
            base_stock: 기준 종목 코드
            price_data: 가격 데이터 딕셔너리
            max_correlation: 최대 상관계수
            min_correlation: 최소 상관계수

        Returns:
            [(종목코드, 상관계수), ...] 리스트 (낮은 상관계수 순)
        """
        if base_stock not in price_data:
            return []

        base_prices = price_data[base_stock]
        candidates = []

        for code, prices in price_data.items():
            if code == base_stock:
                continue

            result = self.calculate_correlation(base_prices, prices, base_stock, code)

            if min_correlation <= result.correlation <= max_correlation:
                candidates.append((code, result.correlation))

        # 상관계수가 낮은 순으로 정렬
        candidates.sort(key=lambda x: abs(x[1]))

        return candidates

    def analyze_portfolio_correlation(
        self,
        price_data: Dict[str, pd.Series],
        weights: Dict[str, float] = None
    ) -> Dict:
        """
        포트폴리오 전체 상관관계 분석

        Args:
            price_data: 가격 데이터 딕셔너리
            weights: 포트폴리오 가중치

        Returns:
            분석 결과 딕셔너리
        """
        if len(price_data) < 2:
            return {'error': '최소 2개 종목이 필요합니다'}

        stocks = list(price_data.keys())
        if weights is None:
            weights = {s: 1.0 / len(stocks) for s in stocks}

        # 상관관계 매트릭스
        corr_matrix = self.calculate_correlation_matrix(price_data)

        # 평균 상관계수 계산
        n = len(stocks)
        total_corr = 0
        count = 0

        for i in range(n):
            for j in range(i + 1, n):
                total_corr += corr_matrix.matrix.iloc[i, j]
                count += 1

        avg_correlation = total_corr / count if count > 0 else 0

        # 가장 높은/낮은 상관관계 쌍 찾기
        highest_corr = {'pair': None, 'value': -2}
        lowest_corr = {'pair': None, 'value': 2}

        for i in range(n):
            for j in range(i + 1, n):
                corr_val = corr_matrix.matrix.iloc[i, j]
                if corr_val > highest_corr['value']:
                    highest_corr = {'pair': (stocks[i], stocks[j]), 'value': corr_val}
                if corr_val < lowest_corr['value']:
                    lowest_corr = {'pair': (stocks[i], stocks[j]), 'value': corr_val}

        # 분산 효과 평가
        if avg_correlation < 0.3:
            diversification = "우수"
            diversification_desc = "종목 간 상관관계가 낮아 분산 효과가 큽니다."
        elif avg_correlation < 0.5:
            diversification = "양호"
            diversification_desc = "적정 수준의 분산 효과가 있습니다."
        elif avg_correlation < 0.7:
            diversification = "보통"
            diversification_desc = "상관관계가 다소 높아 분산 효과가 제한적입니다."
        else:
            diversification = "미흡"
            diversification_desc = "높은 상관관계로 분산 효과가 거의 없습니다."

        return {
            'average_correlation': avg_correlation,
            'highest_correlation': highest_corr,
            'lowest_correlation': lowest_corr,
            'diversification_grade': diversification,
            'diversification_description': diversification_desc,
            'correlation_matrix': corr_matrix.matrix,
            'stock_count': n
        }

    def get_rolling_correlation(
        self,
        prices1: pd.Series,
        prices2: pd.Series,
        window: int = 20
    ) -> pd.Series:
        """
        롤링 상관관계 계산

        Args:
            prices1: 첫 번째 가격 시계열
            prices2: 두 번째 가격 시계열
            window: 롤링 윈도우 크기

        Returns:
            롤링 상관관계 시계열
        """
        # 길이 맞춤
        min_len = min(len(prices1), len(prices2))
        prices1 = prices1.tail(min_len)
        prices2 = prices2.tail(min_len)

        returns1 = prices1.pct_change().dropna()
        returns2 = prices2.pct_change().dropna()

        return returns1.rolling(window).corr(returns2)


# 싱글톤 인스턴스
correlation_analyzer = CorrelationAnalyzer()
