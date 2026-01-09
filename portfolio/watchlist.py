"""
워치리스트 관리
커스텀 그룹, 빠른 비교, 일괄 분석 기능
"""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


class WatchlistGroup(Enum):
    """워치리스트 그룹 유형"""
    FAVORITES = "favorites"
    TECH = "tech"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    ENERGY = "energy"
    DIVIDEND = "dividend"
    GROWTH = "growth"
    VALUE = "value"
    CUSTOM = "custom"


@dataclass
class WatchlistItem:
    """워치리스트 항목"""
    symbol: str
    name: str
    group: str = "favorites"
    added_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    notes: str = ""
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    alert_enabled: bool = False

    # 실시간 데이터 (캐시)
    current_price: Optional[float] = None
    change_pct: Optional[float] = None
    volume: Optional[int] = None
    last_updated: Optional[str] = None


@dataclass
class WatchlistGroupInfo:
    """워치리스트 그룹 정보"""
    name: str
    display_name: str
    icon: str = "📋"
    color: str = "#1f77b4"
    items: List[WatchlistItem] = field(default_factory=list)


class WatchlistManager:
    """워치리스트 관리자"""

    DEFAULT_GROUPS = {
        "favorites": WatchlistGroupInfo("favorites", "관심종목", "⭐", "#ffc107"),
        "tech": WatchlistGroupInfo("tech", "기술주", "💻", "#2196F3"),
        "finance": WatchlistGroupInfo("finance", "금융주", "🏦", "#4CAF50"),
        "healthcare": WatchlistGroupInfo("healthcare", "헬스케어", "🏥", "#9C27B0"),
        "energy": WatchlistGroupInfo("energy", "에너지", "⚡", "#FF5722"),
        "dividend": WatchlistGroupInfo("dividend", "배당주", "💰", "#795548"),
        "growth": WatchlistGroupInfo("growth", "성장주", "📈", "#00BCD4"),
        "value": WatchlistGroupInfo("value", "가치주", "💎", "#607D8B"),
    }

    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir or Path.home() / ".notion_portfolio")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.data_dir / "watchlist.json"

        self.groups: Dict[str, WatchlistGroupInfo] = {}
        self.items: Dict[str, WatchlistItem] = {}  # symbol -> item

        self._load()

    def _load(self):
        """데이터 로드"""
        # 기본 그룹 초기화
        self.groups = {k: WatchlistGroupInfo(v.name, v.display_name, v.icon, v.color)
                       for k, v in self.DEFAULT_GROUPS.items()}

        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 커스텀 그룹 로드
                for group_data in data.get('custom_groups', []):
                    group = WatchlistGroupInfo(**group_data)
                    self.groups[group.name] = group

                # 항목 로드
                for item_data in data.get('items', []):
                    item = WatchlistItem(**item_data)
                    self.items[item.symbol] = item

                    # 그룹에 항목 연결
                    if item.group in self.groups:
                        self.groups[item.group].items.append(item)

            except Exception as e:
                logger.error(f"워치리스트 로드 실패: {e}")

    def _save(self):
        """데이터 저장"""
        try:
            data = {
                'custom_groups': [
                    {
                        'name': g.name,
                        'display_name': g.display_name,
                        'icon': g.icon,
                        'color': g.color
                    }
                    for k, g in self.groups.items()
                    if k not in self.DEFAULT_GROUPS
                ],
                'items': [
                    {
                        'symbol': item.symbol,
                        'name': item.name,
                        'group': item.group,
                        'added_date': item.added_date,
                        'notes': item.notes,
                        'target_price': item.target_price,
                        'stop_loss': item.stop_loss,
                        'alert_enabled': item.alert_enabled
                    }
                    for item in self.items.values()
                ]
            }

            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"워치리스트 저장 실패: {e}")

    def add_item(self, symbol: str, name: str,
                 group: str = "favorites", **kwargs) -> WatchlistItem:
        """항목 추가"""
        if symbol in self.items:
            # 기존 항목 업데이트
            item = self.items[symbol]
            if item.group != group:
                # 그룹 변경
                if item.group in self.groups:
                    self.groups[item.group].items = [
                        i for i in self.groups[item.group].items
                        if i.symbol != symbol
                    ]
                item.group = group
                if group in self.groups:
                    self.groups[group].items.append(item)
        else:
            # 새 항목
            item = WatchlistItem(
                symbol=symbol,
                name=name,
                group=group,
                **kwargs
            )
            self.items[symbol] = item

            if group in self.groups:
                self.groups[group].items.append(item)

        self._save()
        return item

    def remove_item(self, symbol: str) -> bool:
        """항목 제거"""
        if symbol not in self.items:
            return False

        item = self.items[symbol]

        # 그룹에서 제거
        if item.group in self.groups:
            self.groups[item.group].items = [
                i for i in self.groups[item.group].items
                if i.symbol != symbol
            ]

        del self.items[symbol]
        self._save()
        return True

    def add_group(self, name: str, display_name: str,
                  icon: str = "📋", color: str = "#1f77b4") -> WatchlistGroupInfo:
        """커스텀 그룹 추가"""
        group = WatchlistGroupInfo(name, display_name, icon, color)
        self.groups[name] = group
        self._save()
        return group

    def remove_group(self, name: str) -> bool:
        """그룹 제거 (항목은 favorites로 이동)"""
        if name in self.DEFAULT_GROUPS or name not in self.groups:
            return False

        # 항목을 favorites로 이동
        for item in self.groups[name].items:
            item.group = "favorites"
            self.groups["favorites"].items.append(item)

        del self.groups[name]
        self._save()
        return True

    def get_items(self, group: str = None) -> List[WatchlistItem]:
        """항목 조회"""
        if group:
            return self.groups.get(group, WatchlistGroupInfo("", "")).items
        return list(self.items.values())

    def get_groups(self) -> Dict[str, WatchlistGroupInfo]:
        """그룹 조회"""
        return self.groups

    def update_prices(self) -> Dict[str, Dict]:
        """실시간 가격 업데이트"""
        if not YFINANCE_AVAILABLE or not self.items:
            return {}

        results = {}
        symbols = list(self.items.keys())

        try:
            # 배치로 가격 조회
            tickers = yf.Tickers(' '.join(symbols))

            for symbol in symbols:
                try:
                    ticker = tickers.tickers.get(symbol)
                    if ticker:
                        info = ticker.fast_info
                        hist = ticker.history(period="2d")

                        if not hist.empty:
                            current = hist['Close'].iloc[-1]
                            prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
                            change = ((current - prev) / prev * 100) if prev else 0

                            self.items[symbol].current_price = current
                            self.items[symbol].change_pct = change
                            self.items[symbol].volume = int(hist['Volume'].iloc[-1])
                            self.items[symbol].last_updated = datetime.now().strftime("%H:%M:%S")

                            results[symbol] = {
                                "price": current,
                                "change_pct": change,
                                "volume": int(hist['Volume'].iloc[-1])
                            }

                except Exception as e:
                    logger.warning(f"{symbol} 가격 조회 실패: {e}")

        except Exception as e:
            logger.error(f"가격 업데이트 실패: {e}")

        return results

    def get_comparison_data(self, symbols: List[str] = None,
                            period: str = "1mo") -> Dict[str, Any]:
        """비교 데이터 조회"""
        if not YFINANCE_AVAILABLE:
            return {}

        symbols = symbols or list(self.items.keys())
        if not symbols:
            return {}

        result = {
            "symbols": symbols,
            "period": period,
            "data": {},
            "summary": []
        }

        for symbol in symbols[:10]:  # 최대 10개
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period)

                if not hist.empty:
                    start_price = hist['Close'].iloc[0]
                    end_price = hist['Close'].iloc[-1]
                    return_pct = ((end_price - start_price) / start_price * 100)

                    result["data"][symbol] = {
                        "prices": hist['Close'].tolist(),
                        "dates": [d.strftime("%Y-%m-%d") for d in hist.index],
                        "start_price": start_price,
                        "end_price": end_price,
                        "return_pct": return_pct,
                        "high": hist['High'].max(),
                        "low": hist['Low'].min(),
                        "avg_volume": hist['Volume'].mean()
                    }

                    result["summary"].append({
                        "symbol": symbol,
                        "name": self.items.get(symbol, WatchlistItem(symbol, symbol)).name,
                        "return_pct": return_pct,
                        "current": end_price
                    })

            except Exception as e:
                logger.warning(f"{symbol} 데이터 조회 실패: {e}")

        # 수익률 순 정렬
        result["summary"].sort(key=lambda x: x["return_pct"], reverse=True)

        return result

    def batch_analysis(self, symbols: List[str] = None) -> List[Dict]:
        """일괄 분석"""
        if not YFINANCE_AVAILABLE:
            return []

        symbols = symbols or list(self.items.keys())
        results = []

        for symbol in symbols[:20]:  # 최대 20개
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="3mo")

                if hist.empty:
                    continue

                # 기본 정보
                current = hist['Close'].iloc[-1]
                ma20 = hist['Close'].rolling(20).mean().iloc[-1]
                ma50 = hist['Close'].rolling(50).mean().iloc[-1] if len(hist) >= 50 else ma20

                # RSI 계산
                delta = hist['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs.iloc[-1]))

                # 변동성
                volatility = hist['Close'].pct_change().std() * 100

                # 신호 판단
                if current > ma20 > ma50 and rsi < 70:
                    signal = "매수"
                    signal_strength = "강함"
                elif current < ma20 < ma50 and rsi > 30:
                    signal = "매도"
                    signal_strength = "강함"
                elif current > ma20:
                    signal = "보유"
                    signal_strength = "보통"
                else:
                    signal = "관망"
                    signal_strength = "약함"

                results.append({
                    "symbol": symbol,
                    "name": self.items.get(symbol, WatchlistItem(symbol, symbol)).name,
                    "current_price": current,
                    "ma20": ma20,
                    "ma50": ma50,
                    "rsi": rsi,
                    "volatility": volatility,
                    "signal": signal,
                    "signal_strength": signal_strength,
                    "above_ma20": current > ma20,
                    "above_ma50": current > ma50,
                    "pe_ratio": info.get('forwardPE'),
                    "market_cap": info.get('marketCap'),
                    "sector": info.get('sector', 'N/A')
                })

            except Exception as e:
                logger.warning(f"{symbol} 분석 실패: {e}")

        return results

    def export_to_csv(self, filepath: str = None) -> str:
        """CSV 내보내기"""
        import csv

        filepath = filepath or str(self.data_dir / "watchlist_export.csv")

        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['심볼', '종목명', '그룹', '추가일', '메모',
                             '목표가', '손절가', '현재가', '변동률'])

            for item in self.items.values():
                writer.writerow([
                    item.symbol,
                    item.name,
                    item.group,
                    item.added_date,
                    item.notes,
                    item.target_price or '',
                    item.stop_loss or '',
                    item.current_price or '',
                    f"{item.change_pct:.2f}%" if item.change_pct else ''
                ])

        return filepath

    def import_from_csv(self, filepath: str) -> int:
        """CSV 가져오기"""
        import csv

        count = 0
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    self.add_item(
                        symbol=row.get('심볼', row.get('symbol', '')),
                        name=row.get('종목명', row.get('name', '')),
                        group=row.get('그룹', row.get('group', 'favorites')),
                        notes=row.get('메모', row.get('notes', ''))
                    )
                    count += 1
                except Exception:
                    pass

        return count


# 싱글톤 인스턴스
watchlist_manager = WatchlistManager()


def add_to_watchlist(symbol: str, name: str,
                     group: str = "favorites") -> WatchlistItem:
    """워치리스트 추가"""
    return watchlist_manager.add_item(symbol, name, group)


def get_watchlist(group: str = None) -> List[WatchlistItem]:
    """워치리스트 조회"""
    return watchlist_manager.get_items(group)


def update_watchlist_prices() -> Dict[str, Dict]:
    """가격 업데이트"""
    return watchlist_manager.update_prices()
