"""
재무제표 분석
분기/연간 실적 비교, 밸류에이션 지표
"""

import pandas as pd
import numpy as np
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


@dataclass
class FinancialMetrics:
    """재무 지표"""
    # 수익성
    revenue: float = 0.0
    gross_profit: float = 0.0
    operating_income: float = 0.0
    net_income: float = 0.0
    gross_margin: float = 0.0
    operating_margin: float = 0.0
    net_margin: float = 0.0
    roe: float = 0.0  # 자기자본이익률
    roa: float = 0.0  # 총자산이익률

    # 성장성
    revenue_growth: float = 0.0
    earnings_growth: float = 0.0

    # 밸류에이션
    per: float = 0.0  # P/E Ratio
    pbr: float = 0.0  # P/B Ratio
    psr: float = 0.0  # P/S Ratio
    ev_ebitda: float = 0.0  # EV/EBITDA
    peg: float = 0.0  # PEG Ratio

    # 안정성
    debt_ratio: float = 0.0  # 부채비율
    current_ratio: float = 0.0  # 유동비율
    quick_ratio: float = 0.0  # 당좌비율

    # 배당
    dividend_yield: float = 0.0
    payout_ratio: float = 0.0

    # 효율성
    asset_turnover: float = 0.0
    inventory_turnover: float = 0.0


@dataclass
class CompanyProfile:
    """회사 프로필"""
    symbol: str
    name: str
    sector: str = ""
    industry: str = ""
    market_cap: float = 0.0
    employees: int = 0
    description: str = ""
    website: str = ""
    country: str = ""


@dataclass
class FinancialAnalysisResult:
    """재무 분석 결과"""
    symbol: str
    name: str
    profile: CompanyProfile
    current_metrics: FinancialMetrics
    historical_data: Dict[str, Any] = field(default_factory=dict)
    peer_comparison: Dict[str, Any] = field(default_factory=dict)
    valuation_grade: str = ""  # A, B, C, D, F
    health_score: float = 0.0  # 0-100
    analysis_date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))


class FinancialAnalyzer:
    """재무제표 분석기"""

    # 섹터별 평균 지표 (대략적인 값)
    SECTOR_AVERAGES = {
        "Technology": {"per": 25, "pbr": 5, "roe": 15, "gross_margin": 50},
        "Healthcare": {"per": 20, "pbr": 4, "roe": 12, "gross_margin": 60},
        "Financial Services": {"per": 12, "pbr": 1.2, "roe": 10, "gross_margin": 40},
        "Consumer Cyclical": {"per": 18, "pbr": 3, "roe": 15, "gross_margin": 35},
        "Industrials": {"per": 18, "pbr": 3, "roe": 12, "gross_margin": 30},
        "Energy": {"per": 10, "pbr": 1.5, "roe": 8, "gross_margin": 25},
        "default": {"per": 15, "pbr": 2, "roe": 12, "gross_margin": 35}
    }

    def __init__(self):
        pass

    def analyze(self, symbol: str) -> Optional[FinancialAnalysisResult]:
        """재무 분석 실행"""
        if not YFINANCE_AVAILABLE:
            return None

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            if not info:
                return None

            # 프로필
            profile = self._get_profile(symbol, info)

            # 현재 지표
            metrics = self._calculate_metrics(ticker, info)

            # 히스토리컬 데이터
            historical = self._get_historical_data(ticker)

            # 밸류에이션 등급
            grade = self._calculate_valuation_grade(metrics, profile.sector)

            # 건강 점수
            health = self._calculate_health_score(metrics)

            return FinancialAnalysisResult(
                symbol=symbol,
                name=profile.name,
                profile=profile,
                current_metrics=metrics,
                historical_data=historical,
                valuation_grade=grade,
                health_score=health
            )

        except Exception as e:
            print(f"분석 실패: {e}")
            return None

    def _get_profile(self, symbol: str, info: Dict) -> CompanyProfile:
        """회사 프로필 추출"""
        return CompanyProfile(
            symbol=symbol,
            name=info.get('longName', info.get('shortName', symbol)),
            sector=info.get('sector', ''),
            industry=info.get('industry', ''),
            market_cap=info.get('marketCap', 0),
            employees=info.get('fullTimeEmployees', 0),
            description=info.get('longBusinessSummary', '')[:500],
            website=info.get('website', ''),
            country=info.get('country', '')
        )

    def _calculate_metrics(self, ticker, info: Dict) -> FinancialMetrics:
        """재무 지표 계산"""
        metrics = FinancialMetrics()

        # 수익성
        metrics.revenue = info.get('totalRevenue', 0) or 0
        metrics.gross_profit = info.get('grossProfits', 0) or 0
        metrics.operating_income = info.get('operatingCashflow', 0) or 0
        metrics.net_income = info.get('netIncomeToCommon', 0) or 0

        if metrics.revenue > 0:
            metrics.gross_margin = (metrics.gross_profit / metrics.revenue) * 100
            metrics.net_margin = (metrics.net_income / metrics.revenue) * 100

        metrics.operating_margin = (info.get('operatingMargins', 0) or 0) * 100
        metrics.roe = (info.get('returnOnEquity', 0) or 0) * 100
        metrics.roa = (info.get('returnOnAssets', 0) or 0) * 100

        # 성장성
        metrics.revenue_growth = (info.get('revenueGrowth', 0) or 0) * 100
        metrics.earnings_growth = (info.get('earningsGrowth', 0) or 0) * 100

        # 밸류에이션
        metrics.per = info.get('forwardPE', info.get('trailingPE', 0)) or 0
        metrics.pbr = info.get('priceToBook', 0) or 0
        metrics.psr = info.get('priceToSalesTrailing12Months', 0) or 0
        metrics.ev_ebitda = info.get('enterpriseToEbitda', 0) or 0
        metrics.peg = info.get('pegRatio', 0) or 0

        # 안정성
        metrics.debt_ratio = (info.get('debtToEquity', 0) or 0)
        metrics.current_ratio = info.get('currentRatio', 0) or 0
        metrics.quick_ratio = info.get('quickRatio', 0) or 0

        # 배당
        metrics.dividend_yield = (info.get('dividendYield', 0) or 0) * 100
        metrics.payout_ratio = (info.get('payoutRatio', 0) or 0) * 100

        return metrics

    def _get_historical_data(self, ticker) -> Dict[str, Any]:
        """히스토리컬 데이터"""
        try:
            # 손익계산서
            income_stmt = ticker.income_stmt
            balance_sheet = ticker.balance_sheet
            cash_flow = ticker.cashflow

            result = {
                'income_statement': {},
                'balance_sheet': {},
                'cash_flow': {}
            }

            if income_stmt is not None and not income_stmt.empty:
                result['income_statement'] = {
                    'dates': [str(d.date()) for d in income_stmt.columns],
                    'revenue': income_stmt.loc['Total Revenue'].tolist() if 'Total Revenue' in income_stmt.index else [],
                    'net_income': income_stmt.loc['Net Income'].tolist() if 'Net Income' in income_stmt.index else []
                }

            if balance_sheet is not None and not balance_sheet.empty:
                result['balance_sheet'] = {
                    'dates': [str(d.date()) for d in balance_sheet.columns],
                    'total_assets': balance_sheet.loc['Total Assets'].tolist() if 'Total Assets' in balance_sheet.index else [],
                    'total_debt': balance_sheet.loc['Total Debt'].tolist() if 'Total Debt' in balance_sheet.index else []
                }

            if cash_flow is not None and not cash_flow.empty:
                result['cash_flow'] = {
                    'dates': [str(d.date()) for d in cash_flow.columns],
                    'operating_cf': cash_flow.loc['Operating Cash Flow'].tolist() if 'Operating Cash Flow' in cash_flow.index else [],
                    'free_cf': cash_flow.loc['Free Cash Flow'].tolist() if 'Free Cash Flow' in cash_flow.index else []
                }

            return result

        except Exception:
            return {}

    def _calculate_valuation_grade(self, metrics: FinancialMetrics,
                                    sector: str) -> str:
        """밸류에이션 등급 계산"""
        avg = self.SECTOR_AVERAGES.get(sector, self.SECTOR_AVERAGES["default"])
        score = 0

        # PER 평가
        if metrics.per > 0:
            if metrics.per < avg['per'] * 0.7:
                score += 2  # 저평가
            elif metrics.per < avg['per']:
                score += 1
            elif metrics.per > avg['per'] * 1.5:
                score -= 1  # 고평가

        # PBR 평가
        if metrics.pbr > 0:
            if metrics.pbr < avg['pbr'] * 0.7:
                score += 2
            elif metrics.pbr < avg['pbr']:
                score += 1
            elif metrics.pbr > avg['pbr'] * 1.5:
                score -= 1

        # ROE 평가
        if metrics.roe > avg['roe'] * 1.3:
            score += 2
        elif metrics.roe > avg['roe']:
            score += 1
        elif metrics.roe < avg['roe'] * 0.5:
            score -= 1

        # 등급 결정
        if score >= 5:
            return "A"
        elif score >= 3:
            return "B"
        elif score >= 1:
            return "C"
        elif score >= -1:
            return "D"
        else:
            return "F"

    def _calculate_health_score(self, metrics: FinancialMetrics) -> float:
        """재무 건강 점수 (0-100)"""
        score = 50  # 기본 점수

        # 수익성 (최대 +20)
        if metrics.net_margin > 20:
            score += 20
        elif metrics.net_margin > 10:
            score += 15
        elif metrics.net_margin > 5:
            score += 10
        elif metrics.net_margin > 0:
            score += 5

        # ROE (최대 +15)
        if metrics.roe > 20:
            score += 15
        elif metrics.roe > 15:
            score += 10
        elif metrics.roe > 10:
            score += 5

        # 부채 (최대 +15)
        if metrics.debt_ratio < 50:
            score += 15
        elif metrics.debt_ratio < 100:
            score += 10
        elif metrics.debt_ratio < 150:
            score += 5
        elif metrics.debt_ratio > 200:
            score -= 10

        # 유동성 (최대 +10)
        if metrics.current_ratio > 2:
            score += 10
        elif metrics.current_ratio > 1.5:
            score += 7
        elif metrics.current_ratio > 1:
            score += 3
        elif metrics.current_ratio < 1:
            score -= 5

        # 성장성 (최대 +10)
        if metrics.revenue_growth > 20:
            score += 10
        elif metrics.revenue_growth > 10:
            score += 7
        elif metrics.revenue_growth > 0:
            score += 3
        elif metrics.revenue_growth < -10:
            score -= 5

        return max(0, min(100, score))

    def compare_peers(self, symbol: str, peers: List[str] = None) -> pd.DataFrame:
        """동종 업계 비교"""
        if not YFINANCE_AVAILABLE:
            return pd.DataFrame()

        try:
            main_ticker = yf.Ticker(symbol)
            main_info = main_ticker.info

            # 피어 자동 선택 (같은 섹터)
            if not peers:
                # yfinance에서 추천 종목 활용
                peers = main_info.get('recommendedSymbols', [])[:5]

            all_symbols = [symbol] + peers
            comparison_data = []

            for sym in all_symbols[:6]:  # 최대 6개
                try:
                    ticker = yf.Ticker(sym)
                    info = ticker.info

                    comparison_data.append({
                        '종목': info.get('shortName', sym),
                        '심볼': sym,
                        '시가총액(B)': (info.get('marketCap', 0) or 0) / 1e9,
                        'PER': info.get('forwardPE', 0) or 0,
                        'PBR': info.get('priceToBook', 0) or 0,
                        'ROE(%)': (info.get('returnOnEquity', 0) or 0) * 100,
                        '매출성장(%)': (info.get('revenueGrowth', 0) or 0) * 100,
                        '영업이익률(%)': (info.get('operatingMargins', 0) or 0) * 100,
                        '배당수익률(%)': (info.get('dividendYield', 0) or 0) * 100
                    })
                except Exception:
                    continue

            return pd.DataFrame(comparison_data)

        except Exception:
            return pd.DataFrame()

    def get_valuation_summary(self, symbol: str) -> Dict[str, Any]:
        """밸류에이션 요약"""
        result = self.analyze(symbol)
        if not result:
            return {}

        m = result.current_metrics

        return {
            'symbol': symbol,
            'name': result.name,
            'grade': result.valuation_grade,
            'health_score': result.health_score,
            'metrics': {
                'PER': m.per,
                'PBR': m.pbr,
                'PSR': m.psr,
                'EV/EBITDA': m.ev_ebitda,
                'ROE': m.roe,
                'ROA': m.roa,
                '매출성장률': m.revenue_growth,
                '순이익률': m.net_margin,
                '부채비율': m.debt_ratio,
                '배당수익률': m.dividend_yield
            },
            'sector': result.profile.sector,
            'market_cap': result.profile.market_cap
        }


# 싱글톤 인스턴스
financial_analyzer = FinancialAnalyzer()


def analyze_financials(symbol: str) -> Optional[FinancialAnalysisResult]:
    """재무 분석"""
    return financial_analyzer.analyze(symbol)


def compare_companies(symbol: str, peers: List[str] = None) -> pd.DataFrame:
    """회사 비교"""
    return financial_analyzer.compare_peers(symbol, peers)


def get_valuation(symbol: str) -> Dict[str, Any]:
    """밸류에이션 조회"""
    return financial_analyzer.get_valuation_summary(symbol)
