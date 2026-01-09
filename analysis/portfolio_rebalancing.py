"""
포트폴리오 리밸런싱 모듈
========================

포트폴리오 분석, 리밸런싱 제안, 최적 비중 계산을 제공합니다.

주요 기능:
---------
- PortfolioAnalyzer: 포트폴리오 분석
- RebalancingCalculator: 리밸런싱 계산
- OptimalWeightCalculator: 최적 비중 계산

사용 예시:
---------
    from analysis.portfolio_rebalancing import (
        PortfolioAnalyzer,
        calculate_rebalancing_actions,
        render_rebalancing_dashboard
    )

    # 포트폴리오 분석
    analyzer = PortfolioAnalyzer(holdings)
    analysis = analyzer.analyze()

    # 리밸런싱 액션 계산
    actions = calculate_rebalancing_actions(
        holdings=holdings,
        target_weights=target_weights,
        total_value=10000000
    )

유지보수 노트:
------------
- 리밸런싱 전략 추가: REBALANCING_STRATEGIES에 새 전략 추가
- 섹터 분류 변경: SECTOR_CATEGORIES 수정
- 기본 비중 변경: DEFAULT_ALLOCATIONS 수정
"""

import streamlit as st
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
import json
import os
import logging
import math

logger = logging.getLogger(__name__)


# ============ 설정 ============

PORTFOLIO_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'portfolios'
)


# ============ 열거형 및 상수 ============

class RebalancingStrategy(Enum):
    """리밸런싱 전략"""
    THRESHOLD = "threshold"           # 임계값 기반 (비중 이탈 시)
    CALENDAR = "calendar"             # 정기 리밸런싱
    TACTICAL = "tactical"             # 전술적 리밸런싱 (시장 상황)
    CONSTANT_MIX = "constant_mix"     # 고정 비중 유지


class AssetClass(Enum):
    """자산 분류"""
    STOCK = "주식"
    BOND = "채권"
    CASH = "현금"
    REAL_ESTATE = "부동산"
    COMMODITY = "원자재"
    CRYPTO = "암호화폐"


# 섹터 분류
SECTOR_CATEGORIES = {
    '반도체': 'technology',
    'IT': 'technology',
    '2차전지': 'technology',
    '바이오': 'healthcare',
    '제약': 'healthcare',
    '자동차': 'consumer_cyclical',
    '화학': 'basic_materials',
    '금융': 'financial',
    '은행': 'financial',
    '건설': 'industrials',
    '에너지': 'energy',
    '엔터': 'communication',
    '지주': 'financial',
    '유통': 'consumer_defensive',
    '식품': 'consumer_defensive',
}

# 기본 섹터 비중 (보수적/균형/공격적)
DEFAULT_ALLOCATIONS = {
    'conservative': {
        'technology': 0.15,
        'healthcare': 0.10,
        'financial': 0.20,
        'consumer_defensive': 0.20,
        'industrials': 0.15,
        'basic_materials': 0.10,
        'energy': 0.05,
        'communication': 0.05
    },
    'balanced': {
        'technology': 0.25,
        'healthcare': 0.15,
        'financial': 0.15,
        'consumer_defensive': 0.10,
        'industrials': 0.15,
        'basic_materials': 0.10,
        'energy': 0.05,
        'communication': 0.05
    },
    'aggressive': {
        'technology': 0.40,
        'healthcare': 0.20,
        'financial': 0.10,
        'consumer_defensive': 0.05,
        'industrials': 0.10,
        'basic_materials': 0.05,
        'energy': 0.05,
        'communication': 0.05
    }
}


# ============ 데이터 클래스 ============

@dataclass
class Holding:
    """보유 종목"""
    stock_code: str
    stock_name: str
    quantity: int
    avg_price: float
    current_price: float
    sector: str = ""

    @property
    def current_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_price

    @property
    def profit_loss(self) -> float:
        return self.current_value - self.cost_basis

    @property
    def profit_loss_percent(self) -> float:
        if self.cost_basis == 0:
            return 0
        return (self.profit_loss / self.cost_basis) * 100


@dataclass
class Portfolio:
    """포트폴리오"""
    name: str
    holdings: List[Holding]
    cash: float = 0
    created_at: str = ""
    updated_at: str = ""

    @property
    def total_value(self) -> float:
        holdings_value = sum(h.current_value for h in self.holdings)
        return holdings_value + self.cash

    @property
    def holdings_value(self) -> float:
        return sum(h.current_value for h in self.holdings)


@dataclass
class RebalancingAction:
    """리밸런싱 액션"""
    stock_code: str
    stock_name: str
    action: str  # 'buy' or 'sell'
    quantity: int
    current_weight: float
    target_weight: float
    amount: float  # 거래 금액

    @property
    def weight_change(self) -> float:
        return self.target_weight - self.current_weight


@dataclass
class PortfolioAnalysis:
    """포트폴리오 분석 결과"""
    total_value: float
    sector_weights: Dict[str, float]
    concentration_index: float  # HHI
    top_holdings: List[Tuple[str, float]]  # (종목명, 비중)
    diversification_score: float  # 0-100
    risk_level: str  # 'low', 'medium', 'high'
    recommendations: List[str]


# ============ 저장/로드 ============

def ensure_portfolio_dir():
    """포트폴리오 디렉토리 확인"""
    if not os.path.exists(PORTFOLIO_DATA_DIR):
        os.makedirs(PORTFOLIO_DATA_DIR, exist_ok=True)


def save_portfolio(portfolio: Portfolio) -> bool:
    """포트폴리오 저장"""
    try:
        ensure_portfolio_dir()
        portfolio.updated_at = datetime.now().isoformat()

        data = {
            'name': portfolio.name,
            'cash': portfolio.cash,
            'created_at': portfolio.created_at,
            'updated_at': portfolio.updated_at,
            'holdings': [asdict(h) for h in portfolio.holdings]
        }

        filepath = os.path.join(PORTFOLIO_DATA_DIR, f"{portfolio.name}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return True
    except Exception as e:
        logger.error(f"포트폴리오 저장 실패: {e}")
        return False


def load_portfolio(name: str) -> Optional[Portfolio]:
    """포트폴리오 로드"""
    try:
        filepath = os.path.join(PORTFOLIO_DATA_DIR, f"{name}.json")
        if not os.path.exists(filepath):
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        holdings = [Holding(**h) for h in data.get('holdings', [])]

        return Portfolio(
            name=data['name'],
            holdings=holdings,
            cash=data.get('cash', 0),
            created_at=data.get('created_at', ''),
            updated_at=data.get('updated_at', '')
        )
    except Exception as e:
        logger.error(f"포트폴리오 로드 실패: {e}")
        return None


def list_portfolios() -> List[str]:
    """저장된 포트폴리오 목록"""
    ensure_portfolio_dir()
    portfolios = []

    for filename in os.listdir(PORTFOLIO_DATA_DIR):
        if filename.endswith('.json'):
            portfolios.append(filename[:-5])

    return portfolios


# ============ 분석 클래스 ============

class PortfolioAnalyzer:
    """
    포트폴리오 분석기

    Usage:
        analyzer = PortfolioAnalyzer(portfolio)
        analysis = analyzer.analyze()
    """

    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio

    def analyze(self) -> PortfolioAnalysis:
        """포트폴리오 분석"""
        total_value = self.portfolio.total_value
        holdings = self.portfolio.holdings

        # 섹터별 비중 계산
        sector_weights = self._calculate_sector_weights()

        # 집중도 (HHI 지수)
        concentration_index = self._calculate_hhi()

        # 상위 보유 종목
        top_holdings = self._get_top_holdings(5)

        # 분산 점수
        diversification_score = self._calculate_diversification_score()

        # 리스크 레벨
        risk_level = self._assess_risk_level(concentration_index, sector_weights)

        # 추천사항
        recommendations = self._generate_recommendations(
            sector_weights, concentration_index, diversification_score
        )

        return PortfolioAnalysis(
            total_value=total_value,
            sector_weights=sector_weights,
            concentration_index=concentration_index,
            top_holdings=top_holdings,
            diversification_score=diversification_score,
            risk_level=risk_level,
            recommendations=recommendations
        )

    def _calculate_sector_weights(self) -> Dict[str, float]:
        """섹터별 비중 계산"""
        total_value = self.portfolio.holdings_value
        if total_value == 0:
            return {}

        sector_values: Dict[str, float] = {}

        for holding in self.portfolio.holdings:
            category = SECTOR_CATEGORIES.get(holding.sector, 'other')
            sector_values[category] = sector_values.get(category, 0) + holding.current_value

        return {
            sector: value / total_value
            for sector, value in sector_values.items()
        }

    def _calculate_hhi(self) -> float:
        """HHI (Herfindahl-Hirschman Index) 계산"""
        total_value = self.portfolio.holdings_value
        if total_value == 0:
            return 0

        hhi = sum(
            (h.current_value / total_value) ** 2
            for h in self.portfolio.holdings
        )
        return hhi * 10000  # 0-10000 스케일

    def _get_top_holdings(self, n: int) -> List[Tuple[str, float]]:
        """상위 n개 보유 종목"""
        total_value = self.portfolio.holdings_value
        if total_value == 0:
            return []

        holdings_with_weight = [
            (h.stock_name, h.current_value / total_value * 100)
            for h in self.portfolio.holdings
        ]

        return sorted(holdings_with_weight, key=lambda x: x[1], reverse=True)[:n]

    def _calculate_diversification_score(self) -> float:
        """분산 점수 계산 (0-100)"""
        holdings_count = len(self.portfolio.holdings)
        sector_count = len(set(h.sector for h in self.portfolio.holdings))
        hhi = self._calculate_hhi()

        # 종목 수 점수 (10개 이상이면 만점)
        count_score = min(holdings_count / 10, 1) * 30

        # 섹터 수 점수 (5개 이상이면 만점)
        sector_score = min(sector_count / 5, 1) * 30

        # HHI 점수 (낮을수록 좋음, 2500 이하면 만점)
        hhi_score = max(0, (5000 - hhi) / 5000) * 40

        return round(count_score + sector_score + hhi_score, 1)

    def _assess_risk_level(
        self,
        concentration_index: float,
        sector_weights: Dict[str, float]
    ) -> str:
        """리스크 레벨 평가"""
        # 고집중 (HHI > 2500)
        if concentration_index > 2500:
            return 'high'

        # 특정 섹터 과다 비중 (50% 이상)
        max_sector_weight = max(sector_weights.values()) if sector_weights else 0
        if max_sector_weight > 0.5:
            return 'high'

        # 중집중 (HHI > 1500)
        if concentration_index > 1500:
            return 'medium'

        return 'low'

    def _generate_recommendations(
        self,
        sector_weights: Dict[str, float],
        concentration_index: float,
        diversification_score: float
    ) -> List[str]:
        """추천사항 생성"""
        recommendations = []

        # 집중도 체크
        if concentration_index > 2500:
            recommendations.append("📊 포트폴리오가 소수 종목에 집중되어 있습니다. 종목 분산을 고려하세요.")

        # 섹터 편중 체크
        for sector, weight in sector_weights.items():
            if weight > 0.4:
                sector_name = {
                    'technology': '기술',
                    'healthcare': '헬스케어',
                    'financial': '금융',
                    'consumer_defensive': '필수소비재'
                }.get(sector, sector)
                recommendations.append(f"⚠️ {sector_name} 섹터 비중이 {weight*100:.0f}%로 높습니다.")

        # 분산 점수 체크
        if diversification_score < 50:
            recommendations.append("💡 분산 투자를 통해 리스크를 줄이세요.")

        # 종목 수 체크
        if len(self.portfolio.holdings) < 5:
            recommendations.append("📈 최소 5개 이상의 종목으로 분산하는 것을 권장합니다.")

        if not recommendations:
            recommendations.append("✅ 포트폴리오가 잘 분산되어 있습니다.")

        return recommendations


# ============ 리밸런싱 계산 ============

def calculate_rebalancing_actions(
    holdings: List[Holding],
    target_weights: Dict[str, float],
    total_value: float,
    min_trade_amount: float = 100000
) -> List[RebalancingAction]:
    """
    리밸런싱 액션 계산

    Args:
        holdings: 현재 보유 종목
        target_weights: {종목코드: 목표비중}
        total_value: 포트폴리오 총 가치
        min_trade_amount: 최소 거래 금액

    Returns:
        리밸런싱 액션 리스트
    """
    actions = []
    holdings_value = sum(h.current_value for h in holdings)

    # 현재 비중 계산
    current_weights = {
        h.stock_code: h.current_value / holdings_value if holdings_value > 0 else 0
        for h in holdings
    }

    holdings_dict = {h.stock_code: h for h in holdings}

    for code, target_weight in target_weights.items():
        current_weight = current_weights.get(code, 0)
        weight_diff = target_weight - current_weight

        # 목표 금액
        target_amount = total_value * target_weight
        current_amount = holdings_dict[code].current_value if code in holdings_dict else 0
        trade_amount = target_amount - current_amount

        # 최소 거래 금액 체크
        if abs(trade_amount) < min_trade_amount:
            continue

        holding = holdings_dict.get(code)
        if not holding:
            continue

        # 거래 수량 계산
        quantity = int(abs(trade_amount) / holding.current_price)
        if quantity == 0:
            continue

        action = RebalancingAction(
            stock_code=code,
            stock_name=holding.stock_name,
            action='buy' if trade_amount > 0 else 'sell',
            quantity=quantity,
            current_weight=current_weight * 100,
            target_weight=target_weight * 100,
            amount=abs(trade_amount)
        )
        actions.append(action)

    # 매도 먼저, 그 다음 매수
    actions.sort(key=lambda x: (x.action == 'buy', -x.amount))

    return actions


def calculate_threshold_rebalancing(
    holdings: List[Holding],
    target_weights: Dict[str, float],
    threshold: float = 5.0
) -> List[RebalancingAction]:
    """
    임계값 기반 리밸런싱

    Args:
        holdings: 현재 보유 종목
        target_weights: 목표 비중
        threshold: 리밸런싱 임계값 (%)

    Returns:
        리밸런싱 액션 (임계값 초과 시에만)
    """
    holdings_value = sum(h.current_value for h in holdings)

    # 임계값 체크
    needs_rebalancing = False
    for holding in holdings:
        current_weight = (holding.current_value / holdings_value * 100) if holdings_value > 0 else 0
        target_weight = target_weights.get(holding.stock_code, 0) * 100

        if abs(current_weight - target_weight) > threshold:
            needs_rebalancing = True
            break

    if not needs_rebalancing:
        return []

    return calculate_rebalancing_actions(holdings, target_weights, holdings_value)


def suggest_optimal_weights(
    holdings: List[Holding],
    strategy: str = 'balanced'
) -> Dict[str, float]:
    """
    최적 비중 제안

    Args:
        holdings: 보유 종목
        strategy: 전략 ('conservative', 'balanced', 'aggressive')

    Returns:
        {종목코드: 권장비중} 딕셔너리
    """
    # 섹터별 목표 비중 가져오기
    sector_targets = DEFAULT_ALLOCATIONS.get(strategy, DEFAULT_ALLOCATIONS['balanced'])

    # 섹터별 종목 그룹핑
    sector_holdings: Dict[str, List[Holding]] = {}
    for holding in holdings:
        category = SECTOR_CATEGORIES.get(holding.sector, 'other')
        if category not in sector_holdings:
            sector_holdings[category] = []
        sector_holdings[category].append(holding)

    # 종목별 목표 비중 계산
    optimal_weights = {}

    for sector, target_weight in sector_targets.items():
        if sector in sector_holdings:
            holdings_in_sector = sector_holdings[sector]
            per_stock_weight = target_weight / len(holdings_in_sector)

            for holding in holdings_in_sector:
                optimal_weights[holding.stock_code] = per_stock_weight

    # 기타 섹터 처리
    if 'other' in sector_holdings:
        remaining_weight = 1 - sum(optimal_weights.values())
        if remaining_weight > 0:
            per_stock_weight = remaining_weight / len(sector_holdings['other'])
            for holding in sector_holdings['other']:
                optimal_weights[holding.stock_code] = per_stock_weight

    return optimal_weights


# ============ UI 컴포넌트 ============

def render_portfolio_input() -> Optional[Portfolio]:
    """포트폴리오 입력 UI"""
    st.subheader("📊 포트폴리오 입력")

    # 저장된 포트폴리오 로드 옵션
    saved_portfolios = list_portfolios()

    if saved_portfolios:
        col1, col2 = st.columns([3, 1])
        with col1:
            selected = st.selectbox(
                "저장된 포트폴리오",
                options=['새로 입력'] + saved_portfolios
            )
        with col2:
            if selected != '새로 입력':
                if st.button("삭제"):
                    filepath = os.path.join(PORTFOLIO_DATA_DIR, f"{selected}.json")
                    if os.path.exists(filepath):
                        os.remove(filepath)
                        st.rerun()

        if selected != '새로 입력':
            return load_portfolio(selected)

    # 새 포트폴리오 입력
    portfolio_name = st.text_input("포트폴리오 이름", value="내 포트폴리오")

    st.markdown("### 보유 종목")

    # 동적 종목 입력
    if 'portfolio_holdings' not in st.session_state:
        st.session_state['portfolio_holdings'] = [
            {'code': '', 'name': '', 'qty': 0, 'avg': 0, 'current': 0, 'sector': ''}
        ]

    holdings_data = st.session_state['portfolio_holdings']

    for i, holding in enumerate(holdings_data):
        col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 1, 1.5, 1.5, 0.5])

        with col1:
            holdings_data[i]['code'] = st.text_input(
                "종목코드", value=holding['code'], key=f"code_{i}",
                label_visibility='collapsed' if i > 0 else 'visible'
            )
        with col2:
            holdings_data[i]['name'] = st.text_input(
                "종목명", value=holding['name'], key=f"name_{i}",
                label_visibility='collapsed' if i > 0 else 'visible'
            )
        with col3:
            holdings_data[i]['qty'] = st.number_input(
                "수량", value=holding['qty'], key=f"qty_{i}", min_value=0,
                label_visibility='collapsed' if i > 0 else 'visible'
            )
        with col4:
            holdings_data[i]['avg'] = st.number_input(
                "평균단가", value=holding['avg'], key=f"avg_{i}", min_value=0,
                label_visibility='collapsed' if i > 0 else 'visible'
            )
        with col5:
            holdings_data[i]['current'] = st.number_input(
                "현재가", value=holding['current'], key=f"current_{i}", min_value=0,
                label_visibility='collapsed' if i > 0 else 'visible'
            )
        with col6:
            if i > 0 and st.button("🗑️", key=f"del_{i}"):
                holdings_data.pop(i)
                st.rerun()

    if st.button("+ 종목 추가"):
        holdings_data.append({'code': '', 'name': '', 'qty': 0, 'avg': 0, 'current': 0, 'sector': ''})
        st.rerun()

    cash = st.number_input("현금 보유액", value=0, min_value=0, format="%d")

    # 포트폴리오 생성
    if st.button("포트폴리오 분석", type="primary"):
        holdings = []
        for h in holdings_data:
            if h['code'] and h['qty'] > 0:
                holdings.append(Holding(
                    stock_code=h['code'],
                    stock_name=h['name'] or h['code'],
                    quantity=h['qty'],
                    avg_price=h['avg'],
                    current_price=h['current'] or h['avg'],
                    sector=h.get('sector', '')
                ))

        if holdings:
            portfolio = Portfolio(
                name=portfolio_name,
                holdings=holdings,
                cash=cash,
                created_at=datetime.now().isoformat()
            )
            save_portfolio(portfolio)
            return portfolio
        else:
            st.error("최소 1개 이상의 종목을 입력하세요")

    return None


def render_portfolio_analysis(analysis: PortfolioAnalysis):
    """포트폴리오 분석 결과 렌더링"""
    st.subheader("📈 포트폴리오 분석")

    # 요약 메트릭
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("총 평가금액", f"₩{analysis.total_value:,.0f}")

    with col2:
        risk_colors = {'low': '🟢', 'medium': '🟡', 'high': '🔴'}
        risk_labels = {'low': '낮음', 'medium': '보통', 'high': '높음'}
        st.metric(
            "리스크 수준",
            f"{risk_colors[analysis.risk_level]} {risk_labels[analysis.risk_level]}"
        )

    with col3:
        st.metric("분산 점수", f"{analysis.diversification_score}/100")

    with col4:
        st.metric("집중도 (HHI)", f"{analysis.concentration_index:.0f}")

    # 섹터별 비중
    st.markdown("### 섹터별 비중")

    sector_labels = {
        'technology': '기술',
        'healthcare': '헬스케어',
        'financial': '금융',
        'consumer_defensive': '필수소비재',
        'consumer_cyclical': '경기소비재',
        'industrials': '산업재',
        'basic_materials': '기초소재',
        'energy': '에너지',
        'communication': '커뮤니케이션',
        'other': '기타'
    }

    for sector, weight in sorted(analysis.sector_weights.items(), key=lambda x: x[1], reverse=True):
        label = sector_labels.get(sector, sector)
        st.progress(weight, text=f"{label}: {weight*100:.1f}%")

    # 상위 보유 종목
    st.markdown("### 상위 보유 종목")

    for name, weight in analysis.top_holdings:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{name}**")
        with col2:
            st.markdown(f"{weight:.1f}%")

    # 추천사항
    st.markdown("### 💡 추천사항")

    for rec in analysis.recommendations:
        st.markdown(f"- {rec}")


def render_rebalancing_actions(actions: List[RebalancingAction]):
    """리밸런싱 액션 렌더링"""
    if not actions:
        st.info("리밸런싱이 필요하지 않습니다.")
        return

    st.subheader("🔄 리밸런싱 액션")

    total_sell = sum(a.amount for a in actions if a.action == 'sell')
    total_buy = sum(a.amount for a in actions if a.action == 'buy')

    col1, col2 = st.columns(2)
    with col1:
        st.metric("매도 예정", f"₩{total_sell:,.0f}", delta_color="inverse")
    with col2:
        st.metric("매수 예정", f"₩{total_buy:,.0f}")

    st.markdown("### 상세 내역")

    for action in actions:
        icon = "🔴" if action.action == 'sell' else "🟢"
        action_text = "매도" if action.action == 'sell' else "매수"

        with st.container():
            col1, col2, col3, col4 = st.columns([2, 1, 1, 2])

            with col1:
                st.markdown(f"{icon} **{action.stock_name}**")
            with col2:
                st.markdown(f"{action_text} {action.quantity}주")
            with col3:
                st.markdown(f"₩{action.amount:,.0f}")
            with col4:
                st.markdown(
                    f"{action.current_weight:.1f}% → {action.target_weight:.1f}%"
                )

            st.divider()


def render_rebalancing_dashboard():
    """리밸런싱 대시보드"""
    st.title("⚖️ 포트폴리오 리밸런싱")

    # 포트폴리오 입력
    portfolio = render_portfolio_input()

    if portfolio is None:
        return

    # 분석
    analyzer = PortfolioAnalyzer(portfolio)
    analysis = analyzer.analyze()

    render_portfolio_analysis(analysis)

    st.divider()

    # 리밸런싱 설정
    st.subheader("⚙️ 리밸런싱 설정")

    col1, col2 = st.columns(2)

    with col1:
        strategy = st.selectbox(
            "투자 성향",
            options=['conservative', 'balanced', 'aggressive'],
            format_func=lambda x: {'conservative': '보수적', 'balanced': '균형', 'aggressive': '공격적'}[x],
            index=1
        )

    with col2:
        threshold = st.slider("리밸런싱 임계값 (%)", min_value=1, max_value=20, value=5)

    if st.button("리밸런싱 계산", type="primary"):
        # 목표 비중 계산
        target_weights = suggest_optimal_weights(portfolio.holdings, strategy)

        # 리밸런싱 액션
        actions = calculate_threshold_rebalancing(
            portfolio.holdings,
            target_weights,
            threshold
        )

        render_rebalancing_actions(actions)


# ============ 내보내기 ============

__all__ = [
    'Holding',
    'Portfolio',
    'RebalancingAction',
    'PortfolioAnalysis',
    'PortfolioAnalyzer',
    'RebalancingStrategy',
    'calculate_rebalancing_actions',
    'calculate_threshold_rebalancing',
    'suggest_optimal_weights',
    'save_portfolio',
    'load_portfolio',
    'list_portfolios',
    'render_portfolio_input',
    'render_portfolio_analysis',
    'render_rebalancing_actions',
    'render_rebalancing_dashboard',
]
