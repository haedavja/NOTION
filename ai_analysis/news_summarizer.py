"""
AI 뉴스 요약기
GPT를 활용한 뉴스 분석 및 요약
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from .gpt_analyzer import GPTAnalyzer

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


@dataclass
class NewsSummary:
    """뉴스 요약 결과"""
    timestamp: datetime
    headlines: List[str]
    summary: str
    sentiment: str  # bullish, bearish, neutral
    key_topics: List[str]
    market_impact: str
    source_count: int


class AINewsSummarizer:
    """AI 뉴스 요약기"""

    def __init__(self, api_key: Optional[str] = None,
                 news_api_key: Optional[str] = None):
        """
        초기화

        Args:
            api_key: OpenAI API 키
            news_api_key: NewsAPI 키 (선택)
        """
        self.gpt = GPTAnalyzer(api_key=api_key)
        self.news_api_key = news_api_key or os.getenv('NEWS_API_KEY')

        # RSS 피드 소스
        self.rss_feeds = {
            'Reuters Business': 'https://feeds.reuters.com/reuters/businessNews',
            'Bloomberg Markets': 'https://feeds.bloomberg.com/markets/news.rss',
            'CNBC': 'https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147',
            'MarketWatch': 'https://feeds.marketwatch.com/marketwatch/topstories/',
            'Yahoo Finance': 'https://finance.yahoo.com/news/rssindex',
        }

    def _fetch_rss_news(self, max_items: int = 50) -> List[Dict]:
        """RSS 피드에서 뉴스 수집"""
        if not FEEDPARSER_AVAILABLE:
            return self._get_sample_news()

        all_news = []

        for source, url in self.rss_feeds.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:10]:  # 소스당 최대 10개
                    all_news.append({
                        'title': entry.get('title', ''),
                        'summary': entry.get('summary', '')[:500],
                        'source': source,
                        'link': entry.get('link', ''),
                        'published': entry.get('published', ''),
                    })
            except Exception as e:
                print(f"RSS 피드 오류 ({source}): {e}")

        # 최신순 정렬 (대략적)
        return all_news[:max_items]

    def _fetch_newsapi(self, query: str = 'stock market',
                       max_items: int = 20) -> List[Dict]:
        """NewsAPI에서 뉴스 수집"""
        if not REQUESTS_AVAILABLE or not self.news_api_key:
            return []

        try:
            url = 'https://newsapi.org/v2/everything'
            params = {
                'q': query,
                'language': 'en',
                'sortBy': 'publishedAt',
                'pageSize': max_items,
                'apiKey': self.news_api_key,
            }

            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data.get('status') != 'ok':
                return []

            return [
                {
                    'title': article.get('title', ''),
                    'summary': article.get('description', '')[:500],
                    'source': article.get('source', {}).get('name', 'Unknown'),
                    'link': article.get('url', ''),
                    'published': article.get('publishedAt', ''),
                }
                for article in data.get('articles', [])
            ]

        except Exception as e:
            print(f"NewsAPI 오류: {e}")
            return []

    def _get_sample_news(self) -> List[Dict]:
        """샘플 뉴스 데이터"""
        return [
            {
                'title': 'Fed Officials Signal Potential Rate Cuts Later This Year',
                'summary': 'Several Federal Reserve officials indicated that interest rate cuts could come in the second half of the year if inflation continues to cool.',
                'source': 'Reuters',
                'link': '#',
                'published': datetime.now().isoformat(),
            },
            {
                'title': 'Tech Stocks Rally on Strong Earnings Reports',
                'summary': 'Major technology companies reported better-than-expected quarterly results, pushing the NASDAQ to new highs.',
                'source': 'CNBC',
                'link': '#',
                'published': datetime.now().isoformat(),
            },
            {
                'title': 'Oil Prices Drop on Demand Concerns',
                'summary': 'Crude oil prices fell 3% as economic data from China raised concerns about global demand.',
                'source': 'Bloomberg',
                'link': '#',
                'published': datetime.now().isoformat(),
            },
            {
                'title': 'Retail Sales Beat Expectations in March',
                'summary': 'US retail sales rose 0.7% in March, exceeding economists expectations and suggesting resilient consumer spending.',
                'source': 'MarketWatch',
                'link': '#',
                'published': datetime.now().isoformat(),
            },
            {
                'title': 'Bank Earnings Mixed as Loan Growth Slows',
                'summary': 'Major banks reported mixed quarterly results with concerns about slowing loan growth and potential credit losses.',
                'source': 'Yahoo Finance',
                'link': '#',
                'published': datetime.now().isoformat(),
            },
        ]

    def collect_news(self, query: Optional[str] = None) -> List[Dict]:
        """
        뉴스 수집

        Args:
            query: 검색어 (NewsAPI용)

        Returns:
            뉴스 목록
        """
        news = []

        # RSS 피드
        news.extend(self._fetch_rss_news())

        # NewsAPI (query가 있는 경우)
        if query and self.news_api_key:
            news.extend(self._fetch_newsapi(query))

        return news

    def summarize(self, news_items: Optional[List[Dict]] = None,
                  topic: Optional[str] = None) -> NewsSummary:
        """
        뉴스 요약

        Args:
            news_items: 뉴스 목록 (없으면 자동 수집)
            topic: 특정 주제 필터

        Returns:
            뉴스 요약 결과
        """
        if news_items is None:
            news_items = self.collect_news(query=topic)

        if not news_items:
            return NewsSummary(
                timestamp=datetime.now(),
                headlines=[],
                summary="수집된 뉴스가 없습니다.",
                sentiment="neutral",
                key_topics=[],
                market_impact="영향 없음",
                source_count=0,
            )

        # GPT 분석
        raw_analysis = self.gpt.analyze_news(news_items)

        if raw_analysis is None:
            return self._rule_based_summary(news_items)

        # 결과 파싱
        return NewsSummary(
            timestamp=datetime.now(),
            headlines=[n['title'] for n in news_items[:5]],
            summary=raw_analysis,
            sentiment=self._extract_sentiment(raw_analysis),
            key_topics=self._extract_topics(raw_analysis),
            market_impact=self._extract_impact(raw_analysis),
            source_count=len(set(n['source'] for n in news_items)),
        )

    def _extract_sentiment(self, text: str) -> str:
        """감정 추출"""
        text_lower = text.lower()
        if any(word in text_lower for word in ['긍정', 'bullish', '상승', '호재']):
            return 'bullish'
        elif any(word in text_lower for word in ['부정', 'bearish', '하락', '악재']):
            return 'bearish'
        return 'neutral'

    def _extract_topics(self, text: str) -> List[str]:
        """주요 토픽 추출"""
        topics = []
        keywords = ['금리', '인플레이션', '실적', '고용', 'Fed', '연준',
                   '기술주', '에너지', '중국', '유가', '달러']
        for kw in keywords:
            if kw in text:
                topics.append(kw)
        return topics[:5]

    def _extract_impact(self, text: str) -> str:
        """시장 영향 추출"""
        if '큰 영향' in text or '주목' in text:
            return "높음"
        elif '제한적' in text or '미미' in text:
            return "낮음"
        return "보통"

    def _rule_based_summary(self, news_items: List[Dict]) -> NewsSummary:
        """규칙 기반 요약"""
        headlines = [n['title'] for n in news_items[:5]]

        # 간단한 키워드 기반 감정 분석
        positive_words = ['rally', 'surge', 'gain', 'rise', 'beat', 'strong', 'growth']
        negative_words = ['fall', 'drop', 'decline', 'fear', 'concern', 'weak', 'loss']

        positive_count = sum(
            1 for n in news_items
            if any(w in n['title'].lower() for w in positive_words)
        )
        negative_count = sum(
            1 for n in news_items
            if any(w in n['title'].lower() for w in negative_words)
        )

        if positive_count > negative_count * 1.5:
            sentiment = 'bullish'
        elif negative_count > positive_count * 1.5:
            sentiment = 'bearish'
        else:
            sentiment = 'neutral'

        summary = f"총 {len(news_items)}개의 뉴스를 분석했습니다. "
        summary += f"긍정 {positive_count}개, 부정 {negative_count}개의 헤드라인이 발견되었습니다."

        return NewsSummary(
            timestamp=datetime.now(),
            headlines=headlines,
            summary=summary,
            sentiment=sentiment,
            key_topics=['주식시장', '경제'],
            market_impact="보통",
            source_count=len(set(n['source'] for n in news_items)),
        )

    def get_topic_news(self, topic: str) -> NewsSummary:
        """
        특정 주제 뉴스 요약

        Args:
            topic: 주제 (예: 'AAPL', 'Fed', 'inflation')

        Returns:
            뉴스 요약
        """
        news_items = self._fetch_newsapi(query=topic) if self.news_api_key else []

        if not news_items:
            # RSS에서 필터링
            all_news = self._fetch_rss_news()
            news_items = [
                n for n in all_news
                if topic.lower() in n['title'].lower() or
                   topic.lower() in n['summary'].lower()
            ]

        return self.summarize(news_items, topic=topic)

    def get_daily_digest(self) -> str:
        """일일 뉴스 다이제스트"""
        summary = self.summarize()

        sentiment_emoji = {
            'bullish': '🟢',
            'bearish': '🔴',
            'neutral': '⚪',
        }

        digest = f"""
📰 일일 뉴스 다이제스트
{'-'*40}
🕐 {summary.timestamp.strftime('%Y-%m-%d %H:%M')}
📊 분석 소스: {summary.source_count}개

{sentiment_emoji.get(summary.sentiment, '⚪')} 시장 심리: {summary.sentiment.upper()}

📌 주요 헤드라인:
{chr(10).join('• ' + h for h in summary.headlines[:5])}

🔑 핵심 주제: {', '.join(summary.key_topics) if summary.key_topics else '없음'}

💡 시장 영향: {summary.market_impact}

📝 요약:
{summary.summary[:1000]}
"""
        return digest

    def analyze_sentiment_trend(self, days: int = 7) -> Dict:
        """
        감정 추세 분석 (캐시된 데이터 필요)

        Args:
            days: 분석 기간

        Returns:
            감정 추세
        """
        # 실제 구현시 DB에서 과거 데이터 로드
        return {
            'period': f'{days} days',
            'trend': 'improving',  # improving, worsening, stable
            'current_sentiment': 'neutral',
            'note': '과거 데이터 저장이 필요합니다.',
        }

    def get_status(self) -> Dict:
        """상태 확인"""
        return {
            'gpt_enabled': self.gpt.enabled,
            'newsapi_enabled': bool(self.news_api_key),
            'feedparser_available': FEEDPARSER_AVAILABLE,
            'requests_available': REQUESTS_AVAILABLE,
            'rss_sources': len(self.rss_feeds),
        }


# 사용 예시
def example_usage():
    """사용 예시"""
    summarizer = AINewsSummarizer()

    # 일일 다이제스트
    print(summarizer.get_daily_digest())

    # 특정 주제
    apple_news = summarizer.get_topic_news('Apple')
    print(f"\nApple 관련 뉴스 감정: {apple_news.sentiment}")
