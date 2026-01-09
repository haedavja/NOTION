"""
기술적 분석 모듈
가격 데이터 기반 기술적 지표를 계산합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TechnicalSignal:
    """기술적 신호"""
    indicator: str
    value: float
    signal: str       # bullish, bearish, neutral
    strength: float   # 0-1
    description: str


class TechnicalAnalyzer:
    """기술적 분석 클래스"""

    def __init__(self):
        """초기화"""
        pass

    # ========== 이동평균 ==========

    def sma(self, prices: pd.Series, period: int) -> pd.Series:
        """단순 이동평균"""
        return prices.rolling(window=period).mean()

    def ema(self, prices: pd.Series, period: int) -> pd.Series:
        """지수 이동평균"""
        return prices.ewm(span=period, adjust=False).mean()

    def moving_average_signals(self, prices: pd.Series) -> Dict:
        """
        이동평균 신호 분석

        Args:
            prices: 가격 시계열

        Returns:
            이동평균 분석 결과
        """
        current = prices.iloc[-1]

        ma_20 = self.sma(prices, 20).iloc[-1]
        ma_50 = self.sma(prices, 50).iloc[-1]
        ma_200 = self.sma(prices, 200).iloc[-1]

        signals = {
            'current_price': current,
            'ma_20': ma_20,
            'ma_50': ma_50,
            'ma_200': ma_200,
            'above_ma_20': current > ma_20,
            'above_ma_50': current > ma_50,
            'above_ma_200': current > ma_200,
        }

        # 골든크로스/데스크로스
        ma_50_prev = self.sma(prices, 50).iloc[-2]
        ma_200_prev = self.sma(prices, 200).iloc[-2]

        if ma_50_prev < ma_200_prev and ma_50 > ma_200:
            signals['cross_signal'] = 'Golden Cross'
        elif ma_50_prev > ma_200_prev and ma_50 < ma_200:
            signals['cross_signal'] = 'Death Cross'
        else:
            signals['cross_signal'] = 'None'

        # 전체 트렌드 판단
        trend_score = sum([
            signals['above_ma_20'],
            signals['above_ma_50'],
            signals['above_ma_200'],
        ])

        if trend_score == 3:
            signals['trend'] = 'Strong Uptrend'
        elif trend_score == 2:
            signals['trend'] = 'Uptrend'
        elif trend_score == 1:
            signals['trend'] = 'Downtrend'
        else:
            signals['trend'] = 'Strong Downtrend'

        return signals

    # ========== 모멘텀 지표 ==========

    def rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        RSI (Relative Strength Index)

        Args:
            prices: 가격 시계열
            period: 기간 (기본 14)

        Returns:
            RSI 시계열
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        # ZeroDivisionError 방지
        loss_adj = loss.replace(0, 1e-10)
        rs = gain / loss_adj
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def macd(self, prices: pd.Series,
             fast: int = 12,
             slow: int = 26,
             signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD (Moving Average Convergence Divergence)

        Returns:
            (MACD선, 시그널선, 히스토그램)
        """
        ema_fast = self.ema(prices, fast)
        ema_slow = self.ema(prices, slow)

        macd_line = ema_fast - ema_slow
        signal_line = self.ema(macd_line, signal)
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram

    def stochastic(self, high: pd.Series,
                   low: pd.Series,
                   close: pd.Series,
                   k_period: int = 14,
                   d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """
        스토캐스틱

        Returns:
            (%K, %D)
        """
        lowest_low = low.rolling(k_period).min()
        highest_high = high.rolling(k_period).max()

        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(d_period).mean()

        return k, d

    def momentum_signals(self, prices: pd.Series) -> Dict:
        """
        모멘텀 지표 종합 분석

        Args:
            prices: 가격 시계열

        Returns:
            모멘텀 분석 결과
        """
        signals = {}

        # RSI
        rsi_values = self.rsi(prices)
        current_rsi = rsi_values.iloc[-1]
        signals['rsi'] = current_rsi

        if current_rsi > 70:
            signals['rsi_signal'] = 'Overbought'
        elif current_rsi < 30:
            signals['rsi_signal'] = 'Oversold'
        else:
            signals['rsi_signal'] = 'Neutral'

        # RSI 다이버전스
        price_trend = prices.iloc[-1] > prices.iloc[-5]
        rsi_trend = rsi_values.iloc[-1] > rsi_values.iloc[-5]

        if price_trend and not rsi_trend:
            signals['rsi_divergence'] = 'Bearish Divergence'
        elif not price_trend and rsi_trend:
            signals['rsi_divergence'] = 'Bullish Divergence'
        else:
            signals['rsi_divergence'] = 'None'

        # MACD
        macd_line, signal_line, histogram = self.macd(prices)
        signals['macd'] = macd_line.iloc[-1]
        signals['macd_signal'] = signal_line.iloc[-1]
        signals['macd_histogram'] = histogram.iloc[-1]

        if macd_line.iloc[-1] > signal_line.iloc[-1] and macd_line.iloc[-2] <= signal_line.iloc[-2]:
            signals['macd_cross'] = 'Bullish Crossover'
        elif macd_line.iloc[-1] < signal_line.iloc[-1] and macd_line.iloc[-2] >= signal_line.iloc[-2]:
            signals['macd_cross'] = 'Bearish Crossover'
        else:
            signals['macd_cross'] = 'None'

        return signals

    # ========== 변동성 지표 ==========

    def bollinger_bands(self, prices: pd.Series,
                       period: int = 20,
                       std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        볼린저 밴드

        Returns:
            (상단밴드, 중간밴드, 하단밴드)
        """
        middle = self.sma(prices, period)
        std = prices.rolling(window=period).std()

        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        return upper, middle, lower

    def atr(self, high: pd.Series,
            low: pd.Series,
            close: pd.Series,
            period: int = 14) -> pd.Series:
        """
        ATR (Average True Range)
        """
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr

    def volatility_signals(self, prices: pd.Series,
                          high: Optional[pd.Series] = None,
                          low: Optional[pd.Series] = None) -> Dict:
        """
        변동성 지표 분석

        Args:
            prices: 종가 시계열
            high: 고가 시계열 (옵션)
            low: 저가 시계열 (옵션)

        Returns:
            변동성 분석 결과
        """
        signals = {}

        # 볼린저 밴드
        upper, middle, lower = self.bollinger_bands(prices)
        current = prices.iloc[-1]

        signals['bb_upper'] = upper.iloc[-1]
        signals['bb_middle'] = middle.iloc[-1]
        signals['bb_lower'] = lower.iloc[-1]

        # 밴드 위치 (0-1)
        bb_position = (current - lower.iloc[-1]) / (upper.iloc[-1] - lower.iloc[-1])
        signals['bb_position'] = bb_position

        if bb_position > 0.95:
            signals['bb_signal'] = 'Near Upper Band - Overbought'
        elif bb_position < 0.05:
            signals['bb_signal'] = 'Near Lower Band - Oversold'
        elif bb_position > 0.8:
            signals['bb_signal'] = 'Upper Region'
        elif bb_position < 0.2:
            signals['bb_signal'] = 'Lower Region'
        else:
            signals['bb_signal'] = 'Middle Region'

        # 밴드폭 (변동성 측정)
        bandwidth = (upper.iloc[-1] - lower.iloc[-1]) / middle.iloc[-1] * 100
        signals['bb_bandwidth'] = bandwidth

        # 역사적 변동성
        returns = prices.pct_change()
        historical_vol = returns.tail(20).std() * np.sqrt(252) * 100
        signals['historical_volatility'] = historical_vol

        # ATR (고가/저가 있을 경우)
        if high is not None and low is not None:
            atr_values = self.atr(high, low, prices)
            signals['atr'] = atr_values.iloc[-1]
            signals['atr_pct'] = atr_values.iloc[-1] / current * 100

        return signals

    # ========== 지지/저항 ==========

    def find_support_resistance(self, prices: pd.Series,
                                window: int = 20,
                                threshold: float = 0.02) -> Dict:
        """
        지지/저항선 탐지

        Args:
            prices: 가격 시계열
            window: 피벗 포인트 탐지 윈도우
            threshold: 클러스터링 임계값

        Returns:
            지지/저항 레벨
        """
        # 로컬 고점/저점 찾기
        highs = []
        lows = []

        for i in range(window, len(prices) - window):
            if prices.iloc[i] == prices.iloc[i-window:i+window+1].max():
                highs.append(prices.iloc[i])
            if prices.iloc[i] == prices.iloc[i-window:i+window+1].min():
                lows.append(prices.iloc[i])

        # 클러스터링 (유사한 레벨 병합)
        def cluster_levels(levels, threshold):
            if not levels:
                return []
            levels = sorted(levels)
            clusters = [[levels[0]]]

            for level in levels[1:]:
                if (level - clusters[-1][-1]) / clusters[-1][-1] < threshold:
                    clusters[-1].append(level)
                else:
                    clusters.append([level])

            return [np.mean(c) for c in clusters]

        resistance_levels = cluster_levels(highs, threshold)
        support_levels = cluster_levels(lows, threshold)

        current = prices.iloc[-1]

        # 가장 가까운 지지/저항
        nearby_resistance = [r for r in resistance_levels if r > current]
        nearby_support = [s for s in support_levels if s < current]

        return {
            'current_price': current,
            'resistance_levels': resistance_levels[-5:],  # 최근 5개
            'support_levels': support_levels[-5:],
            'nearest_resistance': min(nearby_resistance) if nearby_resistance else None,
            'nearest_support': max(nearby_support) if nearby_support else None,
            'distance_to_resistance': (nearby_resistance[0] / current - 1) * 100 if nearby_resistance else None,
            'distance_to_support': (1 - nearby_support[-1] / current) * 100 if nearby_support else None,
        }

    # ========== 종합 분석 ==========

    def get_technical_summary(self, prices: pd.Series,
                             high: Optional[pd.Series] = None,
                             low: Optional[pd.Series] = None) -> Dict:
        """
        기술적 분석 종합 요약

        Args:
            prices: 종가 시계열
            high: 고가 시계열 (옵션)
            low: 저가 시계열 (옵션)

        Returns:
            종합 기술적 분석 결과
        """
        # 이동평균 분석
        ma_signals = self.moving_average_signals(prices)

        # 모멘텀 분석
        momentum = self.momentum_signals(prices)

        # 변동성 분석
        volatility = self.volatility_signals(prices, high, low)

        # 지지/저항
        sr_levels = self.find_support_resistance(prices)

        # 종합 점수 계산
        bullish_signals = 0
        bearish_signals = 0
        total_signals = 0

        # 트렌드 점수
        if 'Strong Uptrend' in ma_signals['trend']:
            bullish_signals += 2
        elif 'Uptrend' in ma_signals['trend']:
            bullish_signals += 1
        elif 'Strong Downtrend' in ma_signals['trend']:
            bearish_signals += 2
        elif 'Downtrend' in ma_signals['trend']:
            bearish_signals += 1
        total_signals += 2

        # RSI
        if momentum['rsi_signal'] == 'Oversold':
            bullish_signals += 1
        elif momentum['rsi_signal'] == 'Overbought':
            bearish_signals += 1
        total_signals += 1

        # MACD
        if momentum['macd_histogram'] > 0:
            bullish_signals += 1
        else:
            bearish_signals += 1
        total_signals += 1

        # 골든/데스 크로스
        if ma_signals['cross_signal'] == 'Golden Cross':
            bullish_signals += 2
        elif ma_signals['cross_signal'] == 'Death Cross':
            bearish_signals += 2
        total_signals += 2

        # 종합 점수 (-1 ~ 1)
        score = (bullish_signals - bearish_signals) / total_signals

        # 신호 강도
        if abs(score) > 0.5:
            signal_strength = 'Strong'
        elif abs(score) > 0.25:
            signal_strength = 'Moderate'
        else:
            signal_strength = 'Weak'

        return {
            'trend_analysis': ma_signals,
            'momentum_analysis': momentum,
            'volatility_analysis': volatility,
            'support_resistance': sr_levels,
            'composite_score': score,
            'signal_direction': 'Bullish' if score > 0.1 else ('Bearish' if score < -0.1 else 'Neutral'),
            'signal_strength': signal_strength,
            'summary': self._generate_summary(ma_signals, momentum, volatility, sr_levels, score),
        }

    def _generate_summary(self, ma: Dict, momentum: Dict,
                         volatility: Dict, sr: Dict, score: float) -> str:
        """기술적 분석 요약 문구 생성"""
        parts = []

        # 트렌드
        parts.append(f"추세: {ma['trend']}")

        # RSI
        parts.append(f"RSI: {momentum['rsi']:.1f} ({momentum['rsi_signal']})")

        # 변동성
        parts.append(f"변동성: {volatility['historical_volatility']:.1f}%")

        # 지지/저항
        if sr['nearest_resistance']:
            parts.append(f"저항선까지: {sr['distance_to_resistance']:.1f}%")
        if sr['nearest_support']:
            parts.append(f"지지선까지: {sr['distance_to_support']:.1f}%")

        # 종합
        direction = 'Bullish' if score > 0.1 else ('Bearish' if score < -0.1 else 'Neutral')
        parts.append(f"종합 신호: {direction} ({score:.2f})")

        return " | ".join(parts)

    def generate_signals(self, prices: pd.Series) -> List[TechnicalSignal]:
        """
        기술적 신호 리스트 생성

        Args:
            prices: 가격 시계열

        Returns:
            기술적 신호 리스트
        """
        signals = []

        # 이동평균
        ma_analysis = self.moving_average_signals(prices)

        if ma_analysis['above_ma_200']:
            signals.append(TechnicalSignal(
                indicator='MA200',
                value=ma_analysis['ma_200'],
                signal='bullish',
                strength=0.7,
                description='200일 이동평균선 위에서 거래 중'
            ))
        else:
            signals.append(TechnicalSignal(
                indicator='MA200',
                value=ma_analysis['ma_200'],
                signal='bearish',
                strength=0.7,
                description='200일 이동평균선 아래에서 거래 중'
            ))

        # RSI
        momentum = self.momentum_signals(prices)
        rsi_val = momentum['rsi']

        if rsi_val > 70:
            signals.append(TechnicalSignal(
                indicator='RSI',
                value=rsi_val,
                signal='bearish',
                strength=min((rsi_val - 70) / 30, 1),
                description=f'RSI {rsi_val:.1f} - 과매수 구간'
            ))
        elif rsi_val < 30:
            signals.append(TechnicalSignal(
                indicator='RSI',
                value=rsi_val,
                signal='bullish',
                strength=min((30 - rsi_val) / 30, 1),
                description=f'RSI {rsi_val:.1f} - 과매도 구간'
            ))
        else:
            signals.append(TechnicalSignal(
                indicator='RSI',
                value=rsi_val,
                signal='neutral',
                strength=0.5,
                description=f'RSI {rsi_val:.1f} - 중립 구간'
            ))

        # MACD
        if momentum['macd_cross'] == 'Bullish Crossover':
            signals.append(TechnicalSignal(
                indicator='MACD',
                value=momentum['macd'],
                signal='bullish',
                strength=0.8,
                description='MACD 골든 크로스 발생'
            ))
        elif momentum['macd_cross'] == 'Bearish Crossover':
            signals.append(TechnicalSignal(
                indicator='MACD',
                value=momentum['macd'],
                signal='bearish',
                strength=0.8,
                description='MACD 데드 크로스 발생'
            ))

        return signals
