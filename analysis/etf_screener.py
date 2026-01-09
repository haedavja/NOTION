"""
ETF 스크리너
테마별 ETF 검색, 구성 종목 분석, 비용 비교
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


@dataclass
class ETFInfo:
    """ETF 정보"""
    symbol: str
    name: str
    category: str = ""
    expense_ratio: float = 0.0
    aum: float = 0.0  # 순자산 (USD)
    avg_volume: int = 0
    inception_date: str = ""
    yield_: float = 0.0
    ytd_return: float = 0.0
    one_year_return: float = 0.0
    three_year_return: float = 0.0
    holdings_count: int = 0
    top_holdings: List[Dict] = field(default_factory=list)


@dataclass
class ETFComparison:
    """ETF 비교 결과"""
    etfs: List[ETFInfo]
    correlation_matrix: Optional[pd.DataFrame] = None
    performance_data: Optional[pd.DataFrame] = None


class ETFScreener:
    """ETF 스크리너"""

    # 인기 ETF 목록 (테마별)
    POPULAR_ETFS = {
        "미국 대형주": ["SPY", "IVV", "VOO", "VTI", "QQQ"],
        "기술": ["QQQ", "VGT", "XLK", "ARKK", "SOXX"],
        "반도체": ["SOXX", "SMH", "SOXL", "XSD", "PSI"],
        "AI/클라우드": ["BOTZ", "ROBO", "AIQ", "CLOU", "WCLD"],
        "헬스케어": ["XLV", "VHT", "IBB", "XBI", "ARKG"],
        "금융": ["XLF", "VFH", "KBE", "KRE", "IYF"],
        "에너지": ["XLE", "VDE", "OIH", "XOP", "IYE"],
        "부동산": ["VNQ", "IYR", "XLRE", "RWR", "SCHH"],
        "배당": ["VYM", "SCHD", "DVY", "HDV", "SPHD"],
        "성장": ["VUG", "IWF", "SPYG", "SCHG", "VONG"],
        "가치": ["VTV", "IWD", "SPYV", "SCHV", "VONV"],
        "소형주": ["IWM", "VB", "IJR", "SCHA", "VBK"],
        "신흥국": ["EEM", "VWO", "IEMG", "SCHE", "EWZ"],
        "선진국": ["EFA", "VEA", "IEFA", "SCHF", "VGK"],
        "채권": ["BND", "AGG", "TLT", "IEF", "LQD"],
        "금/원자재": ["GLD", "IAU", "SLV", "DBC", "GSG"],
        "클린에너지": ["ICLN", "TAN", "QCLN", "PBW", "FAN"],
        "전기차": ["LIT", "DRIV", "KARS", "IDRV", "HAIL"],
        "메타버스": ["META", "METV", "MTVR", "PUNK", "VR"],
        "한국": ["EWY", "KORU", "FLKR"]
    }

    # 한국 ETF (국내상장)
    KOREAN_ETFS = {
        "코스피": ["069500.KS", "102110.KS", "226490.KS"],  # KODEX 200 등
        "코스닥": ["229200.KS", "251340.KS"],  # KODEX 코스닥150
        "반도체": ["091160.KS", "091180.KS"],  # KODEX 반도체
        "2차전지": ["305720.KS", "371460.KS"],  # TIGER 2차전지
        "바이오": ["244580.KS", "143860.KS"],  # KODEX 바이오
    }

    def __init__(self):
        self.cache: Dict[str, ETFInfo] = {}

    def get_etf_info(self, symbol: str) -> Optional[ETFInfo]:
        """ETF 정보 조회"""
        if not YFINANCE_AVAILABLE:
            return None

        if symbol in self.cache:
            return self.cache[symbol]

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            if not info:
                return None

            # 수익률 계산
            hist = ticker.history(period="3y")
            ytd_return = 0
            one_year_return = 0
            three_year_return = 0

            if not hist.empty:
                current = hist['Close'].iloc[-1]

                # YTD
                year_start = hist[hist.index.year == datetime.now().year]
                if not year_start.empty:
                    ytd_return = ((current - year_start['Close'].iloc[0]) /
                                  year_start['Close'].iloc[0]) * 100

                # 1년
                one_year_ago = hist[hist.index >= datetime.now() - timedelta(days=365)]
                if len(one_year_ago) > 0:
                    one_year_return = ((current - one_year_ago['Close'].iloc[0]) /
                                        one_year_ago['Close'].iloc[0]) * 100

                # 3년
                if len(hist) > 0:
                    three_year_return = ((current - hist['Close'].iloc[0]) /
                                          hist['Close'].iloc[0]) * 100

            etf_info = ETFInfo(
                symbol=symbol,
                name=info.get('longName', info.get('shortName', symbol)),
                category=info.get('category', ''),
                expense_ratio=info.get('annualReportExpenseRatio', 0) or 0,
                aum=info.get('totalAssets', 0) or 0,
                avg_volume=info.get('averageVolume', 0) or 0,
                yield_=(info.get('yield', 0) or 0) * 100,
                ytd_return=ytd_return,
                one_year_return=one_year_return,
                three_year_return=three_year_return,
                holdings_count=info.get('holdings', 0) or 0
            )

            # Top Holdings
            try:
                holdings = ticker.get_holdings()
                if holdings is not None and not holdings.empty:
                    etf_info.top_holdings = holdings.head(10).to_dict('records')
            except Exception:
                pass

            self.cache[symbol] = etf_info
            return etf_info

        except Exception as e:
            print(f"ETF 정보 조회 실패 ({symbol}): {e}")
            return None

    def screen_by_theme(self, theme: str) -> List[ETFInfo]:
        """테마별 ETF 스크리닝"""
        symbols = self.POPULAR_ETFS.get(theme, [])

        results = []
        for symbol in symbols:
            info = self.get_etf_info(symbol)
            if info:
                results.append(info)

        # AUM 순 정렬
        results.sort(key=lambda x: x.aum, reverse=True)

        return results

    def search_etfs(self, keywords: List[str], min_aum: float = 0,
                    max_expense: float = 1.0) -> List[ETFInfo]:
        """ETF 검색"""
        results = []

        # 모든 테마에서 검색
        for theme, symbols in self.POPULAR_ETFS.items():
            theme_lower = theme.lower()
            keyword_match = any(kw.lower() in theme_lower for kw in keywords)

            if keyword_match:
                for symbol in symbols:
                    info = self.get_etf_info(symbol)
                    if info:
                        if info.aum >= min_aum and info.expense_ratio <= max_expense:
                            results.append(info)

        # 중복 제거
        seen = set()
        unique_results = []
        for etf in results:
            if etf.symbol not in seen:
                seen.add(etf.symbol)
                unique_results.append(etf)

        return unique_results

    def compare_etfs(self, symbols: List[str], period: str = "1y") -> ETFComparison:
        """ETF 비교"""
        if not YFINANCE_AVAILABLE:
            return ETFComparison(etfs=[])

        etfs = []
        for symbol in symbols:
            info = self.get_etf_info(symbol)
            if info:
                etfs.append(info)

        # 가격 데이터 다운로드
        try:
            data = yf.download(symbols, period=period, progress=False)['Adj Close']
            if isinstance(data, pd.Series):
                data = data.to_frame(name=symbols[0])

            # 수익률 데이터
            returns = data.pct_change().dropna()

            # 상관관계 행렬
            correlation = returns.corr()

            # 성과 데이터
            performance = pd.DataFrame()
            for symbol in symbols:
                if symbol in data.columns:
                    col_data = data[symbol].dropna()
                    if len(col_data) > 0:
                        performance[symbol] = (col_data / col_data.iloc[0] - 1) * 100

            return ETFComparison(
                etfs=etfs,
                correlation_matrix=correlation,
                performance_data=performance
            )

        except Exception as e:
            print(f"비교 실패: {e}")
            return ETFComparison(etfs=etfs)

    def get_low_cost_etfs(self, limit: int = 20) -> List[ETFInfo]:
        """저비용 ETF 조회"""
        all_etfs = []

        for symbols in self.POPULAR_ETFS.values():
            for symbol in symbols:
                info = self.get_etf_info(symbol)
                if info and info.expense_ratio > 0:
                    all_etfs.append(info)

        # 비용 순 정렬
        all_etfs.sort(key=lambda x: x.expense_ratio)

        # 중복 제거
        seen = set()
        unique = []
        for etf in all_etfs:
            if etf.symbol not in seen:
                seen.add(etf.symbol)
                unique.append(etf)

        return unique[:limit]

    def get_high_dividend_etfs(self, min_yield: float = 2.0,
                                limit: int = 20) -> List[ETFInfo]:
        """고배당 ETF 조회"""
        dividend_themes = ["배당", "부동산"]
        all_etfs = []

        for theme in dividend_themes:
            etfs = self.screen_by_theme(theme)
            all_etfs.extend(etfs)

        # 배당수익률 순 정렬
        all_etfs = [e for e in all_etfs if e.yield_ >= min_yield]
        all_etfs.sort(key=lambda x: x.yield_, reverse=True)

        return all_etfs[:limit]

    def get_best_performers(self, period: str = "ytd",
                             limit: int = 20) -> List[ETFInfo]:
        """최고 성과 ETF"""
        all_etfs = []

        for symbols in self.POPULAR_ETFS.values():
            for symbol in symbols:
                info = self.get_etf_info(symbol)
                if info:
                    all_etfs.append(info)

        # 성과 순 정렬
        if period == "ytd":
            all_etfs.sort(key=lambda x: x.ytd_return, reverse=True)
        elif period == "1y":
            all_etfs.sort(key=lambda x: x.one_year_return, reverse=True)
        else:
            all_etfs.sort(key=lambda x: x.three_year_return, reverse=True)

        # 중복 제거
        seen = set()
        unique = []
        for etf in all_etfs:
            if etf.symbol not in seen:
                seen.add(etf.symbol)
                unique.append(etf)

        return unique[:limit]

    def get_themes(self) -> List[str]:
        """사용 가능한 테마 목록"""
        return list(self.POPULAR_ETFS.keys())

    def get_etf_table(self, symbols: List[str]) -> pd.DataFrame:
        """ETF 테이블 생성"""
        data = []

        for symbol in symbols:
            info = self.get_etf_info(symbol)
            if info:
                data.append({
                    '심볼': info.symbol,
                    '이름': info.name[:30],
                    '카테고리': info.category[:20] if info.category else '',
                    '비용(%)': f"{info.expense_ratio:.2f}",
                    'AUM($B)': f"{info.aum/1e9:.1f}",
                    'YTD(%)': f"{info.ytd_return:+.1f}",
                    '1Y(%)': f"{info.one_year_return:+.1f}",
                    '배당(%)': f"{info.yield_:.2f}"
                })

        return pd.DataFrame(data)


# 싱글톤 인스턴스
etf_screener = ETFScreener()


def screen_etfs(theme: str) -> List[ETFInfo]:
    """테마별 ETF 스크리닝"""
    return etf_screener.screen_by_theme(theme)


def compare_etfs(symbols: List[str]) -> ETFComparison:
    """ETF 비교"""
    return etf_screener.compare_etfs(symbols)


def get_etf_themes() -> List[str]:
    """테마 목록"""
    return etf_screener.get_themes()
