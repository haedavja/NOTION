"""
백테스트 전략
다양한 투자 전략 구현
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from abc import ABC, abstractmethod


class Strategy(ABC):
    """전략 베이스 클래스"""

    def __init__(self, name: str = "Strategy"):
        self.name = name
        self.params: Dict = {}

    @abstractmethod
    def initialize(self, engine: 'BacktestEngine'):
        """전략 초기화"""
        pass

    @abstractmethod
    def on_bar(self, engine: 'BacktestEngine', date: datetime):
        """매 봉(bar)마다 실행"""
        pass


class BuyAndHoldStrategy(Strategy):
    """바이 앤 홀드 전략"""

    def __init__(self, symbol: str, allocation: float = 1.0):
        """
        Args:
            symbol: 매수할 종목
            allocation: 자본 중 투자 비율 (0-1)
        """
        super().__init__(f"BuyAndHold_{symbol}")
        self.symbol = symbol
        self.allocation = allocation
        self.bought = False

    def initialize(self, engine):
        self.bought = False

    def on_bar(self, engine, date):
        if not self.bought:
            engine.buy_percent(date, self.symbol, self.allocation)
            self.bought = True


class MovingAverageCrossStrategy(Strategy):
    """이동평균 크로스 전략"""

    def __init__(self, symbol: str,
                 fast_period: int = 20,
                 slow_period: int = 50,
                 allocation: float = 1.0):
        """
        Args:
            symbol: 거래할 종목
            fast_period: 단기 이동평균 기간
            slow_period: 장기 이동평균 기간
            allocation: 투자 비율
        """
        super().__init__(f"MA_Cross_{fast_period}_{slow_period}")
        self.symbol = symbol
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.allocation = allocation

        self.price_history: List[float] = []
        self.in_position = False

    def initialize(self, engine):
        self.price_history = []
        self.in_position = False

    def _calculate_ma(self, period: int) -> Optional[float]:
        if len(self.price_history) < period:
            return None
        return np.mean(self.price_history[-period:])

    def on_bar(self, engine, date):
        price = engine.get_price(self.symbol, date)
        if price is None:
            return

        self.price_history.append(price)

        fast_ma = self._calculate_ma(self.fast_period)
        slow_ma = self._calculate_ma(self.slow_period)

        if fast_ma is None or slow_ma is None:
            return

        # 골든 크로스: 매수
        if fast_ma > slow_ma and not self.in_position:
            engine.buy_percent(date, self.symbol, self.allocation)
            self.in_position = True

        # 데드 크로스: 매도
        elif fast_ma < slow_ma and self.in_position:
            engine.sell_all(date, self.symbol)
            self.in_position = False


class RSIStrategy(Strategy):
    """RSI 전략"""

    def __init__(self, symbol: str,
                 period: int = 14,
                 oversold: float = 30,
                 overbought: float = 70,
                 allocation: float = 1.0):
        """
        Args:
            symbol: 거래할 종목
            period: RSI 기간
            oversold: 과매도 기준
            overbought: 과매수 기준
            allocation: 투자 비율
        """
        super().__init__(f"RSI_{period}")
        self.symbol = symbol
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.allocation = allocation

        self.price_history: List[float] = []
        self.in_position = False

    def initialize(self, engine):
        self.price_history = []
        self.in_position = False

    def _calculate_rsi(self) -> Optional[float]:
        if len(self.price_history) < self.period + 1:
            return None

        prices = np.array(self.price_history[-(self.period + 1):])
        deltas = np.diff(prices)

        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def on_bar(self, engine, date):
        price = engine.get_price(self.symbol, date)
        if price is None:
            return

        self.price_history.append(price)

        rsi = self._calculate_rsi()
        if rsi is None:
            return

        # 과매도: 매수
        if rsi < self.oversold and not self.in_position:
            engine.buy_percent(date, self.symbol, self.allocation)
            self.in_position = True

        # 과매수: 매도
        elif rsi > self.overbought and self.in_position:
            engine.sell_all(date, self.symbol)
            self.in_position = False


class MomentumStrategy(Strategy):
    """모멘텀 전략"""

    def __init__(self, symbol: str,
                 lookback: int = 20,
                 threshold: float = 0.0,
                 allocation: float = 1.0):
        """
        Args:
            symbol: 거래할 종목
            lookback: 모멘텀 측정 기간
            threshold: 매수 기준 수익률
            allocation: 투자 비율
        """
        super().__init__(f"Momentum_{lookback}")
        self.symbol = symbol
        self.lookback = lookback
        self.threshold = threshold
        self.allocation = allocation

        self.price_history: List[float] = []
        self.in_position = False

    def initialize(self, engine):
        self.price_history = []
        self.in_position = False

    def on_bar(self, engine, date):
        price = engine.get_price(self.symbol, date)
        if price is None:
            return

        self.price_history.append(price)

        if len(self.price_history) < self.lookback:
            return

        # 모멘텀 계산
        past_price = self.price_history[-self.lookback]
        momentum = (price / past_price - 1)

        # 양의 모멘텀: 매수
        if momentum > self.threshold and not self.in_position:
            engine.buy_percent(date, self.symbol, self.allocation)
            self.in_position = True

        # 음의 모멘텀: 매도
        elif momentum < 0 and self.in_position:
            engine.sell_all(date, self.symbol)
            self.in_position = False


class MeanReversionStrategy(Strategy):
    """평균 회귀 전략"""

    def __init__(self, symbol: str,
                 period: int = 20,
                 std_dev: float = 2.0,
                 allocation: float = 1.0):
        """
        Args:
            symbol: 거래할 종목
            period: 볼린저 밴드 기간
            std_dev: 표준편차 배수
            allocation: 투자 비율
        """
        super().__init__(f"MeanReversion_{period}")
        self.symbol = symbol
        self.period = period
        self.std_dev = std_dev
        self.allocation = allocation

        self.price_history: List[float] = []
        self.in_position = False

    def initialize(self, engine):
        self.price_history = []
        self.in_position = False

    def on_bar(self, engine, date):
        price = engine.get_price(self.symbol, date)
        if price is None:
            return

        self.price_history.append(price)

        if len(self.price_history) < self.period:
            return

        prices = np.array(self.price_history[-self.period:])
        ma = np.mean(prices)
        std = np.std(prices)

        upper_band = ma + self.std_dev * std
        lower_band = ma - self.std_dev * std

        # 하단 밴드 터치: 매수
        if price < lower_band and not self.in_position:
            engine.buy_percent(date, self.symbol, self.allocation)
            self.in_position = True

        # 중간 밴드 도달: 매도
        elif price > ma and self.in_position:
            engine.sell_all(date, self.symbol)
            self.in_position = False


class MacroStrategy(Strategy):
    """
    거시경제 기반 전략
    경기 사이클에 따라 자산 배분
    """

    def __init__(self,
                 equity_symbol: str = 'SPY',
                 bond_symbol: str = 'TLT',
                 gold_symbol: str = 'GLD',
                 rebalance_days: int = 30):
        """
        Args:
            equity_symbol: 주식 ETF
            bond_symbol: 채권 ETF
            gold_symbol: 금 ETF
            rebalance_days: 리밸런싱 주기 (일)
        """
        super().__init__("Macro_Strategy")
        self.equity_symbol = equity_symbol
        self.bond_symbol = bond_symbol
        self.gold_symbol = gold_symbol
        self.rebalance_days = rebalance_days

        self.symbols = [equity_symbol, bond_symbol, gold_symbol]
        self.last_rebalance = None
        self.price_histories: Dict[str, List[float]] = {}

    def initialize(self, engine):
        self.last_rebalance = None
        self.price_histories = {s: [] for s in self.symbols}

    def _get_market_regime(self) -> str:
        """시장 상태 판단"""
        equity_prices = self.price_histories.get(self.equity_symbol, [])

        if len(equity_prices) < 200:
            return 'neutral'

        current_price = equity_prices[-1]
        ma_50 = np.mean(equity_prices[-50:])
        ma_200 = np.mean(equity_prices[-200:])

        # 상승 추세
        if current_price > ma_50 > ma_200:
            return 'bull'
        # 하락 추세
        elif current_price < ma_50 < ma_200:
            return 'bear'
        # 횡보
        else:
            return 'neutral'

    def _get_allocations(self, regime: str) -> Dict[str, float]:
        """상태별 자산 배분"""
        allocations = {
            'bull': {
                self.equity_symbol: 0.70,
                self.bond_symbol: 0.20,
                self.gold_symbol: 0.10,
            },
            'bear': {
                self.equity_symbol: 0.20,
                self.bond_symbol: 0.50,
                self.gold_symbol: 0.30,
            },
            'neutral': {
                self.equity_symbol: 0.40,
                self.bond_symbol: 0.40,
                self.gold_symbol: 0.20,
            },
        }
        return allocations.get(regime, allocations['neutral'])

    def _rebalance(self, engine, date, allocations: Dict[str, float]):
        """리밸런싱 실행"""
        portfolio_value = engine.get_portfolio_value(date)

        # 먼저 모든 포지션 청산
        for symbol in self.symbols:
            if symbol in engine.positions:
                engine.sell_all(date, symbol)

        # 새로운 배분대로 매수
        for symbol, allocation in allocations.items():
            if allocation > 0:
                engine.buy_percent(date, symbol, allocation * 0.99)  # 수수료 여유

    def on_bar(self, engine, date):
        # 가격 기록
        for symbol in self.symbols:
            price = engine.get_price(symbol, date)
            if price is not None:
                self.price_histories[symbol].append(price)

        # 리밸런싱 체크
        should_rebalance = False

        if self.last_rebalance is None:
            should_rebalance = True
        elif (date - self.last_rebalance).days >= self.rebalance_days:
            should_rebalance = True

        if should_rebalance:
            regime = self._get_market_regime()
            allocations = self._get_allocations(regime)
            self._rebalance(engine, date, allocations)
            self.last_rebalance = date


class DualMomentumStrategy(Strategy):
    """
    듀얼 모멘텀 전략
    절대 모멘텀 + 상대 모멘텀
    """

    def __init__(self,
                 risky_symbol: str = 'SPY',
                 safe_symbol: str = 'TLT',
                 lookback: int = 60,
                 allocation: float = 1.0):
        """
        Args:
            risky_symbol: 위험 자산
            safe_symbol: 안전 자산
            lookback: 모멘텀 측정 기간
            allocation: 투자 비율
        """
        super().__init__(f"DualMomentum_{lookback}")
        self.risky_symbol = risky_symbol
        self.safe_symbol = safe_symbol
        self.lookback = lookback
        self.allocation = allocation

        self.price_histories: Dict[str, List[float]] = {}
        self.current_holding: Optional[str] = None

    def initialize(self, engine):
        self.price_histories = {
            self.risky_symbol: [],
            self.safe_symbol: [],
        }
        self.current_holding = None

    def _get_momentum(self, symbol: str) -> Optional[float]:
        prices = self.price_histories.get(symbol, [])
        if len(prices) < self.lookback:
            return None
        return prices[-1] / prices[-self.lookback] - 1

    def on_bar(self, engine, date):
        # 가격 기록
        for symbol in [self.risky_symbol, self.safe_symbol]:
            price = engine.get_price(symbol, date)
            if price is not None:
                self.price_histories[symbol].append(price)

        risky_momentum = self._get_momentum(self.risky_symbol)
        safe_momentum = self._get_momentum(self.safe_symbol)

        if risky_momentum is None or safe_momentum is None:
            return

        # 절대 모멘텀: 위험자산 모멘텀이 0 이상
        # 상대 모멘텀: 위험자산 > 안전자산
        if risky_momentum > 0 and risky_momentum > safe_momentum:
            target = self.risky_symbol
        else:
            target = self.safe_symbol

        # 포지션 변경
        if target != self.current_holding:
            if self.current_holding:
                engine.sell_all(date, self.current_holding)
            engine.buy_percent(date, target, self.allocation)
            self.current_holding = target
