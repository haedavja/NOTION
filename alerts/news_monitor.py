"""
뉴스 모니터링 모듈
보유 종목 관련 뉴스 수집 및 알림
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import re
import time


@dataclass
class NewsItem:
    """뉴스 항목"""
    title: str
    url: str
    source: str
    published: datetime
    symbol: str = ""
    sentiment: str = "neutral"  # positive, negative, neutral
    keywords: List[str] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []

    def to_dict(self) -> Dict:
        return {
            'title': self.title,
            'url': self.url,
            'source': self.source,
            'published': self.published.isoformat(),
            'symbol': self.symbol,
            'sentiment': self.sentiment,
            'keywords': self.keywords
        }


class NewsMonitor:
    """뉴스 모니터링"""

    # 감성 분석 키워드
    POSITIVE_KEYWORDS = [
        '상승', '급등', '호재', '실적개선', '최고', '돌파', '신고가',
        '성장', '호실적', '매수', '기대', '긍정', '상향', '증가',
        '계약', '수주', '출시', '승인', '합병', '인수'
    ]

    NEGATIVE_KEYWORDS = [
        '하락', '급락', '악재', '실적악화', '최저', '폭락', '신저가',
        '감소', '적자', '매도', '우려', '부정', '하향', '감소',
        '소송', '분쟁', '리콜', '제재', '손실', '파산'
    ]

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self._news_cache: Dict[str, List[NewsItem]] = {}
        self._last_fetch: Dict[str, datetime] = {}
        self.cache_ttl = 300  # 5분 캐시

    def get_naver_news(self, query: str, limit: int = 10) -> List[NewsItem]:
        """네이버 뉴스 검색"""
        try:
            url = f"https://search.naver.com/search.naver?where=news&query={query}&sort=1"
            resp = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')

            news_items = []
            articles = soup.select('.news_wrap.api_ani_send')[:limit]

            for article in articles:
                title_elem = article.select_one('.news_tit')
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                url = title_elem.get('href', '')

                source_elem = article.select_one('.info_group .press')
                source = source_elem.get_text(strip=True) if source_elem else '뉴스'

                # 시간 파싱
                time_elem = article.select_one('.info_group span.info')
                published = self._parse_time(time_elem.get_text() if time_elem else '')

                # 감성 분석
                sentiment = self._analyze_sentiment(title)

                news_items.append(NewsItem(
                    title=title,
                    url=url,
                    source=source,
                    published=published,
                    symbol=query,
                    sentiment=sentiment,
                    keywords=self._extract_keywords(title)
                ))

            return news_items

        except Exception as e:
            print(f"Naver news error: {e}")
            return []

    def get_stock_news(self, symbol: str, name: str = None) -> List[NewsItem]:
        """종목 관련 뉴스 조회"""
        # 캐시 확인
        cache_key = f"{symbol}_{name}"
        if cache_key in self._news_cache:
            if datetime.now() - self._last_fetch.get(cache_key, datetime.min) < timedelta(seconds=self.cache_ttl):
                return self._news_cache[cache_key]

        # 검색어 구성
        queries = [symbol]
        if name:
            queries.append(name)

        all_news = []
        seen_titles = set()

        for query in queries:
            news = self.get_naver_news(query, limit=5)
            for item in news:
                if item.title not in seen_titles:
                    item.symbol = symbol
                    all_news.append(item)
                    seen_titles.add(item.title)
            time.sleep(0.5)  # 레이트 리미팅

        # 최신순 정렬
        all_news.sort(key=lambda x: x.published, reverse=True)

        # 캐시 저장
        self._news_cache[cache_key] = all_news[:10]
        self._last_fetch[cache_key] = datetime.now()

        return all_news[:10]

    def get_portfolio_news(self, symbols: List[Dict]) -> List[NewsItem]:
        """
        포트폴리오 전체 종목 뉴스
        symbols: [{'symbol': 'AAPL', 'name': '애플'}, ...]
        """
        all_news = []

        for stock in symbols[:10]:  # 최대 10종목
            symbol = stock.get('symbol', '')
            name = stock.get('name', '')

            news = self.get_stock_news(symbol, name)
            all_news.extend(news)
            time.sleep(0.3)

        # 최신순 정렬 후 상위 20개
        all_news.sort(key=lambda x: x.published, reverse=True)
        return all_news[:20]

    def get_important_news(self, symbols: List[Dict]) -> List[NewsItem]:
        """중요 뉴스만 필터링 (감성이 positive/negative인 것)"""
        all_news = self.get_portfolio_news(symbols)
        return [n for n in all_news if n.sentiment != 'neutral']

    def _parse_time(self, time_str: str) -> datetime:
        """시간 문자열 파싱"""
        now = datetime.now()

        if '분 전' in time_str:
            minutes = int(re.search(r'(\d+)', time_str).group(1))
            return now - timedelta(minutes=minutes)
        elif '시간 전' in time_str:
            hours = int(re.search(r'(\d+)', time_str).group(1))
            return now - timedelta(hours=hours)
        elif '일 전' in time_str:
            days = int(re.search(r'(\d+)', time_str).group(1))
            return now - timedelta(days=days)
        else:
            return now

    def _analyze_sentiment(self, text: str) -> str:
        """간단한 감성 분석"""
        text = text.lower()

        pos_count = sum(1 for kw in self.POSITIVE_KEYWORDS if kw in text)
        neg_count = sum(1 for kw in self.NEGATIVE_KEYWORDS if kw in text)

        if pos_count > neg_count:
            return 'positive'
        elif neg_count > pos_count:
            return 'negative'
        return 'neutral'

    def _extract_keywords(self, text: str) -> List[str]:
        """키워드 추출"""
        keywords = []

        for kw in self.POSITIVE_KEYWORDS + self.NEGATIVE_KEYWORDS:
            if kw in text:
                keywords.append(kw)

        return keywords[:5]


# 전역 인스턴스
news_monitor = NewsMonitor()
