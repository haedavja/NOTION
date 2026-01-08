"""
뉴스 알림 시스템
실시간 경제 뉴스를 모니터링하고 알림을 전송합니다.
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
import hashlib
import json
import os

try:
    import schedule
    SCHEDULE_AVAILABLE = True
except ImportError:
    SCHEDULE_AVAILABLE = False

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.news_collector import NewsCollector
from analysis.sentiment import SentimentAnalyzer
from .telegram_bot import TelegramNotifier
from .discord_bot import DiscordNotifier


@dataclass
class NewsFilter:
    """뉴스 필터 설정"""
    keywords: List[str] = field(default_factory=list)           # 포함 키워드
    exclude_keywords: List[str] = field(default_factory=list)   # 제외 키워드
    sources: List[str] = field(default_factory=list)            # 특정 소스만
    sentiment_filter: Optional[str] = None                       # positive/negative/neutral
    min_relevance: float = 0.5                                   # 최소 관련도


@dataclass
class AlertRule:
    """알림 규칙"""
    name: str
    filter: NewsFilter
    channels: List[str] = field(default_factory=lambda: ['telegram', 'discord'])
    cooldown_minutes: int = 30   # 같은 규칙 알림 간격
    enabled: bool = True


class NewsAlertSystem:
    """뉴스 알림 시스템"""

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

        self.news_collector = NewsCollector()
        self.sentiment_analyzer = SentimentAnalyzer(use_ml=False)

        self.rules: List[AlertRule] = []
        self.seen_news: Dict[str, datetime] = {}  # 중복 방지
        self.last_alert_time: Dict[str, datetime] = {}  # 쿨다운 관리

        self.is_running = False
        self._thread: Optional[threading.Thread] = None

        # 기본 규칙 추가
        self._add_default_rules()

    def _add_default_rules(self):
        """기본 알림 규칙 추가"""
        # 금리 관련 뉴스
        self.add_rule(AlertRule(
            name="금리 뉴스",
            filter=NewsFilter(
                keywords=['fed', 'federal reserve', 'interest rate', 'rate hike',
                         'rate cut', 'fomc', 'powell', '금리', '연준'],
            ),
            cooldown_minutes=60,
        ))

        # 급락 관련 뉴스
        self.add_rule(AlertRule(
            name="시장 급변",
            filter=NewsFilter(
                keywords=['crash', 'plunge', 'selloff', 'rout', 'collapse',
                         '폭락', '급락', '패닉'],
            ),
            cooldown_minutes=15,
        ))

        # 긍정적 뉴스
        self.add_rule(AlertRule(
            name="호재 뉴스",
            filter=NewsFilter(
                keywords=['rally', 'surge', 'record high', 'all-time high',
                         '급등', '신고가', '랠리'],
                sentiment_filter='positive',
            ),
            cooldown_minutes=60,
        ))

    def add_rule(self, rule: AlertRule):
        """알림 규칙 추가"""
        self.rules.append(rule)

    def remove_rule(self, name: str):
        """알림 규칙 제거"""
        self.rules = [r for r in self.rules if r.name != name]

    def _get_news_hash(self, news: Dict) -> str:
        """뉴스 고유 해시 생성"""
        content = f"{news.get('title', '')}{news.get('url', '')}"
        return hashlib.md5(content.encode()).hexdigest()

    def _is_duplicate(self, news: Dict, hours: int = 24) -> bool:
        """중복 뉴스 확인"""
        news_hash = self._get_news_hash(news)
        if news_hash in self.seen_news:
            last_seen = self.seen_news[news_hash]
            if datetime.now() - last_seen < timedelta(hours=hours):
                return True
        return False

    def _mark_seen(self, news: Dict):
        """뉴스를 본 것으로 표시"""
        news_hash = self._get_news_hash(news)
        self.seen_news[news_hash] = datetime.now()

        # 오래된 기록 정리 (24시간 이상)
        cutoff = datetime.now() - timedelta(hours=24)
        self.seen_news = {
            k: v for k, v in self.seen_news.items()
            if v > cutoff
        }

    def _check_cooldown(self, rule_name: str, cooldown_minutes: int) -> bool:
        """쿨다운 확인"""
        if rule_name not in self.last_alert_time:
            return True

        last_time = self.last_alert_time[rule_name]
        return datetime.now() - last_time > timedelta(minutes=cooldown_minutes)

    def _update_cooldown(self, rule_name: str):
        """쿨다운 업데이트"""
        self.last_alert_time[rule_name] = datetime.now()

    def _matches_filter(self, news: Dict, filter: NewsFilter) -> Tuple[bool, float]:
        """뉴스가 필터 조건과 일치하는지 확인"""
        text = f"{news.get('title', '')} {news.get('description', '')}".lower()

        # 키워드 필터
        if filter.keywords:
            keyword_matches = sum(1 for kw in filter.keywords if kw.lower() in text)
            if keyword_matches == 0:
                return False, 0

            relevance = keyword_matches / len(filter.keywords)
        else:
            relevance = 0.5

        # 제외 키워드
        if filter.exclude_keywords:
            for kw in filter.exclude_keywords:
                if kw.lower() in text:
                    return False, 0

        # 소스 필터
        if filter.sources:
            source = news.get('source', '').lower()
            if not any(s.lower() in source for s in filter.sources):
                return False, 0

        # 센티먼트 필터
        if filter.sentiment_filter:
            result = self.sentiment_analyzer.analyze_text(text)
            if result.sentiment != filter.sentiment_filter:
                return False, 0

        # 최소 관련도
        if relevance < filter.min_relevance:
            return False, relevance

        return True, relevance

    def _send_alert(self, news: Dict, rule: AlertRule, relevance: float):
        """알림 전송"""
        title = news.get('title', 'No Title')
        description = news.get('description', '')
        source = news.get('source', 'Unknown')
        url = news.get('url')

        # 센티먼트 분석
        text = f"{title} {description}"
        sentiment_result = self.sentiment_analyzer.analyze_text(text)
        sentiment = sentiment_result.sentiment

        # 텔레그램
        if 'telegram' in rule.channels and self.telegram.enabled:
            self.telegram.send_news_alert(
                title=f"[{rule.name}] {title}",
                summary=description[:300] if description else "내용 없음",
                source=source,
                url=url,
                sentiment=sentiment,
            )

        # 디스코드
        if 'discord' in rule.channels and self.discord.enabled:
            self.discord.send_news_alert(
                title=f"[{rule.name}] {title}",
                summary=description[:500] if description else "내용 없음",
                source=source,
                url=url,
                sentiment=sentiment,
            )

        print(f"[Alert] {rule.name}: {title[:50]}...")

    def check_news(self):
        """뉴스 확인 및 알림"""
        try:
            # 뉴스 수집
            news_list = self.news_collector.get_all_rss_news()

            for news in news_list:
                # 중복 확인
                if self._is_duplicate(news):
                    continue

                # 각 규칙 확인
                for rule in self.rules:
                    if not rule.enabled:
                        continue

                    # 쿨다운 확인
                    if not self._check_cooldown(rule.name, rule.cooldown_minutes):
                        continue

                    # 필터 매칭
                    matches, relevance = self._matches_filter(news, rule.filter)

                    if matches:
                        self._send_alert(news, rule, relevance)
                        self._update_cooldown(rule.name)
                        self._mark_seen(news)
                        break  # 하나의 규칙에만 매칭

        except Exception as e:
            print(f"뉴스 확인 중 오류: {e}")

    def start(self, interval_minutes: int = 5):
        """알림 시스템 시작"""
        if not SCHEDULE_AVAILABLE:
            print("schedule 라이브러리가 필요합니다. pip install schedule")
            return

        if self.is_running:
            print("이미 실행 중입니다.")
            return

        self.is_running = True

        # 스케줄 설정
        schedule.every(interval_minutes).minutes.do(self.check_news)

        # 즉시 1회 실행
        self.check_news()

        # 백그라운드 스레드에서 실행
        def run_schedule():
            while self.is_running:
                schedule.run_pending()
                time.sleep(1)

        self._thread = threading.Thread(target=run_schedule, daemon=True)
        self._thread.start()

        print(f"뉴스 알림 시스템 시작됨 (간격: {interval_minutes}분)")

    def stop(self):
        """알림 시스템 중지"""
        self.is_running = False
        schedule.clear()

        if self._thread:
            self._thread.join(timeout=5)

        print("뉴스 알림 시스템 중지됨")

    def get_status(self) -> Dict:
        """상태 조회"""
        return {
            'is_running': self.is_running,
            'rules_count': len(self.rules),
            'rules': [
                {
                    'name': r.name,
                    'enabled': r.enabled,
                    'keywords': r.filter.keywords[:3],
                    'channels': r.channels,
                }
                for r in self.rules
            ],
            'seen_news_count': len(self.seen_news),
            'telegram_enabled': self.telegram.enabled,
            'discord_enabled': self.discord.enabled,
        }


# 사용 가능한 타입 힌트를 위한 임포트
from typing import Tuple
