"""
실시간 가격 알림 모듈
지정가, 변동률 기준 알림
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
import os
import logging

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


class AlertCondition(Enum):
    ABOVE = "above"         # 지정가 이상
    BELOW = "below"         # 지정가 이하
    CHANGE_UP = "change_up"   # 상승률 초과
    CHANGE_DOWN = "change_down"  # 하락률 초과
    VOLUME_SPIKE = "volume_spike"  # 거래량 급증


@dataclass
class PriceAlert:
    """가격 알림 설정"""
    id: str
    symbol: str
    name: str
    condition: AlertCondition
    target_value: float  # 지정가 또는 변동률(%)
    created_at: datetime = field(default_factory=datetime.now)
    triggered: bool = False
    triggered_at: Optional[datetime] = None
    triggered_price: Optional[float] = None
    base_price: Optional[float] = None  # 변동률 계산 기준가
    active: bool = True
    notification_sent: bool = False

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'symbol': self.symbol,
            'name': self.name,
            'condition': self.condition.value,
            'target_value': self.target_value,
            'created_at': self.created_at.isoformat(),
            'triggered': self.triggered,
            'triggered_at': self.triggered_at.isoformat() if self.triggered_at else None,
            'triggered_price': self.triggered_price,
            'base_price': self.base_price,
            'active': self.active,
            'notification_sent': self.notification_sent
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'PriceAlert':
        data['condition'] = AlertCondition(data['condition'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('triggered_at'):
            data['triggered_at'] = datetime.fromisoformat(data['triggered_at'])
        return cls(**data)


@dataclass
class TriggeredAlert:
    """발동된 알림"""
    alert: PriceAlert
    current_price: float
    change_pct: float
    message: str
    timestamp: datetime = field(default_factory=datetime.now)


class PriceMonitor:
    """실시간 가격 모니터링"""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.expanduser("~"), ".notion_portfolio")

        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

        self.alerts: Dict[str, PriceAlert] = {}
        self.triggered_history: List[TriggeredAlert] = []
        self._callbacks: List[Callable[[TriggeredAlert], None]] = []

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._check_interval = 60  # 1분 간격

        self._price_cache: Dict[str, Dict] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = 30  # 30초 캐시

        self._load_alerts()

    def _load_alerts(self):
        """알림 설정 로드"""
        file_path = os.path.join(self.data_dir, "price_alerts.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for alert_data in data.get('alerts', []):
                    alert = PriceAlert.from_dict(alert_data)
                    self.alerts[alert.id] = alert
            except Exception as e:
                logger.warning(f"가격 알림 로드 실패: {e}")

    def _save_alerts(self):
        """알림 설정 저장"""
        file_path = os.path.join(self.data_dir, "price_alerts.json")
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'alerts': [a.to_dict() for a in self.alerts.values()],
                    'updated_at': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"가격 알림 저장 실패: {e}")

    def add_alert(self, symbol: str, name: str, condition: AlertCondition,
                  target_value: float, base_price: float = None) -> PriceAlert:
        """알림 추가"""
        alert_id = f"{symbol}_{condition.value}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 변동률 알림의 경우 기준가 설정
        if condition in [AlertCondition.CHANGE_UP, AlertCondition.CHANGE_DOWN]:
            if base_price is None:
                price_data = self._get_price(symbol)
                base_price = price_data.get('price', 0) if price_data else 0

        alert = PriceAlert(
            id=alert_id,
            symbol=symbol,
            name=name,
            condition=condition,
            target_value=target_value,
            base_price=base_price
        )

        self.alerts[alert_id] = alert
        self._save_alerts()

        return alert

    def remove_alert(self, alert_id: str) -> bool:
        """알림 삭제"""
        if alert_id in self.alerts:
            del self.alerts[alert_id]
            self._save_alerts()
            return True
        return False

    def toggle_alert(self, alert_id: str) -> bool:
        """알림 활성화/비활성화"""
        if alert_id in self.alerts:
            self.alerts[alert_id].active = not self.alerts[alert_id].active
            self._save_alerts()
            return True
        return False

    def get_alerts(self, symbol: str = None, active_only: bool = False) -> List[PriceAlert]:
        """알림 목록 조회"""
        alerts = list(self.alerts.values())

        if symbol:
            alerts = [a for a in alerts if a.symbol == symbol]
        if active_only:
            alerts = [a for a in alerts if a.active and not a.triggered]

        return sorted(alerts, key=lambda a: a.created_at, reverse=True)

    def add_callback(self, callback: Callable[[TriggeredAlert], None]):
        """알림 발동 시 콜백 추가"""
        self._callbacks.append(callback)

    def _get_price(self, symbol: str) -> Optional[Dict]:
        """가격 조회 (캐시 포함)"""
        now = datetime.now()

        # 캐시 확인
        if symbol in self._cache_time:
            if now - self._cache_time[symbol] < timedelta(seconds=self._cache_ttl):
                return self._price_cache.get(symbol)

        if not YFINANCE_AVAILABLE:
            return None

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info

            price_data = {
                'price': info.last_price,
                'prev_close': info.previous_close,
                'volume': info.last_volume,
                'change_pct': ((info.last_price / info.previous_close) - 1) * 100 if info.previous_close else 0
            }

            self._price_cache[symbol] = price_data
            self._cache_time[symbol] = now

            return price_data

        except Exception as e:
            logger.debug(f"가격 조회 실패 ({symbol}): {e}")
            return None

    def check_alerts(self) -> List[TriggeredAlert]:
        """모든 알림 체크"""
        triggered = []

        for alert in self.alerts.values():
            if not alert.active or alert.triggered:
                continue

            price_data = self._get_price(alert.symbol)
            if not price_data:
                continue

            current_price = price_data['price']
            is_triggered = False
            message = ""

            if alert.condition == AlertCondition.ABOVE:
                if current_price >= alert.target_value:
                    is_triggered = True
                    message = f"📈 {alert.name}({alert.symbol}) 목표가 도달! 현재가: {current_price:,.0f}원 (목표: {alert.target_value:,.0f}원)"

            elif alert.condition == AlertCondition.BELOW:
                if current_price <= alert.target_value:
                    is_triggered = True
                    message = f"📉 {alert.name}({alert.symbol}) 손절가 도달! 현재가: {current_price:,.0f}원 (기준: {alert.target_value:,.0f}원)"

            elif alert.condition == AlertCondition.CHANGE_UP:
                if alert.base_price and alert.base_price > 0:
                    change = ((current_price / alert.base_price) - 1) * 100
                    if change >= alert.target_value:
                        is_triggered = True
                        message = f"🚀 {alert.name}({alert.symbol}) +{change:.1f}% 상승! (기준: +{alert.target_value:.1f}%)"

            elif alert.condition == AlertCondition.CHANGE_DOWN:
                if alert.base_price and alert.base_price > 0:
                    change = ((current_price / alert.base_price) - 1) * 100
                    if change <= -alert.target_value:
                        is_triggered = True
                        message = f"⚠️ {alert.name}({alert.symbol}) {change:.1f}% 하락! (기준: -{alert.target_value:.1f}%)"

            elif alert.condition == AlertCondition.VOLUME_SPIKE:
                # 거래량 급증 (평소 대비 N배 이상)
                avg_volume = price_data.get('avg_volume', price_data['volume'])
                if avg_volume > 0 and price_data['volume'] >= avg_volume * alert.target_value:
                    is_triggered = True
                    ratio = price_data['volume'] / avg_volume
                    message = f"📊 {alert.name}({alert.symbol}) 거래량 급증! 평소 대비 {ratio:.1f}배"

            if is_triggered:
                alert.triggered = True
                alert.triggered_at = datetime.now()
                alert.triggered_price = current_price

                triggered_alert = TriggeredAlert(
                    alert=alert,
                    current_price=current_price,
                    change_pct=price_data['change_pct'],
                    message=message
                )

                triggered.append(triggered_alert)
                self.triggered_history.append(triggered_alert)

                # 콜백 실행
                for callback in self._callbacks:
                    try:
                        callback(triggered_alert)
                    except Exception as e:
                        logger.warning(f"알림 콜백 실행 실패: {e}")

        if triggered:
            self._save_alerts()

        return triggered

    def start(self, interval: int = 60):
        """모니터링 시작"""
        if self._running:
            return

        self._check_interval = interval
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """모니터링 중지"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _monitor_loop(self):
        """모니터링 루프"""
        while self._running:
            try:
                self.check_alerts()
            except Exception as e:
                logger.error(f"모니터링 루프 오류: {e}")

            time.sleep(self._check_interval)

    def get_triggered_history(self, days: int = 7) -> List[TriggeredAlert]:
        """발동 이력 조회"""
        cutoff = datetime.now() - timedelta(days=days)
        return [t for t in self.triggered_history if t.timestamp > cutoff]


# 전역 인스턴스
price_monitor = PriceMonitor()
