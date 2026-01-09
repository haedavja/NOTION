"""
포트폴리오 최적화
현대 포트폴리오 이론(MPT) 기반 최적화
"""

import numpy as np
import pandas as pd
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from scipy.optimize import minimize
import warnings
import logging

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


@dataclass
class OptimizationResult:
    """최적화 결과"""
    weights: Dict[str, float]
    expected_return: float
    volatility: float
    sharpe_ratio: float
    optimization_type: str
    constraints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EfficientFrontierPoint:
    """효율적 프론티어 포인트"""
    return_: float
    volatility: float
    sharpe_ratio: float
    weights: Dict[str, float]


class PortfolioOptimizer:
    """포트폴리오 최적화기"""

    def __init__(self, risk_free_rate: float = 0.04):
        self.risk_free_rate = risk_free_rate
        self.returns_data: Optional[pd.DataFrame] = None
        self.symbols: List[str] = []
        self.names: Dict[str, str] = {}

    def load_data(self, symbols: List[str], period: str = "2y",
                  names: Dict[str, str] = None) -> bool:
        """주가 데이터 로드"""
        if not YFINANCE_AVAILABLE:
            return False

        self.symbols = symbols
        self.names = names or {s: s for s in symbols}

        try:
            # 데이터 다운로드
            data = yf.download(symbols, period=period, progress=False)['Adj Close']

            if isinstance(data, pd.Series):
                data = data.to_frame(name=symbols[0])

            # 일간 수익률 계산
            self.returns_data = data.pct_change().dropna()

            return len(self.returns_data) > 0

        except Exception as e:
            logger.error(f"데이터 로드 실패: {e}")
            return False

    def calculate_portfolio_metrics(self, weights: np.ndarray) -> Tuple[float, float, float]:
        """포트폴리오 지표 계산"""
        if self.returns_data is None:
            return 0.0, 0.0, 0.0

        # 연간화 수익률
        mean_returns = self.returns_data.mean() * 252
        # 공분산 행렬
        cov_matrix = self.returns_data.cov() * 252

        # 포트폴리오 수익률
        portfolio_return = np.sum(mean_returns * weights)
        # 포트폴리오 변동성
        portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        # 샤프 비율
        sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_volatility

        return portfolio_return, portfolio_volatility, sharpe_ratio

    def _negative_sharpe(self, weights: np.ndarray) -> float:
        """음수 샤프 비율 (최소화용)"""
        _, _, sharpe = self.calculate_portfolio_metrics(weights)
        return -sharpe

    def _portfolio_volatility(self, weights: np.ndarray) -> float:
        """포트폴리오 변동성"""
        _, vol, _ = self.calculate_portfolio_metrics(weights)
        return vol

    def _portfolio_return(self, weights: np.ndarray) -> float:
        """포트폴리오 수익률"""
        ret, _, _ = self.calculate_portfolio_metrics(weights)
        return ret

    def optimize_max_sharpe(self, constraints: Dict = None) -> OptimizationResult:
        """샤프 비율 최대화"""
        if self.returns_data is None:
            raise ValueError("데이터를 먼저 로드하세요")

        n_assets = len(self.symbols)
        init_weights = np.array([1/n_assets] * n_assets)

        # 제약 조건
        bounds = tuple((0, 1) for _ in range(n_assets))
        constraint_list = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]

        # 최소/최대 비중 제약
        if constraints:
            min_weight = constraints.get('min_weight', 0)
            max_weight = constraints.get('max_weight', 1)
            bounds = tuple((min_weight, max_weight) for _ in range(n_assets))

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = minimize(
                self._negative_sharpe,
                init_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraint_list
            )

        optimal_weights = result.x
        ret, vol, sharpe = self.calculate_portfolio_metrics(optimal_weights)

        return OptimizationResult(
            weights={self.symbols[i]: float(optimal_weights[i])
                     for i in range(n_assets)},
            expected_return=ret,
            volatility=vol,
            sharpe_ratio=sharpe,
            optimization_type="max_sharpe",
            constraints=constraints or {}
        )

    def optimize_min_volatility(self, constraints: Dict = None) -> OptimizationResult:
        """최소 변동성"""
        if self.returns_data is None:
            raise ValueError("데이터를 먼저 로드하세요")

        n_assets = len(self.symbols)
        init_weights = np.array([1/n_assets] * n_assets)

        bounds = tuple((0, 1) for _ in range(n_assets))
        constraint_list = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]

        if constraints:
            min_weight = constraints.get('min_weight', 0)
            max_weight = constraints.get('max_weight', 1)
            bounds = tuple((min_weight, max_weight) for _ in range(n_assets))

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = minimize(
                self._portfolio_volatility,
                init_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraint_list
            )

        optimal_weights = result.x
        ret, vol, sharpe = self.calculate_portfolio_metrics(optimal_weights)

        return OptimizationResult(
            weights={self.symbols[i]: float(optimal_weights[i])
                     for i in range(n_assets)},
            expected_return=ret,
            volatility=vol,
            sharpe_ratio=sharpe,
            optimization_type="min_volatility",
            constraints=constraints or {}
        )

    def optimize_target_return(self, target_return: float,
                                constraints: Dict = None) -> OptimizationResult:
        """목표 수익률 달성 (최소 변동성)"""
        if self.returns_data is None:
            raise ValueError("데이터를 먼저 로드하세요")

        n_assets = len(self.symbols)
        init_weights = np.array([1/n_assets] * n_assets)

        bounds = tuple((0, 1) for _ in range(n_assets))
        constraint_list = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
            {'type': 'eq', 'fun': lambda x: self._portfolio_return(x) - target_return}
        ]

        if constraints:
            min_weight = constraints.get('min_weight', 0)
            max_weight = constraints.get('max_weight', 1)
            bounds = tuple((min_weight, max_weight) for _ in range(n_assets))

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = minimize(
                self._portfolio_volatility,
                init_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraint_list
            )

        optimal_weights = result.x
        ret, vol, sharpe = self.calculate_portfolio_metrics(optimal_weights)

        return OptimizationResult(
            weights={self.symbols[i]: float(optimal_weights[i])
                     for i in range(n_assets)},
            expected_return=ret,
            volatility=vol,
            sharpe_ratio=sharpe,
            optimization_type="target_return",
            constraints={'target_return': target_return, **(constraints or {})}
        )

    def calculate_efficient_frontier(self, n_points: int = 50) -> List[EfficientFrontierPoint]:
        """효율적 프론티어 계산"""
        if self.returns_data is None:
            raise ValueError("데이터를 먼저 로드하세요")

        # 최소/최대 수익률 찾기
        min_vol_result = self.optimize_min_volatility()
        max_sharpe_result = self.optimize_max_sharpe()

        mean_returns = self.returns_data.mean() * 252
        min_return = min_vol_result.expected_return
        max_return = mean_returns.max()

        target_returns = np.linspace(min_return, max_return, n_points)

        frontier_points = []

        for target in target_returns:
            try:
                result = self.optimize_target_return(target)
                frontier_points.append(EfficientFrontierPoint(
                    return_=result.expected_return,
                    volatility=result.volatility,
                    sharpe_ratio=result.sharpe_ratio,
                    weights=result.weights
                ))
            except Exception as e:
                logger.debug(f"목표 수익률 {target:.2%} 최적화 실패: {e}")
                continue

        return frontier_points

    def get_asset_statistics(self) -> pd.DataFrame:
        """개별 자산 통계"""
        if self.returns_data is None:
            return pd.DataFrame()

        stats = []
        for symbol in self.symbols:
            returns = self.returns_data[symbol]
            annual_return = returns.mean() * 252
            annual_vol = returns.std() * np.sqrt(252)
            sharpe = (annual_return - self.risk_free_rate) / annual_vol

            stats.append({
                '종목': self.names.get(symbol, symbol),
                '심볼': symbol,
                '연간 수익률': f"{annual_return*100:.2f}%",
                '변동성': f"{annual_vol*100:.2f}%",
                '샤프 비율': f"{sharpe:.2f}"
            })

        return pd.DataFrame(stats)

    def get_correlation_matrix(self) -> pd.DataFrame:
        """상관관계 행렬"""
        if self.returns_data is None:
            return pd.DataFrame()

        corr = self.returns_data.corr()
        corr.index = [self.names.get(s, s) for s in corr.index]
        corr.columns = [self.names.get(s, s) for s in corr.columns]

        return corr

    def monte_carlo_simulation(self, n_simulations: int = 5000) -> Dict[str, Any]:
        """몬테카를로 시뮬레이션"""
        if self.returns_data is None:
            return {}

        n_assets = len(self.symbols)
        results = {
            'returns': [],
            'volatilities': [],
            'sharpe_ratios': [],
            'weights': []
        }

        for _ in range(n_simulations):
            # 랜덤 가중치 생성
            weights = np.random.random(n_assets)
            weights /= np.sum(weights)

            ret, vol, sharpe = self.calculate_portfolio_metrics(weights)

            results['returns'].append(ret)
            results['volatilities'].append(vol)
            results['sharpe_ratios'].append(sharpe)
            results['weights'].append(weights)

        # 최적 포트폴리오 찾기
        max_sharpe_idx = np.argmax(results['sharpe_ratios'])
        min_vol_idx = np.argmin(results['volatilities'])

        results['max_sharpe'] = {
            'return': results['returns'][max_sharpe_idx],
            'volatility': results['volatilities'][max_sharpe_idx],
            'sharpe': results['sharpe_ratios'][max_sharpe_idx],
            'weights': {self.symbols[i]: float(results['weights'][max_sharpe_idx][i])
                        for i in range(n_assets)}
        }

        results['min_volatility'] = {
            'return': results['returns'][min_vol_idx],
            'volatility': results['volatilities'][min_vol_idx],
            'sharpe': results['sharpe_ratios'][min_vol_idx],
            'weights': {self.symbols[i]: float(results['weights'][min_vol_idx][i])
                        for i in range(n_assets)}
        }

        return results

    def get_optimization_summary(self) -> Dict[str, Any]:
        """최적화 요약"""
        max_sharpe = self.optimize_max_sharpe()
        min_vol = self.optimize_min_volatility()
        equal_weights = np.array([1/len(self.symbols)] * len(self.symbols))
        eq_ret, eq_vol, eq_sharpe = self.calculate_portfolio_metrics(equal_weights)

        return {
            'max_sharpe': max_sharpe,
            'min_volatility': min_vol,
            'equal_weight': OptimizationResult(
                weights={s: 1/len(self.symbols) for s in self.symbols},
                expected_return=eq_ret,
                volatility=eq_vol,
                sharpe_ratio=eq_sharpe,
                optimization_type="equal_weight"
            ),
            'asset_stats': self.get_asset_statistics(),
            'correlation': self.get_correlation_matrix()
        }


# 싱글톤 인스턴스
portfolio_optimizer = PortfolioOptimizer()


def optimize_portfolio(symbols: List[str], period: str = "2y",
                        optimization_type: str = "max_sharpe") -> OptimizationResult:
    """포트폴리오 최적화"""
    optimizer = PortfolioOptimizer()
    optimizer.load_data(symbols, period)

    if optimization_type == "max_sharpe":
        return optimizer.optimize_max_sharpe()
    elif optimization_type == "min_volatility":
        return optimizer.optimize_min_volatility()
    else:
        return optimizer.optimize_max_sharpe()
