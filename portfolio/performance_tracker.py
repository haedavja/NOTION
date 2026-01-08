"""
투자 성과 추적 모듈
시간별 수익률, 실현/미실현 손익, 매매 기록
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
import pandas as pd


@dataclass
class Trade:
    """매매 기록"""
    trade_id: str
    symbol: str
    trade_type: str  # 'BUY', 'SELL'
    quantity: float
    price: float
    timestamp: datetime
    fee: float = 0.0
    notes: str = ""

    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Trade':
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class PerformanceSnapshot:
    """특정 시점의 성과 스냅샷"""
    timestamp: datetime
    total_value: float  # 총 평가액
    total_cost: float   # 총 투자금
    cash: float         # 현금
    unrealized_pnl: float  # 미실현 손익
    realized_pnl: float    # 실현 손익
    daily_return: float    # 일간 수익률 %
    total_return: float    # 총 수익률 %

    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat()
        }


class PerformanceTracker:
    """투자 성과 추적기"""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.expanduser("~"), ".notion_portfolio")

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.trades_file = self.data_dir / "trades.json"
        self.snapshots_file = self.data_dir / "snapshots.json"

        self._trades: List[Trade] = []
        self._snapshots: List[PerformanceSnapshot] = []
        self._realized_pnl: Dict[str, float] = {}  # 종목별 실현 손익

        self._load_data()

    def _load_data(self):
        """데이터 로드"""
        try:
            if self.trades_file.exists():
                with open(self.trades_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._trades = [Trade.from_dict(t) for t in data.get('trades', [])]
                    self._realized_pnl = data.get('realized_pnl', {})

            if self.snapshots_file.exists():
                with open(self.snapshots_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._snapshots = []
                    for s in data:
                        s['timestamp'] = datetime.fromisoformat(s['timestamp'])
                        self._snapshots.append(PerformanceSnapshot(**s))
        except Exception as e:
            print(f"Performance data load error: {e}")

    def _save_data(self):
        """데이터 저장"""
        try:
            with open(self.trades_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'trades': [t.to_dict() for t in self._trades],
                    'realized_pnl': self._realized_pnl
                }, f, ensure_ascii=False, indent=2)

            with open(self.snapshots_file, 'w', encoding='utf-8') as f:
                json.dump([s.to_dict() for s in self._snapshots], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Performance data save error: {e}")

    # ===== 매매 기록 =====

    def record_buy(self, symbol: str, quantity: float, price: float,
                   fee: float = 0.0, notes: str = "") -> Trade:
        """매수 기록"""
        trade = Trade(
            trade_id=f"BUY_{symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            symbol=symbol,
            trade_type='BUY',
            quantity=quantity,
            price=price,
            timestamp=datetime.now(),
            fee=fee,
            notes=notes
        )
        self._trades.append(trade)
        self._save_data()
        return trade

    def record_sell(self, symbol: str, quantity: float, price: float,
                    avg_cost: float, fee: float = 0.0, notes: str = "") -> Tuple[Trade, float]:
        """매도 기록 및 실현 손익 계산"""
        trade = Trade(
            trade_id=f"SELL_{symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            symbol=symbol,
            trade_type='SELL',
            quantity=quantity,
            price=price,
            timestamp=datetime.now(),
            fee=fee,
            notes=notes
        )
        self._trades.append(trade)

        # 실현 손익 계산
        realized = (price - avg_cost) * quantity - fee
        self._realized_pnl[symbol] = self._realized_pnl.get(symbol, 0) + realized

        self._save_data()
        return trade, realized

    def get_trades(self, symbol: str = None, days: int = None) -> List[Trade]:
        """매매 기록 조회"""
        trades = self._trades

        if symbol:
            trades = [t for t in trades if t.symbol == symbol]

        if days:
            cutoff = datetime.now() - timedelta(days=days)
            trades = [t for t in trades if t.timestamp >= cutoff]

        return sorted(trades, key=lambda t: t.timestamp, reverse=True)

    # ===== 성과 스냅샷 =====

    def record_snapshot(self, portfolio) -> PerformanceSnapshot:
        """현재 성과 스냅샷 기록"""
        total_value = sum(p.current_price * p.quantity for p in portfolio.positions)
        total_cost = sum(p.avg_cost * p.quantity for p in portfolio.positions)
        unrealized_pnl = total_value - total_cost
        realized_pnl = sum(self._realized_pnl.values())

        # 이전 스냅샷 대비 일간 수익률
        daily_return = 0.0
        if self._snapshots:
            prev = self._snapshots[-1]
            if prev.total_value > 0:
                daily_return = (total_value - prev.total_value) / prev.total_value * 100

        # 총 수익률
        total_return = 0.0
        if total_cost > 0:
            total_return = (unrealized_pnl + realized_pnl) / total_cost * 100

        snapshot = PerformanceSnapshot(
            timestamp=datetime.now(),
            total_value=total_value,
            total_cost=total_cost,
            cash=0,  # 추후 현금 관리 추가
            unrealized_pnl=unrealized_pnl,
            realized_pnl=realized_pnl,
            daily_return=daily_return,
            total_return=total_return
        )

        self._snapshots.append(snapshot)
        self._save_data()
        return snapshot

    def get_snapshots(self, days: int = 30) -> List[PerformanceSnapshot]:
        """스냅샷 히스토리 조회"""
        cutoff = datetime.now() - timedelta(days=days)
        return [s for s in self._snapshots if s.timestamp >= cutoff]

    def get_performance_df(self, days: int = 30) -> pd.DataFrame:
        """성과 데이터프레임"""
        snapshots = self.get_snapshots(days)
        if not snapshots:
            return pd.DataFrame()

        return pd.DataFrame([{
            '날짜': s.timestamp,
            '총 평가액': s.total_value,
            '투자금': s.total_cost,
            '미실현 손익': s.unrealized_pnl,
            '실현 손익': s.realized_pnl,
            '일간 수익률': s.daily_return,
            '총 수익률': s.total_return,
        } for s in snapshots])

    # ===== 통계 =====

    def get_summary(self) -> Dict:
        """성과 요약"""
        if not self._snapshots:
            return {'status': 'no_data'}

        latest = self._snapshots[-1]
        realized = sum(self._realized_pnl.values())

        # 최대 손실 (MDD)
        values = [s.total_value for s in self._snapshots]
        peak = values[0]
        max_drawdown = 0
        for v in values:
            if v > peak:
                peak = v
            drawdown = (peak - v) / peak * 100 if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)

        # 승률 계산
        sells = [t for t in self._trades if t.trade_type == 'SELL']
        winning = len([t for t in sells if self._realized_pnl.get(t.symbol, 0) > 0])
        win_rate = (winning / len(sells) * 100) if sells else 0

        return {
            'total_value': latest.total_value,
            'total_cost': latest.total_cost,
            'unrealized_pnl': latest.unrealized_pnl,
            'realized_pnl': realized,
            'total_pnl': latest.unrealized_pnl + realized,
            'total_return': latest.total_return,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'total_trades': len(self._trades),
            'last_updated': latest.timestamp.isoformat()
        }

    def get_symbol_performance(self, symbol: str) -> Dict:
        """종목별 성과"""
        trades = [t for t in self._trades if t.symbol == symbol]
        realized = self._realized_pnl.get(symbol, 0)

        buys = [t for t in trades if t.trade_type == 'BUY']
        sells = [t for t in trades if t.trade_type == 'SELL']

        total_bought = sum(t.quantity * t.price for t in buys)
        total_sold = sum(t.quantity * t.price for t in sells)
        total_fees = sum(t.fee for t in trades)

        return {
            'symbol': symbol,
            'total_bought': total_bought,
            'total_sold': total_sold,
            'realized_pnl': realized,
            'total_fees': total_fees,
            'buy_count': len(buys),
            'sell_count': len(sells),
        }


# 전역 인스턴스
performance_tracker = PerformanceTracker()
