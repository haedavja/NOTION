"""
자금 흐름 분석 모듈
자금의 이동 패턴과 섹터 로테이션을 분석합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class FlowDirection(Enum):
    """자금 흐름 방향"""
    STRONG_INFLOW = "강한 유입"
    INFLOW = "유입"
    NEUTRAL = "중립"
    OUTFLOW = "유출"
    STRONG_OUTFLOW = "강한 유출"


class RiskRegime(Enum):
    """위험 선호 체제"""
    RISK_ON = "위험 선호"
    NEUTRAL = "중립"
    RISK_OFF = "위험 회피"


@dataclass
class FlowSignal:
    """자금 흐름 신호"""
    asset: str
    direction: FlowDirection
    magnitude: float
    percentile: float  # 역사적 백분위
    description: str


class FlowAnalyzer:
    """자금 흐름 분석 클래스"""

    # 자산군별 위험도
    ASSET_RISK_SCORES = {
        # 위험자산 (높은 점수)
        'technology': 0.9,
        'consumer_discretionary': 0.8,
        'small_cap': 0.85,
        'emerging_markets': 0.9,
        'high_yield': 0.75,

        # 중립 자산
        'sp500': 0.5,
        'financials': 0.6,
        'industrials': 0.55,
        'healthcare': 0.45,

        # 안전자산 (낮은 점수)
        'utilities': 0.2,
        'consumer_staples': 0.25,
        'treasury_long': 0.1,
        'treasury_short': 0.05,
        'gold': 0.15,
    }

    # 섹터 로테이션 순서 (경기 사이클)
    SECTOR_ROTATION = {
        'early_cycle': ['financials', 'consumer_discretionary', 'industrials'],
        'mid_cycle': ['technology', 'communication', 'materials'],
        'late_cycle': ['energy', 'healthcare', 'materials'],
        'recession': ['utilities', 'consumer_staples', 'healthcare'],
    }

    def __init__(self):
        """초기화"""
        pass

    def analyze_asset_class_flows(self, prices: pd.DataFrame,
                                  window: int = 20) -> Dict[str, FlowSignal]:
        """
        자산군별 자금 흐름 분석

        가격과 거래량 움직임으로 자금 흐름 추정

        Args:
            prices: 자산군별 가격 데이터
            window: 분석 윈도우 (일)

        Returns:
            자산군별 자금 흐름 신호
        """
        signals = {}

        for asset in prices.columns:
            series = prices[asset].dropna()

            if len(series) < window * 2:
                continue

            # 최근 수익률
            recent_return = series.pct_change(window).iloc[-1]

            # 역사적 백분위
            historical_returns = series.pct_change(window).dropna()
            percentile = (historical_returns < recent_return).mean() * 100

            # 모멘텀 (단기 vs 장기)
            short_ma = series.rolling(window).mean().iloc[-1]
            long_ma = series.rolling(window * 3).mean().iloc[-1]
            momentum = (short_ma / long_ma - 1) * 100

            # 흐름 방향 결정
            if recent_return > 0.05 and momentum > 2:
                direction = FlowDirection.STRONG_INFLOW
            elif recent_return > 0.02 or momentum > 0:
                direction = FlowDirection.INFLOW
            elif recent_return < -0.05 and momentum < -2:
                direction = FlowDirection.STRONG_OUTFLOW
            elif recent_return < -0.02 or momentum < 0:
                direction = FlowDirection.OUTFLOW
            else:
                direction = FlowDirection.NEUTRAL

            signals[asset] = FlowSignal(
                asset=asset,
                direction=direction,
                magnitude=recent_return * 100,
                percentile=percentile,
                description=f"{asset}: {recent_return*100:.1f}% ({window}일), 백분위 {percentile:.0f}%"
            )

        return signals

    def calculate_risk_appetite(self, prices: pd.DataFrame,
                               window: int = 20) -> Tuple[RiskRegime, float, Dict]:
        """
        시장 위험 선호도 계산

        Args:
            prices: 자산군별 가격 데이터
            window: 분석 윈도우

        Returns:
            (위험 체제, 점수, 상세 정보)
        """
        risk_indicators = {}

        # 자산별 수익률 계산
        returns = prices.pct_change(window)

        if returns.empty:
            return RiskRegime.NEUTRAL, 0.5, {}

        latest_returns = returns.iloc[-1]

        # 위험 선호 쌍 비교
        pairs = [
            ('technology', 'utilities'),
            ('consumer_discretionary', 'consumer_staples'),
            ('small_cap', 'treasury_long'),
            ('high_yield', 'treasury_short'),
            ('emerging_markets', 'gold'),
        ]

        risk_on_count = 0
        total_pairs = 0

        for risk_asset, safe_asset in pairs:
            if risk_asset in latest_returns and safe_asset in latest_returns:
                risk_return = latest_returns[risk_asset]
                safe_return = latest_returns[safe_asset]

                relative = risk_return - safe_return
                risk_indicators[f"{risk_asset}_vs_{safe_asset}"] = {
                    'risk_return': risk_return,
                    'safe_return': safe_return,
                    'relative': relative,
                    'risk_on': relative > 0
                }

                if relative > 0:
                    risk_on_count += 1
                total_pairs += 1

        # 위험 선호 점수 (0-1)
        if total_pairs > 0:
            risk_score = risk_on_count / total_pairs
        else:
            risk_score = 0.5

        # 체제 결정
        if risk_score > 0.65:
            regime = RiskRegime.RISK_ON
        elif risk_score < 0.35:
            regime = RiskRegime.RISK_OFF
        else:
            regime = RiskRegime.NEUTRAL

        return regime, risk_score, risk_indicators

    def detect_sector_rotation(self, sector_prices: pd.DataFrame,
                              windows: List[int] = [20, 60, 120]) -> Dict:
        """
        섹터 로테이션 감지

        Args:
            sector_prices: 섹터별 가격 데이터
            windows: 분석 기간들

        Returns:
            섹터 로테이션 분석 결과
        """
        results = {
            'rankings': {},
            'momentum_leaders': [],
            'momentum_laggards': [],
            'rotation_signal': None,
        }

        for window in windows:
            returns = sector_prices.pct_change(window).iloc[-1]
            returns = returns.sort_values(ascending=False)
            results['rankings'][f'{window}d'] = returns.to_dict()

        # 복합 모멘텀 점수 (단기/중기/장기 가중 평균)
        if len(windows) >= 3:
            weights = [0.5, 0.3, 0.2]  # 단기 > 중기 > 장기
            composite_momentum = pd.Series(0.0, index=sector_prices.columns)

            for i, window in enumerate(windows):
                returns = sector_prices.pct_change(window).iloc[-1]
                returns_normalized = (returns - returns.mean()) / (returns.std() + 1e-8)
                composite_momentum += weights[i] * returns_normalized

            composite_momentum = composite_momentum.sort_values(ascending=False)

            results['composite_momentum'] = composite_momentum.to_dict()
            results['momentum_leaders'] = composite_momentum.head(3).index.tolist()
            results['momentum_laggards'] = composite_momentum.tail(3).index.tolist()

        # 로테이션 신호 (어느 사이클로 이동 중인지)
        leaders = results.get('momentum_leaders', [])

        for cycle, sectors in self.SECTOR_ROTATION.items():
            overlap = len(set(leaders) & set(sectors))
            if overlap >= 2:
                results['rotation_signal'] = cycle
                break

        return results

    def calculate_breadth(self, prices: pd.DataFrame,
                         ma_periods: List[int] = [50, 200]) -> Dict:
        """
        시장 폭 지표 계산

        Args:
            prices: 자산/섹터 가격 데이터
            ma_periods: 이동평균 기간들

        Returns:
            시장 폭 지표
        """
        breadth = {}

        latest_prices = prices.iloc[-1]

        for period in ma_periods:
            if len(prices) >= period:
                ma = prices.rolling(period).mean().iloc[-1]
                above_ma = (latest_prices > ma).sum()
                total = len(latest_prices)

                breadth[f'above_ma_{period}'] = above_ma
                breadth[f'pct_above_ma_{period}'] = above_ma / total * 100

        # 신고가/신저가
        if len(prices) >= 252:
            high_52w = prices.rolling(252).max().iloc[-1]
            low_52w = prices.rolling(252).min().iloc[-1]

            near_high = ((high_52w - latest_prices) / high_52w < 0.05).sum()
            near_low = ((latest_prices - low_52w) / low_52w < 0.05).sum()

            breadth['near_52w_high'] = near_high
            breadth['near_52w_low'] = near_low
            breadth['high_low_ratio'] = near_high / (near_low + 1)

        # 시장 폭 건강도 점수
        health_score = 0
        if 'pct_above_ma_50' in breadth:
            health_score += breadth['pct_above_ma_50'] / 100 * 0.4
        if 'pct_above_ma_200' in breadth:
            health_score += breadth['pct_above_ma_200'] / 100 * 0.4
        if 'high_low_ratio' in breadth:
            health_score += min(breadth['high_low_ratio'] / 3, 1) * 0.2

        breadth['health_score'] = health_score

        return breadth

    def identify_divergences(self, prices: pd.DataFrame,
                            benchmark: str = 'sp500') -> List[Dict]:
        """
        다이버전스 감지

        벤치마크 대비 이상 움직임 감지

        Args:
            prices: 가격 데이터
            benchmark: 벤치마크 컬럼명

        Returns:
            다이버전스 리스트
        """
        divergences = []

        if benchmark not in prices.columns:
            return divergences

        benchmark_returns = prices[benchmark].pct_change(20).iloc[-1]

        for asset in prices.columns:
            if asset == benchmark:
                continue

            asset_returns = prices[asset].pct_change(20).iloc[-1]

            # 상관관계 계산
            correlation = prices[benchmark].pct_change().tail(60).corr(
                prices[asset].pct_change().tail(60)
            )

            # 예상 수익률 vs 실제 수익률
            expected_return = benchmark_returns * correlation
            deviation = asset_returns - expected_return

            if abs(deviation) > 0.03:  # 3% 이상 괴리
                divergences.append({
                    'asset': asset,
                    'actual_return': asset_returns * 100,
                    'expected_return': expected_return * 100,
                    'deviation': deviation * 100,
                    'direction': 'Outperforming' if deviation > 0 else 'Underperforming',
                    'correlation': correlation,
                })

        # 괴리도 순으로 정렬
        divergences.sort(key=lambda x: abs(x['deviation']), reverse=True)

        return divergences

    def get_flow_summary(self, prices: pd.DataFrame) -> Dict:
        """
        자금 흐름 종합 요약

        Args:
            prices: 가격 데이터

        Returns:
            종합 요약
        """
        # 자산군별 흐름
        flow_signals = self.analyze_asset_class_flows(prices)

        # 위험 선호도
        risk_regime, risk_score, risk_details = self.calculate_risk_appetite(prices)

        # 시장 폭
        breadth = self.calculate_breadth(prices)

        # 다이버전스
        divergences = self.identify_divergences(prices)

        # 강한 유입/유출 자산
        strong_inflows = [
            sig.asset for sig in flow_signals.values()
            if sig.direction in [FlowDirection.STRONG_INFLOW, FlowDirection.INFLOW]
        ]
        strong_outflows = [
            sig.asset for sig in flow_signals.values()
            if sig.direction in [FlowDirection.STRONG_OUTFLOW, FlowDirection.OUTFLOW]
        ]

        return {
            'risk_regime': risk_regime.value,
            'risk_score': risk_score,
            'market_breadth': breadth,
            'inflows': strong_inflows,
            'outflows': strong_outflows,
            'divergences': divergences[:5],  # 상위 5개
            'flow_signals': {
                asset: {
                    'direction': sig.direction.value,
                    'magnitude': sig.magnitude,
                    'percentile': sig.percentile,
                }
                for asset, sig in flow_signals.items()
            },
            'recommendation': self._generate_recommendation(risk_regime, breadth, divergences),
        }

    def _generate_recommendation(self, risk_regime: RiskRegime,
                                 breadth: Dict,
                                 divergences: List[Dict]) -> str:
        """추천 의견 생성"""
        recommendations = []

        # 위험 체제 기반 추천
        if risk_regime == RiskRegime.RISK_ON:
            recommendations.append("위험자산 선호 환경 - 주식/성장주 비중 확대 고려")
        elif risk_regime == RiskRegime.RISK_OFF:
            recommendations.append("위험회피 환경 - 채권/금 등 안전자산 비중 확대 고려")
        else:
            recommendations.append("중립적 환경 - 균형 잡힌 포트폴리오 유지")

        # 시장 폭 기반 추천
        health_score = breadth.get('health_score', 0.5)
        if health_score > 0.7:
            recommendations.append("시장 폭 양호 - 광범위한 상승 참여")
        elif health_score < 0.3:
            recommendations.append("시장 폭 취약 - 소수 종목만 상승, 주의 필요")

        # 다이버전스 기반 추천
        if divergences:
            outperformers = [d['asset'] for d in divergences if d['direction'] == 'Outperforming']
            if outperformers:
                recommendations.append(f"상대 강세: {', '.join(outperformers[:3])}")

        return " | ".join(recommendations)
