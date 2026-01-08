"""
다중 포트폴리오 관리
실제 투자, 모의 투자, 워치리스트 분리 관리
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

from .portfolio import Portfolio, Position


class PortfolioType(Enum):
    REAL = "real"           # 실제 투자
    PAPER = "paper"         # 모의 투자
    WATCHLIST = "watchlist" # 관심 종목


@dataclass
class PortfolioMeta:
    """포트폴리오 메타데이터"""
    id: str
    name: str
    portfolio_type: PortfolioType
    created_at: datetime
    updated_at: datetime
    description: str = ""
    initial_capital: float = 0.0
    currency: str = "KRW"

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'name': self.name,
            'portfolio_type': self.portfolio_type.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'description': self.description,
            'initial_capital': self.initial_capital,
            'currency': self.currency
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'PortfolioMeta':
        data['portfolio_type'] = PortfolioType(data['portfolio_type'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)


@dataclass
class WatchlistItem:
    """관심종목 항목"""
    symbol: str
    name: str
    added_at: datetime
    target_price: Optional[float] = None
    stop_price: Optional[float] = None
    notes: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'name': self.name,
            'added_at': self.added_at.isoformat(),
            'target_price': self.target_price,
            'stop_price': self.stop_price,
            'notes': self.notes,
            'tags': self.tags
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'WatchlistItem':
        data['added_at'] = datetime.fromisoformat(data['added_at'])
        return cls(**data)


class MultiPortfolioManager:
    """다중 포트폴리오 관리자"""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.expanduser("~"), ".notion_portfolio")

        self.data_dir = Path(data_dir)
        self.portfolios_dir = self.data_dir / "portfolios"
        self.portfolios_dir.mkdir(parents=True, exist_ok=True)

        self._portfolios: Dict[str, Portfolio] = {}
        self._meta: Dict[str, PortfolioMeta] = {}
        self._watchlists: Dict[str, List[WatchlistItem]] = {}

        self._load_all()

    def _load_all(self):
        """모든 포트폴리오 로드"""
        index_file = self.portfolios_dir / "index.json"

        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    index = json.load(f)

                for meta_data in index.get('portfolios', []):
                    meta = PortfolioMeta.from_dict(meta_data)
                    self._meta[meta.id] = meta
                    self._load_portfolio(meta.id)

            except Exception as e:
                print(f"Portfolio index load error: {e}")

        # 기본 포트폴리오 생성
        if not self._meta:
            self.create_portfolio("실제 투자", PortfolioType.REAL, "메인 투자 포트폴리오")
            self.create_portfolio("모의 투자", PortfolioType.PAPER, "전략 테스트용")
            self.create_portfolio("관심 종목", PortfolioType.WATCHLIST, "관심 종목 리스트")

    def _load_portfolio(self, portfolio_id: str):
        """개별 포트폴리오 로드"""
        file_path = self.portfolios_dir / f"{portfolio_id}.json"

        if not file_path.exists():
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            meta = self._meta.get(portfolio_id)
            if not meta:
                return

            if meta.portfolio_type == PortfolioType.WATCHLIST:
                self._watchlists[portfolio_id] = [
                    WatchlistItem.from_dict(item) for item in data.get('items', [])
                ]
            else:
                portfolio = Portfolio()
                for pos_data in data.get('positions', []):
                    pos_data['last_updated'] = datetime.fromisoformat(pos_data['last_updated'])
                    portfolio.positions.append(Position(**pos_data))
                self._portfolios[portfolio_id] = portfolio

        except Exception as e:
            print(f"Portfolio load error ({portfolio_id}): {e}")

    def _save_index(self):
        """인덱스 저장"""
        index_file = self.portfolios_dir / "index.json"

        try:
            with open(index_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'portfolios': [m.to_dict() for m in self._meta.values()],
                    'updated_at': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Index save error: {e}")

    def _save_portfolio(self, portfolio_id: str):
        """개별 포트폴리오 저장"""
        file_path = self.portfolios_dir / f"{portfolio_id}.json"
        meta = self._meta.get(portfolio_id)

        if not meta:
            return

        try:
            if meta.portfolio_type == PortfolioType.WATCHLIST:
                items = self._watchlists.get(portfolio_id, [])
                data = {'items': [item.to_dict() for item in items]}
            else:
                portfolio = self._portfolios.get(portfolio_id)
                if portfolio:
                    data = {
                        'positions': [{
                            'symbol': p.symbol,
                            'name': p.name,
                            'quantity': p.quantity,
                            'avg_cost': p.avg_cost,
                            'current_price': p.current_price,
                            'last_updated': p.last_updated.isoformat()
                        } for p in portfolio.positions]
                    }
                else:
                    data = {'positions': []}

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            # 메타 업데이트
            meta.updated_at = datetime.now()
            self._save_index()

        except Exception as e:
            print(f"Portfolio save error ({portfolio_id}): {e}")

    # ===== 포트폴리오 관리 =====

    def create_portfolio(self, name: str, portfolio_type: PortfolioType,
                        description: str = "", initial_capital: float = 0) -> str:
        """새 포트폴리오 생성"""
        portfolio_id = f"{portfolio_type.value}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        meta = PortfolioMeta(
            id=portfolio_id,
            name=name,
            portfolio_type=portfolio_type,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            description=description,
            initial_capital=initial_capital
        )

        self._meta[portfolio_id] = meta

        if portfolio_type == PortfolioType.WATCHLIST:
            self._watchlists[portfolio_id] = []
        else:
            self._portfolios[portfolio_id] = Portfolio()

        self._save_index()
        self._save_portfolio(portfolio_id)

        return portfolio_id

    def delete_portfolio(self, portfolio_id: str) -> bool:
        """포트폴리오 삭제"""
        if portfolio_id not in self._meta:
            return False

        # 파일 삭제
        file_path = self.portfolios_dir / f"{portfolio_id}.json"
        if file_path.exists():
            file_path.unlink()

        # 메모리에서 제거
        del self._meta[portfolio_id]
        self._portfolios.pop(portfolio_id, None)
        self._watchlists.pop(portfolio_id, None)

        self._save_index()
        return True

    def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        """포트폴리오 조회"""
        return self._portfolios.get(portfolio_id)

    def get_watchlist(self, portfolio_id: str) -> List[WatchlistItem]:
        """워치리스트 조회"""
        return self._watchlists.get(portfolio_id, [])

    def get_meta(self, portfolio_id: str) -> Optional[PortfolioMeta]:
        """메타데이터 조회"""
        return self._meta.get(portfolio_id)

    def list_portfolios(self, portfolio_type: PortfolioType = None) -> List[PortfolioMeta]:
        """포트폴리오 목록"""
        metas = list(self._meta.values())

        if portfolio_type:
            metas = [m for m in metas if m.portfolio_type == portfolio_type]

        return sorted(metas, key=lambda m: m.created_at)

    # ===== 포지션 관리 =====

    def add_position(self, portfolio_id: str, symbol: str, name: str,
                    quantity: float, avg_cost: float) -> bool:
        """포지션 추가"""
        portfolio = self._portfolios.get(portfolio_id)
        if not portfolio:
            return False

        portfolio.add_position(symbol, name, quantity, avg_cost)
        self._save_portfolio(portfolio_id)
        return True

    def remove_position(self, portfolio_id: str, symbol: str) -> bool:
        """포지션 제거"""
        portfolio = self._portfolios.get(portfolio_id)
        if not portfolio:
            return False

        portfolio.remove_position(symbol)
        self._save_portfolio(portfolio_id)
        return True

    def update_prices(self, portfolio_id: str):
        """가격 업데이트"""
        portfolio = self._portfolios.get(portfolio_id)
        if portfolio:
            portfolio.update_prices()
            self._save_portfolio(portfolio_id)

    # ===== 워치리스트 관리 =====

    def add_to_watchlist(self, portfolio_id: str, symbol: str, name: str,
                        target_price: float = None, stop_price: float = None,
                        notes: str = "", tags: List[str] = None) -> bool:
        """관심종목 추가"""
        if portfolio_id not in self._watchlists:
            return False

        # 중복 체크
        existing = [w for w in self._watchlists[portfolio_id] if w.symbol == symbol]
        if existing:
            return False

        item = WatchlistItem(
            symbol=symbol,
            name=name,
            added_at=datetime.now(),
            target_price=target_price,
            stop_price=stop_price,
            notes=notes,
            tags=tags or []
        )

        self._watchlists[portfolio_id].append(item)
        self._save_portfolio(portfolio_id)
        return True

    def remove_from_watchlist(self, portfolio_id: str, symbol: str) -> bool:
        """관심종목 제거"""
        if portfolio_id not in self._watchlists:
            return False

        before_count = len(self._watchlists[portfolio_id])
        self._watchlists[portfolio_id] = [
            w for w in self._watchlists[portfolio_id] if w.symbol != symbol
        ]

        if len(self._watchlists[portfolio_id]) < before_count:
            self._save_portfolio(portfolio_id)
            return True
        return False

    def update_watchlist_item(self, portfolio_id: str, symbol: str,
                             target_price: float = None, stop_price: float = None,
                             notes: str = None, tags: List[str] = None) -> bool:
        """관심종목 업데이트"""
        if portfolio_id not in self._watchlists:
            return False

        for item in self._watchlists[portfolio_id]:
            if item.symbol == symbol:
                if target_price is not None:
                    item.target_price = target_price
                if stop_price is not None:
                    item.stop_price = stop_price
                if notes is not None:
                    item.notes = notes
                if tags is not None:
                    item.tags = tags
                self._save_portfolio(portfolio_id)
                return True
        return False

    # ===== 통계 =====

    def get_summary(self, portfolio_id: str) -> Dict:
        """포트폴리오 요약"""
        meta = self._meta.get(portfolio_id)
        if not meta:
            return {}

        if meta.portfolio_type == PortfolioType.WATCHLIST:
            items = self._watchlists.get(portfolio_id, [])
            return {
                'type': 'watchlist',
                'name': meta.name,
                'count': len(items),
                'tags': list(set(tag for item in items for tag in item.tags))
            }
        else:
            portfolio = self._portfolios.get(portfolio_id)
            if not portfolio:
                return {}

            total_value = sum(p.current_price * p.quantity for p in portfolio.positions)
            total_cost = sum(p.avg_cost * p.quantity for p in portfolio.positions)
            pnl = total_value - total_cost
            pnl_pct = (pnl / total_cost * 100) if total_cost > 0 else 0

            return {
                'type': meta.portfolio_type.value,
                'name': meta.name,
                'positions': len(portfolio.positions),
                'total_value': total_value,
                'total_cost': total_cost,
                'pnl': pnl,
                'pnl_pct': pnl_pct,
                'initial_capital': meta.initial_capital
            }

    def get_all_summaries(self) -> List[Dict]:
        """모든 포트폴리오 요약"""
        summaries = []
        for portfolio_id in self._meta:
            summary = self.get_summary(portfolio_id)
            summary['id'] = portfolio_id
            summaries.append(summary)
        return summaries


# 전역 인스턴스
portfolio_manager = MultiPortfolioManager()
