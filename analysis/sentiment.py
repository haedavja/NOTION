"""
센티먼트 분석 모듈
뉴스와 텍스트 데이터의 감성을 분석합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import re
from collections import Counter

# transformers는 선택적 의존성
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False


@dataclass
class SentimentResult:
    """센티먼트 분석 결과"""
    text: str
    sentiment: str       # positive, negative, neutral
    score: float         # 확신도 (0-1)
    keywords: List[str]  # 추출된 키워드


class SentimentAnalyzer:
    """센티먼트 분석 클래스"""

    # 금융 관련 긍정/부정 키워드 (규칙 기반 분석용)
    POSITIVE_KEYWORDS = {
        # 시장 긍정
        'rally', 'surge', 'jump', 'gain', 'rise', 'climb', 'soar',
        'bullish', 'bull', 'upbeat', 'optimistic', 'positive',
        'growth', 'expand', 'recovery', 'rebound', 'bounce',
        'beat', 'exceed', 'outperform', 'strong', 'robust',
        'upgrade', 'buy', 'accumulate', 'overweight',
        'record high', 'all-time high', 'breakthrough',

        # 경제 긍정
        'hiring', 'employment gains', 'job growth', 'wage growth',
        'consumer confidence', 'business confidence',
        'rate cut', 'dovish', 'stimulus', 'easing',
    }

    NEGATIVE_KEYWORDS = {
        # 시장 부정
        'fall', 'drop', 'decline', 'sink', 'plunge', 'crash', 'tumble',
        'bearish', 'bear', 'pessimistic', 'negative', 'concern', 'worry',
        'recession', 'slowdown', 'contraction', 'downturn',
        'miss', 'disappoint', 'underperform', 'weak', 'soft',
        'downgrade', 'sell', 'reduce', 'underweight',
        'correction', 'selloff', 'rout',

        # 경제 부정
        'layoffs', 'job cuts', 'unemployment rise', 'jobless claims',
        'inflation surge', 'price pressure',
        'rate hike', 'hawkish', 'tightening',
        'default', 'bankruptcy', 'crisis',
        'geopolitical risk', 'trade war', 'sanctions',
    }

    # 강조어 (가중치 부여용)
    INTENSIFIERS = {
        'very', 'extremely', 'significantly', 'sharply', 'dramatically',
        'substantially', 'considerably', 'strongly', 'massively',
    }

    DIMINISHERS = {
        'slightly', 'modestly', 'marginally', 'somewhat', 'mildly',
    }

    def __init__(self, use_ml: bool = True):
        """
        초기화

        Args:
            use_ml: ML 모델 사용 여부 (False면 규칙 기반만 사용)
        """
        self.use_ml = use_ml and TRANSFORMERS_AVAILABLE
        self.ml_analyzer = None

        if self.use_ml:
            try:
                self.ml_analyzer = pipeline(
                    "sentiment-analysis",
                    model="ProsusAI/finbert",
                    truncation=True
                )
            except Exception as e:
                print(f"ML 모델 로드 실패, 규칙 기반 분석 사용: {e}")
                self.use_ml = False

    def analyze_text(self, text: str) -> SentimentResult:
        """
        단일 텍스트 센티먼트 분석

        Args:
            text: 분석할 텍스트

        Returns:
            센티먼트 분석 결과
        """
        # 키워드 추출
        keywords = self._extract_keywords(text)

        # ML 분석 시도
        if self.use_ml and self.ml_analyzer:
            try:
                result = self.ml_analyzer(text[:512])[0]
                sentiment = result['label'].lower()
                score = result['score']

                return SentimentResult(
                    text=text[:200],
                    sentiment=sentiment,
                    score=score,
                    keywords=keywords
                )
            except Exception:
                pass

        # 규칙 기반 분석
        sentiment, score = self._rule_based_analysis(text)

        return SentimentResult(
            text=text[:200],
            sentiment=sentiment,
            score=score,
            keywords=keywords
        )

    def _rule_based_analysis(self, text: str) -> Tuple[str, float]:
        """
        규칙 기반 센티먼트 분석

        Args:
            text: 분석할 텍스트

        Returns:
            (sentiment, score)
        """
        text_lower = text.lower()
        words = text_lower.split()

        positive_count = 0
        negative_count = 0
        intensifier_boost = 1.0

        # 강조어 체크
        for intensifier in self.INTENSIFIERS:
            if intensifier in text_lower:
                intensifier_boost = 1.3
                break

        for diminisher in self.DIMINISHERS:
            if diminisher in text_lower:
                intensifier_boost = 0.7
                break

        # 키워드 매칭
        for keyword in self.POSITIVE_KEYWORDS:
            if keyword in text_lower:
                positive_count += 1

        for keyword in self.NEGATIVE_KEYWORDS:
            if keyword in text_lower:
                negative_count += 1

        # 점수 계산
        total = positive_count + negative_count
        if total == 0:
            return 'neutral', 0.5

        positive_ratio = positive_count / total
        negative_ratio = negative_count / total

        if positive_ratio > 0.6:
            sentiment = 'positive'
            score = min(0.5 + positive_ratio * 0.5 * intensifier_boost, 1.0)
        elif negative_ratio > 0.6:
            sentiment = 'negative'
            score = min(0.5 + negative_ratio * 0.5 * intensifier_boost, 1.0)
        else:
            sentiment = 'neutral'
            score = 0.5 + abs(positive_ratio - negative_ratio) * 0.3

        return sentiment, score

    def _extract_keywords(self, text: str) -> List[str]:
        """키워드 추출"""
        text_lower = text.lower()
        keywords = []

        for keyword in self.POSITIVE_KEYWORDS | self.NEGATIVE_KEYWORDS:
            if keyword in text_lower:
                keywords.append(keyword)

        return keywords[:10]  # 상위 10개

    def analyze_articles(self, articles: List[Dict]) -> Dict:
        """
        뉴스 기사 리스트 분석

        Args:
            articles: 뉴스 기사 리스트 (title, description 포함)

        Returns:
            종합 센티먼트 분석 결과
        """
        results = []

        for article in articles:
            text = f"{article.get('title', '')} {article.get('description', '')}"
            if text.strip():
                result = self.analyze_text(text)
                results.append({
                    'title': article.get('title', ''),
                    'sentiment': result.sentiment,
                    'score': result.score,
                    'keywords': result.keywords,
                    'source': article.get('source', ''),
                    'published_at': article.get('published_at', ''),
                })

        # 종합 통계
        if not results:
            return {'error': 'No articles to analyze'}

        sentiments = [r['sentiment'] for r in results]
        scores = [r['score'] for r in results]

        sentiment_counts = Counter(sentiments)
        total = len(sentiments)

        # 모든 키워드 집계
        all_keywords = []
        for r in results:
            all_keywords.extend(r['keywords'])
        keyword_freq = Counter(all_keywords).most_common(20)

        # 종합 점수 계산 (-1 ~ 1)
        composite_score = 0
        for r in results:
            if r['sentiment'] == 'positive':
                composite_score += r['score']
            elif r['sentiment'] == 'negative':
                composite_score -= r['score']
        composite_score = composite_score / total if total > 0 else 0

        return {
            'total_articles': total,
            'sentiment_distribution': {
                'positive': sentiment_counts.get('positive', 0),
                'negative': sentiment_counts.get('negative', 0),
                'neutral': sentiment_counts.get('neutral', 0),
            },
            'sentiment_percentages': {
                'positive': sentiment_counts.get('positive', 0) / total * 100,
                'negative': sentiment_counts.get('negative', 0) / total * 100,
                'neutral': sentiment_counts.get('neutral', 0) / total * 100,
            },
            'average_confidence': np.mean(scores),
            'composite_score': composite_score,
            'overall_sentiment': 'Bullish' if composite_score > 0.1 else ('Bearish' if composite_score < -0.1 else 'Neutral'),
            'top_keywords': keyword_freq,
            'detailed_results': results,
        }

    def get_sentiment_trend(self, articles: List[Dict],
                           time_column: str = 'published_at') -> pd.DataFrame:
        """
        시간별 센티먼트 트렌드 분석

        Args:
            articles: 시간 정보가 포함된 기사 리스트
            time_column: 시간 컬럼명

        Returns:
            시간별 센티먼트 데이터프레임
        """
        results = []

        for article in articles:
            text = f"{article.get('title', '')} {article.get('description', '')}"
            if text.strip():
                result = self.analyze_text(text)
                results.append({
                    'timestamp': article.get(time_column),
                    'sentiment': result.sentiment,
                    'score': result.score,
                })

        df = pd.DataFrame(results)

        if df.empty:
            return df

        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.dropna(subset=['timestamp'])

        # 센티먼트 수치화
        sentiment_map = {'positive': 1, 'neutral': 0, 'negative': -1}
        df['sentiment_value'] = df['sentiment'].map(sentiment_map)

        # 일별 집계
        daily = df.set_index('timestamp').resample('D').agg({
            'sentiment_value': 'mean',
            'score': 'mean',
        }).dropna()

        daily.columns = ['daily_sentiment', 'daily_confidence']

        # 이동평균
        if len(daily) >= 7:
            daily['sentiment_ma_7d'] = daily['daily_sentiment'].rolling(7).mean()

        return daily

    def detect_sentiment_shift(self, articles: List[Dict],
                              window: int = 7) -> Dict:
        """
        센티먼트 변화 감지

        Args:
            articles: 기사 리스트
            window: 비교 기간 (일)

        Returns:
            센티먼트 변화 분석
        """
        trend = self.get_sentiment_trend(articles)

        if len(trend) < window * 2:
            return {'error': 'Insufficient data for trend analysis'}

        recent = trend['daily_sentiment'].tail(window).mean()
        previous = trend['daily_sentiment'].iloc[-window*2:-window].mean()

        shift = recent - previous
        shift_pct = (shift / (abs(previous) + 0.01)) * 100

        return {
            'recent_sentiment': recent,
            'previous_sentiment': previous,
            'shift': shift,
            'shift_percentage': shift_pct,
            'direction': 'Improving' if shift > 0.1 else ('Deteriorating' if shift < -0.1 else 'Stable'),
            'significance': 'High' if abs(shift) > 0.3 else ('Medium' if abs(shift) > 0.15 else 'Low'),
        }

    def get_category_sentiment(self, categorized_articles: Dict[str, List[Dict]]) -> Dict:
        """
        카테고리별 센티먼트 분석

        Args:
            categorized_articles: 카테고리별 기사 딕셔너리

        Returns:
            카테고리별 센티먼트
        """
        category_sentiment = {}

        for category, articles in categorized_articles.items():
            if articles:
                analysis = self.analyze_articles(articles)
                category_sentiment[category] = {
                    'article_count': analysis['total_articles'],
                    'composite_score': analysis['composite_score'],
                    'overall_sentiment': analysis['overall_sentiment'],
                    'positive_pct': analysis['sentiment_percentages']['positive'],
                    'negative_pct': analysis['sentiment_percentages']['negative'],
                }

        return category_sentiment

    def get_summary(self, articles: List[Dict]) -> Dict:
        """
        센티먼트 분석 요약

        Args:
            articles: 뉴스 기사 리스트

        Returns:
            종합 요약
        """
        # 전체 분석
        overall = self.analyze_articles(articles)

        # 트렌드
        trend = self.get_sentiment_trend(articles)

        # 변화 감지
        shift = self.detect_sentiment_shift(articles)

        # 시장 영향 해석
        composite = overall.get('composite_score', 0)

        if composite > 0.3:
            market_implication = "강한 긍정적 센티먼트 - 시장 상승 기대감 높음"
        elif composite > 0.1:
            market_implication = "다소 긍정적 센티먼트 - 시장에 긍정적"
        elif composite < -0.3:
            market_implication = "강한 부정적 센티먼트 - 하락 압력 예상"
        elif composite < -0.1:
            market_implication = "다소 부정적 센티먼트 - 시장에 부정적"
        else:
            market_implication = "중립적 센티먼트 - 뚜렷한 방향성 없음"

        return {
            'overall_analysis': overall,
            'trend_data': trend.to_dict() if not trend.empty else {},
            'sentiment_shift': shift,
            'market_implication': market_implication,
            'key_themes': overall.get('top_keywords', [])[:10],
        }
