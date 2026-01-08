"""
백그라운드 알림 스케줄러
주기적으로 위험 모니터링 및 알림 전송
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Optional
import json
import os

try:
    from portfolio.risk_monitor import RiskMonitor, RiskAlert, AlertSeverity
    RISK_MONITOR_AVAILABLE = True
except ImportError:
    RISK_MONITOR_AVAILABLE = False


class AlertScheduler:
    """백그라운드 알림 스케줄러"""

    def __init__(self, check_interval: int = 300):  # 기본 5분
        self.check_interval = check_interval
        self.running = False
        self._thread = None
        self._callbacks: List[Callable] = []
        self._last_alerts: Dict[str, RiskAlert] = {}
        self._alert_history: List[Dict] = []

        # 알림 설정
        self.settings = {
            'telegram_enabled': False,
            'telegram_token': os.getenv('TELEGRAM_BOT_TOKEN'),
            'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID'),
            'discord_enabled': False,
            'discord_webhook': os.getenv('DISCORD_WEBHOOK_URL'),
            'email_enabled': False,
            'min_severity': 'WARNING',  # WARNING, CRITICAL, EMERGENCY
        }

    def add_callback(self, callback: Callable):
        """알림 콜백 추가"""
        self._callbacks.append(callback)

    def start(self, portfolio=None):
        """스케줄러 시작"""
        if self.running:
            return

        self.running = True
        self._portfolio = portfolio
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print(f"[AlertScheduler] 시작됨 (체크 주기: {self.check_interval}초)")

    def stop(self):
        """스케줄러 중지"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("[AlertScheduler] 중지됨")

    def _run_loop(self):
        """메인 루프"""
        while self.running:
            try:
                self._check_alerts()
            except Exception as e:
                print(f"[AlertScheduler] 체크 오류: {e}")

            time.sleep(self.check_interval)

    def _check_alerts(self):
        """알림 체크"""
        if not RISK_MONITOR_AVAILABLE or not self._portfolio:
            return

        monitor = RiskMonitor()
        alerts = monitor.check_all_risks(self._portfolio)

        # 새로운 알림만 필터링
        new_alerts = []
        for alert in alerts:
            alert_key = f"{alert.symbol}_{alert.alert_type.value}"

            # 이미 전송된 알림인지 확인 (1시간 내 동일 알림 무시)
            if alert_key in self._last_alerts:
                last = self._last_alerts[alert_key]
                if datetime.now() - last.timestamp < timedelta(hours=1):
                    continue

            # 심각도 필터
            severity_order = ['INFO', 'WARNING', 'CRITICAL', 'EMERGENCY']
            min_idx = severity_order.index(self.settings['min_severity'])
            alert_idx = severity_order.index(alert.severity.value.upper())

            if alert_idx >= min_idx:
                new_alerts.append(alert)
                self._last_alerts[alert_key] = alert

        # 새 알림 처리
        for alert in new_alerts:
            self._process_alert(alert)

    def _process_alert(self, alert: RiskAlert):
        """알림 처리"""
        # 히스토리에 추가
        self._alert_history.append({
            'timestamp': alert.timestamp.isoformat(),
            'symbol': alert.symbol,
            'type': alert.alert_type.value,
            'severity': alert.severity.value,
            'title': alert.title,
            'message': alert.message,
        })

        # 콜백 호출
        for callback in self._callbacks:
            try:
                callback(alert)
            except Exception as e:
                print(f"[AlertScheduler] 콜백 오류: {e}")

        # 텔레그램 전송
        if self.settings['telegram_enabled']:
            self._send_telegram(alert)

        # Discord 전송
        if self.settings['discord_enabled']:
            self._send_discord(alert)

    def _send_telegram(self, alert: RiskAlert):
        """텔레그램으로 알림 전송"""
        try:
            import requests

            token = self.settings['telegram_token']
            chat_id = self.settings['telegram_chat_id']

            if not token or not chat_id:
                return

            severity_emoji = {
                'info': 'ℹ️',
                'warning': '⚠️',
                'critical': '🔴',
                'emergency': '🚨'
            }

            emoji = severity_emoji.get(alert.severity.value, '📢')
            message = f"{emoji} *{alert.title}*\n\n"
            message += f"종목: {alert.symbol}\n"
            message += f"내용: {alert.message}\n"
            message += f"조치: {alert.recommended_action}\n"
            message += f"시간: {alert.timestamp.strftime('%H:%M:%S')}"

            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }

            requests.post(url, data=data, timeout=10)
            print(f"[Telegram] 알림 전송: {alert.title}")

        except Exception as e:
            print(f"[Telegram] 전송 실패: {e}")

    def _send_discord(self, alert: RiskAlert):
        """Discord로 알림 전송"""
        try:
            import requests

            webhook_url = self.settings['discord_webhook']
            if not webhook_url:
                return

            color_map = {
                'info': 0x3498db,
                'warning': 0xf39c12,
                'critical': 0xe74c3c,
                'emergency': 0x9b59b6
            }

            embed = {
                'title': alert.title,
                'description': alert.message,
                'color': color_map.get(alert.severity.value, 0x95a5a6),
                'fields': [
                    {'name': '종목', 'value': alert.symbol, 'inline': True},
                    {'name': '심각도', 'value': alert.severity.value.upper(), 'inline': True},
                    {'name': '권고 조치', 'value': alert.recommended_action, 'inline': False},
                ],
                'timestamp': alert.timestamp.isoformat()
            }

            data = {'embeds': [embed]}
            requests.post(webhook_url, json=data, timeout=10)
            print(f"[Discord] 알림 전송: {alert.title}")

        except Exception as e:
            print(f"[Discord] 전송 실패: {e}")

    def get_alert_history(self, limit: int = 50) -> List[Dict]:
        """최근 알림 히스토리"""
        return self._alert_history[-limit:]

    def update_settings(self, **kwargs):
        """설정 업데이트"""
        self.settings.update(kwargs)


# 전역 스케줄러 인스턴스
alert_scheduler = AlertScheduler()


def start_background_alerts(portfolio, interval: int = 300):
    """백그라운드 알림 시작"""
    alert_scheduler.start(portfolio)
    return alert_scheduler


def stop_background_alerts():
    """백그라운드 알림 중지"""
    alert_scheduler.stop()
