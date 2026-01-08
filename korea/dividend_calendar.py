"""
배당 캘린더 모듈
배당 일정, 예상 수익 계산
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import re

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


@dataclass
class DividendInfo:
    """배당 정보"""
    symbol: str
    name: str
    dividend_per_share: float  # 주당 배당금
    dividend_yield: float  # 배당수익률 (%)
    ex_dividend_date: Optional[datetime]  # 배당락일
    record_date: Optional[datetime]  # 배당기준일
    payment_date: Optional[datetime]  # 배당지급일
    dividend_type: str = "연간"  # 연간, 분기, 중간
    currency: str = "KRW"

    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'name': self.name,
            'dividend_per_share': self.dividend_per_share,
            'dividend_yield': self.dividend_yield,
            'ex_dividend_date': self.ex_dividend_date.strftime('%Y-%m-%d') if self.ex_dividend_date else None,
            'record_date': self.record_date.strftime('%Y-%m-%d') if self.record_date else None,
            'payment_date': self.payment_date.strftime('%Y-%m-%d') if self.payment_date else None,
            'dividend_type': self.dividend_type,
            'currency': self.currency
        }


@dataclass
class DividendCalendarEntry:
    """배당 캘린더 항목"""
    date: datetime
    event_type: str  # ex_dividend, record, payment
    dividend_info: DividendInfo

    def to_dict(self) -> Dict:
        return {
            'date': self.date.strftime('%Y-%m-%d'),
            'event_type': self.event_type,
            'dividend_info': self.dividend_info.to_dict()
        }


class DividendCalendar:
    """배당 캘린더"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self._cache: Dict[str, DividendInfo] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = 3600  # 1시간

    def get_dividend_info(self, symbol: str, name: str = "") -> Optional[DividendInfo]:
        """종목 배당 정보 조회"""
        # 캐시 확인
        if symbol in self._cache_time:
            if datetime.now() - self._cache_time[symbol] < timedelta(seconds=self._cache_ttl):
                return self._cache.get(symbol)

        dividend_info = None

        # 한국 주식
        if '.KS' in symbol or '.KQ' in symbol:
            dividend_info = self._get_korean_dividend(symbol, name)
        # 미국 주식
        else:
            dividend_info = self._get_us_dividend(symbol, name)

        if dividend_info:
            self._cache[symbol] = dividend_info
            self._cache_time[symbol] = datetime.now()

        return dividend_info

    def _get_korean_dividend(self, symbol: str, name: str) -> Optional[DividendInfo]:
        """한국 주식 배당 정보 (네이버 금융)"""
        try:
            # 종목코드 추출
            code = symbol.replace('.KS', '').replace('.KQ', '')

            # 네이버 금융 배당 페이지
            url = f"https://finance.naver.com/item/main.naver?code={code}"
            resp = requests.get(url, headers=self.headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')

            # 배당수익률 찾기
            dividend_yield = 0.0
            dividend_per_share = 0.0

            # 투자지표에서 배당수익률 추출
            table = soup.select_one('table.per_table')
            if table:
                rows = table.select('tr')
                for row in rows:
                    text = row.get_text()
                    if '배당수익률' in text:
                        match = re.search(r'([\d.]+)%', text)
                        if match:
                            dividend_yield = float(match.group(1))
                    if '주당배당금' in text or 'DPS' in text:
                        match = re.search(r'([\d,]+)원', text)
                        if match:
                            dividend_per_share = float(match.group(1).replace(',', ''))

            # 현재가 조회해서 배당금 추정
            if YFINANCE_AVAILABLE and dividend_yield > 0 and dividend_per_share == 0:
                ticker = yf.Ticker(symbol)
                try:
                    price = ticker.fast_info.last_price
                    dividend_per_share = price * (dividend_yield / 100)
                except:
                    pass

            if dividend_yield > 0 or dividend_per_share > 0:
                # 배당락일 추정 (12월 결산 기준, 다음해 3월 말)
                now = datetime.now()
                if now.month <= 3:
                    ex_date = datetime(now.year, 3, 28)
                else:
                    ex_date = datetime(now.year + 1, 3, 28)

                return DividendInfo(
                    symbol=symbol,
                    name=name or code,
                    dividend_per_share=dividend_per_share,
                    dividend_yield=dividend_yield,
                    ex_dividend_date=ex_date,
                    record_date=datetime(ex_date.year, 12, 31) if ex_date.month == 3 else None,
                    payment_date=datetime(ex_date.year, 4, 15) if ex_date.month == 3 else None,
                    dividend_type="연간",
                    currency="KRW"
                )

            return None

        except Exception as e:
            print(f"Korean dividend error for {symbol}: {e}")
            return None

    def _get_us_dividend(self, symbol: str, name: str) -> Optional[DividendInfo]:
        """미국 주식 배당 정보 (yfinance)"""
        if not YFINANCE_AVAILABLE:
            return None

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            dividend_yield = info.get('dividendYield', 0) or 0
            dividend_rate = info.get('dividendRate', 0) or 0
            ex_dividend_date = info.get('exDividendDate')

            if dividend_yield == 0 and dividend_rate == 0:
                return None

            # 타임스탬프를 datetime으로 변환
            ex_date = None
            if ex_dividend_date:
                ex_date = datetime.fromtimestamp(ex_dividend_date)

            return DividendInfo(
                symbol=symbol,
                name=name or symbol,
                dividend_per_share=dividend_rate,
                dividend_yield=dividend_yield * 100,  # yfinance는 소수점으로 반환
                ex_dividend_date=ex_date,
                record_date=None,
                payment_date=None,
                dividend_type="분기" if dividend_rate > 0 else "연간",
                currency="USD"
            )

        except Exception as e:
            print(f"US dividend error for {symbol}: {e}")
            return None

    def get_portfolio_dividends(self, positions: List[Dict]) -> List[Dict]:
        """
        포트폴리오 배당 정보
        positions: [{'symbol': 'AAPL', 'name': 'Apple', 'quantity': 10}, ...]
        """
        results = []

        for pos in positions:
            symbol = pos.get('symbol', '')
            name = pos.get('name', '')
            quantity = pos.get('quantity', 0)

            info = self.get_dividend_info(symbol, name)
            if info:
                expected_dividend = info.dividend_per_share * quantity
                results.append({
                    'symbol': symbol,
                    'name': name,
                    'quantity': quantity,
                    'dividend_info': info,
                    'expected_dividend': expected_dividend
                })

        return results

    def get_calendar(self, positions: List[Dict],
                    months_ahead: int = 6) -> List[DividendCalendarEntry]:
        """배당 캘린더 생성"""
        entries = []
        now = datetime.now()
        cutoff = now + timedelta(days=months_ahead * 30)

        for pos in positions:
            symbol = pos.get('symbol', '')
            name = pos.get('name', '')

            info = self.get_dividend_info(symbol, name)
            if not info:
                continue

            # 배당락일
            if info.ex_dividend_date and now <= info.ex_dividend_date <= cutoff:
                entries.append(DividendCalendarEntry(
                    date=info.ex_dividend_date,
                    event_type='ex_dividend',
                    dividend_info=info
                ))

            # 배당기준일
            if info.record_date and now <= info.record_date <= cutoff:
                entries.append(DividendCalendarEntry(
                    date=info.record_date,
                    event_type='record',
                    dividend_info=info
                ))

            # 배당지급일
            if info.payment_date and now <= info.payment_date <= cutoff:
                entries.append(DividendCalendarEntry(
                    date=info.payment_date,
                    event_type='payment',
                    dividend_info=info
                ))

        # 날짜순 정렬
        entries.sort(key=lambda x: x.date)

        return entries

    def calculate_expected_income(self, positions: List[Dict],
                                  months: int = 12) -> Dict:
        """예상 배당 수익 계산"""
        portfolio_dividends = self.get_portfolio_dividends(positions)

        total_expected = 0.0
        by_stock = []
        by_month = {i: 0.0 for i in range(1, 13)}

        for item in portfolio_dividends:
            info = item['dividend_info']
            expected = item['expected_dividend']

            total_expected += expected
            by_stock.append({
                'symbol': item['symbol'],
                'name': item['name'],
                'expected': expected,
                'yield': info.dividend_yield,
                'payment_date': info.payment_date
            })

            # 지급월 추정
            if info.payment_date:
                month = info.payment_date.month
                by_month[month] += expected

        return {
            'total_expected': total_expected,
            'by_stock': sorted(by_stock, key=lambda x: x['expected'], reverse=True),
            'by_month': by_month,
            'average_yield': sum(item['dividend_info'].dividend_yield
                               for item in portfolio_dividends) / len(portfolio_dividends) if portfolio_dividends else 0
        }


# 전역 인스턴스
dividend_calendar = DividendCalendar()
