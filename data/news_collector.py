"""
뉴스 수집 모듈
경제/금융 뉴스를 수집하고 처리합니다.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
import re

try:
    from newsapi import NewsApiClient
    NEWSAPI_AVAILABLE = True
except ImportError:
    NEWSAPI_AVAILABLE = False

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False

try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


class NewsCollector:
    """뉴스 수집 클래스"""

    # 경제/금융 관련 RSS 피드
    RSS_FEEDS = {
        'reuters_business': 'https://feeds.reuters.com/reuters/businessNews',
        'reuters_markets': 'https://feeds.reuters.com/reuters/marketsNews',
        'wsj_markets': 'https://feeds.wsj.com/wsj/xml/rss/3_7031.xml',
        'bloomberg': 'https://feeds.bloomberg.com/markets/news.rss',
        'cnbc': 'https://www.cnbc.com/id/10000664/device/rss/rss.html',
        'ft_markets': 'https://www.ft.com/markets?format=rss',
        'economist': 'https://www.economist.com/finance-and-economics/rss.xml',
    }

    # 경제 키워드
    ECONOMIC_KEYWORDS = {
        'monetary_policy': ['fed', 'federal reserve', 'interest rate', 'rate hike',
                           'rate cut', 'fomc', 'powell', 'monetary policy', 'quantitative'],
        'inflation': ['inflation', 'cpi', 'pce', 'prices', 'deflation', 'stagflation'],
        'employment': ['jobs', 'employment', 'unemployment', 'payroll', 'labor market',
                      'hiring', 'layoffs', 'jobless'],
        'growth': ['gdp', 'economic growth', 'recession', 'expansion', 'slowdown'],
        'markets': ['stocks', 'bonds', 'treasury', 'yield', 'equity', 'bull', 'bear',
                   'rally', 'selloff', 'correction'],
        'geopolitical': ['trade war', 'tariff', 'sanctions', 'geopolitical', 'conflict'],
        'sectors': ['tech', 'energy', 'financials', 'healthcare', 'real estate'],
    }

    def __init__(self, newsapi_key: Optional[str] = None):
        """
        초기화

        Args:
            newsapi_key: NewsAPI 키 (없으면 환경변수 NEWS_API_KEY 사용)
        """
        self.newsapi_key = newsapi_key or os.getenv('NEWS_API_KEY')
        self.newsapi = None

        if NEWSAPI_AVAILABLE and self.newsapi_key:
            self.newsapi = NewsApiClient(api_key=self.newsapi_key)

    def get_news_from_api(self, query: str = 'economy OR stock market',
                         from_date: Optional[str] = None,
                         language: str = 'en',
                         sort_by: str = 'relevancy',
                         page_size: int = 100) -> List[Dict]:
        """
        NewsAPI를 통한 뉴스 수집

        Args:
            query: 검색 쿼리
            from_date: 시작일 (YYYY-MM-DD)
            language: 언어
            sort_by: 정렬 기준 (relevancy, popularity, publishedAt)
            page_size: 결과 수

        Returns:
            뉴스 기사 리스트
        """
        if not self.newsapi:
            raise ValueError("NewsAPI가 설정되지 않았습니다.")

        if not from_date:
            from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

        response = self.newsapi.get_everything(
            q=query,
            from_param=from_date,
            language=language,
            sort_by=sort_by,
            page_size=page_size
        )

        articles = []
        for article in response.get('articles', []):
            articles.append({
                'title': article.get('title'),
                'description': article.get('description'),
                'content': article.get('content'),
                'source': article.get('source', {}).get('name'),
                'url': article.get('url'),
                'published_at': article.get('publishedAt'),
                'author': article.get('author'),
            })

        return articles

    def get_news_from_rss(self, feed_name: Optional[str] = None,
                         feed_url: Optional[str] = None) -> List[Dict]:
        """
        RSS 피드에서 뉴스 수집

        Args:
            feed_name: 사전 정의된 피드 이름
            feed_url: 직접 지정 URL

        Returns:
            뉴스 기사 리스트
        """
        if not FEEDPARSER_AVAILABLE:
            raise ImportError("feedparser가 필요합니다.")

        if feed_name and feed_name in self.RSS_FEEDS:
            url = self.RSS_FEEDS[feed_name]
        elif feed_url:
            url = feed_url
        else:
            raise ValueError("feed_name 또는 feed_url을 지정해주세요.")

        feed = feedparser.parse(url)

        articles = []
        for entry in feed.entries:
            articles.append({
                'title': entry.get('title'),
                'description': entry.get('summary', entry.get('description')),
                'url': entry.get('link'),
                'published_at': entry.get('published', entry.get('updated')),
                'source': feed.feed.get('title', feed_name),
            })

        return articles

    def get_all_rss_news(self) -> List[Dict]:
        """
        모든 RSS 피드에서 뉴스 수집

        Returns:
            모든 피드의 뉴스 기사 리스트
        """
        all_articles = []

        for feed_name in self.RSS_FEEDS.keys():
            try:
                articles = self.get_news_from_rss(feed_name=feed_name)
                all_articles.extend(articles)
            except Exception as e:
                print(f"Warning: {feed_name} 수집 실패 - {e}")

        return all_articles

    def categorize_news(self, articles: List[Dict]) -> Dict[str, List[Dict]]:
        """
        뉴스를 카테고리별로 분류

        Args:
            articles: 뉴스 기사 리스트

        Returns:
            카테고리별 기사 딕셔너리
        """
        categorized = {category: [] for category in self.ECONOMIC_KEYWORDS.keys()}
        categorized['other'] = []

        for article in articles:
            text = f"{article.get('title', '')} {article.get('description', '')}".lower()

            matched_categories = []
            for category, keywords in self.ECONOMIC_KEYWORDS.items():
                if any(keyword in text for keyword in keywords):
                    matched_categories.append(category)

            if matched_categories:
                for category in matched_categories:
                    categorized[category].append(article)
            else:
                categorized['other'].append(article)

        return categorized

    def get_keyword_frequency(self, articles: List[Dict]) -> Dict[str, int]:
        """
        키워드 빈도 분석

        Args:
            articles: 뉴스 기사 리스트

        Returns:
            키워드별 빈도
        """
        all_text = ' '.join([
            f"{a.get('title', '')} {a.get('description', '')}"
            for a in articles
        ]).lower()

        frequency = {}
        for category, keywords in self.ECONOMIC_KEYWORDS.items():
            for keyword in keywords:
                count = len(re.findall(r'\b' + re.escape(keyword) + r'\b', all_text))
                if count > 0:
                    frequency[keyword] = count

        # 빈도순 정렬
        frequency = dict(sorted(frequency.items(), key=lambda x: x[1], reverse=True))

        return frequency

    def get_news_summary(self, days: int = 7) -> Dict:
        """
        뉴스 요약 정보 생성

        Args:
            days: 수집 기간 (일)

        Returns:
            뉴스 요약 정보
        """
        # RSS에서 뉴스 수집
        articles = self.get_all_rss_news()

        # API가 있으면 추가 수집
        if self.newsapi:
            try:
                api_articles = self.get_news_from_api()
                articles.extend(api_articles)
            except Exception:
                pass

        # 중복 제거 (제목 기준)
        seen_titles = set()
        unique_articles = []
        for article in articles:
            title = article.get('title', '')
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_articles.append(article)

        # 카테고리별 분류
        categorized = self.categorize_news(unique_articles)

        # 키워드 빈도
        keyword_freq = self.get_keyword_frequency(unique_articles)

        # 카테고리별 기사 수
        category_counts = {
            category: len(articles)
            for category, articles in categorized.items()
        }

        return {
            'total_articles': len(unique_articles),
            'category_counts': category_counts,
            'top_keywords': dict(list(keyword_freq.items())[:20]),
            'categorized_articles': categorized,
        }

    def to_dataframe(self, articles: List[Dict]) -> pd.DataFrame:
        """
        뉴스 리스트를 데이터프레임으로 변환

        Returns:
            뉴스 데이터프레임
        """
        df = pd.DataFrame(articles)

        if 'published_at' in df.columns:
            df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce')
            df = df.sort_values('published_at', ascending=False)

        return df


# 샘플 뉴스 데이터 생성
def get_sample_news() -> List[Dict]:
    """테스트용 샘플 뉴스 데이터"""
    sample_news = [
        {
            'title': 'Federal Reserve signals potential rate cuts in 2024',
            'description': 'Fed Chair Powell hints at possible monetary policy easing as inflation shows signs of cooling.',
            'source': 'Reuters',
            'published_at': '2024-12-15T10:30:00Z',
            'category': 'monetary_policy',
        },
        {
            'title': 'US unemployment rate holds steady at 3.7%',
            'description': 'Labor market remains resilient despite economic uncertainty, with nonfarm payrolls exceeding expectations.',
            'source': 'Bloomberg',
            'published_at': '2024-12-14T08:00:00Z',
            'category': 'employment',
        },
        {
            'title': 'Tech stocks rally on AI optimism',
            'description': 'Nasdaq reaches new highs as investors bet on artificial intelligence driving future growth.',
            'source': 'CNBC',
            'published_at': '2024-12-13T15:45:00Z',
            'category': 'markets',
        },
        {
            'title': 'CPI data shows inflation cooling to 3.1%',
            'description': 'Consumer prices rise less than expected, boosting hopes for soft landing.',
            'source': 'WSJ',
            'published_at': '2024-12-12T09:00:00Z',
            'category': 'inflation',
        },
        {
            'title': 'Treasury yields fall as investors seek safety',
            'description': '10-year Treasury yield drops to 4.1% amid global uncertainty.',
            'source': 'Financial Times',
            'published_at': '2024-12-11T14:20:00Z',
            'category': 'markets',
        },
        {
            'title': 'China economic data raises slowdown concerns',
            'description': 'Manufacturing PMI contracts for third consecutive month.',
            'source': 'Reuters',
            'published_at': '2024-12-10T06:00:00Z',
            'category': 'growth',
        },
        {
            'title': 'Oil prices surge on OPEC+ production cuts',
            'description': 'Crude oil jumps 5% as Saudi Arabia extends voluntary output reduction.',
            'source': 'Bloomberg',
            'published_at': '2024-12-09T11:30:00Z',
            'category': 'sectors',
        },
        {
            'title': 'Real estate sector faces headwinds from high rates',
            'description': 'Commercial property values decline as borrowing costs remain elevated.',
            'source': 'CNBC',
            'published_at': '2024-12-08T13:00:00Z',
            'category': 'sectors',
        },
    ]

    return sample_news
