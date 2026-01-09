"""
벤치마크 비교 분석 모듈
포트폴리오 또는 개별 종목의 성과를 시장 지수와 비교
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class BenchmarkType(Enum):
    """벤치마크 유형"""
    KOSPI = "KOSPI"
    KOSDAQ = "KOSDAQ"
    KOSPI200 = "KOSPI200"
    KRX100 = "KRX100"
    SECTOR = "SECTOR"
    CUSTOM = "CUSTOM"


@dataclass
class BenchmarkInfo:
    """벤치마크 정보"""
    name: str
    type: BenchmarkType
    code: str
    description: str = ""


@dataclass
class PerformanceMetrics:
    """성과 지표"""
    return_1d: Optional[float] = None
    return_1w: Optional[float] = None
    return_1m: Optional[float] = None
    return_3m: Optional[float] = None
    return_6m: Optional[float] = None
    return_ytd: Optional[float] = None
    return_1y: Optional[float] = None
    volatility: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    beta: Optional[float] = None
    alpha: Optional[float] = None


@dataclass
class BenchmarkComparison:
    """벤치마크 비교 결과"""
    target_name: str
    benchmark_name: str
    target_metrics: PerformanceMetrics
    benchmark_metrics: PerformanceMetrics
    relative_performance: Dict[str, float] = field(default_factory=dict)
    outperformance_periods: int = 0
    total_periods: int = 0
    correlation: Optional[float] = None
    analysis_date: datetime = field(default_factory=datetime.now)


# 주요 벤치마크 정의
BENCHMARKS = {
    'KOSPI': BenchmarkInfo('KOSPI 종합', BenchmarkType.KOSPI, '1001', '한국 대표 주가지수'),
    'KOSDAQ': BenchmarkInfo('KOSDAQ 종합', BenchmarkType.KOSDAQ, '2001', '코스닥 시장 지수'),
    'KOSPI200': BenchmarkInfo('KOSPI 200', BenchmarkType.KOSPI200, '1028', '대형주 200종목'),
    'KRX100': BenchmarkInfo('KRX 100', BenchmarkType.KRX100, '5042', 'KOSPI+KOSDAQ 대표 100종목'),
}

# 섹터 ETF 벤치마크
SECTOR_BENCHMARKS = {
    '반도체': BenchmarkInfo('KODEX 반도체', BenchmarkType.SECTOR, '091160', '반도체 섹터'),
    '2차전지': BenchmarkInfo('KODEX 2차전지', BenchmarkType.SECTOR, '305720', '2차전지 섹터'),
    '바이오': BenchmarkInfo('KODEX 바이오', BenchmarkType.SECTOR, '244580', '바이오 섹터'),
    '은행': BenchmarkInfo('KODEX 은행', BenchmarkType.SECTOR, '091170', '은행 섹터'),
    'IT': BenchmarkInfo('KODEX IT', BenchmarkType.SECTOR, '098560', 'IT 섹터'),
}


class BenchmarkAnalyzer:
    """벤치마크 분석기"""

    def __init__(self):
        self.benchmarks = BENCHMARKS
        self.sector_benchmarks = SECTOR_BENCHMARKS
        self.risk_free_rate = 0.035  # 연간 무위험 수익률 (3.5%)

    def calculate_performance_metrics(
        self,
        prices: pd.Series,
        benchmark_prices: pd.Series = None
    ) -> PerformanceMetrics:
        """
        성과 지표 계산

        Args:
            prices: 가격 시계열
            benchmark_prices: 벤치마크 가격 (베타/알파 계산용)

        Returns:
            PerformanceMetrics
        """
        if prices is None or len(prices) < 2:
            return PerformanceMetrics()

        metrics = PerformanceMetrics()

        try:
            # 수익률 계산
            current_price = prices.iloc[-1]

            # 1일 수익률
            if len(prices) >= 2:
                metrics.return_1d = (current_price / prices.iloc[-2] - 1) * 100

            # 1주 수익률
            if len(prices) >= 6:
                metrics.return_1w = (current_price / prices.iloc[-6] - 1) * 100

            # 1개월 수익률 (약 22 거래일)
            if len(prices) >= 22:
                metrics.return_1m = (current_price / prices.iloc[-22] - 1) * 100

            # 3개월 수익률
            if len(prices) >= 66:
                metrics.return_3m = (current_price / prices.iloc[-66] - 1) * 100

            # 6개월 수익률
            if len(prices) >= 132:
                metrics.return_6m = (current_price / prices.iloc[-132] - 1) * 100

            # 1년 수익률
            if len(prices) >= 252:
                metrics.return_1y = (current_price / prices.iloc[-252] - 1) * 100

            # 변동성 (연간화)
            daily_returns = prices.pct_change().dropna()
            if len(daily_returns) >= 20:
                metrics.volatility = daily_returns.std() * np.sqrt(252) * 100

            # 샤프 비율
            if metrics.volatility and metrics.volatility > 0 and len(prices) >= 252:
                annual_return = metrics.return_1y or 0
                metrics.sharpe_ratio = (annual_return - self.risk_free_rate * 100) / metrics.volatility

            # 최대 낙폭
            rolling_max = prices.expanding().max()
            drawdowns = (prices - rolling_max) / rolling_max
            metrics.max_drawdown = drawdowns.min() * 100

            # 베타/알파 (벤치마크 대비)
            if benchmark_prices is not None and len(benchmark_prices) >= len(prices):
                aligned_benchmark = benchmark_prices.iloc[-len(prices):]
                target_returns = prices.pct_change().dropna()
                benchmark_returns = aligned_benchmark.pct_change().dropna()

                if len(target_returns) >= 20 and len(benchmark_returns) >= 20:
                    # 동일 길이로 맞춤
                    min_len = min(len(target_returns), len(benchmark_returns))
                    target_returns = target_returns.iloc[-min_len:]
                    benchmark_returns = benchmark_returns.iloc[-min_len:]

                    # 베타 계산
                    covariance = np.cov(target_returns, benchmark_returns)[0, 1]
                    benchmark_variance = np.var(benchmark_returns)
                    if benchmark_variance > 0:
                        metrics.beta = covariance / benchmark_variance

                    # 알파 계산 (CAPM 기반)
                    if metrics.beta and metrics.return_1y is not None:
                        benchmark_return = (aligned_benchmark.iloc[-1] / aligned_benchmark.iloc[0] - 1) * 100
                        expected_return = self.risk_free_rate * 100 + metrics.beta * (benchmark_return - self.risk_free_rate * 100)
                        metrics.alpha = metrics.return_1y - expected_return

        except Exception as e:
            logger.warning(f"성과 지표 계산 오류: {e}")

        return metrics

    def compare_with_benchmark(
        self,
        target_name: str,
        target_prices: pd.Series,
        benchmark_key: str = 'KOSPI',
        benchmark_prices: pd.Series = None
    ) -> BenchmarkComparison:
        """
        벤치마크와 비교

        Args:
            target_name: 대상 이름 (종목명 또는 포트폴리오)
            target_prices: 대상 가격 시계열
            benchmark_key: 벤치마크 키 (KOSPI, KOSDAQ 등)
            benchmark_prices: 벤치마크 가격 시계열 (없으면 조회)

        Returns:
            BenchmarkComparison
        """
        benchmark_info = self.benchmarks.get(benchmark_key, BENCHMARKS['KOSPI'])

        # 벤치마크 데이터가 없으면 샘플 생성
        if benchmark_prices is None:
            benchmark_prices = self._generate_sample_benchmark(len(target_prices))

        # 성과 지표 계산
        target_metrics = self.calculate_performance_metrics(target_prices, benchmark_prices)
        benchmark_metrics = self.calculate_performance_metrics(benchmark_prices)

        # 상대 성과 계산
        relative = {}
        periods = ['return_1d', 'return_1w', 'return_1m', 'return_3m', 'return_6m', 'return_1y']

        for period in periods:
            target_val = getattr(target_metrics, period)
            bench_val = getattr(benchmark_metrics, period)
            if target_val is not None and bench_val is not None:
                relative[period] = target_val - bench_val

        # 초과 성과 기간 계산
        outperform_count = 0
        total_count = 0

        if len(target_prices) >= 22:
            target_monthly = target_prices.resample('ME').last().pct_change().dropna()
            bench_monthly = benchmark_prices.iloc[-len(target_prices):].resample('ME').last().pct_change().dropna()

            min_len = min(len(target_monthly), len(bench_monthly))
            if min_len > 0:
                target_monthly = target_monthly.iloc[-min_len:]
                bench_monthly = bench_monthly.iloc[-min_len:]

                total_count = min_len
                outperform_count = (target_monthly > bench_monthly).sum()

        # 상관관계 계산
        correlation = None
        if len(target_prices) >= 20:
            target_returns = target_prices.pct_change().dropna()
            bench_returns = benchmark_prices.iloc[-len(target_prices):].pct_change().dropna()
            min_len = min(len(target_returns), len(bench_returns))
            if min_len >= 20:
                correlation = target_returns.iloc[-min_len:].corr(bench_returns.iloc[-min_len:])

        return BenchmarkComparison(
            target_name=target_name,
            benchmark_name=benchmark_info.name,
            target_metrics=target_metrics,
            benchmark_metrics=benchmark_metrics,
            relative_performance=relative,
            outperformance_periods=int(outperform_count),
            total_periods=total_count,
            correlation=correlation
        )

    def _generate_sample_benchmark(self, length: int) -> pd.Series:
        """샘플 벤치마크 데이터 생성"""
        np.random.seed(42)
        dates = pd.date_range(end=datetime.now(), periods=length, freq='B')
        returns = np.random.randn(length) * 0.01  # 일간 1% 변동성
        prices = 2500 * np.exp(np.cumsum(returns))  # KOSPI 기준
        return pd.Series(prices, index=dates)

    def get_benchmark_info(self, key: str) -> Optional[BenchmarkInfo]:
        """벤치마크 정보 조회"""
        if key in self.benchmarks:
            return self.benchmarks[key]
        if key in self.sector_benchmarks:
            return self.sector_benchmarks[key]
        return None

    def list_benchmarks(self) -> List[Dict]:
        """사용 가능한 벤치마크 목록"""
        result = []

        for key, info in self.benchmarks.items():
            result.append({
                'key': key,
                'name': info.name,
                'type': info.type.value,
                'description': info.description
            })

        for key, info in self.sector_benchmarks.items():
            result.append({
                'key': key,
                'name': info.name,
                'type': 'SECTOR',
                'description': info.description
            })

        return result

    def analyze_multiple_benchmarks(
        self,
        target_name: str,
        target_prices: pd.Series,
        benchmark_keys: List[str] = None
    ) -> List[BenchmarkComparison]:
        """
        여러 벤치마크와 동시 비교

        Args:
            target_name: 대상 이름
            target_prices: 대상 가격 시계열
            benchmark_keys: 비교할 벤치마크 키 목록

        Returns:
            비교 결과 리스트
        """
        if benchmark_keys is None:
            benchmark_keys = ['KOSPI', 'KOSDAQ', 'KOSPI200']

        results = []
        for key in benchmark_keys:
            comparison = self.compare_with_benchmark(target_name, target_prices, key)
            results.append(comparison)

        return results

    def get_performance_summary(self, comparison: BenchmarkComparison) -> str:
        """성과 요약 텍스트 생성"""
        target = comparison.target_metrics
        bench = comparison.benchmark_metrics
        rel = comparison.relative_performance

        summary_lines = []
        summary_lines.append(f"**{comparison.target_name}** vs **{comparison.benchmark_name}**")
        summary_lines.append("")

        # 수익률 비교
        if target.return_1m is not None:
            diff = rel.get('return_1m', 0)
            status = "초과" if diff > 0 else "미달"
            summary_lines.append(f"1개월 수익률: {target.return_1m:+.2f}% ({status} {abs(diff):.2f}%p)")

        if target.return_3m is not None:
            diff = rel.get('return_3m', 0)
            status = "초과" if diff > 0 else "미달"
            summary_lines.append(f"3개월 수익률: {target.return_3m:+.2f}% ({status} {abs(diff):.2f}%p)")

        if target.return_1y is not None:
            diff = rel.get('return_1y', 0)
            status = "초과" if diff > 0 else "미달"
            summary_lines.append(f"1년 수익률: {target.return_1y:+.2f}% ({status} {abs(diff):.2f}%p)")

        # 위험 지표
        summary_lines.append("")
        if target.volatility is not None:
            summary_lines.append(f"변동성: {target.volatility:.1f}%")
        if target.max_drawdown is not None:
            summary_lines.append(f"최대 낙폭: {target.max_drawdown:.1f}%")
        if target.sharpe_ratio is not None:
            summary_lines.append(f"샤프 비율: {target.sharpe_ratio:.2f}")
        if target.beta is not None:
            summary_lines.append(f"베타: {target.beta:.2f}")
        if target.alpha is not None:
            summary_lines.append(f"알파: {target.alpha:+.2f}%")

        # 초과 성과
        if comparison.total_periods > 0:
            win_rate = comparison.outperformance_periods / comparison.total_periods * 100
            summary_lines.append("")
            summary_lines.append(f"초과 성과 비율: {win_rate:.1f}% ({comparison.outperformance_periods}/{comparison.total_periods}개월)")

        # 상관관계
        if comparison.correlation is not None:
            summary_lines.append(f"벤치마크 상관관계: {comparison.correlation:.2f}")

        return "\n".join(summary_lines)


# 싱글톤 인스턴스
benchmark_analyzer = BenchmarkAnalyzer()
