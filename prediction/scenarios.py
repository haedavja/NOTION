"""
시나리오 분석 모듈
다양한 경제 시나리오별 시장 전망을 분석합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class ScenarioType(Enum):
    """시나리오 유형"""
    BASE = "기본 시나리오"
    BULL = "낙관 시나리오"
    BEAR = "비관 시나리오"
    STAGFLATION = "스태그플레이션"
    SOFT_LANDING = "연착륙"
    HARD_LANDING = "경착륙"
    RECOVERY = "회복"


@dataclass
class Scenario:
    """시나리오 정의"""
    name: str
    type: ScenarioType
    probability: float
    description: str
    assumptions: Dict[str, str]
    market_impact: Dict[str, float]
    recommended_allocation: Dict[str, float]


class ScenarioAnalyzer:
    """시나리오 분석 클래스"""

    # 기본 시나리오 템플릿
    SCENARIO_TEMPLATES = {
        ScenarioType.SOFT_LANDING: {
            'description': '인플레이션 완화, 경기 침체 없이 성장 둔화',
            'assumptions': {
                'gdp_growth': '1.5-2.5%',
                'inflation': '2-3%',
                'fed_rate': '4-5%',
                'unemployment': '4-4.5%',
            },
            'market_impact': {
                'equities': 0.10,
                'bonds': 0.05,
                'gold': 0.0,
                'cash': 0.02,
            },
            'allocation': {
                'equities': 0.60,
                'bonds': 0.30,
                'gold': 0.05,
                'cash': 0.05,
            },
        },
        ScenarioType.HARD_LANDING: {
            'description': '경기 침체, 고용 악화, 기업 실적 부진',
            'assumptions': {
                'gdp_growth': '-1 to 0%',
                'inflation': '1-2%',
                'fed_rate': '2-3%',
                'unemployment': '5-7%',
            },
            'market_impact': {
                'equities': -0.20,
                'bonds': 0.10,
                'gold': 0.15,
                'cash': 0.03,
            },
            'allocation': {
                'equities': 0.30,
                'bonds': 0.40,
                'gold': 0.15,
                'cash': 0.15,
            },
        },
        ScenarioType.STAGFLATION: {
            'description': '높은 인플레이션 + 경기 침체',
            'assumptions': {
                'gdp_growth': '0-1%',
                'inflation': '4-6%',
                'fed_rate': '5-6%',
                'unemployment': '5-6%',
            },
            'market_impact': {
                'equities': -0.15,
                'bonds': -0.10,
                'gold': 0.20,
                'cash': 0.05,
            },
            'allocation': {
                'equities': 0.25,
                'bonds': 0.25,
                'gold': 0.25,
                'cash': 0.25,
            },
        },
        ScenarioType.BULL: {
            'description': '강한 경제 성장, 기업 실적 호조',
            'assumptions': {
                'gdp_growth': '3%+',
                'inflation': '2-3%',
                'fed_rate': '3-4%',
                'unemployment': '<4%',
            },
            'market_impact': {
                'equities': 0.20,
                'bonds': -0.05,
                'gold': -0.05,
                'cash': 0.02,
            },
            'allocation': {
                'equities': 0.75,
                'bonds': 0.15,
                'gold': 0.05,
                'cash': 0.05,
            },
        },
        ScenarioType.RECOVERY: {
            'description': '경기 저점 통과 후 회복 국면',
            'assumptions': {
                'gdp_growth': '2-3%',
                'inflation': '2-3%',
                'fed_rate': '3-4%',
                'unemployment': '4-5% (개선 중)',
            },
            'market_impact': {
                'equities': 0.15,
                'bonds': 0.0,
                'gold': 0.0,
                'cash': 0.02,
            },
            'allocation': {
                'equities': 0.65,
                'bonds': 0.25,
                'gold': 0.05,
                'cash': 0.05,
            },
        },
    }

    # 자산별 섹터 추천 (시나리오별)
    SECTOR_RECOMMENDATIONS = {
        ScenarioType.SOFT_LANDING: {
            'overweight': ['technology', 'healthcare', 'consumer_discretionary'],
            'neutral': ['financials', 'industrials', 'communication'],
            'underweight': ['utilities', 'energy', 'materials'],
        },
        ScenarioType.HARD_LANDING: {
            'overweight': ['utilities', 'healthcare', 'consumer_staples'],
            'neutral': ['communication'],
            'underweight': ['technology', 'financials', 'consumer_discretionary', 'industrials'],
        },
        ScenarioType.STAGFLATION: {
            'overweight': ['energy', 'materials', 'utilities'],
            'neutral': ['healthcare', 'consumer_staples'],
            'underweight': ['technology', 'consumer_discretionary', 'financials', 'real_estate'],
        },
        ScenarioType.BULL: {
            'overweight': ['technology', 'consumer_discretionary', 'financials', 'industrials'],
            'neutral': ['healthcare', 'materials', 'communication'],
            'underweight': ['utilities', 'consumer_staples'],
        },
        ScenarioType.RECOVERY: {
            'overweight': ['financials', 'industrials', 'consumer_discretionary'],
            'neutral': ['technology', 'materials', 'energy'],
            'underweight': ['utilities', 'consumer_staples'],
        },
    }

    # 섹터 이름 한글 변환
    SECTOR_NAME_KR = {
        'technology': '기술',
        'healthcare': '헬스케어',
        'consumer_discretionary': '경기소비재',
        'consumer_staples': '필수소비재',
        'financials': '금융',
        'industrials': '산업재',
        'communication': '통신서비스',
        'utilities': '유틸리티',
        'energy': '에너지',
        'materials': '소재',
        'real_estate': '부동산',
    }

    def __init__(self):
        """초기화"""
        self.scenarios: List[Scenario] = []

    def estimate_scenario_probabilities(self,
                                        macro_data: Dict,
                                        flow_data: Dict,
                                        sentiment_data: Dict) -> Dict[ScenarioType, float]:
        """
        시나리오 확률 추정

        Args:
            macro_data: 거시경제 분석 결과
            flow_data: 자금흐름 분석 결과
            sentiment_data: 센티먼트 분석 결과

        Returns:
            시나리오별 확률
        """
        probabilities = {
            ScenarioType.SOFT_LANDING: 0.0,
            ScenarioType.HARD_LANDING: 0.0,
            ScenarioType.STAGFLATION: 0.0,
            ScenarioType.BULL: 0.0,
            ScenarioType.RECOVERY: 0.0,
        }

        # 거시경제 지표 기반 확률 조정
        cycle = macro_data.get('economic_cycle', '')
        signals = macro_data.get('signals', [])

        # 경기 사이클 기반
        if '확장' in cycle:
            probabilities[ScenarioType.BULL] += 0.3
            probabilities[ScenarioType.SOFT_LANDING] += 0.2
        elif '정점' in cycle:
            probabilities[ScenarioType.SOFT_LANDING] += 0.25
            probabilities[ScenarioType.HARD_LANDING] += 0.15
        elif '수축' in cycle:
            probabilities[ScenarioType.HARD_LANDING] += 0.3
            probabilities[ScenarioType.STAGFLATION] += 0.15
        elif '저점' in cycle:
            probabilities[ScenarioType.RECOVERY] += 0.35
            probabilities[ScenarioType.SOFT_LANDING] += 0.15

        # 인플레이션 신호
        for signal in signals:
            if signal.get('indicator') == 'cpi':
                value = signal.get('value', 2.5)
                if value > 4:
                    probabilities[ScenarioType.STAGFLATION] += 0.15
                    probabilities[ScenarioType.HARD_LANDING] += 0.1
                elif value < 2:
                    probabilities[ScenarioType.SOFT_LANDING] += 0.1
                    probabilities[ScenarioType.BULL] += 0.1

        # 수익률 곡선 신호
        for signal in signals:
            if signal.get('indicator') == 'yield_spread':
                if signal.get('signal') == 'bearish':
                    probabilities[ScenarioType.HARD_LANDING] += 0.2
                    probabilities[ScenarioType.STAGFLATION] += 0.1
                elif signal.get('signal') == 'bullish':
                    probabilities[ScenarioType.SOFT_LANDING] += 0.15
                    probabilities[ScenarioType.BULL] += 0.1

        # 자금흐름 기반
        risk_regime = flow_data.get('risk_regime', '')
        if 'Risk-On' in risk_regime or '선호' in risk_regime:
            probabilities[ScenarioType.BULL] += 0.15
            probabilities[ScenarioType.RECOVERY] += 0.1
        elif 'Risk-Off' in risk_regime or '회피' in risk_regime:
            probabilities[ScenarioType.HARD_LANDING] += 0.15
            probabilities[ScenarioType.STAGFLATION] += 0.1

        # 센티먼트 기반
        overall = sentiment_data.get('overall_analysis', {})
        composite_score = overall.get('composite_score', 0)

        if composite_score > 0.2:
            probabilities[ScenarioType.BULL] += 0.1
            probabilities[ScenarioType.RECOVERY] += 0.1
        elif composite_score < -0.2:
            probabilities[ScenarioType.HARD_LANDING] += 0.1
            probabilities[ScenarioType.STAGFLATION] += 0.05

        # 정규화
        total = sum(probabilities.values())
        if total > 0:
            probabilities = {k: v / total for k, v in probabilities.items()}

        return probabilities

    def generate_scenarios(self, probabilities: Dict[ScenarioType, float]) -> List[Scenario]:
        """
        시나리오 생성

        Args:
            probabilities: 시나리오별 확률

        Returns:
            시나리오 리스트
        """
        scenarios = []

        for scenario_type, prob in probabilities.items():
            if scenario_type not in self.SCENARIO_TEMPLATES:
                continue

            template = self.SCENARIO_TEMPLATES[scenario_type]

            scenario = Scenario(
                name=scenario_type.value,
                type=scenario_type,
                probability=prob,
                description=template['description'],
                assumptions=template['assumptions'],
                market_impact=template['market_impact'],
                recommended_allocation=template['allocation'],
            )

            scenarios.append(scenario)

        # 확률 순으로 정렬
        scenarios.sort(key=lambda x: x.probability, reverse=True)
        self.scenarios = scenarios

        return scenarios

    def get_expected_returns(self, scenarios: List[Scenario]) -> Dict[str, float]:
        """
        확률 가중 기대 수익률 계산

        Args:
            scenarios: 시나리오 리스트

        Returns:
            자산별 기대 수익률
        """
        expected_returns = {}
        assets = ['equities', 'bonds', 'gold', 'cash']

        for asset in assets:
            weighted_return = sum(
                s.probability * s.market_impact.get(asset, 0)
                for s in scenarios
            )
            expected_returns[asset] = weighted_return * 100  # %로 변환

        return expected_returns

    def get_optimal_allocation(self, scenarios: List[Scenario]) -> Dict[str, float]:
        """
        확률 가중 최적 자산 배분 계산

        Args:
            scenarios: 시나리오 리스트

        Returns:
            자산별 권장 비중
        """
        allocation = {}
        assets = ['equities', 'bonds', 'gold', 'cash']

        for asset in assets:
            weighted_alloc = sum(
                s.probability * s.recommended_allocation.get(asset, 0)
                for s in scenarios
            )
            allocation[asset] = weighted_alloc * 100  # %로 변환

        return allocation

    def get_sector_recommendations(self, scenarios: List[Scenario]) -> Dict:
        """
        시나리오 가중 섹터 추천

        Args:
            scenarios: 시나리오 리스트

        Returns:
            섹터별 추천
        """
        sector_scores = {}

        for scenario in scenarios:
            if scenario.type not in self.SECTOR_RECOMMENDATIONS:
                continue

            recs = self.SECTOR_RECOMMENDATIONS[scenario.type]
            prob = scenario.probability

            for sector in recs.get('overweight', []):
                sector_scores[sector] = sector_scores.get(sector, 0) + prob * 1
            for sector in recs.get('neutral', []):
                sector_scores[sector] = sector_scores.get(sector, 0) + prob * 0
            for sector in recs.get('underweight', []):
                sector_scores[sector] = sector_scores.get(sector, 0) + prob * (-1)

        # 점수 기반 분류
        sorted_sectors = sorted(sector_scores.items(), key=lambda x: x[1], reverse=True)

        overweight = [self.SECTOR_NAME_KR.get(s[0], s[0]) for s in sorted_sectors if s[1] > 0.2]
        underweight = [self.SECTOR_NAME_KR.get(s[0], s[0]) for s in sorted_sectors if s[1] < -0.2]
        neutral = [self.SECTOR_NAME_KR.get(s[0], s[0]) for s in sorted_sectors if -0.2 <= s[1] <= 0.2]

        return {
            'overweight': overweight,
            'neutral': neutral,
            'underweight': underweight,
            'scores': {self.SECTOR_NAME_KR.get(k, k): v for k, v in sorted_sectors},
        }

    def sensitivity_analysis(self, scenarios: List[Scenario],
                            factor: str,
                            variations: List[float]) -> pd.DataFrame:
        """
        민감도 분석

        Args:
            scenarios: 시나리오 리스트
            factor: 분석 요소 (예: 'equities')
            variations: 변동 범위

        Returns:
            민감도 분석 결과
        """
        results = []

        base_scenario = max(scenarios, key=lambda x: x.probability)
        base_impact = base_scenario.market_impact.get(factor, 0)

        for variation in variations:
            adjusted_impact = base_impact + variation

            results.append({
                'variation': variation * 100,
                'base_impact': base_impact * 100,
                'adjusted_impact': adjusted_impact * 100,
                'scenario': base_scenario.name,
            })

        return pd.DataFrame(results)

    def get_summary(self, macro_data: Dict,
                   flow_data: Dict,
                   sentiment_data: Dict) -> Dict:
        """
        시나리오 분석 요약

        Args:
            macro_data: 거시경제 분석 결과
            flow_data: 자금흐름 분석 결과
            sentiment_data: 센티먼트 분석 결과

        Returns:
            종합 요약
        """
        # 확률 추정
        probabilities = self.estimate_scenario_probabilities(
            macro_data, flow_data, sentiment_data
        )

        # 시나리오 생성
        scenarios = self.generate_scenarios(probabilities)

        # 기대 수익률
        expected_returns = self.get_expected_returns(scenarios)

        # 최적 배분
        optimal_allocation = self.get_optimal_allocation(scenarios)

        # 섹터 추천
        sector_recs = self.get_sector_recommendations(scenarios)

        # 가장 가능성 높은 시나리오
        most_likely = scenarios[0] if scenarios else None

        return {
            'most_likely_scenario': {
                'name': most_likely.name if most_likely else 'Unknown',
                'probability': most_likely.probability * 100 if most_likely else 0,
                'description': most_likely.description if most_likely else '',
            },
            'all_scenarios': [
                {
                    'name': s.name,
                    'probability': s.probability * 100,
                    'description': s.description,
                }
                for s in scenarios
            ],
            'expected_returns': expected_returns,
            'recommended_allocation': optimal_allocation,
            'sector_recommendations': sector_recs,
            'key_assumptions': most_likely.assumptions if most_likely else {},
            'risk_factors': self._identify_risk_factors(scenarios),
        }

    def _identify_risk_factors(self, scenarios: List[Scenario]) -> List[str]:
        """주요 리스크 요인 식별"""
        risks = []

        for scenario in scenarios:
            if scenario.probability > 0.2:  # 20% 이상 확률인 시나리오
                if scenario.type == ScenarioType.HARD_LANDING:
                    risks.append("경기 침체 리스크 상승")
                elif scenario.type == ScenarioType.STAGFLATION:
                    risks.append("스태그플레이션 가능성")

        # 기본 리스크
        risks.extend([
            "지정학적 리스크",
            "중앙은행 정책 불확실성",
            "기업 실적 전망 변화",
        ])

        return risks[:5]  # 상위 5개


def compare_scenarios(scenario1: Scenario, scenario2: Scenario) -> Dict:
    """
    두 시나리오 비교

    Args:
        scenario1: 첫 번째 시나리오
        scenario2: 두 번째 시나리오

    Returns:
        비교 결과
    """
    comparison = {
        'scenarios': [scenario1.name, scenario2.name],
        'probability_diff': scenario1.probability - scenario2.probability,
        'impact_comparison': {},
        'allocation_comparison': {},
    }

    for asset in ['equities', 'bonds', 'gold', 'cash']:
        impact1 = scenario1.market_impact.get(asset, 0)
        impact2 = scenario2.market_impact.get(asset, 0)
        comparison['impact_comparison'][asset] = {
            scenario1.name: impact1 * 100,
            scenario2.name: impact2 * 100,
            'difference': (impact1 - impact2) * 100,
        }

        alloc1 = scenario1.recommended_allocation.get(asset, 0)
        alloc2 = scenario2.recommended_allocation.get(asset, 0)
        comparison['allocation_comparison'][asset] = {
            scenario1.name: alloc1 * 100,
            scenario2.name: alloc2 * 100,
            'difference': (alloc1 - alloc2) * 100,
        }

    return comparison
