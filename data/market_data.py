"""
시장 데이터 수집 모듈
주가, ETF, 채권, 환율, 원자재 데이터를 수집합니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


class MarketData:
    """시장 데이터 수집 클래스"""

    # 주요 지수
    INDICES = {
        'sp500': '^GSPC',
        'nasdaq': '^IXIC',
        'dow': '^DJI',
        'russell2000': '^RUT',
        'vix': '^VIX',
        'kospi': '^KS11',
        'kosdaq': '^KQ11',
    }

    # 섹터 ETF (SPDR)
    SECTOR_ETFS = {
        'technology': 'XLK',
        'healthcare': 'XLV',
        'financials': 'XLF',
        'consumer_discretionary': 'XLY',
        'consumer_staples': 'XLP',
        'energy': 'XLE',
        'utilities': 'XLU',
        'industrials': 'XLI',
        'materials': 'XLB',
        'real_estate': 'XLRE',
        'communication': 'XLC',
    }

    # 자산군 ETF
    ASSET_ETFS = {
        # 채권
        'treasury_short': 'SHY',    # 1-3년 국채
        'treasury_mid': 'IEF',      # 7-10년 국채
        'treasury_long': 'TLT',     # 20년+ 국채
        'corporate_bond': 'LQD',    # 투자등급 회사채
        'high_yield': 'HYG',        # 하이일드 채권

        # 원자재
        'gold': 'GLD',
        'silver': 'SLV',
        'oil': 'USO',
        'commodities': 'DBC',

        # 글로벌
        'emerging_markets': 'EEM',
        'developed_intl': 'EFA',
        'china': 'FXI',
        'europe': 'VGK',

        # 스타일
        'growth': 'IWF',
        'value': 'IWD',
        'small_cap': 'IWM',
        'dividend': 'DVY',
    }

    # 환율
    CURRENCIES = {
        'usd_index': 'DX-Y.NYB',
        'eur_usd': 'EURUSD=X',
        'usd_jpy': 'JPY=X',
        'usd_krw': 'KRW=X',
        'gbp_usd': 'GBPUSD=X',
    }

    def __init__(self):
        """초기화"""
        if not YFINANCE_AVAILABLE:
            print("Warning: yfinance가 설치되지 않았습니다.")

    def get_price_data(self, symbol: str,
                       period: str = '5y',
                       interval: str = '1d') -> pd.DataFrame:
        """
        개별 종목/ETF 가격 데이터 수집

        Args:
            symbol: 티커 심볼
            period: 기간 (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            interval: 간격 (1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            OHLCV 데이터프레임
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance가 필요합니다.")

        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=interval)

        return data

    def get_multiple_prices(self, symbols: List[str],
                           period: str = '5y') -> pd.DataFrame:
        """
        여러 종목의 종가 데이터 수집

        Args:
            symbols: 티커 심볼 리스트
            period: 기간

        Returns:
            종가 데이터프레임
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance가 필요합니다.")

        data = yf.download(symbols, period=period, progress=False)['Close']

        if isinstance(data, pd.Series):
            data = data.to_frame(name=symbols[0])

        return data

    def get_index_data(self, period: str = '5y') -> pd.DataFrame:
        """
        주요 지수 데이터 수집

        Returns:
            지수 종가 데이터프레임
        """
        symbols = list(self.INDICES.values())
        data = self.get_multiple_prices(symbols, period)
        data.columns = list(self.INDICES.keys())

        return data

    def get_sector_data(self, period: str = '5y') -> pd.DataFrame:
        """
        섹터 ETF 데이터 수집

        Returns:
            섹터별 종가 데이터프레임
        """
        symbols = list(self.SECTOR_ETFS.values())
        data = self.get_multiple_prices(symbols, period)
        data.columns = list(self.SECTOR_ETFS.keys())

        return data

    def get_asset_class_data(self, period: str = '5y') -> pd.DataFrame:
        """
        자산군별 ETF 데이터 수집

        Returns:
            자산군별 종가 데이터프레임
        """
        symbols = list(self.ASSET_ETFS.values())
        data = self.get_multiple_prices(symbols, period)
        data.columns = list(self.ASSET_ETFS.keys())

        return data

    def get_currency_data(self, period: str = '5y') -> pd.DataFrame:
        """
        환율 데이터 수집

        Returns:
            환율 데이터프레임
        """
        symbols = list(self.CURRENCIES.values())
        data = self.get_multiple_prices(symbols, period)
        data.columns = list(self.CURRENCIES.keys())

        return data

    def calculate_returns(self, prices: pd.DataFrame,
                         period: str = 'daily') -> pd.DataFrame:
        """
        수익률 계산

        Args:
            prices: 가격 데이터프레임
            period: 수익률 기간 (daily, weekly, monthly)

        Returns:
            수익률 데이터프레임
        """
        if period == 'daily':
            returns = prices.pct_change()
        elif period == 'weekly':
            returns = prices.resample('W').last().pct_change()
        elif period == 'monthly':
            returns = prices.resample('M').last().pct_change()
        else:
            returns = prices.pct_change()

        return returns

    def calculate_correlation(self, prices: pd.DataFrame,
                             window: int = 60) -> pd.DataFrame:
        """
        상관관계 계산

        Args:
            prices: 가격 데이터프레임
            window: 롤링 윈도우 크기

        Returns:
            상관관계 행렬
        """
        returns = self.calculate_returns(prices)
        correlation = returns.tail(window).corr()

        return correlation

    def calculate_volatility(self, prices: pd.DataFrame,
                            window: int = 20) -> pd.DataFrame:
        """
        변동성 계산 (연율화)

        Args:
            prices: 가격 데이터프레임
            window: 롤링 윈도우 크기

        Returns:
            변동성 데이터프레임
        """
        returns = self.calculate_returns(prices)
        volatility = returns.rolling(window=window).std() * np.sqrt(252)

        return volatility

    def get_relative_strength(self, prices: pd.DataFrame,
                             benchmark: str = 'sp500',
                             window: int = 20) -> pd.DataFrame:
        """
        상대 강도 계산

        Args:
            prices: 가격 데이터프레임
            benchmark: 벤치마크 컬럼명
            window: 롤링 윈도우

        Returns:
            상대 강도 데이터프레임
        """
        if benchmark not in prices.columns:
            raise ValueError(f"벤치마크 {benchmark}가 데이터에 없습니다.")

        benchmark_prices = prices[benchmark]
        relative_strength = prices.div(benchmark_prices, axis=0)

        # 상대 강도 모멘텀
        rs_momentum = relative_strength.pct_change(window)

        return rs_momentum

    def get_market_breadth(self, period: str = '1y') -> Dict:
        """
        시장 폭 지표 계산

        Returns:
            시장 폭 관련 지표들
        """
        # 섹터 데이터 수집
        sector_data = self.get_sector_data(period)

        # 최근 종가와 이동평균
        latest = sector_data.iloc[-1]
        ma_50 = sector_data.rolling(50).mean().iloc[-1]
        ma_200 = sector_data.rolling(200).mean().iloc[-1]

        # 50일 이동평균 위에 있는 섹터 비율
        above_50ma = (latest > ma_50).sum() / len(latest)

        # 200일 이동평균 위에 있는 섹터 비율
        above_200ma = (latest > ma_200).sum() / len(latest)

        # 52주 신고가 근처 (5% 이내) 섹터 수
        high_52w = sector_data.rolling(252).max().iloc[-1]
        near_high = ((high_52w - latest) / high_52w < 0.05).sum()

        return {
            'above_50ma_pct': above_50ma,
            'above_200ma_pct': above_200ma,
            'sectors_near_52w_high': near_high,
            'total_sectors': len(latest),
        }


# 샘플 데이터 생성 (API 없이 테스트용)
def get_sample_market_data() -> pd.DataFrame:
    """API 없이 테스트용 샘플 데이터 생성"""
    dates = pd.date_range(start='2020-01-01', end='2024-12-31', freq='B')

    np.random.seed(42)

    # S&P 500 시뮬레이션
    sp500_returns = np.random.normal(0.0004, 0.012, len(dates))
    sp500 = 3200 * np.cumprod(1 + sp500_returns)

    # 섹터별 베타를 적용한 시뮬레이션
    sectors = {
        'technology': (1.2, 100),    # 베타, 시작가
        'healthcare': (0.8, 100),
        'financials': (1.1, 30),
        'energy': (1.3, 50),
        'utilities': (0.5, 60),
        'consumer_discretionary': (1.1, 120),
        'consumer_staples': (0.6, 65),
        'industrials': (1.0, 80),
        'real_estate': (0.9, 40),
    }

    data = {'sp500': sp500}

    for sector, (beta, start_price) in sectors.items():
        sector_returns = beta * sp500_returns + np.random.normal(0, 0.005, len(dates))
        data[sector] = start_price * np.cumprod(1 + sector_returns)

    # 채권 (주가와 역상관)
    bond_returns = -0.3 * sp500_returns + np.random.normal(0, 0.003, len(dates))
    data['treasury_long'] = 140 * np.cumprod(1 + bond_returns)

    # 금 (약한 역상관)
    gold_returns = -0.1 * sp500_returns + np.random.normal(0.0002, 0.008, len(dates))
    data['gold'] = 150 * np.cumprod(1 + gold_returns)

    df = pd.DataFrame(data, index=dates)
    return df
