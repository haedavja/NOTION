"""
포트폴리오 분석 모듈
리스크, 리턴, 상관관계, 최적화 분석
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

from .portfolio import Portfolio, Position


@dataclass
class RiskMetrics:
    """리스크 지표"""
    volatility: float               # 연율화 변동성
    beta: float                     # 시장 베타
    var_95: float                   # 95% VaR (Value at Risk)
    var_99: float                   # 99% VaR
    max_drawdown: float             # 최대 낙폭
    sharpe_ratio: float             # 샤프 비율
    sortino_ratio: float            # 소르티노 비율
    calmar_ratio: float             # 칼마 비율


@dataclass
class ReturnMetrics:
    """수익률 지표"""
    total_return: float             # 총 수익률
    annualized_return: float        # 연율화 수익률
    ytd_return: float               # 연초대비 수익률
    monthly_return: float           # 월간 수익률
    best_month: float               # 최고 월간 수익
    worst_month: float              # 최저 월간 수익
    win_rate: float                 # 수익 월 비율


class PortfolioAnalyzer:
    """포트폴리오 분석 클래스"""

    BENCHMARK = '^GSPC'  # S&P 500
    RISK_FREE_RATE = 0.04  # 4% 연율

    def __init__(self, portfolio: Portfolio):
        """
        초기화

        Args:
            portfolio: 분석할 포트폴리오
        """
        self.portfolio = portfolio
        self.price_history: Optional[pd.DataFrame] = None
        self.returns: Optional[pd.DataFrame] = None
        self.benchmark_returns: Optional[pd.Series] = None

    def fetch_historical_data(self, period: str = '1y') -> pd.DataFrame:
        """과거 가격 데이터 조회"""
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance가 필요합니다.")

        symbols = [p.symbol for p in self.portfolio.positions]
        if not symbols:
            return pd.DataFrame()

        # 포트폴리오 종목 데이터
        data = yf.download(symbols, period=period, progress=False)['Close']

        if len(symbols) == 1:
            data = data.to_frame(name=symbols[0])

        # 벤치마크 데이터
        benchmark = yf.download(self.BENCHMARK, period=period, progress=False)['Close']

        self.price_history = data
        self.benchmark_returns = benchmark.pct_change()

        # 수익률 계산
        self.returns = data.pct_change()

        return data

    def calculate_portfolio_returns(self) -> pd.Series:
        """
        포트폴리오 가중 수익률 계산

        Returns:
            포트폴리오 일간 수익률
        """
        if self.returns is None:
            self.fetch_historical_data()

        # 가중치 추출
        weights = {}
        for p in self.portfolio.positions:
            weights[p.symbol] = p.weight / 100 if p.weight else 0

        # 가중 수익률
        portfolio_returns = pd.Series(0.0, index=self.returns.index)

        for symbol in self.returns.columns:
            if symbol in weights:
                portfolio_returns += self.returns[symbol].fillna(0) * weights[symbol]

        return portfolio_returns

    def calculate_risk_metrics(self) -> RiskMetrics:
        """리스크 지표 계산"""
        if self.returns is None:
            self.fetch_historical_data()

        portfolio_returns = self.calculate_portfolio_returns()

        # 변동성 (연율화)
        volatility = portfolio_returns.std() * np.sqrt(252) * 100

        # 베타
        if self.benchmark_returns is not None:
            aligned = pd.concat([portfolio_returns, self.benchmark_returns], axis=1).dropna()
            if len(aligned) > 20:
                covariance = aligned.cov().iloc[0, 1]
                variance = aligned.iloc[:, 1].var()
                beta = covariance / variance if variance > 0 else 1.0
            else:
                beta = 1.0
        else:
            beta = 1.0

        # VaR (Value at Risk)
        var_95 = portfolio_returns.quantile(0.05) * 100
        var_99 = portfolio_returns.quantile(0.01) * 100

        # 최대 낙폭 (Maximum Drawdown)
        cumulative = (1 + portfolio_returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min() * 100

        # 샤프 비율
        excess_return = portfolio_returns.mean() * 252 - self.RISK_FREE_RATE
        sharpe_ratio = excess_return / (portfolio_returns.std() * np.sqrt(252)) if portfolio_returns.std() > 0 else 0

        # 소르티노 비율 (하방 변동성만 고려)
        downside_returns = portfolio_returns[portfolio_returns < 0]
        downside_std = downside_returns.std() * np.sqrt(252)
        sortino_ratio = excess_return / downside_std if downside_std > 0 else 0

        # 칼마 비율
        annualized_return = portfolio_returns.mean() * 252 * 100
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0

        return RiskMetrics(
            volatility=volatility,
            beta=beta,
            var_95=var_95,
            var_99=var_99,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
        )

    def calculate_return_metrics(self) -> ReturnMetrics:
        """수익률 지표 계산"""
        if self.returns is None:
            self.fetch_historical_data()

        portfolio_returns = self.calculate_portfolio_returns()

        # 총 수익률
        total_return = ((1 + portfolio_returns).prod() - 1) * 100

        # 연율화 수익률
        days = len(portfolio_returns)
        annualized_return = ((1 + total_return/100) ** (252/days) - 1) * 100 if days > 0 else 0

        # 월간 수익률
        monthly_returns = portfolio_returns.resample('M').apply(lambda x: (1 + x).prod() - 1)
        monthly_return = monthly_returns.iloc[-1] * 100 if len(monthly_returns) > 0 else 0

        # 연초대비 (YTD)
        current_year = datetime.now().year
        ytd_returns = portfolio_returns[portfolio_returns.index.year == current_year]
        ytd_return = ((1 + ytd_returns).prod() - 1) * 100 if len(ytd_returns) > 0 else 0

        # 최고/최저 월
        best_month = monthly_returns.max() * 100 if len(monthly_returns) > 0 else 0
        worst_month = monthly_returns.min() * 100 if len(monthly_returns) > 0 else 0

        # 수익 월 비율
        win_rate = (monthly_returns > 0).mean() * 100 if len(monthly_returns) > 0 else 50

        return ReturnMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            ytd_return=ytd_return,
            monthly_return=monthly_return,
            best_month=best_month,
            worst_month=worst_month,
            win_rate=win_rate,
        )

    def calculate_correlation_matrix(self) -> pd.DataFrame:
        """종목 간 상관관계 행렬"""
        if self.returns is None:
            self.fetch_historical_data()

        return self.returns.corr()

    def calculate_diversification_ratio(self) -> float:
        """
        분산 비율 계산

        개별 자산의 가중 평균 변동성 / 포트폴리오 변동성
        높을수록 분산 효과가 큰 것
        """
        if self.returns is None:
            self.fetch_historical_data()

        # 개별 변동성
        individual_vols = self.returns.std() * np.sqrt(252)

        # 가중치
        weights = {}
        for p in self.portfolio.positions:
            weights[p.symbol] = p.weight / 100 if p.weight else 0

        # 가중 평균 변동성
        weighted_avg_vol = sum(
            individual_vols.get(symbol, 0) * weight
            for symbol, weight in weights.items()
        )

        # 포트폴리오 변동성
        portfolio_returns = self.calculate_portfolio_returns()
        portfolio_vol = portfolio_returns.std() * np.sqrt(252)

        return weighted_avg_vol / portfolio_vol if portfolio_vol > 0 else 1

    def analyze_concentration(self) -> Dict:
        """집중도 분석"""
        weights = [p.weight for p in self.portfolio.positions if p.weight]

        if not weights:
            return {'error': 'No weights available'}

        weights = np.array(weights) / 100

        # HHI (Herfindahl-Hirschman Index)
        hhi = np.sum(weights ** 2)

        # 상위 3개 종목 비중
        sorted_weights = sorted(weights, reverse=True)
        top_3_concentration = sum(sorted_weights[:3]) * 100

        # 상위 1개 종목 비중
        top_1_concentration = sorted_weights[0] * 100 if sorted_weights else 0

        # 효과적 종목 수 (1/HHI)
        effective_n = 1 / hhi if hhi > 0 else len(weights)

        return {
            'hhi': hhi,
            'effective_n': effective_n,
            'top_1_concentration': top_1_concentration,
            'top_3_concentration': top_3_concentration,
            'total_positions': len(weights),
            'concentration_level': 'High' if top_3_concentration > 70 else ('Medium' if top_3_concentration > 50 else 'Low'),
        }

    def analyze_sector_exposure(self) -> Dict:
        """섹터 노출도 분석"""
        if not YFINANCE_AVAILABLE:
            return {}

        sector_weights = {}

        for p in self.portfolio.positions:
            try:
                ticker = yf.Ticker(p.symbol)
                sector = ticker.info.get('sector', 'Unknown')
                weight = p.weight or 0
                sector_weights[sector] = sector_weights.get(sector, 0) + weight
            except Exception:
                sector_weights['Unknown'] = sector_weights.get('Unknown', 0) + (p.weight or 0)

        return sector_weights

    def stress_test(self, scenarios: Optional[Dict[str, float]] = None) -> Dict:
        """
        스트레스 테스트

        Args:
            scenarios: 시나리오별 시장 변동률

        Returns:
            시나리오별 포트폴리오 영향
        """
        if scenarios is None:
            scenarios = {
                '시장 급락 (-20%)': -0.20,
                '조정 (-10%)': -0.10,
                '약세 (-5%)': -0.05,
                '강세 (+10%)': 0.10,
                '급등 (+20%)': 0.20,
            }

        risk_metrics = self.calculate_risk_metrics()
        beta = risk_metrics.beta

        results = {}
        for scenario_name, market_change in scenarios.items():
            # 베타를 적용한 포트폴리오 변화 추정
            portfolio_change = market_change * beta
            portfolio_value = self.portfolio.total_market_value
            impact = portfolio_value * portfolio_change

            results[scenario_name] = {
                'market_change': market_change * 100,
                'portfolio_change': portfolio_change * 100,
                'value_impact': impact,
                'new_value': portfolio_value + impact,
            }

        return results

    def calculate_expected_return_probability(self, target_return: float,
                                              time_horizon_days: int = 252) -> Dict:
        """
        목표 수익률 달성 확률 계산

        Args:
            target_return: 목표 수익률 (%)
            time_horizon_days: 투자 기간 (일)

        Returns:
            확률 분석 결과
        """
        if self.returns is None:
            self.fetch_historical_data()

        portfolio_returns = self.calculate_portfolio_returns()

        # 일간 수익률 통계
        daily_mean = portfolio_returns.mean()
        daily_std = portfolio_returns.std()

        # 기간 수익률 분포 (정규분포 가정)
        period_mean = daily_mean * time_horizon_days
        period_std = daily_std * np.sqrt(time_horizon_days)

        # 목표 수익률 달성 확률 (z-score)
        target_decimal = target_return / 100
        z_score = (target_decimal - period_mean) / period_std if period_std > 0 else 0

        # 표준정규분포에서 확률
        from scipy.stats import norm
        probability = 1 - norm.cdf(z_score)

        # 기대 수익률 범위 (95% 신뢰구간)
        lower_bound = (period_mean - 1.96 * period_std) * 100
        upper_bound = (period_mean + 1.96 * period_std) * 100

        return {
            'target_return': target_return,
            'time_horizon_days': time_horizon_days,
            'probability': probability * 100,
            'expected_return': period_mean * 100,
            'expected_return_std': period_std * 100,
            'confidence_interval_95': {
                'lower': lower_bound,
                'upper': upper_bound,
            },
        }

    def get_position_analysis(self, symbol: str) -> Dict:
        """개별 포지션 상세 분석"""
        position = self.portfolio.get_position(symbol)
        if not position:
            return {'error': f'{symbol} not found'}

        if self.returns is None:
            self.fetch_historical_data()

        if symbol not in self.returns.columns:
            return {'error': f'No data for {symbol}'}

        returns = self.returns[symbol].dropna()

        # 기본 통계
        volatility = returns.std() * np.sqrt(252) * 100
        total_return = ((1 + returns).prod() - 1) * 100

        # 시장 대비 성과
        if self.benchmark_returns is not None:
            aligned = pd.concat([returns, self.benchmark_returns], axis=1).dropna()
            if len(aligned) > 0:
                position_return = (1 + aligned.iloc[:, 0]).prod() - 1
                benchmark_return = (1 + aligned.iloc[:, 1]).prod() - 1
                alpha = (position_return - benchmark_return) * 100
            else:
                alpha = 0
        else:
            alpha = 0

        # 승률
        win_rate = (returns > 0).mean() * 100

        # 최대 연속 상승/하락
        pos_streak = neg_streak = max_pos = max_neg = 0
        for r in returns:
            if r > 0:
                pos_streak += 1
                neg_streak = 0
                max_pos = max(max_pos, pos_streak)
            elif r < 0:
                neg_streak += 1
                pos_streak = 0
                max_neg = max(max_neg, neg_streak)

        return {
            'symbol': symbol,
            'name': position.name,
            'weight': position.weight,
            'unrealized_pnl': position.unrealized_pnl,
            'unrealized_pnl_pct': position.unrealized_pnl_pct,
            'volatility': volatility,
            'total_return': total_return,
            'alpha': alpha,
            'win_rate': win_rate,
            'max_winning_streak': max_pos,
            'max_losing_streak': max_neg,
            'thesis': position.thesis_description,
            'thesis_type': position.thesis_type.value,
            'target_price': position.target_price,
            'stop_loss': position.stop_loss,
        }

    def get_full_analysis(self) -> Dict:
        """전체 포트폴리오 분석"""
        if self.returns is None:
            self.fetch_historical_data()

        risk_metrics = self.calculate_risk_metrics()
        return_metrics = self.calculate_return_metrics()
        concentration = self.analyze_concentration()
        diversification = self.calculate_diversification_ratio()
        correlation = self.calculate_correlation_matrix()
        stress_test = self.stress_test()
        sector_exposure = self.analyze_sector_exposure()

        return {
            'summary': {
                'total_value': self.portfolio.total_market_value,
                'total_cost': self.portfolio.total_cost_basis,
                'total_pnl': self.portfolio.total_unrealized_pnl,
                'total_pnl_pct': self.portfolio.total_unrealized_pnl_pct,
                'position_count': len(self.portfolio.positions),
            },
            'risk_metrics': {
                'volatility': risk_metrics.volatility,
                'beta': risk_metrics.beta,
                'var_95': risk_metrics.var_95,
                'var_99': risk_metrics.var_99,
                'max_drawdown': risk_metrics.max_drawdown,
                'sharpe_ratio': risk_metrics.sharpe_ratio,
                'sortino_ratio': risk_metrics.sortino_ratio,
                'calmar_ratio': risk_metrics.calmar_ratio,
            },
            'return_metrics': {
                'total_return': return_metrics.total_return,
                'annualized_return': return_metrics.annualized_return,
                'ytd_return': return_metrics.ytd_return,
                'monthly_return': return_metrics.monthly_return,
                'best_month': return_metrics.best_month,
                'worst_month': return_metrics.worst_month,
                'win_rate': return_metrics.win_rate,
            },
            'concentration': concentration,
            'diversification_ratio': diversification,
            'correlation_matrix': correlation.to_dict(),
            'stress_test': stress_test,
            'sector_exposure': sector_exposure,
        }

    def get_recommendations(self) -> List[str]:
        """포트폴리오 개선 권고사항"""
        recommendations = []

        # 분석 실행
        risk_metrics = self.calculate_risk_metrics()
        concentration = self.analyze_concentration()
        diversification = self.calculate_diversification_ratio()

        # 변동성 체크
        if risk_metrics.volatility > 25:
            recommendations.append(f"포트폴리오 변동성이 높습니다 ({risk_metrics.volatility:.1f}%). 채권이나 저변동성 자산 추가를 고려하세요.")

        # 샤프 비율 체크
        if risk_metrics.sharpe_ratio < 0.5:
            recommendations.append(f"위험 대비 수익이 낮습니다 (Sharpe: {risk_metrics.sharpe_ratio:.2f}). 포트폴리오 재조정을 고려하세요.")

        # 집중도 체크
        if concentration.get('top_1_concentration', 0) > 30:
            recommendations.append(f"단일 종목 비중이 높습니다 ({concentration['top_1_concentration']:.1f}%). 분산투자를 고려하세요.")

        if concentration.get('top_3_concentration', 0) > 70:
            recommendations.append("상위 3개 종목 비중이 70%를 초과합니다. 집중 리스크가 높습니다.")

        # 분산 효과 체크
        if diversification < 1.1:
            recommendations.append("분산 효과가 낮습니다. 상관관계가 낮은 자산 추가를 고려하세요.")

        # 현금 비중 체크
        cash_weight = getattr(self.portfolio, 'cash_weight', 0)
        if cash_weight > 20:
            recommendations.append(f"현금 비중이 높습니다 ({cash_weight:.1f}%). 투자 기회를 놓치고 있을 수 있습니다.")
        elif cash_weight < 3:
            recommendations.append("현금 비중이 낮습니다. 긴급 상황 대비 최소 3-5% 현금 보유를 권장합니다.")

        if not recommendations:
            recommendations.append("포트폴리오가 전반적으로 양호합니다. 정기적인 리밸런싱을 유지하세요.")

        return recommendations
