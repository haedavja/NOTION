"""
고급 백테스트 모듈
사용자 정의 전략, 수수료/슬리피지 반영, 상세 분석
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import yfinance as yf


@dataclass
class TradeRecord:
    """매매 기록"""
    date: datetime
    action: str  # 'BUY', 'SELL'
    price: float
    quantity: float
    value: float
    fee: float
    slippage: float
    reason: str = ""


@dataclass
class BacktestConfig:
    """백테스트 설정"""
    initial_capital: float = 10000000  # 1천만원
    commission_rate: float = 0.00015  # 0.015% (증권사 수수료)
    tax_rate: float = 0.0023  # 0.23% (거래세, 매도시만)
    slippage_rate: float = 0.001  # 0.1% 슬리피지
    max_position_size: float = 0.25  # 최대 포지션 25%
    stop_loss: float = -0.07  # 손절 -7%
    take_profit: float = 0.15  # 익절 +15%
    rebalance_threshold: float = 0.05  # 리밸런싱 임계값


@dataclass
class BacktestResult:
    """백테스트 결과"""
    strategy_name: str
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_value: float
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    profit_factor: float
    trades: List[TradeRecord] = field(default_factory=list)
    equity_curve: pd.DataFrame = None
    config: BacktestConfig = None

    def to_dict(self) -> Dict:
        return {
            'strategy_name': self.strategy_name,
            'symbol': self.symbol,
            'period': f"{self.start_date.strftime('%Y-%m-%d')} ~ {self.end_date.strftime('%Y-%m-%d')}",
            'initial_capital': self.initial_capital,
            'final_value': self.final_value,
            'total_return': f"{self.total_return:.2f}%",
            'annual_return': f"{self.annual_return:.2f}%",
            'max_drawdown': f"{self.max_drawdown:.2f}%",
            'sharpe_ratio': f"{self.sharpe_ratio:.2f}",
            'win_rate': f"{self.win_rate:.1f}%",
            'total_trades': self.total_trades,
            'profit_factor': f"{self.profit_factor:.2f}",
        }


class Strategy(ABC):
    """전략 추상 클래스"""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """
        시그널 생성
        Returns: Series with values 1 (buy), -1 (sell), 0 (hold)
        """
        pass


class MovingAverageCrossStrategy(Strategy):
    """이동평균 교차 전략"""

    def __init__(self, short_window: int = 20, long_window: int = 50):
        self.short_window = short_window
        self.long_window = long_window

    @property
    def name(self) -> str:
        return f"MA Cross ({self.short_window}/{self.long_window})"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=data.index)

        short_ma = data['Close'].rolling(window=self.short_window).mean()
        long_ma = data['Close'].rolling(window=self.long_window).mean()

        # 골든 크로스 (매수)
        signals[(short_ma > long_ma) & (short_ma.shift(1) <= long_ma.shift(1))] = 1
        # 데드 크로스 (매도)
        signals[(short_ma < long_ma) & (short_ma.shift(1) >= long_ma.shift(1))] = -1

        return signals


class RSIStrategy(Strategy):
    """RSI 전략"""

    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    @property
    def name(self) -> str:
        return f"RSI ({self.period}, {self.oversold}/{self.overbought})"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=data.index)

        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        # 과매도 탈출 (매수)
        signals[(rsi > self.oversold) & (rsi.shift(1) <= self.oversold)] = 1
        # 과매수 탈출 (매도)
        signals[(rsi < self.overbought) & (rsi.shift(1) >= self.overbought)] = -1

        return signals


class MACDStrategy(Strategy):
    """MACD 전략"""

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal

    @property
    def name(self) -> str:
        return f"MACD ({self.fast}/{self.slow}/{self.signal})"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=data.index)

        exp1 = data['Close'].ewm(span=self.fast, adjust=False).mean()
        exp2 = data['Close'].ewm(span=self.slow, adjust=False).mean()
        macd = exp1 - exp2
        signal_line = macd.ewm(span=self.signal, adjust=False).mean()

        # MACD가 시그널 상향 돌파 (매수)
        signals[(macd > signal_line) & (macd.shift(1) <= signal_line.shift(1))] = 1
        # MACD가 시그널 하향 돌파 (매도)
        signals[(macd < signal_line) & (macd.shift(1) >= signal_line.shift(1))] = -1

        return signals


class BollingerBandStrategy(Strategy):
    """볼린저 밴드 전략"""

    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = period
        self.std_dev = std_dev

    @property
    def name(self) -> str:
        return f"Bollinger ({self.period}, {self.std_dev}σ)"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=data.index)

        ma = data['Close'].rolling(window=self.period).mean()
        std = data['Close'].rolling(window=self.period).std()

        upper = ma + (std * self.std_dev)
        lower = ma - (std * self.std_dev)

        # 하단 밴드 터치 후 반등 (매수)
        signals[(data['Close'] > lower) & (data['Close'].shift(1) <= lower.shift(1))] = 1
        # 상단 밴드 터치 후 하락 (매도)
        signals[(data['Close'] < upper) & (data['Close'].shift(1) >= upper.shift(1))] = -1

        return signals


class CombinedStrategy(Strategy):
    """복합 전략 (여러 전략 조합)"""

    def __init__(self, strategies: List[Strategy], min_agree: int = 2):
        self.strategies = strategies
        self.min_agree = min_agree

    @property
    def name(self) -> str:
        return f"Combined ({len(self.strategies)} strategies)"

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        all_signals = pd.DataFrame()

        for i, strategy in enumerate(self.strategies):
            all_signals[f's{i}'] = strategy.generate_signals(data)

        # 다수결
        buy_count = (all_signals == 1).sum(axis=1)
        sell_count = (all_signals == -1).sum(axis=1)

        signals = pd.Series(0, index=data.index)
        signals[buy_count >= self.min_agree] = 1
        signals[sell_count >= self.min_agree] = -1

        return signals


class AdvancedBacktester:
    """고급 백테스터"""

    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()

    def run(self, symbol: str, strategy: Strategy,
            start_date: str = None, end_date: str = None) -> BacktestResult:
        """백테스트 실행"""

        # 데이터 로드
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')

        data = self._load_data(symbol, start_date, end_date)
        if data is None or len(data) < 50:
            return None

        # 시그널 생성
        signals = strategy.generate_signals(data)

        # 백테스트 실행
        result = self._execute_backtest(data, signals, strategy.name, symbol)

        return result

    def _load_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """데이터 로드"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date)
            return data
        except Exception as e:
            print(f"Data load error: {e}")
            return None

    def _execute_backtest(self, data: pd.DataFrame, signals: pd.Series,
                          strategy_name: str, symbol: str) -> BacktestResult:
        """백테스트 실행 로직"""

        cash = self.config.initial_capital
        position = 0
        position_price = 0
        trades: List[TradeRecord] = []

        equity_history = []
        peak_equity = cash

        for i, (date, row) in enumerate(data.iterrows()):
            price = row['Close']
            signal = signals.iloc[i] if i < len(signals) else 0

            # 현재 포트폴리오 가치
            current_value = cash + position * price
            equity_history.append({
                'date': date,
                'equity': current_value,
                'cash': cash,
                'position_value': position * price
            })

            # MDD 계산용
            if current_value > peak_equity:
                peak_equity = current_value

            # 손절/익절 체크 (포지션 있을 때)
            if position > 0 and position_price > 0:
                pnl_pct = (price - position_price) / position_price

                if pnl_pct <= self.config.stop_loss:
                    signal = -1  # 강제 손절
                elif pnl_pct >= self.config.take_profit:
                    signal = -1  # 익절

            # 매수 시그널
            if signal == 1 and position == 0:
                # 최대 포지션 사이즈 적용
                max_invest = cash * self.config.max_position_size
                actual_invest = min(max_invest, cash * 0.95)  # 5% 여유 유지

                # 슬리피지 적용
                buy_price = price * (1 + self.config.slippage_rate)

                # 수수료 계산
                fee = actual_invest * self.config.commission_rate

                # 매수 가능 수량
                quantity = (actual_invest - fee) / buy_price

                if quantity > 0:
                    cost = quantity * buy_price + fee
                    cash -= cost
                    position = quantity
                    position_price = buy_price

                    trades.append(TradeRecord(
                        date=date,
                        action='BUY',
                        price=buy_price,
                        quantity=quantity,
                        value=cost,
                        fee=fee,
                        slippage=price * self.config.slippage_rate * quantity,
                        reason='Signal'
                    ))

            # 매도 시그널
            elif signal == -1 and position > 0:
                # 슬리피지 적용
                sell_price = price * (1 - self.config.slippage_rate)

                # 매도 금액
                sell_value = position * sell_price

                # 수수료 + 세금
                fee = sell_value * self.config.commission_rate
                tax = sell_value * self.config.tax_rate

                net_value = sell_value - fee - tax
                cash += net_value

                trades.append(TradeRecord(
                    date=date,
                    action='SELL',
                    price=sell_price,
                    quantity=position,
                    value=net_value,
                    fee=fee + tax,
                    slippage=price * self.config.slippage_rate * position,
                    reason='Signal'
                ))

                position = 0
                position_price = 0

        # 마지막 포지션 청산
        if position > 0:
            final_price = data['Close'].iloc[-1]
            sell_price = final_price * (1 - self.config.slippage_rate)
            sell_value = position * sell_price
            fee = sell_value * self.config.commission_rate
            tax = sell_value * self.config.tax_rate
            cash += sell_value - fee - tax

        # 결과 계산
        final_value = cash
        total_return = (final_value - self.config.initial_capital) / self.config.initial_capital * 100

        # 연환산 수익률
        days = (data.index[-1] - data.index[0]).days
        years = days / 365 if days > 0 else 1
        annual_return = ((final_value / self.config.initial_capital) ** (1 / years) - 1) * 100 if years > 0 else 0

        # MDD
        equity_df = pd.DataFrame(equity_history)
        equity_df['peak'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak'] * 100
        max_drawdown = equity_df['drawdown'].min()

        # 승률 계산
        winning_trades = 0
        losing_trades = 0
        total_wins = 0
        total_losses = 0

        for i in range(0, len(trades) - 1, 2):  # 매수-매도 쌍
            if i + 1 < len(trades):
                buy = trades[i]
                sell = trades[i + 1]
                pnl = sell.value - buy.value

                if pnl > 0:
                    winning_trades += 1
                    total_wins += pnl
                else:
                    losing_trades += 1
                    total_losses += abs(pnl)

        total_trades = len(trades) // 2
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        avg_win = (total_wins / winning_trades) if winning_trades > 0 else 0
        avg_loss = (total_losses / losing_trades) if losing_trades > 0 else 0
        profit_factor = (total_wins / total_losses) if total_losses > 0 else float('inf')

        # 샤프 비율
        if len(equity_df) > 1:
            equity_df['returns'] = equity_df['equity'].pct_change()
            sharpe_ratio = (equity_df['returns'].mean() / equity_df['returns'].std()) * np.sqrt(252) if equity_df['returns'].std() > 0 else 0
        else:
            sharpe_ratio = 0

        return BacktestResult(
            strategy_name=strategy_name,
            symbol=symbol,
            start_date=data.index[0].to_pydatetime(),
            end_date=data.index[-1].to_pydatetime(),
            initial_capital=self.config.initial_capital,
            final_value=final_value,
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            win_rate=win_rate,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            avg_win=avg_win,
            avg_loss=avg_loss,
            profit_factor=profit_factor,
            trades=trades,
            equity_curve=equity_df,
            config=self.config
        )

    def compare_strategies(self, symbol: str, strategies: List[Strategy],
                          start_date: str = None, end_date: str = None) -> List[BacktestResult]:
        """여러 전략 비교"""
        results = []

        for strategy in strategies:
            result = self.run(symbol, strategy, start_date, end_date)
            if result:
                results.append(result)

        # 수익률 순 정렬
        results.sort(key=lambda x: x.total_return, reverse=True)
        return results


# 편의 함수
def quick_backtest(symbol: str, strategy_type: str = 'ma',
                   start_date: str = None, **kwargs) -> BacktestResult:
    """빠른 백테스트"""

    strategies = {
        'ma': MovingAverageCrossStrategy(**kwargs),
        'rsi': RSIStrategy(**kwargs),
        'macd': MACDStrategy(**kwargs),
        'bollinger': BollingerBandStrategy(**kwargs),
    }

    strategy = strategies.get(strategy_type, MovingAverageCrossStrategy())
    backtester = AdvancedBacktester()

    return backtester.run(symbol, strategy, start_date)


# 전역 백테스터
backtester = AdvancedBacktester()
