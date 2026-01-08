"""
실시간 시장 키워드 수집
네이버 금융, 한경 등에서 인기 검색어/테마 크롤링
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re
import json


class MarketKeywordCollector:
    """시장 키워드 수집기"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self._cache = {}
        self._cache_time = None
        self._cache_duration = timedelta(minutes=10)

    def _get_cached_or_fetch(self, key: str, fetch_func) -> any:
        """캐시된 데이터 반환 또는 새로 가져오기"""
        now = datetime.now()
        if (self._cache_time and
            now - self._cache_time < self._cache_duration and
            key in self._cache):
            return self._cache[key]

        try:
            data = fetch_func()
            self._cache[key] = data
            self._cache_time = now
            return data
        except Exception as e:
            print(f"키워드 수집 실패 ({key}): {e}")
            return self._cache.get(key, [])

    def get_naver_popular_stocks(self) -> List[Dict]:
        """네이버 금융 인기 검색 종목"""
        def fetch():
            url = "https://finance.naver.com/sise/lastsearch2.naver"
            try:
                resp = requests.get(url, headers=self.headers, timeout=5)
                soup = BeautifulSoup(resp.text, 'html.parser')

                results = []
                rows = soup.select('table.type_5 tr')

                for row in rows[:15]:
                    cols = row.select('td')
                    if len(cols) >= 4:
                        rank = cols[0].get_text(strip=True)
                        name_tag = cols[1].select_one('a')
                        if name_tag:
                            name = name_tag.get_text(strip=True)
                            # 검색량/관심도
                            search_count = cols[2].get_text(strip=True).replace(',', '')
                            change = cols[3].get_text(strip=True)

                            results.append({
                                'rank': int(rank) if rank.isdigit() else 0,
                                'name': name,
                                'search_count': int(search_count) if search_count.isdigit() else 0,
                                'change': change,
                                'type': 'stock'
                            })
                return results
            except:
                return []

        return self._get_cached_or_fetch('naver_popular', fetch)

    def get_naver_themes(self) -> List[Dict]:
        """네이버 금융 테마별 시세"""
        def fetch():
            url = "https://finance.naver.com/sise/theme.naver"
            try:
                resp = requests.get(url, headers=self.headers, timeout=5)
                soup = BeautifulSoup(resp.text, 'html.parser')

                results = []
                rows = soup.select('table.type_1 tr')

                for row in rows[:20]:
                    cols = row.select('td')
                    if len(cols) >= 4:
                        name_tag = cols[0].select_one('a')
                        if name_tag:
                            name = name_tag.get_text(strip=True)
                            change_pct = cols[1].get_text(strip=True)

                            # 변동률 파싱
                            try:
                                change_val = float(change_pct.replace('%', '').replace('+', ''))
                            except:
                                change_val = 0

                            results.append({
                                'name': name,
                                'change_pct': change_val,
                                'trend': '↑' if change_val > 0 else ('↓' if change_val < 0 else '→'),
                                'type': 'theme'
                            })
                return results
            except:
                return []

        return self._get_cached_or_fetch('naver_themes', fetch)

    def get_hankyung_keywords(self) -> List[Dict]:
        """한경 실시간 인기 키워드"""
        def fetch():
            # 한경 증권 페이지에서 키워드 추출 시도
            url = "https://www.hankyung.com/finance"
            try:
                resp = requests.get(url, headers=self.headers, timeout=5)
                soup = BeautifulSoup(resp.text, 'html.parser')

                # 뉴스 헤드라인에서 키워드 추출
                headlines = soup.select('h2.news-tit, h3.news-tit, .article-title')
                keywords = {}

                # 주요 키워드 패턴
                keyword_patterns = [
                    '반도체', 'AI', '2차전지', '배터리', '로봇', '바이오',
                    '삼성', 'SK', 'LG', '현대', '금리', '환율', '유가',
                    '코스피', '코스닥', 'ETF', '공매도', '외국인', '기관'
                ]

                for headline in headlines[:30]:
                    text = headline.get_text()
                    for kw in keyword_patterns:
                        if kw in text:
                            keywords[kw] = keywords.get(kw, 0) + 1

                # 빈도순 정렬
                sorted_kw = sorted(keywords.items(), key=lambda x: -x[1])
                return [{'keyword': kw, 'count': cnt, 'type': 'news'} for kw, cnt in sorted_kw[:10]]
            except:
                return []

        return self._get_cached_or_fetch('hankyung', fetch)

    def get_all_keywords(self) -> Dict:
        """모든 키워드 통합"""
        popular_stocks = self.get_naver_popular_stocks()
        themes = self.get_naver_themes()
        news_keywords = self.get_hankyung_keywords()

        # 통합 키워드 (heat 계산)
        all_keywords = []

        # 인기 종목 (순위 기반 heat)
        for stock in popular_stocks[:10]:
            heat = max(95 - (stock['rank'] - 1) * 5, 50)
            all_keywords.append({
                'text': stock['name'],
                'heat': heat,
                'type': 'stock',
                'tooltip': f"검색량: {stock['search_count']:,}"
            })

        # 테마 (변동률 기반 heat)
        for theme in themes[:10]:
            heat = min(max(50 + abs(theme['change_pct']) * 5, 50), 95)
            all_keywords.append({
                'text': theme['name'],
                'heat': heat,
                'type': 'theme',
                'trend': theme['trend'],
                'tooltip': f"변동률: {theme['change_pct']:+.1f}%"
            })

        # 뉴스 키워드 (빈도 기반 heat)
        for kw in news_keywords[:8]:
            heat = min(50 + kw['count'] * 10, 90)
            all_keywords.append({
                'text': kw['keyword'],
                'heat': heat,
                'type': 'news',
                'tooltip': f"뉴스 언급: {kw['count']}회"
            })

        return {
            'popular_stocks': popular_stocks,
            'themes': themes,
            'news_keywords': news_keywords,
            'all_keywords': sorted(all_keywords, key=lambda x: -x['heat'])
        }


# 전역 인스턴스
keyword_collector = MarketKeywordCollector()


def get_realtime_keywords() -> Dict:
    """실시간 키워드 가져오기 (캐시 적용)"""
    return keyword_collector.get_all_keywords()


def get_fallback_keywords() -> Dict:
    """크롤링 실패 시 폴백 데이터"""
    return {
        '핫 테마': [
            {'keyword': '2차전지', 'heat': 95, 'trend': '↑', 'related': ['LG에너지솔루션', 'POSCO홀딩스', '에코프로']},
            {'keyword': 'AI/반도체', 'heat': 92, 'trend': '↑', 'related': ['삼성전자', 'SK하이닉스', '한미반도체']},
            {'keyword': '로봇', 'heat': 78, 'trend': '↑', 'related': ['현대차', '두산로보틱스', '레인보우로보틱스']},
            {'keyword': '조선', 'heat': 75, 'trend': '→', 'related': ['HD한국조선해양', '삼성중공업', 'HD현대중공업']},
            {'keyword': '방산', 'heat': 70, 'trend': '↑', 'related': ['한화에어로스페이스', 'LIG넥스원', '한국항공우주']},
        ],
        '정책/이슈': [
            {'keyword': '금리', 'heat': 88, 'impact': '중립', 'desc': '한은 기준금리 동향'},
            {'keyword': '밸류업', 'heat': 85, 'impact': '호재', 'desc': '저PBR 기업 자사주 매입'},
            {'keyword': '공매도', 'heat': 80, 'impact': '주의', 'desc': '공매도 재개 이슈'},
        ],
        '섹터 모멘텀': [
            {'sector': '반도체', 'momentum': '강세', 'reason': 'AI 수요'},
            {'sector': '자동차', 'momentum': '중립', 'reason': '전기차 둔화'},
            {'sector': '바이오', 'momentum': '약세', 'reason': '금리 부담'},
        ],
        '글로벌 이슈': [
            {'keyword': '미국 금리', 'status': '인하 기대'},
            {'keyword': '중국 경기', 'status': '부진 지속'},
        ]
    }
