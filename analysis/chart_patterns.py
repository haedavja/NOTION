"""
차트 패턴 인식
헤드앤숄더, 더블탑/바텀, 삼각수렴 등 패턴 감지
"""

import numpy as np
import pandas as pd
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from scipy.signal import argrelextrema
import logging

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """패턴 유형"""
    # 반전 패턴
    HEAD_AND_SHOULDERS = "head_and_shoulders"
    INVERSE_HEAD_AND_SHOULDERS = "inverse_head_and_shoulders"
    DOUBLE_TOP = "double_top"
    DOUBLE_BOTTOM = "double_bottom"
    TRIPLE_TOP = "triple_top"
    TRIPLE_BOTTOM = "triple_bottom"

    # 지속 패턴
    ASCENDING_TRIANGLE = "ascending_triangle"
    DESCENDING_TRIANGLE = "descending_triangle"
    SYMMETRICAL_TRIANGLE = "symmetrical_triangle"
    RISING_WEDGE = "rising_wedge"
    FALLING_WEDGE = "falling_wedge"
    FLAG = "flag"
    PENNANT = "pennant"

    # 기타
    CUP_AND_HANDLE = "cup_and_handle"
    ROUNDING_BOTTOM = "rounding_bottom"


class PatternSignal(Enum):
    """패턴 신호"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class SupportResistance:
    """지지/저항선"""
    level: float
    strength: int  # 터치 횟수
    type: str  # support, resistance
    first_touch: str  # 최초 터치 날짜
    last_touch: str  # 최근 터치 날짜


@dataclass
class PatternResult:
    """패턴 인식 결과"""
    pattern_type: PatternType
    signal: PatternSignal
    confidence: float  # 0-1
    start_date: str
    end_date: str
    key_levels: Dict[str, float]
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    description: str = ""


class ChartPatternAnalyzer:
    """차트 패턴 분석기"""

    def __init__(self, lookback: int = 100):
        self.lookback = lookback

    def analyze(self, df: pd.DataFrame) -> Dict[str, Any]:
        """전체 패턴 분석"""
        if len(df) < 20:
            return {"patterns": [], "support_resistance": [], "trend": "unknown"}

        # OHLC 컬럼 확인
        if 'Close' not in df.columns:
            if 'close' in df.columns:
                df = df.rename(columns={'open': 'Open', 'high': 'High',
                                        'low': 'Low', 'close': 'Close'})
            else:
                return {"patterns": [], "support_resistance": [], "trend": "unknown"}

        patterns = []

        # 각 패턴 검출
        patterns.extend(self._detect_double_patterns(df))
        patterns.extend(self._detect_head_and_shoulders(df))
        patterns.extend(self._detect_triangles(df))
        patterns.extend(self._detect_wedges(df))

        # 지지/저항선
        sr_levels = self._find_support_resistance(df)

        # 현재 추세
        trend = self._detect_trend(df)

        return {
            "patterns": patterns,
            "support_resistance": sr_levels,
            "trend": trend,
            "current_price": float(df['Close'].iloc[-1]),
            "analysis_date": datetime.now().strftime("%Y-%m-%d")
        }

    def _find_peaks_valleys(self, prices: pd.Series,
                            order: int = 5) -> Tuple[np.ndarray, np.ndarray]:
        """고점/저점 찾기"""
        prices_arr = prices.values

        # 로컬 최대/최소 찾기
        peaks = argrelextrema(prices_arr, np.greater, order=order)[0]
        valleys = argrelextrema(prices_arr, np.less, order=order)[0]

        return peaks, valleys

    def _find_support_resistance(self, df: pd.DataFrame,
                                  tolerance: float = 0.02) -> List[SupportResistance]:
        """지지/저항선 찾기"""
        prices = df['Close']
        highs = df['High'] if 'High' in df.columns else prices
        lows = df['Low'] if 'Low' in df.columns else prices

        current_price = prices.iloc[-1]
        levels = []

        # 고점/저점 찾기
        peaks, valleys = self._find_peaks_valleys(prices)

        # 가격 레벨 클러스터링
        all_levels = []

        for idx in peaks:
            all_levels.append({
                'price': float(highs.iloc[idx]),
                'date': str(df.index[idx].date()) if hasattr(df.index[idx], 'date') else str(df.index[idx]),
                'type': 'high'
            })

        for idx in valleys:
            all_levels.append({
                'price': float(lows.iloc[idx]),
                'date': str(df.index[idx].date()) if hasattr(df.index[idx], 'date') else str(df.index[idx]),
                'type': 'low'
            })

        # 클러스터링
        if not all_levels:
            return []

        all_levels.sort(key=lambda x: x['price'])

        clusters = []
        current_cluster = [all_levels[0]]

        for level in all_levels[1:]:
            if abs(level['price'] - current_cluster[-1]['price']) / current_cluster[-1]['price'] <= tolerance:
                current_cluster.append(level)
            else:
                if len(current_cluster) >= 2:
                    clusters.append(current_cluster)
                current_cluster = [level]

        if len(current_cluster) >= 2:
            clusters.append(current_cluster)

        # 클러스터를 지지/저항선으로 변환
        for cluster in clusters:
            avg_price = np.mean([l['price'] for l in cluster])
            dates = sorted([l['date'] for l in cluster])

            sr_type = "resistance" if avg_price > current_price else "support"

            levels.append(SupportResistance(
                level=round(avg_price, 2),
                strength=len(cluster),
                type=sr_type,
                first_touch=dates[0],
                last_touch=dates[-1]
            ))

        # 강도순 정렬
        levels.sort(key=lambda x: x.strength, reverse=True)

        return levels[:10]  # 상위 10개

    def _detect_trend(self, df: pd.DataFrame) -> str:
        """추세 감지"""
        prices = df['Close'].values[-50:]  # 최근 50일

        if len(prices) < 10:
            return "unknown"

        # 선형 회귀
        x = np.arange(len(prices))
        slope = np.polyfit(x, prices, 1)[0]

        # 기울기로 추세 판단
        price_range = np.max(prices) - np.min(prices)
        normalized_slope = slope / price_range * len(prices)

        if normalized_slope > 0.1:
            return "uptrend"
        elif normalized_slope < -0.1:
            return "downtrend"
        else:
            return "sideways"

    def _detect_double_patterns(self, df: pd.DataFrame) -> List[PatternResult]:
        """더블탑/더블바텀 감지"""
        patterns = []
        prices = df['Close']
        highs = df['High'] if 'High' in df.columns else prices
        lows = df['Low'] if 'Low' in df.columns else prices

        peaks, valleys = self._find_peaks_valleys(prices, order=7)

        # 더블탑 감지
        if len(peaks) >= 2:
            last_peaks = peaks[-2:]
            peak_prices = [highs.iloc[p] for p in last_peaks]

            # 두 고점이 비슷한 가격대 (2% 이내)
            if abs(peak_prices[0] - peak_prices[1]) / peak_prices[0] < 0.02:
                # 중간에 저점이 있어야 함
                mid_valleys = [v for v in valleys if last_peaks[0] < v < last_peaks[1]]
                if mid_valleys:
                    neckline = lows.iloc[mid_valleys[0]]
                    current = prices.iloc[-1]

                    # 현재가가 넥라인 근처거나 아래면 확정
                    if current <= neckline * 1.02:
                        target = neckline - (peak_prices[0] - neckline)

                        patterns.append(PatternResult(
                            pattern_type=PatternType.DOUBLE_TOP,
                            signal=PatternSignal.BEARISH,
                            confidence=0.75,
                            start_date=str(df.index[last_peaks[0]].date()) if hasattr(df.index[0], 'date') else str(df.index[last_peaks[0]]),
                            end_date=str(df.index[-1].date()) if hasattr(df.index[0], 'date') else str(df.index[-1]),
                            key_levels={
                                "top1": float(peak_prices[0]),
                                "top2": float(peak_prices[1]),
                                "neckline": float(neckline)
                            },
                            target_price=float(target),
                            stop_loss=float(max(peak_prices) * 1.02),
                            description="더블탑 패턴 - 하락 반전 신호"
                        ))

        # 더블바텀 감지
        if len(valleys) >= 2:
            last_valleys = valleys[-2:]
            valley_prices = [lows.iloc[v] for v in last_valleys]

            if abs(valley_prices[0] - valley_prices[1]) / valley_prices[0] < 0.02:
                mid_peaks = [p for p in peaks if last_valleys[0] < p < last_valleys[1]]
                if mid_peaks:
                    neckline = highs.iloc[mid_peaks[0]]
                    current = prices.iloc[-1]

                    if current >= neckline * 0.98:
                        target = neckline + (neckline - valley_prices[0])

                        patterns.append(PatternResult(
                            pattern_type=PatternType.DOUBLE_BOTTOM,
                            signal=PatternSignal.BULLISH,
                            confidence=0.75,
                            start_date=str(df.index[last_valleys[0]].date()) if hasattr(df.index[0], 'date') else str(df.index[last_valleys[0]]),
                            end_date=str(df.index[-1].date()) if hasattr(df.index[0], 'date') else str(df.index[-1]),
                            key_levels={
                                "bottom1": float(valley_prices[0]),
                                "bottom2": float(valley_prices[1]),
                                "neckline": float(neckline)
                            },
                            target_price=float(target),
                            stop_loss=float(min(valley_prices) * 0.98),
                            description="더블바텀 패턴 - 상승 반전 신호"
                        ))

        return patterns

    def _detect_head_and_shoulders(self, df: pd.DataFrame) -> List[PatternResult]:
        """헤드앤숄더 패턴 감지"""
        patterns = []
        prices = df['Close']
        highs = df['High'] if 'High' in df.columns else prices
        lows = df['Low'] if 'Low' in df.columns else prices

        peaks, valleys = self._find_peaks_valleys(prices, order=5)

        # 헤드앤숄더 (최소 3개 고점 필요)
        if len(peaks) >= 3:
            last_peaks = peaks[-3:]
            peak_prices = [highs.iloc[p] for p in last_peaks]

            left = peak_prices[0]
            head = peak_prices[1]
            right = peak_prices[2]

            # 헤드가 양 숄더보다 높아야 함
            if head > left and head > right:
                # 양 숄더가 비슷한 높이 (5% 이내)
                if abs(left - right) / left < 0.05:
                    # 넥라인 계산
                    valleys_between = [v for v in valleys if last_peaks[0] < v < last_peaks[2]]
                    if len(valleys_between) >= 2:
                        neckline = (lows.iloc[valleys_between[0]] + lows.iloc[valleys_between[1]]) / 2
                        current = prices.iloc[-1]

                        if current <= neckline * 1.02:
                            target = neckline - (head - neckline)

                            patterns.append(PatternResult(
                                pattern_type=PatternType.HEAD_AND_SHOULDERS,
                                signal=PatternSignal.BEARISH,
                                confidence=0.8,
                                start_date=str(df.index[last_peaks[0]].date()) if hasattr(df.index[0], 'date') else str(df.index[last_peaks[0]]),
                                end_date=str(df.index[-1].date()) if hasattr(df.index[0], 'date') else str(df.index[-1]),
                                key_levels={
                                    "left_shoulder": float(left),
                                    "head": float(head),
                                    "right_shoulder": float(right),
                                    "neckline": float(neckline)
                                },
                                target_price=float(target),
                                stop_loss=float(head * 1.02),
                                description="헤드앤숄더 패턴 - 강력한 하락 반전 신호"
                            ))

        # 역헤드앤숄더
        if len(valleys) >= 3:
            last_valleys = valleys[-3:]
            valley_prices = [lows.iloc[v] for v in last_valleys]

            left = valley_prices[0]
            head = valley_prices[1]
            right = valley_prices[2]

            if head < left and head < right:
                if abs(left - right) / left < 0.05:
                    peaks_between = [p for p in peaks if last_valleys[0] < p < last_valleys[2]]
                    if len(peaks_between) >= 2:
                        neckline = (highs.iloc[peaks_between[0]] + highs.iloc[peaks_between[1]]) / 2
                        current = prices.iloc[-1]

                        if current >= neckline * 0.98:
                            target = neckline + (neckline - head)

                            patterns.append(PatternResult(
                                pattern_type=PatternType.INVERSE_HEAD_AND_SHOULDERS,
                                signal=PatternSignal.BULLISH,
                                confidence=0.8,
                                start_date=str(df.index[last_valleys[0]].date()) if hasattr(df.index[0], 'date') else str(df.index[last_valleys[0]]),
                                end_date=str(df.index[-1].date()) if hasattr(df.index[0], 'date') else str(df.index[-1]),
                                key_levels={
                                    "left_shoulder": float(left),
                                    "head": float(head),
                                    "right_shoulder": float(right),
                                    "neckline": float(neckline)
                                },
                                target_price=float(target),
                                stop_loss=float(head * 0.98),
                                description="역헤드앤숄더 패턴 - 강력한 상승 반전 신호"
                            ))

        return patterns

    def _detect_triangles(self, df: pd.DataFrame) -> List[PatternResult]:
        """삼각형 패턴 감지"""
        patterns = []
        prices = df['Close'].values[-30:]  # 최근 30일
        highs = df['High'].values[-30:] if 'High' in df.columns else prices
        lows = df['Low'].values[-30:] if 'Low' in df.columns else prices

        if len(prices) < 20:
            return []

        x = np.arange(len(prices))

        # 고점/저점 추세선
        try:
            high_slope = np.polyfit(x, highs, 1)[0]
            low_slope = np.polyfit(x, lows, 1)[0]
        except Exception as e:
            logger.debug(f"추세선 계산 실패: {e}")
            return []

        # 패턴 분류
        if high_slope < -0.001 and abs(low_slope) < 0.001:
            # 하강 삼각형 (하락)
            patterns.append(PatternResult(
                pattern_type=PatternType.DESCENDING_TRIANGLE,
                signal=PatternSignal.BEARISH,
                confidence=0.65,
                start_date=str(df.index[-30].date()) if hasattr(df.index[0], 'date') else str(df.index[-30]),
                end_date=str(df.index[-1].date()) if hasattr(df.index[0], 'date') else str(df.index[-1]),
                key_levels={
                    "resistance_slope": float(high_slope),
                    "support": float(np.mean(lows))
                },
                description="하강 삼각형 - 하락 지속 패턴"
            ))

        elif abs(high_slope) < 0.001 and low_slope > 0.001:
            # 상승 삼각형 (상승)
            patterns.append(PatternResult(
                pattern_type=PatternType.ASCENDING_TRIANGLE,
                signal=PatternSignal.BULLISH,
                confidence=0.65,
                start_date=str(df.index[-30].date()) if hasattr(df.index[0], 'date') else str(df.index[-30]),
                end_date=str(df.index[-1].date()) if hasattr(df.index[0], 'date') else str(df.index[-1]),
                key_levels={
                    "resistance": float(np.mean(highs)),
                    "support_slope": float(low_slope)
                },
                description="상승 삼각형 - 상승 지속 패턴"
            ))

        elif high_slope < -0.001 and low_slope > 0.001:
            # 대칭 삼각형 (중립)
            patterns.append(PatternResult(
                pattern_type=PatternType.SYMMETRICAL_TRIANGLE,
                signal=PatternSignal.NEUTRAL,
                confidence=0.6,
                start_date=str(df.index[-30].date()) if hasattr(df.index[0], 'date') else str(df.index[-30]),
                end_date=str(df.index[-1].date()) if hasattr(df.index[0], 'date') else str(df.index[-1]),
                key_levels={
                    "high_slope": float(high_slope),
                    "low_slope": float(low_slope)
                },
                description="대칭 삼각형 - 돌파 방향 주시 필요"
            ))

        return patterns

    def _detect_wedges(self, df: pd.DataFrame) -> List[PatternResult]:
        """웨지 패턴 감지"""
        patterns = []
        prices = df['Close'].values[-40:]
        highs = df['High'].values[-40:] if 'High' in df.columns else prices
        lows = df['Low'].values[-40:] if 'Low' in df.columns else prices

        if len(prices) < 25:
            return []

        x = np.arange(len(prices))

        try:
            high_slope = np.polyfit(x, highs, 1)[0]
            low_slope = np.polyfit(x, lows, 1)[0]
        except Exception as e:
            logger.debug(f"추세선 계산 실패: {e}")
            return []

        # 라이징 웨지 (두 추세선이 모두 상승하지만 수렴)
        if high_slope > 0 and low_slope > 0 and low_slope > high_slope:
            patterns.append(PatternResult(
                pattern_type=PatternType.RISING_WEDGE,
                signal=PatternSignal.BEARISH,
                confidence=0.6,
                start_date=str(df.index[-40].date()) if hasattr(df.index[0], 'date') else str(df.index[-40]),
                end_date=str(df.index[-1].date()) if hasattr(df.index[0], 'date') else str(df.index[-1]),
                key_levels={
                    "high_slope": float(high_slope),
                    "low_slope": float(low_slope)
                },
                description="상승 웨지 - 하락 반전 가능성"
            ))

        # 폴링 웨지 (두 추세선이 모두 하락하지만 수렴)
        elif high_slope < 0 and low_slope < 0 and low_slope < high_slope:
            patterns.append(PatternResult(
                pattern_type=PatternType.FALLING_WEDGE,
                signal=PatternSignal.BULLISH,
                confidence=0.6,
                start_date=str(df.index[-40].date()) if hasattr(df.index[0], 'date') else str(df.index[-40]),
                end_date=str(df.index[-1].date()) if hasattr(df.index[0], 'date') else str(df.index[-1]),
                key_levels={
                    "high_slope": float(high_slope),
                    "low_slope": float(low_slope)
                },
                description="하락 웨지 - 상승 반전 가능성"
            ))

        return patterns


# 싱글톤 인스턴스
chart_analyzer = ChartPatternAnalyzer()


def analyze_patterns(df: pd.DataFrame) -> Dict[str, Any]:
    """패턴 분석"""
    return chart_analyzer.analyze(df)


def find_support_resistance(df: pd.DataFrame) -> List[SupportResistance]:
    """지지/저항선 찾기"""
    return chart_analyzer._find_support_resistance(df)
