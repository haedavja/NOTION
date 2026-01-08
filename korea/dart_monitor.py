"""
DART 공시 모니터링 모듈
전자공시시스템 데이터 수집
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import re
import time


@dataclass
class Disclosure:
    """공시 정보"""
    corp_name: str
    corp_code: str
    report_name: str
    report_type: str  # 주요사항, 정기보고, 지분공시 등
    submit_date: datetime
    url: str
    importance: str = "normal"  # high, normal, low
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            'corp_name': self.corp_name,
            'corp_code': self.corp_code,
            'report_name': self.report_name,
            'report_type': self.report_type,
            'submit_date': self.submit_date.isoformat(),
            'url': self.url,
            'importance': self.importance,
            'keywords': self.keywords
        }


class DartMonitor:
    """DART 공시 모니터"""

    # 중요 공시 키워드
    HIGH_IMPORTANCE_KEYWORDS = [
        '실적', '매출', '영업이익', '순이익', '배당', '유상증자', '무상증자',
        '합병', '인수', '분할', '상장폐지', '관리종목', '투자주의',
        '횡령', '배임', '소송', '제재', '감사의견', '계약'
    ]

    # 공시 유형 분류
    REPORT_TYPES = {
        '사업보고서': '정기보고',
        '반기보고서': '정기보고',
        '분기보고서': '정기보고',
        '주요사항보고서': '주요사항',
        '임원ㆍ주요주주특정증권등': '지분공시',
        '공개매수': '지분공시',
        '자기주식': '자기주식',
        '증권발행실적보고서': '자금조달',
        '투자설명서': '자금조달',
        '감사보고서': '감사',
        '기업설명회': 'IR',
    }

    def __init__(self, api_key: str = None):
        """
        api_key: DART OpenAPI 인증키 (없으면 웹 크롤링)
        """
        self.api_key = api_key
        self.base_url = "https://dart.fss.or.kr"
        self.api_url = "https://opendart.fss.or.kr/api"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self._cache: Dict[str, List[Disclosure]] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = 300  # 5분

    def get_recent_disclosures(self, corp_name: str = None,
                               days: int = 7) -> List[Disclosure]:
        """최근 공시 조회"""
        cache_key = f"{corp_name}_{days}"

        # 캐시 확인
        if cache_key in self._cache_time:
            if datetime.now() - self._cache_time[cache_key] < timedelta(seconds=self._cache_ttl):
                return self._cache.get(cache_key, [])

        disclosures = []

        if self.api_key:
            disclosures = self._fetch_from_api(corp_name, days)
        else:
            disclosures = self._fetch_from_web(corp_name, days)

        self._cache[cache_key] = disclosures
        self._cache_time[cache_key] = datetime.now()

        return disclosures

    def _fetch_from_api(self, corp_name: str = None, days: int = 7) -> List[Disclosure]:
        """DART OpenAPI로 조회"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            params = {
                'crtfc_key': self.api_key,
                'bgn_de': start_date.strftime('%Y%m%d'),
                'end_de': end_date.strftime('%Y%m%d'),
                'page_count': 100
            }

            if corp_name:
                # 회사명으로 회사코드 조회 필요
                params['corp_name'] = corp_name

            url = f"{self.api_url}/list.json"
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()

            disclosures = []
            for item in data.get('list', []):
                disclosure = Disclosure(
                    corp_name=item.get('corp_name', ''),
                    corp_code=item.get('corp_code', ''),
                    report_name=item.get('report_nm', ''),
                    report_type=self._classify_report(item.get('report_nm', '')),
                    submit_date=datetime.strptime(item.get('rcept_dt', ''), '%Y%m%d'),
                    url=f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item.get('rcept_no', '')}",
                    importance=self._assess_importance(item.get('report_nm', '')),
                    keywords=self._extract_keywords(item.get('report_nm', ''))
                )
                disclosures.append(disclosure)

            return disclosures

        except Exception as e:
            print(f"DART API error: {e}")
            return []

    def _fetch_from_web(self, corp_name: str = None, days: int = 7) -> List[Disclosure]:
        """웹 크롤링으로 조회"""
        try:
            # DART 최신공시 페이지
            url = f"{self.base_url}/dsac001/mainAll.do"

            params = {
                'selectDate': '',
                'sort': 'date',
                'series': 'desc',
                'pageSize': '100'
            }

            resp = requests.get(url, params=params, headers=self.headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')

            disclosures = []
            cutoff_date = datetime.now() - timedelta(days=days)

            # 공시 테이블 파싱
            table = soup.select_one('table.tbList')
            if not table:
                return disclosures

            rows = table.select('tbody tr')

            for row in rows:
                cols = row.select('td')
                if len(cols) < 4:
                    continue

                try:
                    # 시간 파싱
                    time_text = cols[0].get_text(strip=True)

                    # 회사명
                    corp_elem = cols[1].select_one('a')
                    company = corp_elem.get_text(strip=True) if corp_elem else ''

                    # 보고서명
                    report_elem = cols[2].select_one('a')
                    report_name = report_elem.get_text(strip=True) if report_elem else ''
                    report_url = report_elem.get('href', '') if report_elem else ''

                    if report_url and not report_url.startswith('http'):
                        report_url = self.base_url + report_url

                    # 제출일
                    submit_text = cols[3].get_text(strip=True) if len(cols) > 3 else ''

                    # 날짜 파싱
                    try:
                        if '.' in submit_text:
                            submit_date = datetime.strptime(submit_text, '%Y.%m.%d')
                        else:
                            submit_date = datetime.now()
                    except:
                        submit_date = datetime.now()

                    if submit_date < cutoff_date:
                        continue

                    # 필터링
                    if corp_name and corp_name not in company:
                        continue

                    disclosure = Disclosure(
                        corp_name=company,
                        corp_code='',
                        report_name=report_name,
                        report_type=self._classify_report(report_name),
                        submit_date=submit_date,
                        url=report_url,
                        importance=self._assess_importance(report_name),
                        keywords=self._extract_keywords(report_name)
                    )
                    disclosures.append(disclosure)

                except Exception as e:
                    continue

            return disclosures

        except Exception as e:
            print(f"DART web scraping error: {e}")
            return []

    def get_portfolio_disclosures(self, symbols: List[Dict],
                                  days: int = 7) -> List[Disclosure]:
        """
        포트폴리오 종목 공시 조회
        symbols: [{'symbol': '005930.KS', 'name': '삼성전자'}, ...]
        """
        all_disclosures = []
        seen_urls = set()

        for stock in symbols[:10]:  # 최대 10종목
            name = stock.get('name', '')
            if not name:
                continue

            # 회사명에서 괄호 내용 제거
            clean_name = re.sub(r'\(.*?\)', '', name).strip()

            disclosures = self.get_recent_disclosures(clean_name, days)

            for d in disclosures:
                if d.url not in seen_urls:
                    all_disclosures.append(d)
                    seen_urls.add(d.url)

            time.sleep(0.5)  # 레이트 리미팅

        # 날짜순 정렬
        all_disclosures.sort(key=lambda x: x.submit_date, reverse=True)

        return all_disclosures

    def get_important_disclosures(self, symbols: List[Dict],
                                  days: int = 7) -> List[Disclosure]:
        """중요 공시만 필터링"""
        all_disclosures = self.get_portfolio_disclosures(symbols, days)
        return [d for d in all_disclosures if d.importance == 'high']

    def _classify_report(self, report_name: str) -> str:
        """보고서 유형 분류"""
        for keyword, report_type in self.REPORT_TYPES.items():
            if keyword in report_name:
                return report_type
        return '기타'

    def _assess_importance(self, report_name: str) -> str:
        """중요도 평가"""
        for keyword in self.HIGH_IMPORTANCE_KEYWORDS:
            if keyword in report_name:
                return 'high'
        return 'normal'

    def _extract_keywords(self, report_name: str) -> List[str]:
        """키워드 추출"""
        keywords = []
        for keyword in self.HIGH_IMPORTANCE_KEYWORDS:
            if keyword in report_name:
                keywords.append(keyword)
        return keywords


# 전역 인스턴스
dart_monitor = DartMonitor()
