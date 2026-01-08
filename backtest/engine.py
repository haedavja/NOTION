"""
백테스트 엔진
투자 전략을 과거 데이터로 검증합니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


class OrderType(Enum):
    """주문 유형"""
    BUY = "buy"
    SELL = "sell"


class PositionType(Enum):
    """포지션 유형"""
    LONG = "long"
    SHORT = "short"


@dataclass
class Order:
    """주문"""
    date: datetime
    symbol: str
    order_type: OrderType
    quantity: float
    price: float
    commission: float = 0.0

    @property
    def value(self) -> float:
        return self.quantity * self.price

    @property
    def total_cost(self) -> float:
        return self.value + self.commission


@dataclass
class Position:
    """포지션"""
    symbol: str
    quantity: float
    avg_price: float
    position_type: PositionType = PositionType.LONG

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_price

    def market_value(self, current_price: float) -> float:
        return self.quantity * current_price

    def unrealized_pnl(self, current_price: float) -> float:
        if self.position_type == PositionType.LONG:
            return (current_price - self.avg_price) * self.quantity
        else:
            return (self.avg_price - current_price) * self.quantity


@dataclass
class BacktestResult:
    """백테스트 결과"""
    # 기본 정보
    strategy_name: str
    start_date: datetime
    end_date: datetime
    initial_capital: float

    # 수익률
    total_return: float
    annualized_return: float
    benchmark_return: float
    alpha: float

    # 리스크
    volatility: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float

    # 거래 통계
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float

    # 시계열 데이터
    equity_curve: pd.Series
    drawdown_series: pd.Series
    trades: List[Dict]

    def summary(self) -> str:
        """결과 요약"""
        return f"""
=== 백테스트 결과: {self.strategy_name} ===
기간: {self.start_date.strftime('%Y-%m-%d')} ~ {self.end_date.strftime('%Y-%m-%d')}
초기 자본: ${self.initial_capital:,.0f}

📈 수익률
  총 수익률: {self.total_return:.2f}%
  연환산 수익률: {self.annualized_return:.2f}%
  벤치마크 수익률: {self.benchmark_return:.2f}%
  알파: {self.alpha:.2f}%

📊 리스크
  변동성: {self.volatility:.2f}%
  최대 낙폭: {self.max_drawdown:.2f}%
  샤프 비율: {self.sharpe_ratio:.2f}
  소르티노 비율: {self.sortino_ratio:.2f}

💹 거래 통계
  총 거래: {self.total_trades}회
  승률: {self.win_rate:.1f}%
  평균 수익: {self.avg_win:.2f}%
  평균 손실: {self.avg_loss:.2f}%
  손익비: {self.profit_factor:.2f}
"""


class BacktestEngine:
    """백테스트 엔진"""

    def __init__(self,
                 initial_capital: float = 100000,
                 commission: float = 0.001,       # 0.1% 수수료
                 slippage: float = 0.0005,        # 0.05% 슬리피지
                 risk_free_rate: float = 0.04):   # 4% 무위험 수익률
        """
        초기화

        Args:
            initial_capital: 초기 자본
            commission: 수수료율
            slippage: 슬리피지율
            risk_free_rate: 무위험 수익률
        """
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.risk_free_rate = risk_free_rate

        # 상태
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: List[Order] = []
        self.equity_history: List[Tuple[datetime, float]] = []

        # 데이터
        self.price_data: Optional[pd.DataFrame] = None
        self.benchmark_data: Optional[pd.Series] = None

    def load_data(self, symbols: List[str],
                 start_date: str,
                 end_date: str,
                 benchmark: str = '^GSPC') -> pd.DataFrame:
        """
        가격 데이터 로드

        Args:
            symbols: 종목 리스트
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            benchmark: 벤치마크 심볼

        Returns:
            가격 데이터프레임
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance가 필요합니다.")

        # 종목 데이터
        all_symbols = symbols + [benchmark]
        data = yf.download(all_symbols, start=start_date, end=end_date, progress=False)

        # OHLCV 데이터
        self.price_data = data

        # 벤치마크 종가
        if len(all_symbols) > 1:
            self.benchmark_data = data['Close'][benchmark]
        else:
            self.benchmark_data = data['Close']

        return data

    def reset(self):
        """상태 초기화"""
        self.cash = self.initial_capital
        self.positions = {}
        self.orders = []
        self.equity_history = []

    def get_price(self, symbol: str, date: datetime) -> Optional[float]:
        """특정 날짜 가격 조회"""
        if self.price_data is None:
            return None

        try:
            if 'Close' in self.price_data.columns.get_level_values(0):
                return self.price_data['Close'][symbol].loc[date]
            else:
                return self.price_data['Close'].loc[date]
        except (KeyError, TypeError):
            return None

    def get_portfolio_value(self, date: datetime) -> float:
        """포트폴리오 총 가치"""
        total = self.cash

        for symbol, position in self.positions.items():
            price = self.get_price(symbol, date)
            if price:
                total += position.market_value(price)

        return total

    def execute_order(self, date: datetime, symbol: str,
                     order_type: OrderType, quantity: float) -> Optional[Order]:
        """
        주문 실행

        Args:
            date: 주문일
            symbol: 종목
            order_type: 주문 유형
            quantity: 수량

        Returns:
            실행된 주문
        """
        price = self.get_price(symbol, date)
        if price is None:
            return None

        # 슬리피지 적용
        if order_type == OrderType.BUY:
            execution_price = price * (1 + self.slippage)
        else:
            execution_price = price * (1 - self.slippage)

        # 수수료 계산
        order_value = quantity * execution_price
        commission = order_value * self.commission

        # 매수
        if order_type == OrderType.BUY:
            total_cost = order_value + commission

            if total_cost > self.cash:
                # 자금 부족 - 가능한 수량만 매수
                quantity = (self.cash - commission) / execution_price
                if quantity <= 0:
                    return None
                order_value = quantity * execution_price
                commission = order_value * self.commission
                total_cost = order_value + commission

            self.cash -= total_cost

            # 포지션 업데이트
            if symbol in self.positions:
                pos = self.positions[symbol]
                new_quantity = pos.quantity + quantity
                new_avg_price = (pos.cost_basis + order_value) / new_quantity
                pos.quantity = new_quantity
                pos.avg_price = new_avg_price
            else:
                self.positions[symbol] = Position(
                    symbol=symbol,
                    quantity=quantity,
                    avg_price=execution_price,
                )

        # 매도
        else:
            if symbol not in self.positions:
                return None

            pos = self.positions[symbol]
            quantity = min(quantity, pos.quantity)

            if quantity <= 0:
                return None

            proceeds = order_value - commission
            self.cash += proceeds

            # 포지션 업데이트
            pos.quantity -= quantity
            if pos.quantity <= 0:
                del self.positions[symbol]

        # 주문 기록
        order = Order(
            date=date,
            symbol=symbol,
            order_type=order_type,
            quantity=quantity,
            price=execution_price,
            commission=commission,
        )
        self.orders.append(order)

        return order

    def buy(self, date: datetime, symbol: str, quantity: float) -> Optional[Order]:
        """매수"""
        return self.execute_order(date, symbol, OrderType.BUY, quantity)

    def sell(self, date: datetime, symbol: str, quantity: float) -> Optional[Order]:
        """매도"""
        return self.execute_order(date, symbol, OrderType.SELL, quantity)

    def buy_percent(self, date: datetime, symbol: str, percent: float) -> Optional[Order]:
        """자산의 일정 비율로 매수"""
        portfolio_value = self.get_portfolio_value(date)
        price = self.get_price(symbol, date)

        if price is None or price <= 0:
            return None

        target_value = portfolio_value * percent
        quantity = target_value / price

        return self.buy(date, symbol, quantity)

    def sell_all(self, date: datetime, symbol: str) -> Optional[Order]:
        """전량 매도"""
        if symbol not in self.positions:
            return None
        return self.sell(date, symbol, self.positions[symbol].quantity)

    def run(self, strategy: 'Strategy',
           start_date: Optional[str] = None,
           end_date: Optional[str] = None) -> BacktestResult:
        """
        백테스트 실행

        Args:
            strategy: 전략 객체
            start_date: 시작일
            end_date: 종료일

        Returns:
            백테스트 결과
        """
        if self.price_data is None:
            raise ValueError("먼저 load_data()로 데이터를 로드하세요.")

        self.reset()

        # 날짜 범위
        if 'Close' in self.price_data.columns.get_level_values(0):
            dates = self.price_data['Close'].index
        else:
            dates = self.price_data.index

        if start_date:
            dates = dates[dates >= start_date]
        if end_date:
            dates = dates[dates <= end_date]

        # 전략 초기화
        strategy.initialize(self)

        # 시뮬레이션 실행
        for date in dates:
            # 전략 실행
            strategy.on_bar(self, date)

            # 포트폴리오 가치 기록
            portfolio_value = self.get_portfolio_value(date)
            self.equity_history.append((date, portfolio_value))

        # 결과 계산
        return self._calculate_results(strategy.name, dates[0], dates[-1])

    def _calculate_results(self, strategy_name: str,
                          start_date: datetime,
                          end_date: datetime) -> BacktestResult:
        """결과 계산"""
        # 에쿼티 커브
        equity_df = pd.DataFrame(self.equity_history, columns=['date', 'value'])
        equity_df.set_index('date', inplace=True)
        equity_curve = equity_df['value']

        # 수익률
        total_return = (equity_curve.iloc[-1] / self.initial_capital - 1) * 100

        # 거래일 수
        days = (end_date - start_date).days
        years = days / 365

        # 연환산 수익률
        if years > 0:
            annualized_return = ((equity_curve.iloc[-1] / self.initial_capital) ** (1/years) - 1) * 100
        else:
            annualized_return = total_return

        # 벤치마크 수익률
        if self.benchmark_data is not None:
            benchmark_start = self.benchmark_data.iloc[0]
            benchmark_end = self.benchmark_data.iloc[-1]
            benchmark_return = (benchmark_end / benchmark_start - 1) * 100
        else:
            benchmark_return = 0

        # 알파
        alpha = annualized_return - benchmark_return

        # 일간 수익률
        daily_returns = equity_curve.pct_change().dropna()

        # 변동성
        volatility = daily_returns.std() * np.sqrt(252) * 100

        # 낙폭 계산
        running_max = equity_curve.expanding().max()
        drawdown = (equity_curve - running_max) / running_max * 100
        max_drawdown = drawdown.min()

        # 샤프 비율
        excess_return = daily_returns.mean() * 252 - self.risk_free_rate
        sharpe_ratio = excess_return / (daily_returns.std() * np.sqrt(252)) if daily_returns.std() > 0 else 0

        # 소르티노 비율
        downside_returns = daily_returns[daily_returns < 0]
        downside_std = downside_returns.std() * np.sqrt(252)
        sortino_ratio = excess_return / downside_std if downside_std > 0 else 0

        # 칼마 비율
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0

        # 거래 분석
        trades = self._analyze_trades()

        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] <= 0]

        total_trades = len(trades)
        win_count = len(winning_trades)
        loss_count = len(losing_trades)

        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

        avg_win = np.mean([t['pnl_pct'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl_pct'] for t in losing_trades]) if losing_trades else 0

        total_wins = sum(t['pnl'] for t in winning_trades)
        total_losses = abs(sum(t['pnl'] for t in losing_trades))
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')

        return BacktestResult(
            strategy_name=strategy_name,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,

            total_return=total_return,
            annualized_return=annualized_return,
            benchmark_return=benchmark_return,
            alpha=alpha,

            volatility=volatility,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,

            total_trades=total_trades,
            winning_trades=win_count,
            losing_trades=loss_count,
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,

            equity_curve=equity_curve,
            drawdown_series=drawdown,
            trades=trades,
        )

    def _analyze_trades(self) -> List[Dict]:
        """거래 분석"""
        trades = []
        buy_orders = {}  # symbol -> List[Order]

        for order in self.orders:
            symbol = order.symbol

            if order.order_type == OrderType.BUY:
                if symbol not in buy_orders:
                    buy_orders[symbol] = []
                buy_orders[symbol].append(order)

            elif order.order_type == OrderType.SELL:
                if symbol in buy_orders and buy_orders[symbol]:
                    # FIFO 방식으로 매칭
                    buy_order = buy_orders[symbol].pop(0)

                    pnl = (order.price - buy_order.price) * order.quantity - order.commission - buy_order.commission
                    pnl_pct = (order.price / buy_order.price - 1) * 100

                    trades.append({
                        'symbol': symbol,
                        'buy_date': buy_order.date,
                        'buy_price': buy_order.price,
                        'sell_date': order.date,
                        'sell_price': order.price,
                        'quantity': order.quantity,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'holding_days': (order.date - buy_order.date).days,
                    })

        return trades
