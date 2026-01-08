"""
가격 알림 시스템
실시간 가격 모니터링 및 알림
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False

from .telegram_bot import TelegramNotifier
from .discord_bot import DiscordNotifier


class AlertCondition(Enum):
    """알림 조건"""
    ABOVE = "above"           # 가격 이상
    BELOW = "below"           # 가격 이하
    CHANGE_UP = "change_up"   # % 상승
    CHANGE_DOWN = "change_down"  # % 하락
    CHANGE_ABS = "change_abs"    # % 절대 변동


@dataclass
class PriceAlert:
    """가격 알림 설정"""
    symbol: str
    condition: AlertCondition
    value: float              # 가격 또는 %
    name: Optional[str] = None
    triggered: bool = False
    repeat: bool = False      # 반복 알림 여부
    cooldown_minutes: int = 60
    last_triggered: Optional[datetime] = None
    channels: List[str] = field(default_factory=lambda: ['telegram', 'discord'])

    def __post_init__(self):
        if self.name is None:
            self.name = f"{self.symbol} {self.condition.value} {self.value}"


class PriceAlertSystem:
    """가격 알림 시스템"""

    def __init__(self,
                 telegram_notifier: Optional[TelegramNotifier] = None,
                 discord_notifier: Optional[DiscordNotifier] = None):
        """
        초기화

        Args:
            telegram_notifier: 텔레그램 알림기
            discord_notifier: 디스코드 알림기
        """
        self.telegram = telegram_notifier or TelegramNotifier()
        self.discord = discord_notifier or DiscordNotifier()

        self.alerts: List[PriceAlert] = []
        self.price_cache: Dict[str, Dict] = {}  # symbol -> {price, timestamp, prev_close}

        self.is_running = False
        self._thread: Optional[threading.Thread] = None

    def add_alert(self, alert: PriceAlert):
        """알림 추가"""
        self.alerts.append(alert)
        print(f"알림 추가: {alert.name}")

    def add_price_alert(self, symbol: str, condition: str, value: float,
                       name: Optional[str] = None, repeat: bool = False) -> PriceAlert:
        """간편하게 알림 추가"""
        condition_enum = AlertCondition(condition)

        alert = PriceAlert(
            symbol=symbol.upper(),
            condition=condition_enum,
            value=value,
            name=name,
            repeat=repeat,
        )
        self.add_alert(alert)
        return alert

    def remove_alert(self, name: str):
        """알림 제거"""
        self.alerts = [a for a in self.alerts if a.name != name]

    def list_alerts(self) -> List[Dict]:
        """알림 목록"""
        return [
            {
                'name': a.name,
                'symbol': a.symbol,
                'condition': a.condition.value,
                'value': a.value,
                'triggered': a.triggered,
                'repeat': a.repeat,
            }
            for a in self.alerts
        ]

    def _fetch_price(self, symbol: str) -> Optional[Dict]:
        """현재 가격 조회"""
        if not YFINANCE_AVAILABLE:
            return None

        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='2d')

            if data.empty:
                return None

            current_price = data['Close'].iloc[-1]
            prev_close = data['Close'].iloc[-2] if len(data) > 1 else current_price

            return {
                'price': current_price,
                'prev_close': prev_close,
                'change': current_price - prev_close,
                'change_pct': (current_price / prev_close - 1) * 100,
                'timestamp': datetime.now(),
            }
        except Exception as e:
            print(f"가격 조회 실패 ({symbol}): {e}")
            return None

    def _update_prices(self):
        """모든 심볼 가격 업데이트"""
        symbols = list(set(a.symbol for a in self.alerts))

        for symbol in symbols:
            price_data = self._fetch_price(symbol)
            if price_data:
                self.price_cache[symbol] = price_data

    def _check_condition(self, alert: PriceAlert, price_data: Dict) -> bool:
        """조건 충족 여부 확인"""
        price = price_data['price']
        change_pct = price_data['change_pct']

        if alert.condition == AlertCondition.ABOVE:
            return price >= alert.value

        elif alert.condition == AlertCondition.BELOW:
            return price <= alert.value

        elif alert.condition == AlertCondition.CHANGE_UP:
            return change_pct >= alert.value

        elif alert.condition == AlertCondition.CHANGE_DOWN:
            return change_pct <= -alert.value

        elif alert.condition == AlertCondition.CHANGE_ABS:
            return abs(change_pct) >= alert.value

        return False

    def _can_trigger(self, alert: PriceAlert) -> bool:
        """알림 발송 가능 여부"""
        # 이미 트리거되고 반복 아닌 경우
        if alert.triggered and not alert.repeat:
            return False

        # 쿨다운 확인
        if alert.last_triggered:
            elapsed = datetime.now() - alert.last_triggered
            if elapsed < timedelta(minutes=alert.cooldown_minutes):
                return False

        return True

    def _send_alert(self, alert: PriceAlert, price_data: Dict):
        """알림 전송"""
        symbol = alert.symbol
        price = price_data['price']
        change_pct = price_data['change_pct']

        # 알림 타입 결정
        if alert.condition in [AlertCondition.ABOVE, AlertCondition.CHANGE_UP]:
            alert_type = 'above'
        elif alert.condition in [AlertCondition.BELOW, AlertCondition.CHANGE_DOWN]:
            alert_type = 'below'
        else:
            alert_type = 'change'

        # 텔레그램
        if 'telegram' in alert.channels and self.telegram.enabled:
            self.telegram.send_price_alert(
                symbol=symbol,
                current_price=price,
                alert_type=alert_type,
                threshold=alert.value,
                change_pct=change_pct,
            )

        # 디스코드
        if 'discord' in alert.channels and self.discord.enabled:
            self.discord.send_price_alert(
                symbol=symbol,
                current_price=price,
                alert_type=alert_type,
                threshold=alert.value,
                change_pct=change_pct,
            )

        print(f"[Price Alert] {alert.name}: ${price:.2f} ({change_pct:+.2f}%)")

        # 상태 업데이트
        alert.triggered = True
        alert.last_triggered = datetime.now()

    def check_alerts(self):
        """알림 확인"""
        if not self.alerts:
            return

        # 가격 업데이트
        self._update_prices()

        # 각 알림 확인
        for alert in self.alerts:
            if alert.symbol not in self.price_cache:
                continue

            price_data = self.price_cache[alert.symbol]

            if not self._can_trigger(alert):
                continue

            if self._check_condition(alert, price_data):
                self._send_alert(alert, price_data)

    def start(self, interval_seconds: int = 60):
        """알림 시스템 시작"""
        if not SCHEDULE_AVAILABLE:
            print("schedule 라이브러리가 필요합니다. pip install schedule")
            return

        if not YFINANCE_AVAILABLE:
            print("yfinance 라이브러리가 필요합니다.")
            return

        if self.is_running:
            print("이미 실행 중입니다.")
            return

        self.is_running = True

        # 스케줄 설정
        schedule.every(interval_seconds).seconds.do(self.check_alerts)

        # 즉시 1회 실행
        self.check_alerts()

        # 백그라운드 스레드
        def run_schedule():
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)

        self._thread = threading.Thread(target=run_schedule, daemon=True)
        self._thread.start()

        print(f"가격 알림 시스템 시작됨 (간격: {interval_seconds}초)")

    def stop(self):
        """알림 시스템 중지"""
        self.is_running = False
        schedule.clear()

        if self._thread:
            self._thread.join(timeout=5)

        print("가격 알림 시스템 중지됨")

    def get_status(self) -> Dict:
        """상태 조회"""
        return {
            'is_running': self.is_running,
            'alerts_count': len(self.alerts),
            'active_alerts': len([a for a in self.alerts if not a.triggered or a.repeat]),
            'triggered_alerts': len([a for a in self.alerts if a.triggered]),
            'cached_symbols': list(self.price_cache.keys()),
            'telegram_enabled': self.telegram.enabled,
            'discord_enabled': self.discord.enabled,
        }

    def get_current_prices(self) -> Dict:
        """캐시된 현재 가격"""
        return {
            symbol: {
                'price': data['price'],
                'change_pct': data['change_pct'],
                'updated': data['timestamp'].strftime('%H:%M:%S'),
            }
            for symbol, data in self.price_cache.items()
        }


# 사용 예시
def example_usage():
    """사용 예시"""
    system = PriceAlertSystem()

    # 가격 알림 추가
    system.add_price_alert('AAPL', 'above', 200, name='애플 $200 돌파')
    system.add_price_alert('AAPL', 'below', 170, name='애플 $170 하회')
    system.add_price_alert('NVDA', 'change_abs', 5, name='엔비디아 5% 변동', repeat=True)

    # 시작
    system.start(interval_seconds=60)

    # 상태 확인
    print(system.get_status())

    # 중지
    # system.stop()
