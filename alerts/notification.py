"""
푸시 알림 시스템
텔레그램, 슬랙, 이메일 알림 지원
"""

import os
import json
import smtplib
import requests
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class NotificationMessage:
    """알림 메시지"""
    title: str
    body: str
    type: str = "info"  # info, alert, warning, error
    symbol: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class NotificationConfig:
    """알림 설정"""
    # 텔레그램
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # 슬랙
    slack_enabled: bool = False
    slack_webhook_url: str = ""

    # 이메일
    email_enabled: bool = False
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_to: str = ""

    # 알림 필터
    min_priority: str = "info"  # info, alert, warning, error
    quiet_hours_start: int = 22  # 22시부터
    quiet_hours_end: int = 8     # 8시까지 무음


class NotificationChannel(ABC):
    """알림 채널 추상 클래스"""

    @abstractmethod
    def send(self, message: NotificationMessage) -> bool:
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        pass


class TelegramChannel(NotificationChannel):
    """텔레그램 알림 채널"""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send(self, message: NotificationMessage) -> bool:
        if not self.is_configured():
            return False

        try:
            # 이모지 매핑
            emoji_map = {
                "info": "ℹ️",
                "alert": "🔔",
                "warning": "⚠️",
                "error": "🚨"
            }
            emoji = emoji_map.get(message.type, "📢")

            # 메시지 포맷
            text = f"{emoji} *{message.title}*\n\n{message.body}"

            if message.symbol:
                text += f"\n\n📊 종목: {message.symbol}"

            if message.data:
                text += "\n\n📋 상세 정보:"
                for key, value in message.data.items():
                    text += f"\n• {key}: {value}"

            # API 호출
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": "Markdown"
                },
                timeout=10
            )

            return response.status_code == 200

        except Exception as e:
            print(f"텔레그램 전송 실패: {e}")
            return False


class SlackChannel(NotificationChannel):
    """슬랙 알림 채널"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def is_configured(self) -> bool:
        return bool(self.webhook_url)

    def send(self, message: NotificationMessage) -> bool:
        if not self.is_configured():
            return False

        try:
            # 색상 매핑
            color_map = {
                "info": "#36a64f",
                "alert": "#2196F3",
                "warning": "#ff9800",
                "error": "#f44336"
            }
            color = color_map.get(message.type, "#808080")

            # 슬랙 블록 포맷
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": message.title
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message.body
                    }
                }
            ]

            if message.symbol:
                blocks.append({
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"📊 *종목:* {message.symbol}"
                        }
                    ]
                })

            # 웹훅 호출
            response = requests.post(
                self.webhook_url,
                json={
                    "attachments": [{
                        "color": color,
                        "blocks": blocks
                    }]
                },
                timeout=10
            )

            return response.status_code == 200

        except Exception as e:
            print(f"슬랙 전송 실패: {e}")
            return False


class EmailChannel(NotificationChannel):
    """이메일 알림 채널"""

    def __init__(self, smtp_server: str, smtp_port: int,
                 username: str, password: str, to_email: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.to_email = to_email

    def is_configured(self) -> bool:
        return bool(self.username and self.password and self.to_email)

    def send(self, message: NotificationMessage) -> bool:
        if not self.is_configured():
            return False

        try:
            # 이메일 생성
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[NOTION] {message.title}"
            msg['From'] = self.username
            msg['To'] = self.to_email

            # HTML 본문
            html = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    .header {{ background: #1f77b4; color: white; padding: 15px; }}
                    .content {{ padding: 20px; }}
                    .footer {{ background: #f5f5f5; padding: 10px; font-size: 12px; color: #666; }}
                    .alert {{ border-left: 4px solid #f44336; padding-left: 10px; }}
                    .info {{ border-left: 4px solid #2196F3; padding-left: 10px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>{message.title}</h2>
                </div>
                <div class="content">
                    <div class="{message.type}">
                        <p>{message.body}</p>
                    </div>
            """

            if message.symbol:
                html += f"<p><strong>종목:</strong> {message.symbol}</p>"

            if message.data:
                html += "<h4>상세 정보</h4><ul>"
                for key, value in message.data.items():
                    html += f"<li><strong>{key}:</strong> {value}</li>"
                html += "</ul>"

            html += f"""
                </div>
                <div class="footer">
                    <p>발송 시간: {message.timestamp}</p>
                    <p>NOTION 포트폴리오 관리 시스템</p>
                </div>
            </body>
            </html>
            """

            msg.attach(MIMEText(html, 'html'))

            # SMTP 전송
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            return True

        except Exception as e:
            print(f"이메일 전송 실패: {e}")
            return False


class NotificationManager:
    """알림 관리자"""

    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config or NotificationConfig()
        self.channels: List[NotificationChannel] = []
        self.history: List[Dict] = []
        self.history_file = Path.home() / ".notion_portfolio" / "notification_history.json"

        self._init_channels()
        self._load_history()

    def _init_channels(self):
        """알림 채널 초기화"""
        # 환경변수에서 설정 로드
        if os.getenv("TELEGRAM_BOT_TOKEN"):
            self.config.telegram_enabled = True
            self.config.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
            self.config.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

        if os.getenv("SLACK_WEBHOOK_URL"):
            self.config.slack_enabled = True
            self.config.slack_webhook_url = os.getenv("SLACK_WEBHOOK_URL", "")

        if os.getenv("SMTP_USERNAME"):
            self.config.email_enabled = True
            self.config.smtp_username = os.getenv("SMTP_USERNAME", "")
            self.config.smtp_password = os.getenv("SMTP_PASSWORD", "")
            self.config.email_to = os.getenv("EMAIL_TO", "")

        # 채널 생성
        if self.config.telegram_enabled:
            self.channels.append(TelegramChannel(
                self.config.telegram_bot_token,
                self.config.telegram_chat_id
            ))

        if self.config.slack_enabled:
            self.channels.append(SlackChannel(self.config.slack_webhook_url))

        if self.config.email_enabled:
            self.channels.append(EmailChannel(
                self.config.smtp_server,
                self.config.smtp_port,
                self.config.smtp_username,
                self.config.smtp_password,
                self.config.email_to
            ))

    def _load_history(self):
        """알림 히스토리 로드"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
        except Exception as e:
            logger.warning(f"알림 히스토리 로드 실패: {e}")
            self.history = []

    def _save_history(self):
        """알림 히스토리 저장"""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            # 최근 1000개만 유지
            self.history = self.history[-1000:]
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"알림 히스토리 저장 실패: {e}")

    def _is_quiet_hours(self) -> bool:
        """무음 시간 확인"""
        hour = datetime.now().hour
        if self.config.quiet_hours_start > self.config.quiet_hours_end:
            # 예: 22시 ~ 8시
            return hour >= self.config.quiet_hours_start or hour < self.config.quiet_hours_end
        else:
            return self.config.quiet_hours_start <= hour < self.config.quiet_hours_end

    def _check_priority(self, msg_type: str) -> bool:
        """우선순위 확인"""
        priority_order = ["info", "alert", "warning", "error"]
        min_idx = priority_order.index(self.config.min_priority)
        msg_idx = priority_order.index(msg_type) if msg_type in priority_order else 0
        return msg_idx >= min_idx

    def send(self, message: NotificationMessage, force: bool = False) -> Dict[str, bool]:
        """알림 전송"""
        results = {}

        # 무음 시간 및 우선순위 체크
        if not force:
            if self._is_quiet_hours() and message.type not in ["warning", "error"]:
                return {"skipped": True, "reason": "quiet_hours"}

            if not self._check_priority(message.type):
                return {"skipped": True, "reason": "low_priority"}

        # 각 채널로 전송
        for channel in self.channels:
            channel_name = channel.__class__.__name__
            if channel.is_configured():
                results[channel_name] = channel.send(message)

        # 히스토리 저장
        self.history.append({
            **asdict(message),
            "results": results
        })
        self._save_history()

        return results

    def send_price_alert(self, symbol: str, name: str,
                         current_price: float, target_price: float,
                         condition: str) -> Dict[str, bool]:
        """가격 알림 전송"""
        direction = "상승" if condition == "above" else "하락"
        message = NotificationMessage(
            title=f"가격 알림: {name}",
            body=f"{name}({symbol})이 목표가에 도달했습니다.\n"
                 f"현재가: {current_price:,.0f}원 ({direction})",
            type="alert",
            symbol=symbol,
            data={
                "목표가": f"{target_price:,.0f}원",
                "현재가": f"{current_price:,.0f}원",
                "조건": direction
            }
        )
        return self.send(message)

    def send_disclosure_alert(self, symbol: str, name: str,
                              title: str, disclosure_type: str) -> Dict[str, bool]:
        """공시 알림 전송"""
        message = NotificationMessage(
            title=f"공시 알림: {name}",
            body=f"{name}({symbol})의 새로운 공시가 등록되었습니다.\n{title}",
            type="alert",
            symbol=symbol,
            data={
                "공시 유형": disclosure_type
            }
        )
        return self.send(message)

    def send_portfolio_alert(self, alert_type: str,
                             details: str, data: Dict = None) -> Dict[str, bool]:
        """포트폴리오 알림 전송"""
        message = NotificationMessage(
            title=f"포트폴리오 알림: {alert_type}",
            body=details,
            type="warning",
            data=data or {}
        )
        return self.send(message)

    def send_daily_report(self, report_summary: str,
                          performance: Dict) -> Dict[str, bool]:
        """일일 리포트 전송"""
        message = NotificationMessage(
            title="일일 포트폴리오 리포트",
            body=report_summary,
            type="info",
            data=performance
        )
        return self.send(message, force=True)

    def get_history(self, limit: int = 50) -> List[Dict]:
        """알림 히스토리 조회"""
        return self.history[-limit:]

    def get_channel_status(self) -> Dict[str, bool]:
        """채널 상태 조회"""
        return {
            channel.__class__.__name__: channel.is_configured()
            for channel in self.channels
        }

    def test_channels(self) -> Dict[str, bool]:
        """채널 테스트"""
        test_msg = NotificationMessage(
            title="테스트 알림",
            body="NOTION 알림 시스템 테스트 메시지입니다.",
            type="info"
        )
        return self.send(test_msg, force=True)


# 싱글톤 인스턴스
notification_manager = NotificationManager()


# 편의 함수
def send_notification(title: str, body: str,
                      msg_type: str = "info", **kwargs) -> Dict[str, bool]:
    """알림 전송"""
    message = NotificationMessage(
        title=title,
        body=body,
        type=msg_type,
        **kwargs
    )
    return notification_manager.send(message)


def send_price_alert(symbol: str, name: str,
                     current_price: float, target_price: float,
                     condition: str = "above") -> Dict[str, bool]:
    """가격 알림"""
    return notification_manager.send_price_alert(
        symbol, name, current_price, target_price, condition
    )
