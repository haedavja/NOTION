"""
포트폴리오 데이터 모델
사용자의 포트폴리오와 포지션 정보를 관리합니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


class AssetType(Enum):
    """자산 유형"""
    STOCK = "주식"
    ETF = "ETF"
    BOND = "채권"
    COMMODITY = "원자재"
    CRYPTO = "암호화폐"
    CASH = "현금"
    OTHER = "기타"


class InvestmentThesis(Enum):
    """투자 논리 유형"""
    GROWTH = "성장주"              # 성장 기대
    VALUE = "가치주"               # 저평가
    DIVIDEND = "배당"              # 배당 수익
    MOMENTUM = "모멘텀"            # 추세 추종
    MACRO = "거시경제"             # 거시경제 전망
    SECTOR_ROTATION = "섹터로테이션"  # 섹터 전환
    TECHNICAL = "기술적"           # 차트 기반
    EVENT = "이벤트"               # 특정 이벤트
    HEDGE = "헷지"                 # 리스크 헷지
    SPECULATION = "투기"           # 단기 투기
    OTHER = "기타"


@dataclass
class Position:
    """개별 포지션"""
    symbol: str                              # 티커 심볼
    name: str                                # 종목명
    quantity: float                          # 수량
    avg_cost: float                          # 평균 매수가
    purchase_date: Optional[datetime] = None # 매수일
    asset_type: AssetType = AssetType.STOCK

    # 투자 논리
    thesis_type: InvestmentThesis = InvestmentThesis.OTHER
    thesis_description: str = ""             # 왜 샀는지 이유
    target_price: Optional[float] = None     # 목표가
    stop_loss: Optional[float] = None        # 손절가
    time_horizon: str = "중기"               # 투자 기간 (단기/중기/장기)

    # 실시간 데이터 (분석 시 업데이트)
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_pct: Optional[float] = None
    weight: Optional[float] = None           # 포트폴리오 비중

    def __post_init__(self):
        """초기화 후 처리"""
        if isinstance(self.thesis_type, str):
            try:
                self.thesis_type = InvestmentThesis[self.thesis_type.upper()]
            except KeyError:
                self.thesis_type = InvestmentThesis.OTHER

        if isinstance(self.asset_type, str):
            try:
                self.asset_type = AssetType[self.asset_type.upper()]
            except KeyError:
                self.asset_type = AssetType.OTHER

    @property
    def cost_basis(self) -> float:
        """총 매수 금액"""
        return self.quantity * self.avg_cost

    def update_market_data(self, current_price: float):
        """시장 데이터 업데이트"""
        self.current_price = current_price
        self.market_value = self.quantity * current_price
        self.unrealized_pnl = self.market_value - self.cost_basis
        self.unrealized_pnl_pct = (self.unrealized_pnl / self.cost_basis) * 100 if self.cost_basis > 0 else 0

    def to_dict(self) -> Dict:
        """딕셔너리 변환"""
        return {
            'symbol': self.symbol,
            'name': self.name,
            'quantity': self.quantity,
            'avg_cost': self.avg_cost,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'asset_type': self.asset_type.value,
            'thesis_type': self.thesis_type.value,
            'thesis_description': self.thesis_description,
            'target_price': self.target_price,
            'stop_loss': self.stop_loss,
            'time_horizon': self.time_horizon,
            'current_price': self.current_price,
            'market_value': self.market_value,
            'unrealized_pnl': self.unrealized_pnl,
            'unrealized_pnl_pct': self.unrealized_pnl_pct,
            'weight': self.weight,
        }


@dataclass
class Portfolio:
    """포트폴리오"""
    name: str = "My Portfolio"
    positions: List[Position] = field(default_factory=list)
    cash: float = 0.0
    currency: str = "USD"
    created_at: datetime = field(default_factory=datetime.now)

    def add_position(self, position: Position):
        """포지션 추가"""
        # 같은 심볼이 있으면 업데이트
        for i, p in enumerate(self.positions):
            if p.symbol.upper() == position.symbol.upper():
                self.positions[i] = position
                return
        self.positions.append(position)

    def remove_position(self, symbol: str):
        """포지션 제거"""
        self.positions = [p for p in self.positions if p.symbol.upper() != symbol.upper()]

    def get_position(self, symbol: str) -> Optional[Position]:
        """특정 포지션 조회"""
        for p in self.positions:
            if p.symbol.upper() == symbol.upper():
                return p
        return None

    @property
    def total_cost_basis(self) -> float:
        """총 투자 원금"""
        return sum(p.cost_basis for p in self.positions)

    @property
    def total_market_value(self) -> float:
        """총 시장 가치"""
        market_value = sum(p.market_value for p in self.positions if p.market_value is not None)
        return market_value + self.cash

    @property
    def total_unrealized_pnl(self) -> float:
        """총 미실현 손익"""
        return sum(p.unrealized_pnl for p in self.positions if p.unrealized_pnl is not None)

    @property
    def total_unrealized_pnl_pct(self) -> float:
        """총 미실현 손익률"""
        if self.total_cost_basis > 0:
            return (self.total_unrealized_pnl / self.total_cost_basis) * 100
        return 0

    def update_weights(self):
        """포지션 비중 업데이트"""
        total = self.total_market_value
        if total > 0:
            for p in self.positions:
                if p.market_value is not None:
                    p.weight = (p.market_value / total) * 100
            # 현금 비중
            self.cash_weight = (self.cash / total) * 100

    def fetch_current_prices(self):
        """현재가 조회"""
        if not YFINANCE_AVAILABLE:
            print("Warning: yfinance가 설치되지 않았습니다.")
            return

        symbols = [p.symbol for p in self.positions]
        if not symbols:
            return

        try:
            data = yf.download(symbols, period='1d', progress=False)

            if len(symbols) == 1:
                current_price = data['Close'].iloc[-1]
                self.positions[0].update_market_data(current_price)
            else:
                for p in self.positions:
                    if p.symbol in data['Close'].columns:
                        current_price = data['Close'][p.symbol].iloc[-1]
                        p.update_market_data(current_price)

            self.update_weights()

        except Exception as e:
            print(f"가격 조회 실패: {e}")

    def get_allocation_by_asset_type(self) -> Dict[str, float]:
        """자산 유형별 비중"""
        allocation = {}
        for p in self.positions:
            asset_type = p.asset_type.value
            weight = p.weight or 0
            allocation[asset_type] = allocation.get(asset_type, 0) + weight
        return allocation

    def get_allocation_by_thesis(self) -> Dict[str, float]:
        """투자 논리별 비중"""
        allocation = {}
        for p in self.positions:
            thesis = p.thesis_type.value
            weight = p.weight or 0
            allocation[thesis] = allocation.get(thesis, 0) + weight
        return allocation

    def to_dataframe(self) -> pd.DataFrame:
        """데이터프레임 변환"""
        if not self.positions:
            return pd.DataFrame()

        data = [p.to_dict() for p in self.positions]
        return pd.DataFrame(data)

    def to_dict(self) -> Dict:
        """딕셔너리 변환"""
        return {
            'name': self.name,
            'positions': [p.to_dict() for p in self.positions],
            'cash': self.cash,
            'currency': self.currency,
            'total_cost_basis': self.total_cost_basis,
            'total_market_value': self.total_market_value,
            'total_unrealized_pnl': self.total_unrealized_pnl,
            'total_unrealized_pnl_pct': self.total_unrealized_pnl_pct,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'Portfolio':
        """딕셔너리에서 생성"""
        portfolio = cls(
            name=data.get('name', 'My Portfolio'),
            cash=data.get('cash', 0),
            currency=data.get('currency', 'USD'),
        )

        for pos_data in data.get('positions', []):
            position = Position(
                symbol=pos_data['symbol'],
                name=pos_data.get('name', pos_data['symbol']),
                quantity=pos_data['quantity'],
                avg_cost=pos_data['avg_cost'],
                purchase_date=datetime.fromisoformat(pos_data['purchase_date']) if pos_data.get('purchase_date') else None,
                asset_type=pos_data.get('asset_type', 'STOCK'),
                thesis_type=pos_data.get('thesis_type', 'OTHER'),
                thesis_description=pos_data.get('thesis_description', ''),
                target_price=pos_data.get('target_price'),
                stop_loss=pos_data.get('stop_loss'),
                time_horizon=pos_data.get('time_horizon', '중기'),
            )
            portfolio.add_position(position)

        return portfolio


# 샘플 포트폴리오 생성
def create_sample_portfolio() -> Portfolio:
    """샘플 포트폴리오 생성"""
    portfolio = Portfolio(name="샘플 포트폴리오", cash=5000)

    # 샘플 포지션들
    positions = [
        Position(
            symbol="AAPL",
            name="Apple Inc.",
            quantity=50,
            avg_cost=175.0,
            purchase_date=datetime(2024, 3, 15),
            asset_type=AssetType.STOCK,
            thesis_type=InvestmentThesis.GROWTH,
            thesis_description="AI와 Vision Pro로 새로운 성장 동력 확보. 서비스 매출 지속 성장 기대. 강력한 현금 창출력과 자사주 매입.",
            target_price=220.0,
            stop_loss=160.0,
            time_horizon="중기",
        ),
        Position(
            symbol="NVDA",
            name="NVIDIA Corp.",
            quantity=30,
            avg_cost=450.0,
            purchase_date=datetime(2024, 1, 10),
            asset_type=AssetType.STOCK,
            thesis_type=InvestmentThesis.GROWTH,
            thesis_description="AI 칩 시장 독점적 지위. 데이터센터 GPU 수요 폭발적 증가. AI 인프라 투자 사이클 초입.",
            target_price=600.0,
            stop_loss=380.0,
            time_horizon="장기",
        ),
        Position(
            symbol="TLT",
            name="iShares 20+ Year Treasury Bond ETF",
            quantity=100,
            avg_cost=92.0,
            purchase_date=datetime(2024, 6, 1),
            asset_type=AssetType.ETF,
            thesis_type=InvestmentThesis.MACRO,
            thesis_description="금리 인하 사이클 진입 기대. 경기 둔화 시 안전자산 선호 증가. 주식 포트폴리오 헷지 목적.",
            target_price=110.0,
            stop_loss=85.0,
            time_horizon="중기",
        ),
        Position(
            symbol="XLE",
            name="Energy Select Sector SPDR",
            quantity=80,
            avg_cost=85.0,
            purchase_date=datetime(2024, 4, 20),
            asset_type=AssetType.ETF,
            thesis_type=InvestmentThesis.SECTOR_ROTATION,
            thesis_description="인플레이션 헷지. 지정학적 리스크로 유가 상승 가능성. 배당 수익률 매력적.",
            target_price=100.0,
            stop_loss=75.0,
            time_horizon="중기",
        ),
        Position(
            symbol="MSFT",
            name="Microsoft Corp.",
            quantity=25,
            avg_cost=380.0,
            purchase_date=datetime(2024, 2, 5),
            asset_type=AssetType.STOCK,
            thesis_type=InvestmentThesis.GROWTH,
            thesis_description="클라우드 Azure 성장 지속. Copilot AI 제품군 확대. 기업용 소프트웨어 독점적 지위.",
            target_price=450.0,
            stop_loss=340.0,
            time_horizon="장기",
        ),
        Position(
            symbol="JPM",
            name="JPMorgan Chase & Co.",
            quantity=40,
            avg_cost=165.0,
            purchase_date=datetime(2024, 5, 10),
            asset_type=AssetType.STOCK,
            thesis_type=InvestmentThesis.VALUE,
            thesis_description="고금리 환경에서 순이자마진 확대. 저평가된 밸류에이션. 안정적 배당.",
            target_price=200.0,
            stop_loss=150.0,
            time_horizon="중기",
        ),
    ]

    for pos in positions:
        portfolio.add_position(pos)

    # 샘플 가격 설정 (실제로는 fetch_current_prices 사용)
    sample_prices = {
        'AAPL': 195.0,
        'NVDA': 520.0,
        'TLT': 88.0,
        'XLE': 90.0,
        'MSFT': 420.0,
        'JPM': 180.0,
    }

    for p in portfolio.positions:
        if p.symbol in sample_prices:
            p.update_market_data(sample_prices[p.symbol])

    portfolio.update_weights()

    return portfolio
