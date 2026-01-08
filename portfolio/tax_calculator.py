"""
세금 계산기 모듈
양도소득세 예상 계산, 절세 전략
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class MarketType(Enum):
    KOREA_LISTED = "korea_listed"        # 국내 상장주식
    KOREA_UNLISTED = "korea_unlisted"    # 국내 비상장주식
    OVERSEAS = "overseas"                 # 해외주식
    FUND = "fund"                         # 펀드
    ETF_KOREA = "etf_korea"              # 국내 ETF
    ETF_OVERSEAS = "etf_overseas"        # 해외 ETF


@dataclass
class TaxCalculation:
    """세금 계산 결과"""
    market_type: MarketType
    total_gain: float           # 총 양도차익
    total_loss: float           # 총 양도손실
    net_gain: float             # 순 양도차익
    deduction: float            # 기본공제
    taxable_gain: float         # 과세표준
    tax_rate: float             # 세율
    local_tax_rate: float       # 지방소득세율
    calculated_tax: float       # 산출세액
    local_tax: float            # 지방소득세
    total_tax: float            # 총 납부세액
    effective_rate: float       # 실효세율

    def to_dict(self) -> Dict:
        return {
            'market_type': self.market_type.value,
            'total_gain': self.total_gain,
            'total_loss': self.total_loss,
            'net_gain': self.net_gain,
            'deduction': self.deduction,
            'taxable_gain': self.taxable_gain,
            'tax_rate': self.tax_rate * 100,
            'local_tax_rate': self.local_tax_rate * 100,
            'calculated_tax': self.calculated_tax,
            'local_tax': self.local_tax,
            'total_tax': self.total_tax,
            'effective_rate': self.effective_rate * 100
        }


@dataclass
class TaxOptimization:
    """절세 최적화 제안"""
    strategy: str
    description: str
    potential_savings: float
    actions: List[str]


class TaxCalculator:
    """세금 계산기"""

    # 2024년 기준 세율
    TAX_RATES = {
        MarketType.KOREA_LISTED: {
            'deduction': 2500000,      # 250만원 기본공제
            'rate': 0.22,              # 22% (지방세 포함)
            'large_shareholder_rate': 0.27,  # 대주주 27.5%
        },
        MarketType.OVERSEAS: {
            'deduction': 2500000,      # 250만원 기본공제
            'rate': 0.22,              # 22% (지방세 포함)
        },
        MarketType.ETF_OVERSEAS: {
            'deduction': 2500000,
            'rate': 0.22,
        },
        MarketType.KOREA_UNLISTED: {
            'deduction': 2500000,
            'rate': 0.22,
            'sme_rate': 0.11,          # 중소기업 11%
        }
    }

    # 대주주 기준 (2024년)
    LARGE_SHAREHOLDER_THRESHOLD = {
        'kospi': {'amount': 1000000000, 'ratio': 0.01},   # 10억 or 1%
        'kosdaq': {'amount': 1000000000, 'ratio': 0.02},  # 10억 or 2%
    }

    def __init__(self):
        self.year = datetime.now().year

    def calculate_tax(self, trades: List[Dict],
                      market_type: MarketType = MarketType.OVERSEAS) -> TaxCalculation:
        """
        세금 계산
        trades: [{'symbol': 'AAPL', 'buy_price': 100, 'sell_price': 150,
                 'quantity': 10, 'buy_date': '2023-01-01', 'sell_date': '2024-01-01'}, ...]
        """
        total_gain = 0
        total_loss = 0

        for trade in trades:
            buy_price = trade.get('buy_price', 0)
            sell_price = trade.get('sell_price', 0)
            quantity = trade.get('quantity', 0)

            profit = (sell_price - buy_price) * quantity

            if profit > 0:
                total_gain += profit
            else:
                total_loss += abs(profit)

        # 손익 통산
        net_gain = total_gain - total_loss

        # 세율 정보
        tax_info = self.TAX_RATES.get(market_type, self.TAX_RATES[MarketType.OVERSEAS])
        deduction = tax_info['deduction']
        tax_rate = tax_info['rate']

        # 과세표준
        taxable_gain = max(0, net_gain - deduction)

        # 산출세액 (지방세 별도 계산)
        base_rate = tax_rate / 1.1  # 지방세 제외 기본세율
        local_rate = base_rate * 0.1  # 지방소득세 (기본세율의 10%)

        calculated_tax = taxable_gain * base_rate
        local_tax = calculated_tax * 0.1
        total_tax = calculated_tax + local_tax

        # 실효세율
        effective_rate = total_tax / net_gain if net_gain > 0 else 0

        return TaxCalculation(
            market_type=market_type,
            total_gain=total_gain,
            total_loss=total_loss,
            net_gain=net_gain,
            deduction=deduction,
            taxable_gain=taxable_gain,
            tax_rate=base_rate,
            local_tax_rate=local_rate,
            calculated_tax=calculated_tax,
            local_tax=local_tax,
            total_tax=total_tax,
            effective_rate=effective_rate
        )

    def estimate_from_positions(self, positions: List[Dict],
                                market_type: MarketType = MarketType.OVERSEAS) -> Dict:
        """
        현재 포지션 기준 예상 세금
        positions: [{'symbol': 'AAPL', 'avg_cost': 100, 'current_price': 150, 'quantity': 10}, ...]
        """
        unrealized_gains = []
        unrealized_losses = []
        total_unrealized = 0

        for pos in positions:
            avg_cost = pos.get('avg_cost', 0)
            current_price = pos.get('current_price', 0)
            quantity = pos.get('quantity', 0)

            profit = (current_price - avg_cost) * quantity
            total_unrealized += profit

            if profit > 0:
                unrealized_gains.append({
                    'symbol': pos.get('symbol', ''),
                    'name': pos.get('name', ''),
                    'profit': profit,
                    'quantity': quantity,
                    'avg_cost': avg_cost,
                    'current_price': current_price
                })
            elif profit < 0:
                unrealized_losses.append({
                    'symbol': pos.get('symbol', ''),
                    'name': pos.get('name', ''),
                    'loss': abs(profit),
                    'quantity': quantity,
                    'avg_cost': avg_cost,
                    'current_price': current_price
                })

        # 세금 계산 (전량 매도 가정)
        trades = [{'buy_price': p['avg_cost'], 'sell_price': p['current_price'],
                   'quantity': p['quantity']} for p in positions]
        tax_result = self.calculate_tax(trades, market_type)

        return {
            'total_unrealized_pnl': total_unrealized,
            'unrealized_gains': sorted(unrealized_gains, key=lambda x: x['profit'], reverse=True),
            'unrealized_losses': sorted(unrealized_losses, key=lambda x: x['loss'], reverse=True),
            'estimated_tax': tax_result.to_dict(),
            'tax_if_all_sold': tax_result.total_tax
        }

    def optimize_tax(self, positions: List[Dict],
                    realized_gain: float = 0,
                    market_type: MarketType = MarketType.OVERSEAS) -> List[TaxOptimization]:
        """절세 최적화 제안"""
        optimizations = []
        estimate = self.estimate_from_positions(positions, market_type)
        deduction = self.TAX_RATES.get(market_type, {}).get('deduction', 2500000)

        # 1. 손실 실현으로 손익 통산
        if estimate['unrealized_losses'] and realized_gain > 0:
            total_loss = sum(l['loss'] for l in estimate['unrealized_losses'])
            potential_savings = min(total_loss, realized_gain) * 0.22

            if potential_savings > 10000:  # 1만원 이상일 때만
                loss_symbols = [l['symbol'] for l in estimate['unrealized_losses'][:3]]
                optimizations.append(TaxOptimization(
                    strategy="손실 실현을 통한 손익 통산",
                    description=f"평가손실 {total_loss:,.0f}원을 실현하여 양도차익과 상계",
                    potential_savings=potential_savings,
                    actions=[f"{s} 매도 후 재매수 고려" for s in loss_symbols]
                ))

        # 2. 기본공제 활용
        current_net_gain = realized_gain + estimate['total_unrealized_pnl']
        if 0 < current_net_gain < deduction:
            remaining_deduction = deduction - current_net_gain
            optimizations.append(TaxOptimization(
                strategy="기본공제 한도 활용",
                description=f"기본공제 잔여 {remaining_deduction:,.0f}원 활용 가능",
                potential_savings=remaining_deduction * 0.22,
                actions=[f"추가로 {remaining_deduction:,.0f}원까지 이익 실현 시 비과세"]
            ))

        # 3. 연도 분산 매도
        if estimate['total_unrealized_pnl'] > deduction * 2:
            annual_tax = (estimate['total_unrealized_pnl'] - deduction) * 0.22
            split_tax = max(0, (estimate['total_unrealized_pnl'] / 2 - deduction)) * 0.22 * 2
            savings = annual_tax - split_tax

            if savings > 50000:
                optimizations.append(TaxOptimization(
                    strategy="연도 분산 매도",
                    description="2개 과세연도에 나눠 매도하여 기본공제 2회 적용",
                    potential_savings=savings,
                    actions=["올해 일부 매도", "내년 나머지 매도"]
                ))

        # 4. 1년 보유 후 매도 (해외주식)
        if market_type == MarketType.OVERSEAS:
            short_term_gains = [g for g in estimate['unrealized_gains']
                               if g.get('hold_days', 400) < 365]
            if short_term_gains:
                optimizations.append(TaxOptimization(
                    strategy="1년 이상 보유",
                    description="장기보유 시 환율 변동 반영 등 유리",
                    potential_savings=0,
                    actions=["1년 미만 보유 종목 매도 연기 검토"]
                ))

        # 5. 증여 활용
        total_gain = sum(g['profit'] for g in estimate['unrealized_gains'])
        if total_gain > 50000000:  # 5천만원 이상
            optimizations.append(TaxOptimization(
                strategy="가족 증여 활용",
                description="배우자 6억, 자녀 5천만원까지 증여세 면제",
                potential_savings=total_gain * 0.22 * 0.3,  # 대략적 추정
                actions=[
                    "배우자에게 주식 증여 후 매도",
                    "증여 후 바로 매도 시 부당행위 주의"
                ]
            ))

        return optimizations

    def calculate_optimal_sell(self, positions: List[Dict],
                              target_amount: float,
                              market_type: MarketType = MarketType.OVERSEAS) -> List[Dict]:
        """
        목표 금액 달성을 위한 최적 매도 순서
        세금을 최소화하면서 목표 금액 확보
        """
        deduction = self.TAX_RATES.get(market_type, {}).get('deduction', 2500000)

        # 수익률 순 정렬 (손실 종목 우선)
        sorted_positions = sorted(positions, key=lambda p:
            (p.get('current_price', 0) - p.get('avg_cost', 0)) / p.get('avg_cost', 1)
            if p.get('avg_cost', 0) > 0 else 0
        )

        sell_plan = []
        remaining_amount = target_amount
        total_gain = 0

        for pos in sorted_positions:
            if remaining_amount <= 0:
                break

            current_value = pos.get('current_price', 0) * pos.get('quantity', 0)
            profit_per_share = pos.get('current_price', 0) - pos.get('avg_cost', 0)

            # 필요한 수량 계산
            sell_quantity = min(
                pos.get('quantity', 0),
                int(remaining_amount / pos.get('current_price', 1)) + 1
            )

            sell_value = sell_quantity * pos.get('current_price', 0)
            sell_profit = sell_quantity * profit_per_share

            sell_plan.append({
                'symbol': pos.get('symbol', ''),
                'name': pos.get('name', ''),
                'quantity': sell_quantity,
                'sell_value': sell_value,
                'profit': sell_profit,
                'reason': '손실' if profit_per_share < 0 else '이익'
            })

            remaining_amount -= sell_value
            total_gain += sell_profit

        # 예상 세금
        tax = max(0, (total_gain - deduction) * 0.22) if total_gain > 0 else 0

        return {
            'sell_plan': sell_plan,
            'total_sell_value': target_amount - remaining_amount,
            'total_gain': total_gain,
            'estimated_tax': tax,
            'net_proceeds': target_amount - remaining_amount - tax
        }


# 전역 인스턴스
tax_calculator = TaxCalculator()
