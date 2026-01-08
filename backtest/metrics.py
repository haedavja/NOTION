"""
성과 지표 계산 모듈
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PerformanceMetrics:
    """성과 지표"""

    @staticmethod
    def total_return(equity_curve: pd.Series) -> float:
        """총 수익률"""
        return (equity_curve.iloc[-1] / equity_curve.iloc[0] - 1) * 100

    @staticmethod
    def annualized_return(equity_curve: pd.Series, periods_per_year: int = 252) -> float:
        """연환산 수익률"""
        total = equity_curve.iloc[-1] / equity_curve.iloc[0]
        n_periods = len(equity_curve)
        years = n_periods / periods_per_year
        return (total ** (1 / years) - 1) * 100 if years > 0 else 0

    @staticmethod
    def volatility(returns: pd.Series, periods_per_year: int = 252) -> float:
        """연환산 변동성"""
        return returns.std() * np.sqrt(periods_per_year) * 100

    @staticmethod
    def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.04,
                    periods_per_year: int = 252) -> float:
        """샤프 비율"""
        excess_return = returns.mean() * periods_per_year - risk_free_rate
        vol = returns.std() * np.sqrt(periods_per_year)
        return excess_return / vol if vol > 0 else 0

    @staticmethod
    def sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.04,
                     periods_per_year: int = 252) -> float:
        """소르티노 비율"""
        excess_return = returns.mean() * periods_per_year - risk_free_rate
        downside = returns[returns < 0]
        downside_vol = downside.std() * np.sqrt(periods_per_year)
        return excess_return / downside_vol if downside_vol > 0 else 0

    @staticmethod
    def max_drawdown(equity_curve: pd.Series) -> Tuple[float, pd.Timestamp, pd.Timestamp]:
        """최대 낙폭 및 기간"""
        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max

        max_dd = drawdown.min() * 100
        end_idx = drawdown.idxmin()

        # 낙폭 시작점 찾기
        peak_idx = equity_curve[:end_idx].idxmax()

        return max_dd, peak_idx, end_idx

    @staticmethod
    def calmar_ratio(annualized_return: float, max_drawdown: float) -> float:
        """칼마 비율"""
        return annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0

    @staticmethod
    def win_rate(trades: List[Dict]) -> float:
        """승률"""
        if not trades:
            return 0
        wins = sum(1 for t in trades if t.get('pnl', 0) > 0)
        return (wins / len(trades)) * 100

    @staticmethod
    def profit_factor(trades: List[Dict]) -> float:
        """손익비"""
        if not trades:
            return 0
        gains = sum(t['pnl'] for t in trades if t.get('pnl', 0) > 0)
        losses = abs(sum(t['pnl'] for t in trades if t.get('pnl', 0) < 0))
        return gains / losses if losses > 0 else float('inf')

    @staticmethod
    def avg_trade(trades: List[Dict]) -> Dict[str, float]:
        """평균 거래 수익"""
        if not trades:
            return {'avg': 0, 'avg_win': 0, 'avg_loss': 0}

        pnls = [t.get('pnl_pct', 0) for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p <= 0]

        return {
            'avg': np.mean(pnls) if pnls else 0,
            'avg_win': np.mean(wins) if wins else 0,
            'avg_loss': np.mean(losses) if losses else 0,
        }

    @staticmethod
    def max_consecutive(trades: List[Dict]) -> Dict[str, int]:
        """최대 연속 승/패"""
        if not trades:
            return {'wins': 0, 'losses': 0}

        max_wins = max_losses = 0
        current_wins = current_losses = 0

        for trade in trades:
            if trade.get('pnl', 0) > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)

        return {'wins': max_wins, 'losses': max_losses}

    @staticmethod
    def risk_of_ruin(win_rate: float, avg_win: float, avg_loss: float,
                    risk_per_trade: float = 0.02) -> float:
        """파산 확률 (간략화)"""
        if win_rate <= 0 or avg_loss == 0:
            return 1.0

        win_prob = win_rate / 100
        loss_prob = 1 - win_prob

        if avg_win == 0:
            return 1.0

        edge = win_prob * avg_win - loss_prob * abs(avg_loss)

        if edge <= 0:
            return 1.0

        # 간략화된 파산 확률
        q = loss_prob / win_prob if win_prob > 0 else 1
        n = 1 / risk_per_trade  # 파산까지 필요한 연속 손실 수

        if q >= 1:
            return 1.0

        return q ** n

    @staticmethod
    def ulcer_index(equity_curve: pd.Series, period: int = 14) -> float:
        """Ulcer Index (낙폭 기반 리스크 지표)"""
        running_max = equity_curve.rolling(period).max()
        drawdown_pct = ((equity_curve - running_max) / running_max * 100) ** 2
        return np.sqrt(drawdown_pct.mean())

    @staticmethod
    def value_at_risk(returns: pd.Series, confidence: float = 0.95) -> float:
        """Value at Risk"""
        return returns.quantile(1 - confidence) * 100

    @staticmethod
    def expected_shortfall(returns: pd.Series, confidence: float = 0.95) -> float:
        """Expected Shortfall (CVaR)"""
        var = returns.quantile(1 - confidence)
        return returns[returns <= var].mean() * 100

    @classmethod
    def calculate_all(cls, equity_curve: pd.Series,
                     trades: List[Dict],
                     risk_free_rate: float = 0.04) -> Dict:
        """모든 지표 계산"""
        returns = equity_curve.pct_change().dropna()

        total_ret = cls.total_return(equity_curve)
        ann_ret = cls.annualized_return(equity_curve)
        vol = cls.volatility(returns)
        sharpe = cls.sharpe_ratio(returns, risk_free_rate)
        sortino = cls.sortino_ratio(returns, risk_free_rate)

        max_dd, dd_start, dd_end = cls.max_drawdown(equity_curve)
        calmar = cls.calmar_ratio(ann_ret, max_dd)

        win = cls.win_rate(trades)
        pf = cls.profit_factor(trades)
        avg = cls.avg_trade(trades)
        consecutive = cls.max_consecutive(trades)

        var_95 = cls.value_at_risk(returns, 0.95)
        es_95 = cls.expected_shortfall(returns, 0.95)

        return {
            'returns': {
                'total': total_ret,
                'annualized': ann_ret,
            },
            'risk': {
                'volatility': vol,
                'max_drawdown': max_dd,
                'drawdown_start': dd_start,
                'drawdown_end': dd_end,
                'var_95': var_95,
                'expected_shortfall_95': es_95,
            },
            'risk_adjusted': {
                'sharpe_ratio': sharpe,
                'sortino_ratio': sortino,
                'calmar_ratio': calmar,
            },
            'trading': {
                'total_trades': len(trades),
                'win_rate': win,
                'profit_factor': pf,
                'avg_trade': avg['avg'],
                'avg_win': avg['avg_win'],
                'avg_loss': avg['avg_loss'],
                'max_consecutive_wins': consecutive['wins'],
                'max_consecutive_losses': consecutive['losses'],
            },
        }


def compare_strategies(results: List['BacktestResult']) -> pd.DataFrame:
    """여러 전략 비교"""
    data = []

    for result in results:
        data.append({
            '전략': result.strategy_name,
            '총수익률(%)': result.total_return,
            '연환산(%)': result.annualized_return,
            '변동성(%)': result.volatility,
            '최대낙폭(%)': result.max_drawdown,
            '샤프': result.sharpe_ratio,
            '소르티노': result.sortino_ratio,
            '승률(%)': result.win_rate,
            '손익비': result.profit_factor,
            '거래횟수': result.total_trades,
        })

    df = pd.DataFrame(data)
    return df.sort_values('샤프', ascending=False)
