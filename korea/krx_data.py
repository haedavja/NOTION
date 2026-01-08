"""
KRX 데이터 수집 모듈
한국 주식 시장 데이터 (KOSPI, KOSDAQ)
"""

import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd

try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


@dataclass
class KoreanStock:
    """한국 주식 정보"""
    code: str
    name: str
    market: str  # KOSPI or KOSDAQ
    price: float
    change: float
    change_pct: float
    volume: int
    market_cap: Optional[float] = None


class KRXDataCollector:
    """KRX 데이터 수집기"""

    def __init__(self):
        """초기화"""
        self.enabled = PYKRX_AVAILABLE

        # 주요 지수
        self.indices = {
            'KOSPI': '1001',
            'KOSDAQ': '2001',
            'KOSPI200': '1028',
            'KRX100': '5042',
        }

        # 섹터 ETF
        self.sector_etfs = {
            'KODEX 200': '069500',
            'KODEX 코스닥150': '229200',
            'KODEX 반도체': '091160',
            'KODEX 2차전지': '305720',
            'KODEX 은행': '091170',
            'KODEX 바이오': '244580',
            'TIGER 차이나전기차': '371460',
        }

        # 대표 종목
        self.blue_chips = {
            '005930': '삼성전자',
            '000660': 'SK하이닉스',
            '035420': 'NAVER',
            '035720': '카카오',
            '051910': 'LG화학',
            '006400': '삼성SDI',
            '005380': '현대차',
            '000270': '기아',
            '105560': 'KB금융',
            '055550': '신한지주',
        }

    def get_stock_list(self, market: str = 'ALL') -> pd.DataFrame:
        """
        종목 리스트 조회

        Args:
            market: 'KOSPI', 'KOSDAQ', or 'ALL'

        Returns:
            종목 목록 데이터프레임
        """
        if not self.enabled:
            return self._get_sample_stock_list()

        try:
            today = datetime.now().strftime('%Y%m%d')

            if market == 'ALL':
                kospi = stock.get_market_ticker_list(today, market='KOSPI')
                kosdaq = stock.get_market_ticker_list(today, market='KOSDAQ')
                tickers = kospi + kosdaq
                markets = ['KOSPI'] * len(kospi) + ['KOSDAQ'] * len(kosdaq)
            else:
                tickers = stock.get_market_ticker_list(today, market=market)
                markets = [market] * len(tickers)

            data = []
            for ticker, mkt in zip(tickers, markets):
                name = stock.get_market_ticker_name(ticker)
                data.append({
                    'code': ticker,
                    'name': name,
                    'market': mkt,
                })

            return pd.DataFrame(data)

        except Exception as e:
            print(f"종목 리스트 조회 오류: {e}")
            return self._get_sample_stock_list()

    def _get_sample_stock_list(self) -> pd.DataFrame:
        """샘플 종목 리스트"""
        data = [
            {'code': code, 'name': name, 'market': 'KOSPI'}
            for code, name in self.blue_chips.items()
        ]
        return pd.DataFrame(data)

    def get_stock_price(self, code: str,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None) -> pd.DataFrame:
        """
        주가 데이터 조회

        Args:
            code: 종목 코드
            start_date: 시작일 (YYYYMMDD)
            end_date: 종료일 (YYYYMMDD)

        Returns:
            OHLCV 데이터프레임
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365)).strftime('%Y%m%d')

        if not self.enabled:
            return self._get_sample_price_data(code)

        try:
            df = stock.get_market_ohlcv_by_date(start_date, end_date, code)
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            return df

        except Exception as e:
            print(f"주가 조회 오류 ({code}): {e}")
            return self._get_sample_price_data(code)

    def _get_sample_price_data(self, code: str) -> pd.DataFrame:
        """샘플 주가 데이터"""
        import numpy as np

        dates = pd.date_range(end=datetime.now(), periods=100, freq='B')
        base_price = 70000 if code == '005930' else 50000

        np.random.seed(hash(code) % 2**32)
        returns = np.random.randn(100) * 0.02
        prices = base_price * np.exp(np.cumsum(returns))

        df = pd.DataFrame({
            'Open': prices * (1 + np.random.randn(100) * 0.005),
            'High': prices * (1 + abs(np.random.randn(100) * 0.01)),
            'Low': prices * (1 - abs(np.random.randn(100) * 0.01)),
            'Close': prices,
            'Volume': np.random.randint(1000000, 10000000, 100),
        }, index=dates)

        return df

    def get_market_cap(self, code: str) -> Optional[Dict]:
        """
        시가총액 정보 조회

        Args:
            code: 종목 코드

        Returns:
            시가총액 정보
        """
        if not self.enabled:
            return {'market_cap': 500_000_000_000_000, 'shares': 5_969_782_550}

        try:
            today = datetime.now().strftime('%Y%m%d')
            df = stock.get_market_cap_by_date(today, today, code)

            if df.empty:
                return None

            return {
                'market_cap': int(df['시가총액'].iloc[-1]),
                'shares': int(df['상장주식수'].iloc[-1]),
            }

        except Exception as e:
            print(f"시가총액 조회 오류: {e}")
            return None

    def get_index_data(self, index_name: str = 'KOSPI',
                       days: int = 30) -> pd.DataFrame:
        """
        지수 데이터 조회

        Args:
            index_name: 지수명 (KOSPI, KOSDAQ, KOSPI200, KRX100)
            days: 조회 기간

        Returns:
            지수 데이터
        """
        if not self.enabled:
            return self._get_sample_index_data(index_name, days)

        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

            index_code = self.indices.get(index_name, '1001')
            df = stock.get_index_ohlcv_by_date(start_date, end_date, index_code)

            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            return df

        except Exception as e:
            print(f"지수 조회 오류: {e}")
            return self._get_sample_index_data(index_name, days)

    def _get_sample_index_data(self, index_name: str, days: int) -> pd.DataFrame:
        """샘플 지수 데이터"""
        import numpy as np

        dates = pd.date_range(end=datetime.now(), periods=days, freq='B')
        base = 2500 if index_name == 'KOSPI' else 850

        np.random.seed(42)
        returns = np.random.randn(days) * 0.01
        values = base * np.exp(np.cumsum(returns))

        return pd.DataFrame({
            'Open': values * (1 + np.random.randn(days) * 0.002),
            'High': values * (1 + abs(np.random.randn(days) * 0.005)),
            'Low': values * (1 - abs(np.random.randn(days) * 0.005)),
            'Close': values,
            'Volume': np.random.randint(100000000, 500000000, days),
        }, index=dates)

    def get_market_summary(self) -> Dict:
        """
        시장 요약

        Returns:
            시장 요약 정보
        """
        if not self.enabled:
            return self._get_sample_market_summary()

        try:
            today = datetime.now().strftime('%Y%m%d')
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')

            summary = {}

            # KOSPI
            kospi = stock.get_index_ohlcv_by_date(yesterday, today, '1001')
            if not kospi.empty:
                summary['KOSPI'] = {
                    'close': kospi['종가'].iloc[-1],
                    'change': kospi['종가'].iloc[-1] - kospi['종가'].iloc[0],
                    'change_pct': (kospi['종가'].iloc[-1] / kospi['종가'].iloc[0] - 1) * 100,
                    'volume': int(kospi['거래량'].iloc[-1]),
                }

            # KOSDAQ
            kosdaq = stock.get_index_ohlcv_by_date(yesterday, today, '2001')
            if not kosdaq.empty:
                summary['KOSDAQ'] = {
                    'close': kosdaq['종가'].iloc[-1],
                    'change': kosdaq['종가'].iloc[-1] - kosdaq['종가'].iloc[0],
                    'change_pct': (kosdaq['종가'].iloc[-1] / kosdaq['종가'].iloc[0] - 1) * 100,
                    'volume': int(kosdaq['거래량'].iloc[-1]),
                }

            return summary

        except Exception as e:
            print(f"시장 요약 오류: {e}")
            return self._get_sample_market_summary()

    def _get_sample_market_summary(self) -> Dict:
        """샘플 시장 요약"""
        return {
            'KOSPI': {
                'close': 2650.25,
                'change': 15.32,
                'change_pct': 0.58,
                'volume': 350000000,
            },
            'KOSDAQ': {
                'close': 875.50,
                'change': -5.20,
                'change_pct': -0.59,
                'volume': 850000000,
            },
        }

    def get_foreign_investor_trading(self, days: int = 5) -> pd.DataFrame:
        """
        외국인 매매 동향

        Args:
            days: 조회 기간

        Returns:
            외국인 매매 데이터
        """
        if not self.enabled:
            return self._get_sample_foreign_trading()

        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d')

            df = stock.get_market_net_purchases_of_equities_by_ticker(
                start_date, end_date, market='KOSPI', investor='외국인'
            )

            return df.head(20)  # 상위 20개 종목

        except Exception as e:
            print(f"외국인 매매 조회 오류: {e}")
            return self._get_sample_foreign_trading()

    def _get_sample_foreign_trading(self) -> pd.DataFrame:
        """샘플 외국인 매매"""
        data = {
            '종목명': ['삼성전자', 'SK하이닉스', 'NAVER', '카카오', '삼성SDI'],
            '매수': [500_000_000_000, 200_000_000_000, 150_000_000_000, 100_000_000_000, 80_000_000_000],
            '매도': [450_000_000_000, 220_000_000_000, 130_000_000_000, 120_000_000_000, 70_000_000_000],
            '순매수': [50_000_000_000, -20_000_000_000, 20_000_000_000, -20_000_000_000, 10_000_000_000],
        }
        return pd.DataFrame(data)

    def get_sector_performance(self) -> Dict[str, Dict]:
        """
        섹터별 성과

        Returns:
            섹터별 수익률
        """
        if not self.enabled:
            return self._get_sample_sector_performance()

        try:
            performance = {}
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

            for name, code in self.sector_etfs.items():
                df = stock.get_market_ohlcv_by_date(start_date, end_date, code)
                if not df.empty:
                    start_price = df['종가'].iloc[0]
                    end_price = df['종가'].iloc[-1]
                    performance[name] = {
                        'price': end_price,
                        'change_1m': (end_price / start_price - 1) * 100,
                    }

            return performance

        except Exception as e:
            print(f"섹터 성과 조회 오류: {e}")
            return self._get_sample_sector_performance()

    def _get_sample_sector_performance(self) -> Dict[str, Dict]:
        """샘플 섹터 성과"""
        return {
            'KODEX 200': {'price': 35000, 'change_1m': 2.5},
            'KODEX 코스닥150': {'price': 12000, 'change_1m': -1.2},
            'KODEX 반도체': {'price': 42000, 'change_1m': 5.8},
            'KODEX 2차전지': {'price': 18000, 'change_1m': -3.5},
            'KODEX 은행': {'price': 8500, 'change_1m': 1.8},
            'KODEX 바이오': {'price': 95000, 'change_1m': 0.5},
        }

    def search_stock(self, query: str) -> List[Dict]:
        """
        종목 검색

        Args:
            query: 검색어 (종목명 또는 코드)

        Returns:
            검색 결과
        """
        stock_list = self.get_stock_list()

        # 코드로 검색
        code_match = stock_list[stock_list['code'].str.contains(query, case=False)]

        # 이름으로 검색
        name_match = stock_list[stock_list['name'].str.contains(query, case=False)]

        results = pd.concat([code_match, name_match]).drop_duplicates()

        return results.head(10).to_dict('records')

    def get_status(self) -> Dict:
        """상태 확인"""
        return {
            'pykrx_available': PYKRX_AVAILABLE,
            'yfinance_available': YFINANCE_AVAILABLE,
            'enabled': self.enabled,
        }


# 편의 함수
def get_korean_stock_price(code: str, days: int = 30) -> pd.DataFrame:
    """한국 주식 가격 조회 (간편 함수)"""
    collector = KRXDataCollector()
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
    return collector.get_stock_price(code, start_date, end_date)
