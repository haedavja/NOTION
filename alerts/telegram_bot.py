"""
텔레그램 알림 모듈
투자 관련 알림을 텔레그램으로 전송합니다.
"""

import os
import logging
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


@dataclass
class TelegramMessage:
    """텔레그램 메시지"""
    title: str
    body: str
    category: str = "general"      # news, price, signal, portfolio
    priority: str = "normal"       # low, normal, high, urgent
    url: Optional[str] = None


class TelegramNotifier:
    """텔레그램 알림 클래스"""

    BASE_URL = "https://api.telegram.org/bot{token}/{method}"

    # 카테고리별 이모지
    CATEGORY_EMOJI = {
        'news': '📰',
        'price': '💹',
        'signal': '🎯',
        'portfolio': '💼',
        'macro': '🌐',
        'alert': '🚨',
        'general': '📌',
    }

    # 우선순위별 표시
    PRIORITY_PREFIX = {
        'low': '',
        'normal': '',
        'high': '⚠️ ',
        'urgent': '🚨🚨 ',
    }

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        초기화

        Args:
            bot_token: 텔레그램 봇 토큰 (없으면 환경변수 TELEGRAM_BOT_TOKEN)
            chat_id: 채팅 ID (없으면 환경변수 TELEGRAM_CHAT_ID)
        """
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        self.enabled = bool(self.bot_token and self.chat_id)

        if not self.enabled:
            logger.warning("텔레그램 설정이 없습니다. TELEGRAM_BOT_TOKEN과 TELEGRAM_CHAT_ID를 설정하세요.")

    def _call_api(self, method: str, params: Dict) -> Dict:
        """텔레그램 API 호출"""
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests 라이브러리가 필요합니다.")

        url = self.BASE_URL.format(token=self.bot_token, method=method)
        response = requests.post(url, json=params, timeout=10)

        return response.json()

    def send_message(self, message: TelegramMessage) -> bool:
        """
        메시지 전송

        Args:
            message: TelegramMessage 객체

        Returns:
            성공 여부
        """
        if not self.enabled:
            logger.debug(f"[Telegram Disabled] {message.title}: {message.body}")
            return False

        emoji = self.CATEGORY_EMOJI.get(message.category, '📌')
        prefix = self.PRIORITY_PREFIX.get(message.priority, '')

        # 메시지 포맷팅
        text = f"{prefix}{emoji} *{message.title}*\n\n{message.body}"

        if message.url:
            text += f"\n\n🔗 [자세히 보기]({message.url})"

        text += f"\n\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

        params = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True,
        }

        try:
            result = self._call_api('sendMessage', params)
            return result.get('ok', False)
        except Exception as e:
            logger.error(f"텔레그램 전송 실패: {e}")
            return False

    def send_text(self, text: str, category: str = "general") -> bool:
        """간단한 텍스트 전송"""
        message = TelegramMessage(
            title="알림",
            body=text,
            category=category,
        )
        return self.send_message(message)

    def send_news_alert(self, title: str, summary: str,
                       source: str, url: Optional[str] = None,
                       sentiment: Optional[str] = None) -> bool:
        """뉴스 알림 전송"""
        body = f"{summary}\n\n📍 출처: {source}"
        if sentiment:
            sentiment_emoji = {'positive': '🟢', 'negative': '🔴', 'neutral': '🟡'}
            body += f"\n💭 센티먼트: {sentiment_emoji.get(sentiment, '⚪')} {sentiment}"

        message = TelegramMessage(
            title=title,
            body=body,
            category='news',
            url=url,
        )
        return self.send_message(message)

    def send_price_alert(self, symbol: str, current_price: float,
                        alert_type: str, threshold: float,
                        change_pct: Optional[float] = None) -> bool:
        """가격 알림 전송"""
        alert_messages = {
            'above': f"📈 {symbol}이(가) ${threshold:.2f} 돌파!",
            'below': f"📉 {symbol}이(가) ${threshold:.2f} 하회!",
            'change': f"💥 {symbol} {change_pct:+.1f}% 급변동!",
        }

        title = alert_messages.get(alert_type, f"{symbol} 가격 알림")
        body = f"현재가: ${current_price:.2f}"

        if change_pct:
            body += f"\n변동률: {change_pct:+.2f}%"

        message = TelegramMessage(
            title=title,
            body=body,
            category='price',
            priority='high' if abs(change_pct or 0) > 5 else 'normal',
        )
        return self.send_message(message)

    def send_signal_alert(self, signal_type: str, description: str,
                         probability: Optional[float] = None,
                         recommendation: Optional[str] = None) -> bool:
        """매매 신호 알림"""
        body = description

        if probability:
            body += f"\n\n확률: {probability:.1f}%"
        if recommendation:
            body += f"\n추천: {recommendation}"

        message = TelegramMessage(
            title=f"매매 신호: {signal_type}",
            body=body,
            category='signal',
            priority='high',
        )
        return self.send_message(message)

    def send_portfolio_update(self, portfolio_name: str,
                             total_value: float,
                             daily_change: float,
                             daily_change_pct: float,
                             top_movers: Optional[List[Dict]] = None) -> bool:
        """포트폴리오 업데이트 알림"""
        change_emoji = '📈' if daily_change >= 0 else '📉'

        body = f"총 평가금액: ${total_value:,.0f}\n"
        body += f"일간 변동: {change_emoji} ${daily_change:+,.0f} ({daily_change_pct:+.2f}%)"

        if top_movers:
            body += "\n\n📊 주요 변동:"
            for mover in top_movers[:3]:
                symbol = mover.get('symbol', '')
                change = mover.get('change_pct', 0)
                emoji = '🟢' if change >= 0 else '🔴'
                body += f"\n  {emoji} {symbol}: {change:+.2f}%"

        message = TelegramMessage(
            title=f"포트폴리오 리포트: {portfolio_name}",
            body=body,
            category='portfolio',
        )
        return self.send_message(message)

    def send_macro_alert(self, indicator: str, value: float,
                        previous: float, impact: str) -> bool:
        """거시경제 지표 알림"""
        change = value - previous
        change_emoji = '📈' if change >= 0 else '📉'

        body = f"현재: {value:.2f} (이전: {previous:.2f})\n"
        body += f"변화: {change_emoji} {change:+.2f}\n\n"
        body += f"시장 영향: {impact}"

        message = TelegramMessage(
            title=f"거시경제 지표: {indicator}",
            body=body,
            category='macro',
            priority='high',
        )
        return self.send_message(message)

    def test_connection(self) -> bool:
        """연결 테스트"""
        if not self.enabled:
            return False

        try:
            result = self._call_api('getMe', {})
            if result.get('ok'):
                bot_name = result['result']['username']
                logger.info(f"텔레그램 봇 연결 성공: @{bot_name}")
                return True
        except Exception as e:
            logger.error(f"텔레그램 연결 실패: {e}")

        return False


# 텔레그램 봇 생성 가이드
TELEGRAM_SETUP_GUIDE = """
=== 텔레그램 봇 설정 가이드 ===

1. @BotFather에게 메시지 전송
   - 텔레그램에서 @BotFather 검색
   - /newbot 명령어 입력
   - 봇 이름과 username 설정
   - 발급받은 토큰 저장

2. Chat ID 확인
   - 생성한 봇에게 아무 메시지 전송
   - 브라우저에서 접속:
     https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   - "chat":{"id": 숫자} 에서 숫자가 Chat ID

3. 환경변수 설정
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id

4. 테스트
   from alerts.telegram_bot import TelegramNotifier
   notifier = TelegramNotifier()
   notifier.test_connection()
   notifier.send_text("테스트 메시지입니다!")
"""

def print_setup_guide():
    """설정 가이드 출력"""
    print(TELEGRAM_SETUP_GUIDE)
