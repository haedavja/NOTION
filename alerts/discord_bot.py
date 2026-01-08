"""
디스코드 알림 모듈
투자 관련 알림을 디스코드 웹훅으로 전송합니다.
"""

import os
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


@dataclass
class DiscordEmbed:
    """디스코드 Embed"""
    title: str
    description: str
    color: int = 0x5865F2          # 기본 디스코드 블루
    fields: List[Dict] = None
    footer: Optional[str] = None
    url: Optional[str] = None
    thumbnail: Optional[str] = None


class DiscordNotifier:
    """디스코드 알림 클래스"""

    # 카테고리별 색상
    CATEGORY_COLORS = {
        'news': 0x3498db,       # 파랑
        'price_up': 0x2ecc71,   # 초록
        'price_down': 0xe74c3c, # 빨강
        'signal': 0xf39c12,     # 주황
        'portfolio': 0x9b59b6,  # 보라
        'macro': 0x1abc9c,      # 청록
        'alert': 0xe74c3c,      # 빨강
        'general': 0x95a5a6,    # 회색
    }

    def __init__(self, webhook_url: Optional[str] = None):
        """
        초기화

        Args:
            webhook_url: 디스코드 웹훅 URL (없으면 환경변수 DISCORD_WEBHOOK_URL)
        """
        self.webhook_url = webhook_url or os.getenv('DISCORD_WEBHOOK_URL')
        self.enabled = bool(self.webhook_url)

        if not self.enabled:
            print("Warning: 디스코드 웹훅이 설정되지 않았습니다. DISCORD_WEBHOOK_URL을 설정하세요.")

    def send_embed(self, embed: DiscordEmbed, username: str = "투자 알리미") -> bool:
        """
        Embed 메시지 전송

        Args:
            embed: DiscordEmbed 객체
            username: 봇 표시 이름

        Returns:
            성공 여부
        """
        if not self.enabled:
            print(f"[Discord Disabled] {embed.title}: {embed.description}")
            return False

        if not REQUESTS_AVAILABLE:
            raise ImportError("requests 라이브러리가 필요합니다.")

        embed_data = {
            'title': embed.title,
            'description': embed.description,
            'color': embed.color,
            'timestamp': datetime.utcnow().isoformat(),
        }

        if embed.url:
            embed_data['url'] = embed.url

        if embed.fields:
            embed_data['fields'] = embed.fields

        if embed.footer:
            embed_data['footer'] = {'text': embed.footer}

        if embed.thumbnail:
            embed_data['thumbnail'] = {'url': embed.thumbnail}

        payload = {
            'username': username,
            'embeds': [embed_data],
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            return response.status_code == 204
        except Exception as e:
            print(f"디스코드 전송 실패: {e}")
            return False

    def send_text(self, text: str, username: str = "투자 알리미") -> bool:
        """간단한 텍스트 전송"""
        if not self.enabled:
            print(f"[Discord Disabled] {text}")
            return False

        payload = {
            'username': username,
            'content': text,
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            return response.status_code == 204
        except Exception as e:
            print(f"디스코드 전송 실패: {e}")
            return False

    def send_news_alert(self, title: str, summary: str,
                       source: str, url: Optional[str] = None,
                       sentiment: Optional[str] = None) -> bool:
        """뉴스 알림 전송"""
        fields = [
            {'name': '📍 출처', 'value': source, 'inline': True},
        ]

        if sentiment:
            sentiment_emoji = {'positive': '🟢 긍정', 'negative': '🔴 부정', 'neutral': '🟡 중립'}
            fields.append({
                'name': '💭 센티먼트',
                'value': sentiment_emoji.get(sentiment, sentiment),
                'inline': True
            })

        embed = DiscordEmbed(
            title=f"📰 {title}",
            description=summary,
            color=self.CATEGORY_COLORS['news'],
            fields=fields,
            url=url,
        )
        return self.send_embed(embed)

    def send_price_alert(self, symbol: str, current_price: float,
                        alert_type: str, threshold: float,
                        change_pct: Optional[float] = None) -> bool:
        """가격 알림 전송"""
        if alert_type == 'above':
            title = f"📈 {symbol} 상승 돌파!"
            color = self.CATEGORY_COLORS['price_up']
        elif alert_type == 'below':
            title = f"📉 {symbol} 하락 돌파!"
            color = self.CATEGORY_COLORS['price_down']
        else:
            title = f"💥 {symbol} 급변동!"
            color = self.CATEGORY_COLORS['alert']

        fields = [
            {'name': '현재가', 'value': f'${current_price:.2f}', 'inline': True},
            {'name': '기준가', 'value': f'${threshold:.2f}', 'inline': True},
        ]

        if change_pct:
            fields.append({
                'name': '변동률',
                'value': f'{change_pct:+.2f}%',
                'inline': True
            })

        embed = DiscordEmbed(
            title=title,
            description=f"{symbol}이(가) 설정한 가격 조건을 충족했습니다.",
            color=color,
            fields=fields,
        )
        return self.send_embed(embed)

    def send_signal_alert(self, signal_type: str, description: str,
                         assets: List[str] = None,
                         probability: Optional[float] = None,
                         recommendation: Optional[str] = None) -> bool:
        """매매 신호 알림"""
        fields = []

        if assets:
            fields.append({
                'name': '🎯 관련 자산',
                'value': ', '.join(assets),
                'inline': False
            })

        if probability:
            fields.append({
                'name': '📊 확률',
                'value': f'{probability:.1f}%',
                'inline': True
            })

        if recommendation:
            fields.append({
                'name': '💡 추천',
                'value': recommendation,
                'inline': True
            })

        embed = DiscordEmbed(
            title=f"🎯 매매 신호: {signal_type}",
            description=description,
            color=self.CATEGORY_COLORS['signal'],
            fields=fields,
        )
        return self.send_embed(embed)

    def send_portfolio_report(self, portfolio_name: str,
                             total_value: float,
                             daily_change: float,
                             daily_change_pct: float,
                             positions: Optional[List[Dict]] = None) -> bool:
        """포트폴리오 리포트 전송"""
        color = self.CATEGORY_COLORS['price_up'] if daily_change >= 0 else self.CATEGORY_COLORS['price_down']
        change_emoji = '📈' if daily_change >= 0 else '📉'

        fields = [
            {'name': '💰 총 평가금액', 'value': f'${total_value:,.0f}', 'inline': True},
            {'name': f'{change_emoji} 일간 변동', 'value': f'${daily_change:+,.0f} ({daily_change_pct:+.2f}%)', 'inline': True},
        ]

        if positions:
            # 상위 5개 포지션
            position_text = ""
            for pos in positions[:5]:
                symbol = pos.get('symbol', '')
                weight = pos.get('weight', 0)
                pnl_pct = pos.get('pnl_pct', 0)
                emoji = '🟢' if pnl_pct >= 0 else '🔴'
                position_text += f"{emoji} **{symbol}** ({weight:.1f}%): {pnl_pct:+.2f}%\n"

            fields.append({
                'name': '📊 주요 포지션',
                'value': position_text or "없음",
                'inline': False
            })

        embed = DiscordEmbed(
            title=f"💼 포트폴리오 리포트: {portfolio_name}",
            description=f"일일 포트폴리오 현황 ({datetime.now().strftime('%Y-%m-%d')})",
            color=color,
            fields=fields,
        )
        return self.send_embed(embed)

    def send_macro_alert(self, indicator: str, value: float,
                        previous: float, expected: Optional[float] = None,
                        impact: str = "") -> bool:
        """거시경제 지표 알림"""
        change = value - previous
        change_pct = (change / previous * 100) if previous != 0 else 0

        fields = [
            {'name': '📊 발표치', 'value': f'{value:.2f}', 'inline': True},
            {'name': '📈 이전치', 'value': f'{previous:.2f}', 'inline': True},
            {'name': '📉 변화', 'value': f'{change:+.2f} ({change_pct:+.1f}%)', 'inline': True},
        ]

        if expected:
            surprise = value - expected
            fields.append({
                'name': '🎯 예상치',
                'value': f'{expected:.2f} (서프라이즈: {surprise:+.2f})',
                'inline': False
            })

        if impact:
            fields.append({
                'name': '💡 시장 영향',
                'value': impact,
                'inline': False
            })

        embed = DiscordEmbed(
            title=f"🌐 거시경제 지표: {indicator}",
            description="주요 경제 지표가 발표되었습니다.",
            color=self.CATEGORY_COLORS['macro'],
            fields=fields,
        )
        return self.send_embed(embed)

    def send_market_summary(self, indices: Dict[str, Dict],
                           top_gainers: List[Dict] = None,
                           top_losers: List[Dict] = None) -> bool:
        """시장 요약 전송"""
        # 지수 정보
        index_text = ""
        for name, data in indices.items():
            change = data.get('change_pct', 0)
            emoji = '🟢' if change >= 0 else '🔴'
            index_text += f"{emoji} **{name}**: {data.get('price', 0):,.0f} ({change:+.2f}%)\n"

        fields = [
            {'name': '📊 주요 지수', 'value': index_text or "데이터 없음", 'inline': False},
        ]

        if top_gainers:
            gainers_text = "\n".join([
                f"🚀 {g['symbol']}: {g['change_pct']:+.2f}%"
                for g in top_gainers[:3]
            ])
            fields.append({'name': '📈 상승 상위', 'value': gainers_text, 'inline': True})

        if top_losers:
            losers_text = "\n".join([
                f"💥 {l['symbol']}: {l['change_pct']:+.2f}%"
                for l in top_losers[:3]
            ])
            fields.append({'name': '📉 하락 상위', 'value': losers_text, 'inline': True})

        embed = DiscordEmbed(
            title="📈 시장 요약",
            description=f"오늘의 시장 현황 ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
            color=self.CATEGORY_COLORS['general'],
            fields=fields,
        )
        return self.send_embed(embed)

    def test_connection(self) -> bool:
        """연결 테스트"""
        return self.send_text("🔔 디스코드 알림 연결 테스트 성공!")


# 디스코드 웹훅 설정 가이드
DISCORD_SETUP_GUIDE = """
=== 디스코드 웹훅 설정 가이드 ===

1. 디스코드 서버에서 채널 설정
   - 알림 받을 채널 우클릭 → "채널 편집"
   - "연동" 탭 클릭
   - "웹후크" → "새 웹후크" 클릭

2. 웹훅 설정
   - 이름 설정 (예: "투자 알리미")
   - 아바타 설정 (선택)
   - "웹후크 URL 복사" 클릭

3. 환경변수 설정
   DISCORD_WEBHOOK_URL=your_webhook_url

4. 테스트
   from alerts.discord_bot import DiscordNotifier
   notifier = DiscordNotifier()
   notifier.test_connection()
"""

def print_setup_guide():
    """설정 가이드 출력"""
    print(DISCORD_SETUP_GUIDE)
