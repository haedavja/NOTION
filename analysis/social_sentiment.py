"""
소셜 센티먼트 분석 모듈
네이버 종토방, 검색량 트렌드 분석
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import re
import time
from collections import Counter


@dataclass
class SocialPost:
    """소셜 게시글"""
    title: str
    content: str
    author: str
    timestamp: datetime
    likes: int = 0
    comments: int = 0
    sentiment: str = "neutral"  # positive, negative, neutral
    source: str = ""

    def to_dict(self) -> Dict:
        return {
            'title': self.title,
            'content': self.content,
            'author': self.author,
            'timestamp': self.timestamp.isoformat(),
            'likes': self.likes,
            'comments': self.comments,
            'sentiment': self.sentiment,
            'source': self.source
        }


@dataclass
class SentimentScore:
    """센티먼트 점수"""
    symbol: str
    name: str
    positive_ratio: float
    negative_ratio: float
    neutral_ratio: float
    total_posts: int
    sentiment_score: float  # -100 ~ +100
    hot_keywords: List[str]
    trend: str  # rising, falling, stable
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'name': self.name,
            'positive_ratio': self.positive_ratio,
            'negative_ratio': self.negative_ratio,
            'neutral_ratio': self.neutral_ratio,
            'total_posts': self.total_posts,
            'sentiment_score': self.sentiment_score,
            'hot_keywords': self.hot_keywords,
            'trend': self.trend,
            'timestamp': self.timestamp.isoformat()
        }


class SocialSentimentAnalyzer:
    """소셜 센티먼트 분석기"""

    # 감성 분석 키워드
    POSITIVE_KEYWORDS = [
        '상승', '급등', '대박', '호재', '좋다', '오른다', '기대', '추천',
        '매수', '들어간다', '간다', '존버', '홀딩', '물타기', '익절',
        '실적', '성장', '신고가', '돌파', '텐배거', '떡상'
    ]

    NEGATIVE_KEYWORDS = [
        '하락', '급락', '폭락', '악재', '나쁘다', '떨어진다', '위험',
        '매도', '손절', '탈출', '도망', '물렸다', '손실', '개미털기',
        '작전', '세력', '사기', '망함', '떡락', '반토막'
    ]

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self._cache: Dict[str, SentimentScore] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = 600  # 10분

    def get_naver_discussion(self, stock_code: str,
                            pages: int = 3) -> List[SocialPost]:
        """네이버 종목토론방 크롤링"""
        posts = []

        try:
            for page in range(1, pages + 1):
                url = f"https://finance.naver.com/item/board.naver?code={stock_code}&page={page}"
                resp = requests.get(url, headers=self.headers, timeout=10)
                soup = BeautifulSoup(resp.text, 'html.parser')

                # 게시글 테이블
                table = soup.select_one('table.type2')
                if not table:
                    continue

                rows = table.select('tbody tr')

                for row in rows:
                    try:
                        # 제목
                        title_elem = row.select_one('td.title a')
                        if not title_elem:
                            continue

                        title = title_elem.get_text(strip=True)

                        # 작성자
                        author_elem = row.select_one('td.p11')
                        author = author_elem.get_text(strip=True) if author_elem else 'anonymous'

                        # 날짜
                        date_elem = row.select_one('td span.tah')
                        date_str = date_elem.get_text(strip=True) if date_elem else ''

                        # 조회/공감
                        nums = row.select('td.num span')
                        likes = int(nums[0].get_text()) if len(nums) > 0 else 0
                        comments = int(nums[1].get_text()) if len(nums) > 1 else 0

                        # 날짜 파싱
                        try:
                            if '.' in date_str:
                                timestamp = datetime.strptime(date_str, '%Y.%m.%d %H:%M')
                            else:
                                timestamp = datetime.now()
                        except:
                            timestamp = datetime.now()

                        # 감성 분석
                        sentiment = self._analyze_text_sentiment(title)

                        posts.append(SocialPost(
                            title=title,
                            content="",
                            author=author,
                            timestamp=timestamp,
                            likes=likes,
                            comments=comments,
                            sentiment=sentiment,
                            source="naver_discussion"
                        ))

                    except Exception:
                        continue

                time.sleep(0.3)  # 레이트 리미팅

        except Exception as e:
            print(f"Naver discussion error: {e}")

        return posts

    def get_search_trend(self, keyword: str) -> Dict:
        """검색량 트렌드 (네이버 데이터랩 대안)"""
        try:
            # 네이버 연관검색어로 인기도 추정
            url = f"https://search.naver.com/search.naver?where=nexearch&query={keyword}"
            resp = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')

            # 연관 검색어 추출
            related = []
            related_elems = soup.select('.related_srch a')
            for elem in related_elems[:10]:
                related.append(elem.get_text(strip=True))

            # 뉴스 검색 결과 수로 관심도 추정
            news_count = 0
            news_info = soup.select_one('.sub_txt')
            if news_info:
                match = re.search(r'([\d,]+)건', news_info.get_text())
                if match:
                    news_count = int(match.group(1).replace(',', ''))

            return {
                'keyword': keyword,
                'related_keywords': related,
                'news_count': news_count,
                'interest_level': 'high' if news_count > 1000 else ('medium' if news_count > 100 else 'low')
            }

        except Exception as e:
            print(f"Search trend error: {e}")
            return {'keyword': keyword, 'related_keywords': [], 'news_count': 0, 'interest_level': 'unknown'}

    def analyze_stock_sentiment(self, stock_code: str,
                               stock_name: str) -> SentimentScore:
        """종목 소셜 센티먼트 분석"""
        cache_key = f"{stock_code}_{stock_name}"

        # 캐시 확인
        if cache_key in self._cache_time:
            if datetime.now() - self._cache_time[cache_key] < timedelta(seconds=self._cache_ttl):
                return self._cache.get(cache_key)

        # 데이터 수집
        posts = self.get_naver_discussion(stock_code, pages=5)

        if not posts:
            return SentimentScore(
                symbol=stock_code,
                name=stock_name,
                positive_ratio=0,
                negative_ratio=0,
                neutral_ratio=100,
                total_posts=0,
                sentiment_score=0,
                hot_keywords=[],
                trend='stable'
            )

        # 감성 비율 계산
        sentiments = [p.sentiment for p in posts]
        total = len(sentiments)

        positive = sentiments.count('positive')
        negative = sentiments.count('negative')
        neutral = sentiments.count('neutral')

        positive_ratio = (positive / total) * 100
        negative_ratio = (negative / total) * 100
        neutral_ratio = (neutral / total) * 100

        # 센티먼트 점수 (-100 ~ +100)
        sentiment_score = positive_ratio - negative_ratio

        # 핫 키워드 추출
        all_text = ' '.join([p.title for p in posts])
        hot_keywords = self._extract_hot_keywords(all_text)

        # 트렌드 판단 (최근 vs 이전)
        recent_posts = [p for p in posts if p.timestamp > datetime.now() - timedelta(hours=24)]
        older_posts = [p for p in posts if p.timestamp <= datetime.now() - timedelta(hours=24)]

        if recent_posts and older_posts:
            recent_score = sum(1 if p.sentiment == 'positive' else -1 if p.sentiment == 'negative' else 0
                              for p in recent_posts) / len(recent_posts)
            older_score = sum(1 if p.sentiment == 'positive' else -1 if p.sentiment == 'negative' else 0
                             for p in older_posts) / len(older_posts)

            if recent_score > older_score + 0.2:
                trend = 'rising'
            elif recent_score < older_score - 0.2:
                trend = 'falling'
            else:
                trend = 'stable'
        else:
            trend = 'stable'

        result = SentimentScore(
            symbol=stock_code,
            name=stock_name,
            positive_ratio=positive_ratio,
            negative_ratio=negative_ratio,
            neutral_ratio=neutral_ratio,
            total_posts=total,
            sentiment_score=sentiment_score,
            hot_keywords=hot_keywords,
            trend=trend
        )

        # 캐시 저장
        self._cache[cache_key] = result
        self._cache_time[cache_key] = datetime.now()

        return result

    def analyze_portfolio_sentiment(self, positions: List[Dict]) -> List[SentimentScore]:
        """포트폴리오 전체 센티먼트"""
        results = []

        for pos in positions[:10]:  # 최대 10종목
            symbol = pos.get('symbol', '')
            name = pos.get('name', '')

            # 한국 주식 코드 추출
            code = symbol.replace('.KS', '').replace('.KQ', '')

            if code.isdigit() and len(code) == 6:
                score = self.analyze_stock_sentiment(code, name)
                results.append(score)
                time.sleep(0.5)

        return results

    def get_market_mood(self, keywords: List[str] = None) -> Dict:
        """시장 전반 분위기"""
        if keywords is None:
            keywords = ['코스피', '코스닥', '증시', '주식시장']

        moods = []

        for keyword in keywords:
            trend = self.get_search_trend(keyword)
            moods.append({
                'keyword': keyword,
                'interest': trend['interest_level'],
                'related': trend['related_keywords'][:3]
            })

        # 전반적 관심도
        high_count = sum(1 for m in moods if m['interest'] == 'high')
        overall = 'high' if high_count > len(moods) / 2 else 'medium'

        return {
            'overall_interest': overall,
            'details': moods,
            'timestamp': datetime.now().isoformat()
        }

    def _analyze_text_sentiment(self, text: str) -> str:
        """텍스트 감성 분석"""
        text = text.lower()

        positive_count = sum(1 for kw in self.POSITIVE_KEYWORDS if kw in text)
        negative_count = sum(1 for kw in self.NEGATIVE_KEYWORDS if kw in text)

        if positive_count > negative_count:
            return 'positive'
        elif negative_count > positive_count:
            return 'negative'
        return 'neutral'

    def _extract_hot_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """핫 키워드 추출"""
        # 불용어
        stopwords = {'의', '가', '이', '은', '들', '는', '좀', '잘', '걍', '과',
                    '도', '를', '으로', '자', '에', '와', '한', '하다', '것', '수',
                    '있다', '없다', '같다', '그', '저', '이런', '저런'}

        # 단어 추출 (한글 2글자 이상)
        words = re.findall(r'[가-힣]{2,}', text)
        words = [w for w in words if w not in stopwords]

        # 빈도 계산
        counter = Counter(words)

        # 상위 키워드
        return [word for word, count in counter.most_common(top_n)]

    def get_bullish_bearish_ratio(self, stock_code: str) -> Dict:
        """강세/약세 비율"""
        posts = self.get_naver_discussion(stock_code, pages=3)

        bullish_keywords = ['매수', '상승', '간다', '급등', '호재', '좋다']
        bearish_keywords = ['매도', '하락', '빠진다', '급락', '악재', '나쁘다']

        bullish = 0
        bearish = 0

        for post in posts:
            text = post.title.lower()
            if any(kw in text for kw in bullish_keywords):
                bullish += 1
            if any(kw in text for kw in bearish_keywords):
                bearish += 1

        total = bullish + bearish or 1

        return {
            'bullish': bullish,
            'bearish': bearish,
            'bullish_ratio': (bullish / total) * 100,
            'bearish_ratio': (bearish / total) * 100,
            'bias': 'bullish' if bullish > bearish else ('bearish' if bearish > bullish else 'neutral')
        }


# 전역 인스턴스
social_analyzer = SocialSentimentAnalyzer()
