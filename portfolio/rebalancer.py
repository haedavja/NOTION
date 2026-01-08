"""
포트폴리오 리밸런싱 모듈
목표 비중 설정 및 리밸런싱 제안
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import json
import os


@dataclass
class TargetAllocation:
    """목표 배분"""
    symbol: str
    name: str
    target_weight: float  # 목표 비중 (0-100)

    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'name': self.name,
            'target_weight': self.target_weight
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'TargetAllocation':
        return cls(**data)


@dataclass
class RebalanceAction:
    """리밸런싱 액션"""
    symbol: str
    name: str
    action: str  # 'buy', 'sell', 'hold'
    current_weight: float
    target_weight: float
    deviation: float  # 괴리율
    amount: float  # 거래 금액
    quantity: int  # 거래 수량
    current_price: float

    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'name': self.name,
            'action': self.action,
            'current_weight': self.current_weight,
            'target_weight': self.target_weight,
            'deviation': self.deviation,
            'amount': self.amount,
            'quantity': self.quantity,
            'current_price': self.current_price
        }


@dataclass
class RebalanceReport:
    """리밸런싱 리포트"""
    timestamp: datetime
    total_value: float
    actions: List[RebalanceAction]
    total_buy_amount: float
    total_sell_amount: float
    net_cash_flow: float
    max_deviation: float
    needs_rebalance: bool

    def to_dict(self) -> Dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'total_value': self.total_value,
            'actions': [a.to_dict() for a in self.actions],
            'total_buy_amount': self.total_buy_amount,
            'total_sell_amount': self.total_sell_amount,
            'net_cash_flow': self.net_cash_flow,
            'max_deviation': self.max_deviation,
            'needs_rebalance': self.needs_rebalance
        }


class PortfolioRebalancer:
    """포트폴리오 리밸런서"""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.expanduser("~"), ".notion_portfolio")

        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        self.target_allocations: Dict[str, TargetAllocation] = {}
        self.rebalance_threshold = 5.0  # 5% 괴리 시 리밸런싱 제안
        self.min_trade_amount = 100000  # 최소 거래 금액 (10만원)

        self._load_targets()

    def _load_targets(self):
        """목표 배분 로드"""
        file_path = os.path.join(self.data_dir, "target_allocations.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for item in data.get('allocations', []):
                    target = TargetAllocation.from_dict(item)
                    self.target_allocations[target.symbol] = target
                self.rebalance_threshold = data.get('threshold', 5.0)
            except Exception as e:
                print(f"Target allocations load error: {e}")

    def _save_targets(self):
        """목표 배분 저장"""
        file_path = os.path.join(self.data_dir, "target_allocations.json")
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'allocations': [t.to_dict() for t in self.target_allocations.values()],
                    'threshold': self.rebalance_threshold,
                    'updated_at': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Target allocations save error: {e}")

    def set_target(self, symbol: str, name: str, target_weight: float):
        """목표 비중 설정"""
        if target_weight < 0 or target_weight > 100:
            raise ValueError("Target weight must be between 0 and 100")

        self.target_allocations[symbol] = TargetAllocation(
            symbol=symbol,
            name=name,
            target_weight=target_weight
        )
        self._save_targets()

    def remove_target(self, symbol: str):
        """목표 비중 삭제"""
        if symbol in self.target_allocations:
            del self.target_allocations[symbol]
            self._save_targets()

    def set_threshold(self, threshold: float):
        """리밸런싱 임계값 설정"""
        self.rebalance_threshold = threshold
        self._save_targets()

    def get_targets(self) -> List[TargetAllocation]:
        """목표 배분 목록"""
        return list(self.target_allocations.values())

    def validate_targets(self) -> Tuple[bool, str]:
        """목표 배분 유효성 검사"""
        total_weight = sum(t.target_weight for t in self.target_allocations.values())

        if abs(total_weight - 100) > 0.1:
            return False, f"목표 비중 합계가 100%가 아닙니다. (현재: {total_weight:.1f}%)"

        return True, "OK"

    def analyze(self, positions: List[Dict], cash: float = 0) -> RebalanceReport:
        """
        리밸런싱 분석
        positions: [{'symbol': 'AAPL', 'name': 'Apple', 'quantity': 10,
                    'current_price': 150, 'value': 1500}, ...]
        """
        # 총 포트폴리오 가치
        total_value = sum(p.get('value', 0) for p in positions) + cash

        if total_value <= 0:
            return RebalanceReport(
                timestamp=datetime.now(),
                total_value=0,
                actions=[],
                total_buy_amount=0,
                total_sell_amount=0,
                net_cash_flow=0,
                max_deviation=0,
                needs_rebalance=False
            )

        # 현재 비중 계산
        current_weights = {}
        for pos in positions:
            symbol = pos.get('symbol', '')
            value = pos.get('value', 0)
            current_weights[symbol] = (value / total_value) * 100

        actions = []
        total_buy = 0
        total_sell = 0
        max_deviation = 0

        # 각 목표 종목에 대해 분석
        for symbol, target in self.target_allocations.items():
            current_weight = current_weights.get(symbol, 0)
            deviation = current_weight - target.target_weight

            # 현재 가격 찾기
            current_price = 0
            for pos in positions:
                if pos.get('symbol') == symbol:
                    current_price = pos.get('current_price', 0)
                    break

            # 액션 결정
            if abs(deviation) < self.rebalance_threshold:
                action = 'hold'
                amount = 0
                quantity = 0
            elif deviation > 0:
                # 비중 초과 -> 매도
                action = 'sell'
                amount = (deviation / 100) * total_value
                quantity = int(amount / current_price) if current_price > 0 else 0
                total_sell += amount
            else:
                # 비중 부족 -> 매수
                action = 'buy'
                amount = abs(deviation / 100) * total_value
                quantity = int(amount / current_price) if current_price > 0 else 0
                total_buy += amount

            # 최소 거래 금액 미만이면 hold
            if amount < self.min_trade_amount:
                action = 'hold'
                amount = 0
                quantity = 0

            max_deviation = max(max_deviation, abs(deviation))

            actions.append(RebalanceAction(
                symbol=symbol,
                name=target.name,
                action=action,
                current_weight=current_weight,
                target_weight=target.target_weight,
                deviation=deviation,
                amount=amount,
                quantity=quantity,
                current_price=current_price
            ))

        # 목표에 없는 종목 (매도 대상)
        for pos in positions:
            symbol = pos.get('symbol', '')
            if symbol not in self.target_allocations and current_weights.get(symbol, 0) > 0:
                weight = current_weights[symbol]
                amount = pos.get('value', 0)
                quantity = pos.get('quantity', 0)

                actions.append(RebalanceAction(
                    symbol=symbol,
                    name=pos.get('name', ''),
                    action='sell',
                    current_weight=weight,
                    target_weight=0,
                    deviation=weight,
                    amount=amount,
                    quantity=quantity,
                    current_price=pos.get('current_price', 0)
                ))
                total_sell += amount
                max_deviation = max(max_deviation, weight)

        # 액션 정렬 (매도 먼저, 그 다음 매수)
        actions.sort(key=lambda a: (0 if a.action == 'sell' else 1 if a.action == 'buy' else 2, -a.amount))

        needs_rebalance = max_deviation >= self.rebalance_threshold

        return RebalanceReport(
            timestamp=datetime.now(),
            total_value=total_value,
            actions=actions,
            total_buy_amount=total_buy,
            total_sell_amount=total_sell,
            net_cash_flow=total_sell - total_buy,
            max_deviation=max_deviation,
            needs_rebalance=needs_rebalance
        )

    def get_deviation_summary(self, positions: List[Dict]) -> Dict:
        """괴리율 요약"""
        report = self.analyze(positions)

        over_target = []
        under_target = []

        for action in report.actions:
            if action.deviation > self.rebalance_threshold:
                over_target.append({
                    'symbol': action.symbol,
                    'name': action.name,
                    'deviation': action.deviation
                })
            elif action.deviation < -self.rebalance_threshold:
                under_target.append({
                    'symbol': action.symbol,
                    'name': action.name,
                    'deviation': action.deviation
                })

        return {
            'max_deviation': report.max_deviation,
            'needs_rebalance': report.needs_rebalance,
            'over_target': sorted(over_target, key=lambda x: x['deviation'], reverse=True),
            'under_target': sorted(under_target, key=lambda x: x['deviation']),
            'threshold': self.rebalance_threshold
        }

    def suggest_trades(self, positions: List[Dict],
                      available_cash: float = 0) -> List[Dict]:
        """구체적인 매매 제안"""
        report = self.analyze(positions, available_cash)

        suggestions = []

        for action in report.actions:
            if action.action == 'hold':
                continue

            suggestion = {
                'symbol': action.symbol,
                'name': action.name,
                'action': '매도' if action.action == 'sell' else '매수',
                'quantity': action.quantity,
                'amount': action.amount,
                'current_price': action.current_price,
                'reason': f"목표 {action.target_weight:.1f}% vs 현재 {action.current_weight:.1f}% (괴리: {action.deviation:+.1f}%)"
            }
            suggestions.append(suggestion)

        return suggestions


# 전역 인스턴스
rebalancer = PortfolioRebalancer()
