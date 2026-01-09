"""
기술적 지표 모듈
MACD, 볼린저밴드, 스토캐스틱, RSI 등
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class IndicatorSignal:
    """지표 시그널"""
    name: str
    value: float
    signal: str  # 'buy', 'sell', 'neutral'
    strength: int  # 1-5
    description: str


class TechnicalIndicators:
    """기술적 지표 계산"""

    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """단순이동평균"""
        return data.rolling(window=period).mean()

    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """지수이동평균"""
        return data.ewm(span=period, adjust=False).mean()

    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """RSI (Relative Strength Index)"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        # ZeroDivisionError 방지
        loss_adj = loss.replace(0, 1e-10)
        rs = gain / loss_adj
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26,
             signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD (Moving Average Convergence Divergence)
        Returns: (MACD line, Signal line, Histogram)
        """
        exp1 = data.ewm(span=fast, adjust=False).mean()
        exp2 = data.ewm(span=slow, adjust=False).mean()

        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20,
                        std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        볼린저 밴드
        Returns: (Upper band, Middle band, Lower band)
        """
        middle = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()

        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        return upper, middle, lower

    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                   k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """
        스토캐스틱
        Returns: (%K, %D)
        """
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        stoch_k = ((close - lowest_low) / (highest_high - lowest_low)) * 100
        stoch_d = stoch_k.rolling(window=d_period).mean()

        return stoch_k, stoch_d

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series,
            period: int = 14) -> pd.Series:
        """ATR (Average True Range) - 변동성 지표"""
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr

    @staticmethod
    def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
        """OBV (On Balance Volume) - 거래량 지표"""
        obv = (np.sign(close.diff()) * volume).fillna(0).cumsum()
        return obv

    @staticmethod
    def vwap(high: pd.Series, low: pd.Series, close: pd.Series,
             volume: pd.Series) -> pd.Series:
        """VWAP (Volume Weighted Average Price)"""
        typical_price = (high + low + close) / 3
        vwap = (typical_price * volume).cumsum() / volume.cumsum()
        return vwap

    @staticmethod
    def williams_r(high: pd.Series, low: pd.Series, close: pd.Series,
                   period: int = 14) -> pd.Series:
        """Williams %R"""
        highest_high = high.rolling(window=period).max()
        lowest_low = low.rolling(window=period).min()

        wr = ((highest_high - close) / (highest_high - lowest_low)) * -100
        return wr

    @staticmethod
    def cci(high: pd.Series, low: pd.Series, close: pd.Series,
            period: int = 20) -> pd.Series:
        """CCI (Commodity Channel Index)"""
        tp = (high + low + close) / 3
        sma = tp.rolling(window=period).mean()
        mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())

        cci = (tp - sma) / (0.015 * mad)
        return cci


class SignalAnalyzer:
    """시그널 분석기"""

    def __init__(self, df: pd.DataFrame):
        """
        df: OHLCV 데이터프레임 (Open, High, Low, Close, Volume 컬럼 필요)
        """
        self.df = df.copy()
        self.indicators = TechnicalIndicators()
        self._calculate_all()

    def _calculate_all(self):
        """모든 지표 계산"""
        close = self.df['Close']
        high = self.df['High']
        low = self.df['Low']
        volume = self.df['Volume']

        # 이동평균
        self.df['SMA20'] = self.indicators.sma(close, 20)
        self.df['SMA50'] = self.indicators.sma(close, 50)
        self.df['SMA200'] = self.indicators.sma(close, 200)
        self.df['EMA12'] = self.indicators.ema(close, 12)
        self.df['EMA26'] = self.indicators.ema(close, 26)

        # RSI
        self.df['RSI'] = self.indicators.rsi(close, 14)

        # MACD
        macd, signal, hist = self.indicators.macd(close)
        self.df['MACD'] = macd
        self.df['MACD_Signal'] = signal
        self.df['MACD_Hist'] = hist

        # 볼린저 밴드
        upper, middle, lower = self.indicators.bollinger_bands(close)
        self.df['BB_Upper'] = upper
        self.df['BB_Middle'] = middle
        self.df['BB_Lower'] = lower
        self.df['BB_Width'] = (upper - lower) / middle * 100

        # 스토캐스틱
        stoch_k, stoch_d = self.indicators.stochastic(high, low, close)
        self.df['Stoch_K'] = stoch_k
        self.df['Stoch_D'] = stoch_d

        # 기타
        self.df['ATR'] = self.indicators.atr(high, low, close)
        self.df['OBV'] = self.indicators.obv(close, volume)
        self.df['Williams_R'] = self.indicators.williams_r(high, low, close)
        self.df['CCI'] = self.indicators.cci(high, low, close)

    def get_signals(self) -> Dict[str, IndicatorSignal]:
        """현재 시그널 분석"""
        signals = {}
        latest = self.df.iloc[-1]
        prev = self.df.iloc[-2] if len(self.df) > 1 else latest

        # RSI 시그널
        rsi = latest['RSI']
        if rsi < 30:
            signals['RSI'] = IndicatorSignal(
                name='RSI', value=rsi, signal='buy', strength=4,
                description=f'과매도 구간 (RSI: {rsi:.1f})'
            )
        elif rsi > 70:
            signals['RSI'] = IndicatorSignal(
                name='RSI', value=rsi, signal='sell', strength=4,
                description=f'과매수 구간 (RSI: {rsi:.1f})'
            )
        else:
            signals['RSI'] = IndicatorSignal(
                name='RSI', value=rsi, signal='neutral', strength=2,
                description=f'중립 구간 (RSI: {rsi:.1f})'
            )

        # MACD 시그널
        macd = latest['MACD']
        macd_signal = latest['MACD_Signal']
        macd_hist = latest['MACD_Hist']
        prev_hist = prev['MACD_Hist']

        if macd > macd_signal and prev['MACD'] <= prev['MACD_Signal']:
            signals['MACD'] = IndicatorSignal(
                name='MACD', value=macd_hist, signal='buy', strength=5,
                description='골든 크로스 발생'
            )
        elif macd < macd_signal and prev['MACD'] >= prev['MACD_Signal']:
            signals['MACD'] = IndicatorSignal(
                name='MACD', value=macd_hist, signal='sell', strength=5,
                description='데드 크로스 발생'
            )
        elif macd_hist > 0 and macd_hist > prev_hist:
            signals['MACD'] = IndicatorSignal(
                name='MACD', value=macd_hist, signal='buy', strength=3,
                description='상승 모멘텀 증가'
            )
        elif macd_hist < 0 and macd_hist < prev_hist:
            signals['MACD'] = IndicatorSignal(
                name='MACD', value=macd_hist, signal='sell', strength=3,
                description='하락 모멘텀 증가'
            )
        else:
            signals['MACD'] = IndicatorSignal(
                name='MACD', value=macd_hist, signal='neutral', strength=1,
                description='추세 전환 대기'
            )

        # 볼린저 밴드 시그널
        close = latest['Close']
        bb_upper = latest['BB_Upper']
        bb_lower = latest['BB_Lower']
        bb_middle = latest['BB_Middle']

        if close <= bb_lower:
            signals['Bollinger'] = IndicatorSignal(
                name='볼린저밴드', value=(close - bb_lower), signal='buy', strength=4,
                description='하단밴드 터치 (반등 가능)'
            )
        elif close >= bb_upper:
            signals['Bollinger'] = IndicatorSignal(
                name='볼린저밴드', value=(close - bb_upper), signal='sell', strength=4,
                description='상단밴드 터치 (조정 가능)'
            )
        elif close > bb_middle:
            signals['Bollinger'] = IndicatorSignal(
                name='볼린저밴드', value=(close - bb_middle), signal='buy', strength=2,
                description='중심선 상단'
            )
        else:
            signals['Bollinger'] = IndicatorSignal(
                name='볼린저밴드', value=(close - bb_middle), signal='sell', strength=2,
                description='중심선 하단'
            )

        # 스토캐스틱 시그널
        stoch_k = latest['Stoch_K']
        stoch_d = latest['Stoch_D']

        if stoch_k < 20 and stoch_k > stoch_d:
            signals['Stochastic'] = IndicatorSignal(
                name='스토캐스틱', value=stoch_k, signal='buy', strength=4,
                description=f'과매도 반전 (%K: {stoch_k:.1f})'
            )
        elif stoch_k > 80 and stoch_k < stoch_d:
            signals['Stochastic'] = IndicatorSignal(
                name='스토캐스틱', value=stoch_k, signal='sell', strength=4,
                description=f'과매수 반전 (%K: {stoch_k:.1f})'
            )
        elif stoch_k > stoch_d:
            signals['Stochastic'] = IndicatorSignal(
                name='스토캐스틱', value=stoch_k, signal='buy', strength=2,
                description=f'상승 추세 (%K: {stoch_k:.1f})'
            )
        else:
            signals['Stochastic'] = IndicatorSignal(
                name='스토캐스틱', value=stoch_k, signal='sell', strength=2,
                description=f'하락 추세 (%K: {stoch_k:.1f})'
            )

        # 이동평균 시그널
        sma20 = latest['SMA20']
        sma50 = latest['SMA50']

        if close > sma20 > sma50:
            signals['MA'] = IndicatorSignal(
                name='이동평균', value=close, signal='buy', strength=3,
                description='정배열 (상승추세)'
            )
        elif close < sma20 < sma50:
            signals['MA'] = IndicatorSignal(
                name='이동평균', value=close, signal='sell', strength=3,
                description='역배열 (하락추세)'
            )
        else:
            signals['MA'] = IndicatorSignal(
                name='이동평균', value=close, signal='neutral', strength=1,
                description='횡보 구간'
            )

        return signals

    def get_composite_signal(self) -> Dict:
        """종합 시그널"""
        signals = self.get_signals()

        buy_score = 0
        sell_score = 0
        total_strength = 0

        for sig in signals.values():
            total_strength += sig.strength
            if sig.signal == 'buy':
                buy_score += sig.strength
            elif sig.signal == 'sell':
                sell_score += sig.strength

        if total_strength == 0:
            return {'signal': 'neutral', 'confidence': 0, 'details': signals}

        net_score = buy_score - sell_score
        confidence = abs(net_score) / total_strength * 100

        if net_score > 2:
            signal = 'strong_buy'
        elif net_score > 0:
            signal = 'buy'
        elif net_score < -2:
            signal = 'strong_sell'
        elif net_score < 0:
            signal = 'sell'
        else:
            signal = 'neutral'

        return {
            'signal': signal,
            'confidence': confidence,
            'buy_score': buy_score,
            'sell_score': sell_score,
            'net_score': net_score,
            'details': signals
        }

    def get_indicator_df(self) -> pd.DataFrame:
        """지표 데이터프레임 반환"""
        return self.df


def analyze_stock(symbol: str, period: str = "1y") -> Dict:
    """종목 기술적 분석"""
    import yfinance as yf

    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period)

        if df.empty:
            return {'error': 'No data'}

        analyzer = SignalAnalyzer(df)
        result = analyzer.get_composite_signal()
        result['symbol'] = symbol
        result['last_price'] = df['Close'].iloc[-1]
        result['change_pct'] = (df['Close'].iloc[-1] / df['Close'].iloc[-2] - 1) * 100

        return result

    except Exception as e:
        return {'error': str(e)}
