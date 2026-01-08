"""
거시경제 지표 수집 모듈
FRED API를 통해 주요 경제 지표를 수집합니다.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional
import os

try:
    from fredapi import Fred
    FRED_AVAILABLE = True
except ImportError:
    FRED_AVAILABLE = False


class MacroIndicators:
    """거시경제 지표 수집 클래스"""

    # 주요 FRED 시리즈 ID
    INDICATORS = {
        # 금리
        'fed_funds_rate': 'FEDFUNDS',           # 연방기금금리
        'treasury_10y': 'DGS10',                # 10년 국채 수익률
        'treasury_2y': 'DGS2',                  # 2년 국채 수익률
        'treasury_3m': 'DTB3',                  # 3개월 국채

        # 인플레이션
        'cpi': 'CPIAUCSL',                      # 소비자물가지수
        'core_cpi': 'CPILFESL',                 # 근원 CPI
        'pce': 'PCEPI',                         # 개인소비지출 물가지수
        'ppi': 'PPIACO',                        # 생산자물가지수

        # 고용
        'unemployment_rate': 'UNRATE',          # 실업률
        'nonfarm_payroll': 'PAYEMS',            # 비농업 고용
        'initial_claims': 'ICSA',               # 신규 실업수당 청구
        'labor_participation': 'CIVPART',       # 경제활동참가율

        # 경제 성장
        'gdp': 'GDP',                           # GDP
        'real_gdp': 'GDPC1',                    # 실질 GDP
        'industrial_production': 'INDPRO',      # 산업생산지수

        # 소비/심리
        'retail_sales': 'RSXFS',                # 소매판매
        'consumer_sentiment': 'UMCSENT',        # 소비자심리지수
        'personal_income': 'PI',                # 개인소득

        # 주택
        'housing_starts': 'HOUST',              # 주택착공
        'existing_home_sales': 'EXHOSLUSM495S', # 기존주택판매

        # 통화/신용
        'm2': 'M2SL',                           # M2 통화량
        'bank_credit': 'TOTBKCR',               # 은행 신용

        # 금융 스트레스
        'vix': 'VIXCLS',                        # VIX 지수
        'financial_stress': 'STLFSI4',          # 금융스트레스지수
        'yield_spread': 'T10Y2Y',               # 장단기 금리차
    }

    # 지표별 카테고리
    CATEGORIES = {
        'interest_rates': ['fed_funds_rate', 'treasury_10y', 'treasury_2y', 'treasury_3m'],
        'inflation': ['cpi', 'core_cpi', 'pce', 'ppi'],
        'employment': ['unemployment_rate', 'nonfarm_payroll', 'initial_claims', 'labor_participation'],
        'growth': ['gdp', 'real_gdp', 'industrial_production'],
        'consumption': ['retail_sales', 'consumer_sentiment', 'personal_income'],
        'housing': ['housing_starts', 'existing_home_sales'],
        'monetary': ['m2', 'bank_credit'],
        'financial_stress': ['vix', 'financial_stress', 'yield_spread'],
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        초기화

        Args:
            api_key: FRED API 키 (없으면 환경변수 FRED_API_KEY 사용)
        """
        self.api_key = api_key or os.getenv('FRED_API_KEY')
        self.fred = None

        if FRED_AVAILABLE and self.api_key:
            self.fred = Fred(api_key=self.api_key)

    def get_indicator(self, indicator_name: str,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> pd.Series:
        """
        단일 지표 데이터 수집

        Args:
            indicator_name: 지표 이름 (INDICATORS 키 값)
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)

        Returns:
            지표 시계열 데이터
        """
        if not self.fred:
            raise ValueError("FRED API가 설정되지 않았습니다. API 키를 확인하세요.")

        if indicator_name not in self.INDICATORS:
            raise ValueError(f"알 수 없는 지표: {indicator_name}")

        series_id = self.INDICATORS[indicator_name]

        if not start_date:
            start_date = (datetime.now() - timedelta(days=365*5)).strftime('%Y-%m-%d')
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')

        data = self.fred.get_series(series_id, start_date, end_date)
        data.name = indicator_name

        return data

    def get_category(self, category: str,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None) -> pd.DataFrame:
        """
        카테고리별 모든 지표 수집

        Args:
            category: 카테고리 이름
            start_date: 시작일
            end_date: 종료일

        Returns:
            카테고리 내 모든 지표 데이터프레임
        """
        if category not in self.CATEGORIES:
            raise ValueError(f"알 수 없는 카테고리: {category}")

        indicators = self.CATEGORIES[category]
        data = {}

        for indicator in indicators:
            try:
                data[indicator] = self.get_indicator(indicator, start_date, end_date)
            except Exception as e:
                print(f"Warning: {indicator} 수집 실패 - {e}")

        return pd.DataFrame(data)

    def get_all_indicators(self, start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> pd.DataFrame:
        """
        모든 지표 수집

        Returns:
            전체 지표 데이터프레임
        """
        data = {}

        for indicator_name in self.INDICATORS.keys():
            try:
                data[indicator_name] = self.get_indicator(indicator_name, start_date, end_date)
            except Exception as e:
                print(f"Warning: {indicator_name} 수집 실패 - {e}")

        return pd.DataFrame(data)

    def get_latest_values(self) -> Dict[str, float]:
        """
        모든 지표의 최신 값 조회

        Returns:
            지표별 최신 값 딕셔너리
        """
        latest = {}

        for indicator_name in self.INDICATORS.keys():
            try:
                series = self.get_indicator(indicator_name)
                latest[indicator_name] = series.dropna().iloc[-1]
            except Exception as e:
                print(f"Warning: {indicator_name} 최신값 조회 실패 - {e}")

        return latest

    def calculate_yield_curve(self) -> pd.DataFrame:
        """
        수익률 곡선 계산

        Returns:
            각 만기별 수익률 데이터
        """
        maturities = {
            '3M': 'treasury_3m',
            '2Y': 'treasury_2y',
            '10Y': 'treasury_10y',
        }

        data = {}
        for maturity, indicator in maturities.items():
            try:
                data[maturity] = self.get_indicator(indicator)
            except Exception:
                pass

        return pd.DataFrame(data)

    def get_recession_indicators(self) -> pd.DataFrame:
        """
        경기침체 예측 지표 수집

        Returns:
            경기침체 관련 지표들
        """
        recession_indicators = [
            'yield_spread',      # 장단기 금리차 (역전 시 경기침체 신호)
            'unemployment_rate', # 실업률
            'initial_claims',    # 신규 실업수당
            'industrial_production',
            'consumer_sentiment',
        ]

        data = {}
        for indicator in recession_indicators:
            try:
                data[indicator] = self.get_indicator(indicator)
            except Exception as e:
                print(f"Warning: {indicator} 수집 실패 - {e}")

        return pd.DataFrame(data)


# 샘플 데이터 (API 없이 테스트용)
def get_sample_macro_data() -> pd.DataFrame:
    """API 없이 테스트용 샘플 데이터 생성"""
    dates = pd.date_range(start='2020-01-01', end='2024-12-31', freq='M')

    import numpy as np
    np.random.seed(42)

    data = {
        'fed_funds_rate': np.concatenate([
            np.linspace(1.75, 0.25, 12),  # 2020: 금리 인하
            np.full(12, 0.25),             # 2021: 제로금리
            np.linspace(0.25, 4.5, 12),    # 2022: 급격한 인상
            np.linspace(4.5, 5.5, 12),     # 2023: 고금리 유지
            np.linspace(5.5, 4.5, 12),     # 2024: 금리 인하 시작
        ]),
        'cpi': np.concatenate([
            np.linspace(2.5, 1.2, 12),     # 2020
            np.linspace(1.4, 7.0, 12),     # 2021
            np.linspace(7.5, 6.5, 12),     # 2022
            np.linspace(6.4, 3.1, 12),     # 2023
            np.linspace(3.0, 2.5, 12),     # 2024
        ]),
        'unemployment_rate': np.concatenate([
            np.concatenate([np.linspace(3.5, 14.7, 4), np.linspace(13.0, 6.7, 8)]),  # 2020
            np.linspace(6.7, 3.9, 12),     # 2021
            np.linspace(4.0, 3.5, 12),     # 2022
            np.linspace(3.4, 3.7, 12),     # 2023
            np.linspace(3.7, 4.2, 12),     # 2024
        ]),
        'treasury_10y': np.concatenate([
            np.linspace(1.9, 0.9, 12),     # 2020
            np.linspace(1.0, 1.5, 12),     # 2021
            np.linspace(1.6, 3.9, 12),     # 2022
            np.linspace(3.8, 3.9, 12),     # 2023
            np.linspace(4.0, 4.2, 12),     # 2024
        ]),
        'yield_spread': np.concatenate([
            np.linspace(0.3, 0.5, 12),     # 2020
            np.linspace(0.8, 1.0, 12),     # 2021
            np.linspace(0.5, -0.5, 12),    # 2022: 역전 시작
            np.linspace(-0.5, -0.3, 12),   # 2023: 역전 지속
            np.linspace(-0.2, 0.1, 12),    # 2024: 정상화
        ]),
    }

    df = pd.DataFrame(data, index=dates[:len(data['fed_funds_rate'])])
    return df
