"""
섹터 회전 분석 모듈
섹터별 순환 패턴 및 자금 흐름 분석
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class MarketPhase(Enum):
    """시장 국면"""
    EARLY_EXPANSION = "초기 확장"
    LATE_EXPANSION = "후기 확장"
    EARLY_CONTRACTION = "초기 수축"
    LATE_CONTRACTION = "후기 수축"
    RECOVERY = "회복"
    UNKNOWN = "판단 불가"


@dataclass
class SectorPerformance:
    """섹터 성과"""
    name: str
    code: str
    return_1w: float
    return_1m: float
    return_3m: float
    momentum_score: float
    relative_strength: float
    rank: int = 0


@dataclass
class RotationAnalysis:
    """회전 분석 결과"""
    current_phase: MarketPhase
    leading_sectors: List[str]
    lagging_sectors: List[str]
    rotation_signal: str
    sector_performances: List[SectorPerformance]
    analysis_date: datetime = field(default_factory=datetime.now)


# 섹터 ETF 정의
SECTOR_ETFS = {
    '반도체': {'code': '091160', 'name': 'KODEX 반도체'},
    '2차전지': {'code': '305720', 'name': 'KODEX 2차전지'},
    '바이오': {'code': '244580', 'name': 'KODEX 바이오'},
    '은행': {'code': '091170', 'name': 'KODEX 은행'},
    'IT': {'code': '098560', 'name': 'KODEX IT'},
    '자동차': {'code': '091180', 'name': 'KODEX 자동차'},
    '건설': {'code': '117700', 'name': 'KODEX 건설'},
    '화학': {'code': '117460', 'name': 'KODEX 화학'},
    '철강': {'code': '117680', 'name': 'KODEX 철강'},
    '에너지': {'code': '117690', 'name': 'KODEX 에너지화학'},
}

# 경기 순환별 선호 섹터
SECTOR_CYCLE = {
    MarketPhase.EARLY_EXPANSION: ['IT', '반도체', '자동차', '건설'],
    MarketPhase.LATE_EXPANSION: ['에너지', '철강', '화학', '바이오'],
    MarketPhase.EARLY_CONTRACTION: ['은행', '바이오', '유틸리티'],
    MarketPhase.LATE_CONTRACTION: ['유틸리티', '소비재', '통신'],
    MarketPhase.RECOVERY: ['2차전지', 'IT', '반도체', '건설'],
}


class SectorRotationAnalyzer:
    """섹터 회전 분석기"""

    def __init__(self):
        self.sectors = SECTOR_ETFS
        self.cycle_map = SECTOR_CYCLE

    def analyze_sector_rotation(
        self,
        sector_prices: Dict[str, pd.Series],
        benchmark_prices: pd.Series = None
    ) -> RotationAnalysis:
        """
        섹터 회전 분석

        Args:
            sector_prices: {섹터명: 가격시계열} 딕셔너리
            benchmark_prices: 벤치마크 가격 (상대강도 계산용)

        Returns:
            RotationAnalysis
        """
        performances = []

        for sector_name, prices in sector_prices.items():
            if prices is None or len(prices) < 22:
                continue

            perf = self._calculate_sector_performance(
                sector_name, prices, benchmark_prices
            )
            performances.append(perf)

        # 순위 매기기 (모멘텀 점수 기준)
        performances.sort(key=lambda x: x.momentum_score, reverse=True)
        for i, perf in enumerate(performances):
            perf.rank = i + 1

        # 선도/후행 섹터 판별
        leading = [p.name for p in performances[:3]]
        lagging = [p.name for p in performances[-3:]]

        # 시장 국면 판단
        current_phase = self._determine_market_phase(performances)

        # 회전 신호 생성
        rotation_signal = self._generate_rotation_signal(performances, current_phase)

        return RotationAnalysis(
            current_phase=current_phase,
            leading_sectors=leading,
            lagging_sectors=lagging,
            rotation_signal=rotation_signal,
            sector_performances=performances
        )

    def _calculate_sector_performance(
        self,
        name: str,
        prices: pd.Series,
        benchmark_prices: pd.Series = None
    ) -> SectorPerformance:
        """섹터 성과 계산"""
        current = prices.iloc[-1]

        # 수익률 계산
        return_1w = (current / prices.iloc[-6] - 1) * 100 if len(prices) >= 6 else 0
        return_1m = (current / prices.iloc[-22] - 1) * 100 if len(prices) >= 22 else 0
        return_3m = (current / prices.iloc[-66] - 1) * 100 if len(prices) >= 66 else 0

        # 모멘텀 점수 (가중 평균)
        momentum_score = return_1w * 0.2 + return_1m * 0.3 + return_3m * 0.5

        # 상대강도 (벤치마크 대비)
        relative_strength = 0
        if benchmark_prices is not None and len(benchmark_prices) >= 22:
            bench_return = (benchmark_prices.iloc[-1] / benchmark_prices.iloc[-22] - 1) * 100
            relative_strength = return_1m - bench_return

        code = self.sectors.get(name, {}).get('code', '')

        return SectorPerformance(
            name=name,
            code=code,
            return_1w=return_1w,
            return_1m=return_1m,
            return_3m=return_3m,
            momentum_score=momentum_score,
            relative_strength=relative_strength
        )

    def _determine_market_phase(self, performances: List[SectorPerformance]) -> MarketPhase:
        """시장 국면 판단"""
        if not performances:
            return MarketPhase.UNKNOWN

        top_sectors = [p.name for p in performances[:3]]

        # 각 국면별 점수 계산
        phase_scores = {}
        for phase, preferred in self.cycle_map.items():
            score = sum(1 for s in top_sectors if s in preferred)
            phase_scores[phase] = score

        # 가장 높은 점수의 국면
        if phase_scores:
            best_phase = max(phase_scores, key=phase_scores.get)
            if phase_scores[best_phase] >= 2:
                return best_phase

        # 모멘텀 기반 판단
        avg_momentum = np.mean([p.momentum_score for p in performances])

        if avg_momentum > 5:
            return MarketPhase.LATE_EXPANSION
        elif avg_momentum > 0:
            return MarketPhase.EARLY_EXPANSION
        elif avg_momentum > -5:
            return MarketPhase.EARLY_CONTRACTION
        else:
            return MarketPhase.LATE_CONTRACTION

    def _generate_rotation_signal(
        self,
        performances: List[SectorPerformance],
        phase: MarketPhase
    ) -> str:
        """회전 신호 생성"""
        if not performances:
            return "데이터 부족"

        top = performances[:3]
        bottom = performances[-3:]

        # 상위 섹터의 평균 수익률
        top_avg = np.mean([p.return_1m for p in top])
        # 하위 섹터의 평균 수익률
        bottom_avg = np.mean([p.return_1m for p in bottom])

        spread = top_avg - bottom_avg

        if spread > 10:
            return f"강한 로테이션 진행 중 - {', '.join([p.name for p in top])} 선호"
        elif spread > 5:
            return f"로테이션 진행 - {top[0].name} 강세"
        elif spread > 0:
            return "소폭 차별화 - 선별적 접근 권장"
        else:
            return "섹터 간 차별화 미미 - 관망 권장"

    def get_recommended_sectors(self, phase: MarketPhase) -> List[str]:
        """시장 국면에 따른 추천 섹터"""
        return self.cycle_map.get(phase, [])

    def calculate_sector_momentum_ranking(
        self,
        sector_prices: Dict[str, pd.Series]
    ) -> pd.DataFrame:
        """섹터 모멘텀 랭킹 테이블 생성"""
        data = []

        for sector_name, prices in sector_prices.items():
            if prices is None or len(prices) < 66:
                continue

            current = prices.iloc[-1]

            row = {
                '섹터': sector_name,
                '1주': f"{(current / prices.iloc[-6] - 1) * 100:+.1f}%" if len(prices) >= 6 else "N/A",
                '1개월': f"{(current / prices.iloc[-22] - 1) * 100:+.1f}%" if len(prices) >= 22 else "N/A",
                '3개월': f"{(current / prices.iloc[-66] - 1) * 100:+.1f}%" if len(prices) >= 66 else "N/A",
            }

            # 모멘텀 점수
            r1w = (current / prices.iloc[-6] - 1) * 100 if len(prices) >= 6 else 0
            r1m = (current / prices.iloc[-22] - 1) * 100 if len(prices) >= 22 else 0
            r3m = (current / prices.iloc[-66] - 1) * 100 if len(prices) >= 66 else 0

            row['모멘텀 점수'] = r1w * 0.2 + r1m * 0.3 + r3m * 0.5
            data.append(row)

        df = pd.DataFrame(data)
        if not df.empty:
            df = df.sort_values('모멘텀 점수', ascending=False)
            df['순위'] = range(1, len(df) + 1)
            df['모멘텀 점수'] = df['모멘텀 점수'].apply(lambda x: f"{x:.1f}")

        return df

    def get_rotation_insights(self, analysis: RotationAnalysis) -> List[str]:
        """회전 분석 인사이트 생성"""
        insights = []

        # 국면 관련
        insights.append(f"현재 시장 국면: **{analysis.current_phase.value}**")

        # 선도 섹터
        if analysis.leading_sectors:
            insights.append(f"선도 섹터: {', '.join(analysis.leading_sectors)}")

        # 후행 섹터
        if analysis.lagging_sectors:
            insights.append(f"후행 섹터: {', '.join(analysis.lagging_sectors)}")

        # 추천 섹터
        recommended = self.get_recommended_sectors(analysis.current_phase)
        if recommended:
            insights.append(f"이 국면에서 주목할 섹터: {', '.join(recommended[:3])}")

        # 회전 신호
        insights.append(f"로테이션 신호: {analysis.rotation_signal}")

        return insights


# 싱글톤 인스턴스
sector_rotation_analyzer = SectorRotationAnalyzer()
