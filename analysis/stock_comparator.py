"""
종목 비교 분석 모듈
동종업계 비교, 재무지표 비교
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


@dataclass
class StockMetrics:
    """종목 지표"""
    symbol: str
    name: str
    sector: str
    industry: str
    market_cap: float
    price: float
    change_pct: float

    # 밸류에이션
    per: float  # PER
    pbr: float  # PBR
    psr: float  # PSR
    ev_ebitda: float

    # 수익성
    roe: float
    roa: float
    profit_margin: float
    operating_margin: float

    # 성장성
    revenue_growth: float
    earnings_growth: float

    # 재무안정성
    debt_to_equity: float
    current_ratio: float

    # 배당
    dividend_yield: float

    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'name': self.name,
            'sector': self.sector,
            'industry': self.industry,
            'market_cap': self.market_cap,
            'price': self.price,
            'change_pct': self.change_pct,
            'per': self.per,
            'pbr': self.pbr,
            'psr': self.psr,
            'ev_ebitda': self.ev_ebitda,
            'roe': self.roe,
            'roa': self.roa,
            'profit_margin': self.profit_margin,
            'operating_margin': self.operating_margin,
            'revenue_growth': self.revenue_growth,
            'earnings_growth': self.earnings_growth,
            'debt_to_equity': self.debt_to_equity,
            'current_ratio': self.current_ratio,
            'dividend_yield': self.dividend_yield
        }


@dataclass
class ComparisonResult:
    """비교 결과"""
    base_stock: StockMetrics
    compared_stocks: List[StockMetrics]
    rankings: Dict[str, List[Tuple[str, float, int]]]  # metric -> [(symbol, value, rank)]
    summary: Dict[str, str]

    def to_dict(self) -> Dict:
        return {
            'base_stock': self.base_stock.to_dict(),
            'compared_stocks': [s.to_dict() for s in self.compared_stocks],
            'rankings': self.rankings,
            'summary': self.summary
        }


class StockComparator:
    """종목 비교기"""

    # 업종별 대표 종목 (한국)
    KOREA_SECTOR_LEADERS = {
        '반도체': ['005930.KS', '000660.KS', '042700.KQ'],  # 삼성전자, SK하이닉스, 한미반도체
        '자동차': ['005380.KS', '000270.KS', '012330.KS'],  # 현대차, 기아, 현대모비스
        '화학': ['051910.KS', '010140.KS', '011170.KS'],    # LG화학, 삼성SDI, 롯데케미칼
        '금융': ['055550.KS', '105560.KS', '086790.KS'],    # 신한, KB, 하나
        '바이오': ['207940.KS', '068270.KS', '035720.KS'],  # 삼성바이오, 셀트리온, 카카오
        'IT': ['035420.KS', '035720.KS', '259960.KS'],      # 네이버, 카카오, 크래프톤
    }

    # 업종별 대표 종목 (미국)
    US_SECTOR_LEADERS = {
        'Technology': ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'META'],
        'Healthcare': ['UNH', 'JNJ', 'PFE', 'ABBV', 'MRK'],
        'Financials': ['JPM', 'BAC', 'GS', 'MS', 'WFC'],
        'Consumer': ['AMZN', 'TSLA', 'HD', 'NKE', 'MCD'],
        'Energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG'],
    }

    def __init__(self):
        self._cache: Dict[str, StockMetrics] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = 3600  # 1시간

    def get_metrics(self, symbol: str) -> Optional[StockMetrics]:
        """종목 지표 조회"""
        # 캐시 확인
        if symbol in self._cache_time:
            if datetime.now() - self._cache_time[symbol] < timedelta(seconds=self._cache_ttl):
                return self._cache.get(symbol)

        if not YFINANCE_AVAILABLE:
            return None

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            metrics = StockMetrics(
                symbol=symbol,
                name=info.get('shortName', symbol),
                sector=info.get('sector', 'N/A'),
                industry=info.get('industry', 'N/A'),
                market_cap=info.get('marketCap', 0) or 0,
                price=info.get('currentPrice', 0) or info.get('regularMarketPrice', 0) or 0,
                change_pct=info.get('regularMarketChangePercent', 0) or 0,

                per=info.get('trailingPE', 0) or info.get('forwardPE', 0) or 0,
                pbr=info.get('priceToBook', 0) or 0,
                psr=info.get('priceToSalesTrailing12Months', 0) or 0,
                ev_ebitda=info.get('enterpriseToEbitda', 0) or 0,

                roe=info.get('returnOnEquity', 0) or 0,
                roa=info.get('returnOnAssets', 0) or 0,
                profit_margin=info.get('profitMargins', 0) or 0,
                operating_margin=info.get('operatingMargins', 0) or 0,

                revenue_growth=info.get('revenueGrowth', 0) or 0,
                earnings_growth=info.get('earningsGrowth', 0) or 0,

                debt_to_equity=info.get('debtToEquity', 0) or 0,
                current_ratio=info.get('currentRatio', 0) or 0,

                dividend_yield=(info.get('dividendYield', 0) or 0) * 100
            )

            self._cache[symbol] = metrics
            self._cache_time[symbol] = datetime.now()

            return metrics

        except Exception as e:
            print(f"Metrics fetch error for {symbol}: {e}")
            return None

    def compare(self, base_symbol: str,
                compare_symbols: List[str] = None) -> Optional[ComparisonResult]:
        """종목 비교"""
        base_metrics = self.get_metrics(base_symbol)
        if not base_metrics:
            return None

        # 비교 종목이 없으면 같은 섹터에서 자동 선택
        if not compare_symbols:
            compare_symbols = self._get_sector_peers(base_symbol, base_metrics.sector)

        compared = []
        for symbol in compare_symbols:
            if symbol != base_symbol:
                metrics = self.get_metrics(symbol)
                if metrics:
                    compared.append(metrics)

        if not compared:
            return None

        # 순위 계산
        all_stocks = [base_metrics] + compared
        rankings = self._calculate_rankings(all_stocks)

        # 요약 생성
        summary = self._generate_summary(base_metrics, compared, rankings)

        return ComparisonResult(
            base_stock=base_metrics,
            compared_stocks=compared,
            rankings=rankings,
            summary=summary
        )

    def _get_sector_peers(self, symbol: str, sector: str) -> List[str]:
        """같은 섹터 종목 반환"""
        # 한국 주식
        if '.KS' in symbol or '.KQ' in symbol:
            for sector_name, symbols in self.KOREA_SECTOR_LEADERS.items():
                if symbol in symbols:
                    return [s for s in symbols if s != symbol][:4]
            # 기본값
            return ['005930.KS', '000660.KS', '035420.KS', '005380.KS']

        # 미국 주식
        for sector_name, symbols in self.US_SECTOR_LEADERS.items():
            if symbol in symbols or sector_name.lower() in sector.lower():
                return [s for s in symbols if s != symbol][:4]

        # 기본값
        return ['AAPL', 'MSFT', 'GOOGL', 'AMZN']

    def _calculate_rankings(self, stocks: List[StockMetrics]) -> Dict[str, List]:
        """지표별 순위 계산"""
        metrics_to_rank = {
            'per': ('낮을수록 좋음', False),
            'pbr': ('낮을수록 좋음', False),
            'roe': ('높을수록 좋음', True),
            'profit_margin': ('높을수록 좋음', True),
            'revenue_growth': ('높을수록 좋음', True),
            'dividend_yield': ('높을수록 좋음', True),
            'debt_to_equity': ('낮을수록 좋음', False),
        }

        rankings = {}

        for metric, (desc, higher_better) in metrics_to_rank.items():
            values = []
            for stock in stocks:
                value = getattr(stock, metric, 0)
                if value and value > 0:  # 유효한 값만
                    values.append((stock.symbol, value))

            # 정렬 (higher_better에 따라)
            sorted_values = sorted(values, key=lambda x: x[1], reverse=higher_better)

            # 순위 부여
            ranked = [(symbol, value, rank + 1) for rank, (symbol, value) in enumerate(sorted_values)]
            rankings[metric] = ranked

        return rankings

    def _generate_summary(self, base: StockMetrics,
                         compared: List[StockMetrics],
                         rankings: Dict) -> Dict[str, str]:
        """비교 요약 생성"""
        summary = {}

        # 밸류에이션 평가
        avg_per = sum(s.per for s in compared if s.per > 0) / len([s for s in compared if s.per > 0]) if compared else 0
        if base.per > 0 and avg_per > 0:
            if base.per < avg_per * 0.8:
                summary['valuation'] = f"PER {base.per:.1f}배로 동종업계 평균({avg_per:.1f}배) 대비 저평가"
            elif base.per > avg_per * 1.2:
                summary['valuation'] = f"PER {base.per:.1f}배로 동종업계 평균({avg_per:.1f}배) 대비 고평가"
            else:
                summary['valuation'] = f"PER {base.per:.1f}배로 동종업계 평균({avg_per:.1f}배) 수준"

        # 수익성 평가
        avg_roe = sum(s.roe for s in compared if s.roe > 0) / len([s for s in compared if s.roe > 0]) if compared else 0
        if base.roe > 0 and avg_roe > 0:
            if base.roe > avg_roe * 1.2:
                summary['profitability'] = f"ROE {base.roe*100:.1f}%로 업계 평균({avg_roe*100:.1f}%) 상회"
            elif base.roe < avg_roe * 0.8:
                summary['profitability'] = f"ROE {base.roe*100:.1f}%로 업계 평균({avg_roe*100:.1f}%) 하회"
            else:
                summary['profitability'] = f"ROE {base.roe*100:.1f}%로 업계 평균({avg_roe*100:.1f}%) 수준"

        # 성장성 평가
        if base.revenue_growth:
            if base.revenue_growth > 0.15:
                summary['growth'] = f"매출 성장률 {base.revenue_growth*100:.1f}%로 고성장"
            elif base.revenue_growth > 0:
                summary['growth'] = f"매출 성장률 {base.revenue_growth*100:.1f}%로 성장 지속"
            else:
                summary['growth'] = f"매출 성장률 {base.revenue_growth*100:.1f}%로 역성장"

        # 재무안정성 평가
        if base.debt_to_equity is not None:
            if base.debt_to_equity < 50:
                summary['stability'] = f"부채비율 {base.debt_to_equity:.0f}%로 재무구조 우량"
            elif base.debt_to_equity < 100:
                summary['stability'] = f"부채비율 {base.debt_to_equity:.0f}%로 재무구조 양호"
            else:
                summary['stability'] = f"부채비율 {base.debt_to_equity:.0f}%로 재무구조 주의"

        return summary

    def get_price_comparison(self, symbols: List[str],
                             period: str = "1y") -> Optional[pd.DataFrame]:
        """가격 추이 비교"""
        if not YFINANCE_AVAILABLE:
            return None

        try:
            prices = pd.DataFrame()

            for symbol in symbols:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=period)
                if not hist.empty:
                    # 시작일 기준 정규화 (100 = 시작가)
                    normalized = (hist['Close'] / hist['Close'].iloc[0]) * 100
                    prices[symbol] = normalized

            return prices

        except Exception as e:
            print(f"Price comparison error: {e}")
            return None

    def get_comparison_table(self, symbols: List[str]) -> pd.DataFrame:
        """비교 테이블 생성"""
        data = []

        for symbol in symbols:
            metrics = self.get_metrics(symbol)
            if metrics:
                data.append({
                    '종목': f"{metrics.name} ({symbol})",
                    '시가총액': f"{metrics.market_cap/1e12:.1f}조" if metrics.market_cap > 1e12 else f"{metrics.market_cap/1e8:.0f}억",
                    'PER': f"{metrics.per:.1f}" if metrics.per else "-",
                    'PBR': f"{metrics.pbr:.2f}" if metrics.pbr else "-",
                    'ROE': f"{metrics.roe*100:.1f}%" if metrics.roe else "-",
                    '영업이익률': f"{metrics.operating_margin*100:.1f}%" if metrics.operating_margin else "-",
                    '매출성장률': f"{metrics.revenue_growth*100:.1f}%" if metrics.revenue_growth else "-",
                    '부채비율': f"{metrics.debt_to_equity:.0f}%" if metrics.debt_to_equity else "-",
                    '배당수익률': f"{metrics.dividend_yield:.2f}%" if metrics.dividend_yield else "-",
                })

        return pd.DataFrame(data)


# 전역 인스턴스
stock_comparator = StockComparator()
