"""
자금 흐름 추적 모듈
ETF 자금 유출입, 섹터 로테이션을 추적합니다.
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


class FundFlowTracker:
    """자금 흐름 추적 클래스"""

    # 주요 ETF와 자산군 매핑
    FLOW_ETFS = {
        # 주식
        'spy': {'name': 'S&P 500', 'asset_class': 'equity', 'region': 'us'},
        'qqq': {'name': 'Nasdaq 100', 'asset_class': 'equity', 'region': 'us'},
        'iwm': {'name': 'Russell 2000', 'asset_class': 'equity', 'region': 'us'},
        'eem': {'name': 'Emerging Markets', 'asset_class': 'equity', 'region': 'em'},
        'efa': {'name': 'Developed Intl', 'asset_class': 'equity', 'region': 'intl'},

        # 채권
        'tlt': {'name': 'Long Treasury', 'asset_class': 'bond', 'duration': 'long'},
        'ief': {'name': 'Mid Treasury', 'asset_class': 'bond', 'duration': 'mid'},
        'shy': {'name': 'Short Treasury', 'asset_class': 'bond', 'duration': 'short'},
        'lqd': {'name': 'Corp Bond', 'asset_class': 'bond', 'credit': 'ig'},
        'hyg': {'name': 'High Yield', 'asset_class': 'bond', 'credit': 'hy'},

        # 원자재
        'gld': {'name': 'Gold', 'asset_class': 'commodity', 'type': 'precious'},
        'slv': {'name': 'Silver', 'asset_class': 'commodity', 'type': 'precious'},
        'uso': {'name': 'Oil', 'asset_class': 'commodity', 'type': 'energy'},

        # 섹터
        'xlk': {'name': 'Technology', 'asset_class': 'sector', 'sector': 'tech'},
        'xlf': {'name': 'Financials', 'asset_class': 'sector', 'sector': 'financials'},
        'xle': {'name': 'Energy', 'asset_class': 'sector', 'sector': 'energy'},
        'xlv': {'name': 'Healthcare', 'asset_class': 'sector', 'sector': 'healthcare'},
        'xlu': {'name': 'Utilities', 'asset_class': 'sector', 'sector': 'utilities'},
    }

    def __init__(self):
        """초기화"""
        pass

    def estimate_flow_from_volume(self, symbol: str,
                                  period: str = '3mo') -> pd.DataFrame:
        """
        거래량과 가격 변화로 자금 흐름 추정

        실제 자금 흐름 데이터는 유료이므로,
        거래량 * 가격변화 방향으로 추정

        Args:
            symbol: ETF 티커
            period: 기간

        Returns:
            추정 자금 흐름 데이터프레임
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance가 필요합니다.")

        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)

        # 가격 변화 방향
        price_change = data['Close'].diff()
        direction = np.sign(price_change)

        # 거래대금 (거래량 * 평균가)
        avg_price = (data['High'] + data['Low']) / 2
        dollar_volume = data['Volume'] * avg_price

        # 추정 자금 흐름 = 방향 * 거래대금의 일부
        estimated_flow = direction * dollar_volume * 0.1  # 10% 가정

        result = pd.DataFrame({
            'close': data['Close'],
            'volume': data['Volume'],
            'dollar_volume': dollar_volume,
            'estimated_flow': estimated_flow,
            'cumulative_flow': estimated_flow.cumsum(),
        })

        return result

    def get_sector_rotation(self, period: str = '6mo') -> pd.DataFrame:
        """
        섹터 로테이션 분석

        Returns:
            섹터별 성과와 모멘텀 데이터
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance가 필요합니다.")

        sector_etfs = ['XLK', 'XLF', 'XLE', 'XLV', 'XLU', 'XLI', 'XLY', 'XLP', 'XLB', 'XLRE', 'XLC']
        sector_names = ['Technology', 'Financials', 'Energy', 'Healthcare', 'Utilities',
                       'Industrials', 'Consumer Disc', 'Consumer Staples', 'Materials',
                       'Real Estate', 'Communication']

        # 데이터 수집
        data = yf.download(sector_etfs, period=period, progress=False)['Close']

        # 수익률 계산
        returns_1m = data.pct_change(21).iloc[-1]    # 1개월
        returns_3m = data.pct_change(63).iloc[-1]    # 3개월
        returns_6m = data.pct_change(126).iloc[-1]   # 6개월

        # 모멘텀 점수 (가중 평균)
        momentum = 0.5 * returns_1m + 0.3 * returns_3m + 0.2 * returns_6m

        # 변동성
        volatility = data.pct_change().rolling(21).std().iloc[-1] * np.sqrt(252)

        result = pd.DataFrame({
            'sector': sector_names,
            'etf': sector_etfs,
            'return_1m': returns_1m.values,
            'return_3m': returns_3m.values,
            'return_6m': returns_6m.values,
            'momentum_score': momentum.values,
            'volatility': volatility.values,
        })

        result = result.sort_values('momentum_score', ascending=False)

        return result

    def analyze_risk_appetite(self, period: str = '3mo') -> Dict:
        """
        시장 위험 선호도 분석

        위험자산 vs 안전자산 비교를 통해
        현재 시장의 위험 선호도를 분석

        Returns:
            위험 선호도 지표들
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance가 필요합니다.")

        # 위험자산 vs 안전자산 쌍
        pairs = {
            'stock_vs_bond': ('SPY', 'TLT'),
            'high_yield_vs_treasury': ('HYG', 'IEF'),
            'small_vs_large': ('IWM', 'SPY'),
            'em_vs_dm': ('EEM', 'EFA'),
            'growth_vs_value': ('IWF', 'IWD'),
            'cyclical_vs_defensive': ('XLY', 'XLP'),
        }

        results = {}

        for name, (risk_asset, safe_asset) in pairs.items():
            try:
                data = yf.download([risk_asset, safe_asset], period=period, progress=False)['Close']

                # 상대 성과
                ratio = data[risk_asset] / data[safe_asset]
                ratio_change = ratio.pct_change(21).iloc[-1]  # 1개월 변화

                results[name] = {
                    'risk_asset': risk_asset,
                    'safe_asset': safe_asset,
                    'relative_performance_1m': ratio_change,
                    'risk_on': ratio_change > 0,
                }
            except Exception as e:
                print(f"Warning: {name} 분석 실패 - {e}")

        # 종합 위험 선호도 점수
        risk_on_count = sum(1 for r in results.values() if r.get('risk_on', False))
        total_pairs = len(results)

        risk_appetite_score = risk_on_count / total_pairs if total_pairs > 0 else 0.5

        return {
            'pairs': results,
            'risk_appetite_score': risk_appetite_score,
            'market_regime': 'Risk-On' if risk_appetite_score > 0.5 else 'Risk-Off',
        }

    def get_money_flow_summary(self) -> Dict:
        """
        자금 흐름 요약

        Returns:
            자산군별 자금 흐름 요약
        """
        if not YFINANCE_AVAILABLE:
            raise ImportError("yfinance가 필요합니다.")

        summary = {
            'equities': {},
            'bonds': {},
            'commodities': {},
            'sectors': {},
        }

        for etf, info in self.FLOW_ETFS.items():
            try:
                flow_data = self.estimate_flow_from_volume(etf.upper(), '1mo')

                asset_class = info['asset_class']
                if asset_class == 'equity':
                    summary['equities'][info['name']] = {
                        'cumulative_flow': flow_data['cumulative_flow'].iloc[-1],
                        'recent_trend': 'Inflow' if flow_data['estimated_flow'].tail(5).sum() > 0 else 'Outflow',
                    }
                elif asset_class == 'bond':
                    summary['bonds'][info['name']] = {
                        'cumulative_flow': flow_data['cumulative_flow'].iloc[-1],
                        'recent_trend': 'Inflow' if flow_data['estimated_flow'].tail(5).sum() > 0 else 'Outflow',
                    }
                elif asset_class == 'commodity':
                    summary['commodities'][info['name']] = {
                        'cumulative_flow': flow_data['cumulative_flow'].iloc[-1],
                        'recent_trend': 'Inflow' if flow_data['estimated_flow'].tail(5).sum() > 0 else 'Outflow',
                    }
                elif asset_class == 'sector':
                    summary['sectors'][info['name']] = {
                        'cumulative_flow': flow_data['cumulative_flow'].iloc[-1],
                        'recent_trend': 'Inflow' if flow_data['estimated_flow'].tail(5).sum() > 0 else 'Outflow',
                    }
            except Exception as e:
                print(f"Warning: {etf} 분석 실패 - {e}")

        return summary


# 샘플 데이터 생성
def get_sample_fund_flow() -> pd.DataFrame:
    """테스트용 샘플 자금 흐름 데이터"""
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='B')

    np.random.seed(42)

    # 섹터별 자금 흐름 시뮬레이션
    sectors = ['Technology', 'Healthcare', 'Financials', 'Energy',
               'Utilities', 'Consumer', 'Industrials']

    data = {}
    for sector in sectors:
        # 랜덤 워크 + 트렌드
        trend = np.random.choice([-1, 0, 1]) * 0.001
        flow = np.random.normal(trend, 0.02, len(dates))
        cumulative = np.cumsum(flow) * 1e9  # 10억 단위
        data[sector] = cumulative

    df = pd.DataFrame(data, index=dates)
    return df
