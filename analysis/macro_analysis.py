"""
거시경제 분석 모듈
거시경제 지표를 분석하여 시장 환경을 진단합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class EconomicCycle(Enum):
    """경기 사이클 단계"""
    EXPANSION = "확장기"      # 성장 가속, 인플레 상승
    PEAK = "정점"            # 성장 둔화 시작
    CONTRACTION = "수축기"   # 성장 감소, 인플레 하락
    TROUGH = "저점"          # 회복 시작


class MonetaryPolicy(Enum):
    """통화정책 기조"""
    HAWKISH = "긴축적"       # 금리 인상
    NEUTRAL = "중립적"
    DOVISH = "완화적"        # 금리 인하


@dataclass
class MacroSignal:
    """거시경제 신호"""
    indicator: str
    value: float
    signal: str              # bullish, bearish, neutral
    strength: float          # 0-1
    description: str


class MacroAnalyzer:
    """거시경제 분석 클래스"""

    # 지표별 임계값 설정
    THRESHOLDS = {
        'fed_funds_rate': {'low': 2.0, 'high': 4.0},
        'cpi': {'low': 2.0, 'high': 3.5},
        'unemployment_rate': {'low': 4.0, 'high': 6.0},
        'yield_spread': {'warning': 0.0, 'danger': -0.5},
        'vix': {'low': 15, 'high': 25, 'extreme': 35},
        'gdp_growth': {'recession': 0, 'slow': 2.0, 'strong': 3.5},
    }

    def __init__(self):
        """초기화"""
        pass

    def analyze_interest_rates(self, rates_data: pd.DataFrame) -> Dict:
        """
        금리 환경 분석

        Args:
            rates_data: 금리 데이터 (fed_funds_rate, treasury_2y, treasury_10y 등)

        Returns:
            금리 분석 결과
        """
        analysis = {}

        # 최신 금리 수준
        if 'fed_funds_rate' in rates_data.columns:
            current_rate = rates_data['fed_funds_rate'].dropna().iloc[-1]
            rate_change = rates_data['fed_funds_rate'].diff(12).dropna().iloc[-1]  # 1년 변화

            if rate_change > 1.0:
                policy = MonetaryPolicy.HAWKISH
            elif rate_change < -0.5:
                policy = MonetaryPolicy.DOVISH
            else:
                policy = MonetaryPolicy.NEUTRAL

            analysis['current_rate'] = current_rate
            analysis['rate_change_1y'] = rate_change
            analysis['monetary_policy'] = policy.value

        # 수익률 곡선 분석
        if 'treasury_10y' in rates_data.columns and 'treasury_2y' in rates_data.columns:
            spread = rates_data['treasury_10y'] - rates_data['treasury_2y']
            current_spread = spread.dropna().iloc[-1]

            analysis['yield_spread'] = current_spread

            if current_spread < self.THRESHOLDS['yield_spread']['danger']:
                analysis['yield_curve_signal'] = 'Strong Recession Warning'
                analysis['yield_curve_risk'] = 'high'
            elif current_spread < self.THRESHOLDS['yield_spread']['warning']:
                analysis['yield_curve_signal'] = 'Inverted - Recession Risk'
                analysis['yield_curve_risk'] = 'elevated'
            elif current_spread < 0.5:
                analysis['yield_curve_signal'] = 'Flat - Late Cycle'
                analysis['yield_curve_risk'] = 'moderate'
            else:
                analysis['yield_curve_signal'] = 'Normal - Healthy'
                analysis['yield_curve_risk'] = 'low'

        return analysis

    def analyze_inflation(self, inflation_data: pd.DataFrame) -> Dict:
        """
        인플레이션 분석

        Args:
            inflation_data: 인플레이션 데이터 (cpi, core_cpi, pce 등)

        Returns:
            인플레이션 분석 결과
        """
        analysis = {}

        for col in ['cpi', 'core_cpi', 'pce']:
            if col in inflation_data.columns:
                series = inflation_data[col].dropna()
                if len(series) >= 12:
                    # 연간 변화율 계산
                    yoy_change = series.pct_change(12).iloc[-1] * 100

                    analysis[f'{col}_yoy'] = yoy_change

                    # 트렌드 (3개월 이동평균)
                    recent_trend = series.pct_change(3).iloc[-1] * 100 * 4  # 연율화
                    analysis[f'{col}_trend'] = 'Rising' if recent_trend > yoy_change else 'Falling'

        # 인플레이션 환경 판단
        if 'cpi_yoy' in analysis:
            cpi = analysis['cpi_yoy']
            if cpi > 5:
                analysis['inflation_regime'] = 'High Inflation'
                analysis['inflation_risk'] = 'high'
            elif cpi > 3:
                analysis['inflation_regime'] = 'Above Target'
                analysis['inflation_risk'] = 'elevated'
            elif cpi > 1.5:
                analysis['inflation_regime'] = 'Target Range'
                analysis['inflation_risk'] = 'low'
            else:
                analysis['inflation_regime'] = 'Low Inflation/Deflation Risk'
                analysis['inflation_risk'] = 'deflationary'

        return analysis

    def analyze_employment(self, employment_data: pd.DataFrame) -> Dict:
        """
        고용 시장 분석

        Args:
            employment_data: 고용 데이터 (unemployment_rate, nonfarm_payroll 등)

        Returns:
            고용 분석 결과
        """
        analysis = {}

        if 'unemployment_rate' in employment_data.columns:
            series = employment_data['unemployment_rate'].dropna()
            current = series.iloc[-1]
            change_6m = current - series.iloc[-6] if len(series) >= 6 else 0

            analysis['unemployment_rate'] = current
            analysis['unemployment_change_6m'] = change_6m

            # 실업률 상승은 경기 침체 신호
            if change_6m > 0.5:
                analysis['employment_signal'] = 'Deteriorating - Recession Risk'
                analysis['employment_health'] = 'weak'
            elif change_6m > 0:
                analysis['employment_signal'] = 'Softening'
                analysis['employment_health'] = 'moderate'
            elif current < 4.0:
                analysis['employment_signal'] = 'Full Employment'
                analysis['employment_health'] = 'strong'
            else:
                analysis['employment_signal'] = 'Stable'
                analysis['employment_health'] = 'moderate'

        if 'initial_claims' in employment_data.columns:
            series = employment_data['initial_claims'].dropna()
            current = series.iloc[-1]
            ma_4w = series.tail(4).mean()

            analysis['initial_claims'] = current
            analysis['initial_claims_4w_avg'] = ma_4w

            if ma_4w > 300000:
                analysis['claims_signal'] = 'Elevated - Labor Weakness'
            elif ma_4w > 250000:
                analysis['claims_signal'] = 'Moderate'
            else:
                analysis['claims_signal'] = 'Low - Strong Labor Market'

        return analysis

    def identify_economic_cycle(self, macro_data: pd.DataFrame) -> Tuple[EconomicCycle, Dict]:
        """
        현재 경기 사이클 단계 판단

        Args:
            macro_data: 종합 거시경제 데이터

        Returns:
            경기 사이클 단계와 근거
        """
        signals = []
        evidence = {}

        # GDP 성장 추세
        if 'real_gdp' in macro_data.columns:
            gdp = macro_data['real_gdp'].dropna()
            gdp_growth = gdp.pct_change(4).iloc[-1] * 100  # 연간 성장률
            gdp_acceleration = gdp.pct_change(4).diff(4).iloc[-1]  # 가속도

            evidence['gdp_growth'] = gdp_growth
            evidence['gdp_acceleration'] = gdp_acceleration

            if gdp_growth > 2.5 and gdp_acceleration > 0:
                signals.append('expansion')
            elif gdp_growth > 2.0 and gdp_acceleration < 0:
                signals.append('peak')
            elif gdp_growth < 1.0:
                signals.append('contraction')
            else:
                signals.append('trough')

        # 인플레이션 추세
        if 'cpi' in macro_data.columns:
            cpi = macro_data['cpi'].dropna()
            cpi_change = cpi.pct_change(12).iloc[-1] * 100
            cpi_trend = cpi.pct_change(3).iloc[-1] * 100 * 4

            evidence['cpi_yoy'] = cpi_change
            evidence['cpi_trend'] = cpi_trend

            if cpi_change > 3 and cpi_trend > cpi_change:
                signals.append('expansion')
            elif cpi_change > 3 and cpi_trend < cpi_change:
                signals.append('peak')
            elif cpi_change < 2:
                signals.append('contraction' if 'gdp_growth' in evidence and evidence['gdp_growth'] < 2 else 'trough')

        # 실업률 추세
        if 'unemployment_rate' in macro_data.columns:
            unemp = macro_data['unemployment_rate'].dropna()
            unemp_change = unemp.iloc[-1] - unemp.iloc[-12] if len(unemp) >= 12 else 0

            evidence['unemployment_change'] = unemp_change

            if unemp_change < -0.5:
                signals.append('expansion')
            elif unemp_change > 0.5:
                signals.append('contraction')

        # 신호 종합
        from collections import Counter
        signal_counts = Counter(signals)

        if signal_counts:
            dominant = signal_counts.most_common(1)[0][0]
            cycle_map = {
                'expansion': EconomicCycle.EXPANSION,
                'peak': EconomicCycle.PEAK,
                'contraction': EconomicCycle.CONTRACTION,
                'trough': EconomicCycle.TROUGH,
            }
            cycle = cycle_map.get(dominant, EconomicCycle.EXPANSION)
        else:
            cycle = EconomicCycle.EXPANSION

        evidence['signal_counts'] = dict(signal_counts)

        return cycle, evidence

    def get_sector_recommendations(self, cycle: EconomicCycle) -> Dict[str, str]:
        """
        경기 사이클에 따른 섹터 추천

        Args:
            cycle: 현재 경기 사이클

        Returns:
            섹터별 추천 (overweight, neutral, underweight)
        """
        recommendations = {
            EconomicCycle.EXPANSION: {
                'technology': 'overweight',
                'consumer_discretionary': 'overweight',
                'industrials': 'overweight',
                'financials': 'neutral',
                'energy': 'neutral',
                'materials': 'neutral',
                'healthcare': 'underweight',
                'utilities': 'underweight',
                'consumer_staples': 'underweight',
            },
            EconomicCycle.PEAK: {
                'energy': 'overweight',
                'materials': 'overweight',
                'financials': 'neutral',
                'industrials': 'neutral',
                'technology': 'underweight',
                'consumer_discretionary': 'underweight',
                'utilities': 'neutral',
                'healthcare': 'neutral',
                'consumer_staples': 'neutral',
            },
            EconomicCycle.CONTRACTION: {
                'utilities': 'overweight',
                'healthcare': 'overweight',
                'consumer_staples': 'overweight',
                'technology': 'underweight',
                'consumer_discretionary': 'underweight',
                'financials': 'underweight',
                'industrials': 'underweight',
                'energy': 'underweight',
                'materials': 'underweight',
            },
            EconomicCycle.TROUGH: {
                'financials': 'overweight',
                'consumer_discretionary': 'overweight',
                'industrials': 'neutral',
                'technology': 'neutral',
                'materials': 'neutral',
                'energy': 'underweight',
                'utilities': 'underweight',
                'healthcare': 'neutral',
                'consumer_staples': 'underweight',
            },
        }

        return recommendations.get(cycle, {})

    def generate_macro_signals(self, macro_data: pd.DataFrame) -> List[MacroSignal]:
        """
        종합 거시경제 신호 생성

        Args:
            macro_data: 거시경제 데이터

        Returns:
            거시경제 신호 리스트
        """
        signals = []

        # 금리 신호
        if 'yield_spread' in macro_data.columns:
            spread = macro_data['yield_spread'].dropna().iloc[-1]
            if spread < 0:
                signals.append(MacroSignal(
                    indicator='yield_spread',
                    value=spread,
                    signal='bearish',
                    strength=min(abs(spread) / 0.5, 1.0),
                    description=f'수익률 곡선 역전 ({spread:.2f}%) - 경기침체 경고'
                ))
            elif spread < 0.5:
                signals.append(MacroSignal(
                    indicator='yield_spread',
                    value=spread,
                    signal='neutral',
                    strength=0.5,
                    description=f'수익률 곡선 평탄화 ({spread:.2f}%) - 후기 사이클'
                ))
            else:
                signals.append(MacroSignal(
                    indicator='yield_spread',
                    value=spread,
                    signal='bullish',
                    strength=min(spread / 2.0, 1.0),
                    description=f'수익률 곡선 정상 ({spread:.2f}%)'
                ))

        # VIX 신호
        if 'vix' in macro_data.columns:
            vix = macro_data['vix'].dropna().iloc[-1]
            if vix > self.THRESHOLDS['vix']['extreme']:
                signals.append(MacroSignal(
                    indicator='vix',
                    value=vix,
                    signal='bearish',
                    strength=1.0,
                    description=f'극단적 공포 (VIX: {vix:.1f}) - 시장 패닉'
                ))
            elif vix > self.THRESHOLDS['vix']['high']:
                signals.append(MacroSignal(
                    indicator='vix',
                    value=vix,
                    signal='neutral',
                    strength=0.6,
                    description=f'높은 변동성 (VIX: {vix:.1f}) - 불확실성 증가'
                ))
            else:
                signals.append(MacroSignal(
                    indicator='vix',
                    value=vix,
                    signal='bullish',
                    strength=0.7,
                    description=f'낮은 변동성 (VIX: {vix:.1f}) - 안정적 시장'
                ))

        # 인플레이션 신호
        if 'cpi' in macro_data.columns:
            cpi = macro_data['cpi'].dropna()
            cpi_yoy = cpi.pct_change(12).iloc[-1] * 100 if len(cpi) >= 12 else cpi.iloc[-1]

            if cpi_yoy > 4:
                signals.append(MacroSignal(
                    indicator='cpi',
                    value=cpi_yoy,
                    signal='bearish',
                    strength=min(cpi_yoy / 6, 1.0),
                    description=f'높은 인플레이션 ({cpi_yoy:.1f}%) - 긴축 압력'
                ))
            elif cpi_yoy < 1.5:
                signals.append(MacroSignal(
                    indicator='cpi',
                    value=cpi_yoy,
                    signal='neutral',
                    strength=0.5,
                    description=f'낮은 인플레이션 ({cpi_yoy:.1f}%) - 디플레이션 우려'
                ))
            else:
                signals.append(MacroSignal(
                    indicator='cpi',
                    value=cpi_yoy,
                    signal='bullish',
                    strength=0.8,
                    description=f'적정 인플레이션 ({cpi_yoy:.1f}%)'
                ))

        return signals

    def get_summary(self, macro_data: pd.DataFrame) -> Dict:
        """
        거시경제 분석 요약

        Args:
            macro_data: 거시경제 데이터

        Returns:
            종합 분석 요약
        """
        # 경기 사이클 판단
        cycle, cycle_evidence = self.identify_economic_cycle(macro_data)

        # 신호 생성
        signals = self.generate_macro_signals(macro_data)

        # 섹터 추천
        sector_recs = self.get_sector_recommendations(cycle)

        # 불리쉬/베어리쉬 점수
        bullish_count = sum(1 for s in signals if s.signal == 'bullish')
        bearish_count = sum(1 for s in signals if s.signal == 'bearish')
        total_signals = len(signals)

        if total_signals > 0:
            sentiment_score = (bullish_count - bearish_count) / total_signals
        else:
            sentiment_score = 0

        return {
            'economic_cycle': cycle.value,
            'cycle_evidence': cycle_evidence,
            'signals': [
                {
                    'indicator': s.indicator,
                    'value': s.value,
                    'signal': s.signal,
                    'strength': s.strength,
                    'description': s.description,
                }
                for s in signals
            ],
            'sector_recommendations': sector_recs,
            'sentiment_score': sentiment_score,  # -1 to 1
            'overall_outlook': 'Bullish' if sentiment_score > 0.2 else ('Bearish' if sentiment_score < -0.2 else 'Neutral'),
        }
