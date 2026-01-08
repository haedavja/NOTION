"""
한국은행 경제지표 모듈
BOK (Bank of Korea) 경제 데이터
"""

import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


@dataclass
class EconomicIndicator:
    """경제 지표"""
    name: str
    value: float
    unit: str
    date: str
    change: Optional[float] = None
    trend: Optional[str] = None


class BOKIndicators:
    """한국은행 경제지표 수집기"""

    def __init__(self, api_key: Optional[str] = None):
        """
        초기화

        Args:
            api_key: 한국은행 API 키 (없으면 환경변수 사용)
        """
        self.api_key = api_key or os.getenv('BOK_API_KEY')
        self.base_url = 'https://ecos.bok.or.kr/api'
        self.enabled = REQUESTS_AVAILABLE and bool(self.api_key)

        # 주요 지표 코드
        self.indicator_codes = {
            # 금리
            'base_rate': ('722Y001', '0101000', '기준금리'),
            'cd_rate': ('817Y002', '010502000', 'CD금리(91일)'),
            'treasury_3y': ('817Y002', '010200000', '국고채(3년)'),
            'treasury_10y': ('817Y002', '010200003', '국고채(10년)'),

            # 물가
            'cpi': ('901Y009', '*AA', '소비자물가지수'),
            'ppi': ('901Y010', '*AA', '생산자물가지수'),

            # 환율
            'usd_krw': ('731Y001', '0000001', '원/달러 환율'),
            'eur_krw': ('731Y001', '0000002', '원/유로 환율'),
            'jpy_krw': ('731Y001', '0000003', '원/엔 환율'),
            'cny_krw': ('731Y001', '0000004', '원/위안 환율'),

            # 통화
            'm1': ('101Y002', 'BBHA00', 'M1'),
            'm2': ('101Y002', 'BBHA01', 'M2'),

            # 경기
            'leading_index': ('901Y067', 'I16A', '경기선행지수'),
            'coincident_index': ('901Y067', 'I16B', '경기동행지수'),
            'business_sentiment': ('512Y007', '99988', '기업경기실사지수(BSI)'),

            # 고용
            'unemployment_rate': ('901Y027', '*AA', '실업률'),
            'employment_rate': ('901Y027', '*AB', '고용률'),

            # 무역
            'exports': ('301Y013', '*AA', '수출'),
            'imports': ('301Y013', '*AB', '수입'),
            'trade_balance': ('301Y013', '*AC', '무역수지'),
        }

    def _call_api(self, stat_code: str, item_code: str,
                  start_date: str, end_date: str,
                  period: str = 'M') -> Optional[List[Dict]]:
        """
        BOK API 호출

        Args:
            stat_code: 통계표 코드
            item_code: 항목 코드
            start_date: 시작일 (YYYYMM)
            end_date: 종료일 (YYYYMM)
            period: 주기 (D, M, Q, A)

        Returns:
            데이터 목록
        """
        if not self.enabled:
            return None

        try:
            url = f"{self.base_url}/StatisticSearch/{self.api_key}/json/kr/1/100"
            url += f"/{stat_code}/{period}/{start_date}/{end_date}/{item_code}"

            response = requests.get(url, timeout=10)
            data = response.json()

            if 'StatisticSearch' not in data:
                return None

            return data['StatisticSearch']['row']

        except Exception as e:
            print(f"BOK API 오류: {e}")
            return None

    def get_indicator(self, indicator_name: str,
                      months: int = 12) -> Optional[pd.DataFrame]:
        """
        지표 데이터 조회

        Args:
            indicator_name: 지표명 (indicator_codes 키)
            months: 조회 기간 (개월)

        Returns:
            지표 데이터프레임
        """
        if indicator_name not in self.indicator_codes:
            print(f"알 수 없는 지표: {indicator_name}")
            return None

        stat_code, item_code, _ = self.indicator_codes[indicator_name]

        end_date = datetime.now().strftime('%Y%m')
        start_date = (datetime.now() - timedelta(days=months*31)).strftime('%Y%m')

        data = self._call_api(stat_code, item_code, start_date, end_date)

        if data is None:
            return self._get_sample_indicator(indicator_name)

        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['TIME'], format='%Y%m')
        df['value'] = pd.to_numeric(df['DATA_VALUE'], errors='coerce')
        df = df[['date', 'value']].dropna()
        df = df.sort_values('date')

        return df

    def _get_sample_indicator(self, indicator_name: str) -> pd.DataFrame:
        """샘플 지표 데이터"""
        import numpy as np

        dates = pd.date_range(end=datetime.now(), periods=12, freq='M')

        base_values = {
            'base_rate': 3.5,
            'cpi': 102.5,
            'usd_krw': 1320,
            'unemployment_rate': 2.8,
            'leading_index': 100.5,
        }

        base = base_values.get(indicator_name, 100)
        np.random.seed(hash(indicator_name) % 2**32)
        values = base * (1 + np.cumsum(np.random.randn(12) * 0.01))

        return pd.DataFrame({'date': dates, 'value': values})

    def get_base_rate_history(self) -> pd.DataFrame:
        """기준금리 이력"""
        return self.get_indicator('base_rate', months=36) or self._get_sample_indicator('base_rate')

    def get_cpi_history(self) -> pd.DataFrame:
        """소비자물가지수 이력"""
        return self.get_indicator('cpi', months=24) or self._get_sample_indicator('cpi')

    def get_exchange_rates(self) -> Dict[str, float]:
        """현재 환율"""
        rates = {}

        for key in ['usd_krw', 'eur_krw', 'jpy_krw', 'cny_krw']:
            df = self.get_indicator(key, months=1)
            if df is not None and not df.empty:
                rates[key] = df['value'].iloc[-1]
            else:
                # 샘플 데이터
                sample_rates = {
                    'usd_krw': 1320,
                    'eur_krw': 1450,
                    'jpy_krw': 8.9,
                    'cny_krw': 185,
                }
                rates[key] = sample_rates.get(key, 0)

        return rates

    def get_economic_summary(self) -> Dict[str, EconomicIndicator]:
        """
        경제 지표 요약

        Returns:
            주요 지표 딕셔너리
        """
        summary = {}

        key_indicators = [
            'base_rate', 'cpi', 'usd_krw', 'unemployment_rate',
            'leading_index', 'trade_balance'
        ]

        units = {
            'base_rate': '%',
            'cpi': 'index',
            'usd_krw': '원',
            'unemployment_rate': '%',
            'leading_index': 'index',
            'trade_balance': '백만달러',
        }

        for name in key_indicators:
            df = self.get_indicator(name, months=3)

            if df is not None and len(df) >= 2:
                current = df['value'].iloc[-1]
                previous = df['value'].iloc[-2]
                change = current - previous

                if change > 0:
                    trend = '상승'
                elif change < 0:
                    trend = '하락'
                else:
                    trend = '보합'

                summary[name] = EconomicIndicator(
                    name=self.indicator_codes[name][2],
                    value=current,
                    unit=units.get(name, ''),
                    date=df['date'].iloc[-1].strftime('%Y-%m'),
                    change=change,
                    trend=trend,
                )
            else:
                # 샘플 데이터
                sample_values = {
                    'base_rate': 3.5,
                    'cpi': 102.8,
                    'usd_krw': 1320,
                    'unemployment_rate': 2.8,
                    'leading_index': 100.5,
                    'trade_balance': 4500,
                }
                summary[name] = EconomicIndicator(
                    name=self.indicator_codes[name][2],
                    value=sample_values.get(name, 0),
                    unit=units.get(name, ''),
                    date=datetime.now().strftime('%Y-%m'),
                    change=0,
                    trend='보합',
                )

        return summary

    def get_inflation_analysis(self) -> Dict:
        """
        인플레이션 분석

        Returns:
            인플레이션 분석 결과
        """
        cpi_df = self.get_indicator('cpi', months=24)
        ppi_df = self.get_indicator('ppi', months=24)

        if cpi_df is None or cpi_df.empty:
            return {
                'cpi_yoy': 2.5,
                'cpi_mom': 0.3,
                'ppi_yoy': 1.8,
                'trend': '안정적',
                'outlook': '물가 안정 추세',
            }

        # 전년 동월 대비
        if len(cpi_df) >= 13:
            cpi_yoy = (cpi_df['value'].iloc[-1] / cpi_df['value'].iloc[-13] - 1) * 100
        else:
            cpi_yoy = 0

        # 전월 대비
        if len(cpi_df) >= 2:
            cpi_mom = (cpi_df['value'].iloc[-1] / cpi_df['value'].iloc[-2] - 1) * 100
        else:
            cpi_mom = 0

        # PPI
        ppi_yoy = 0
        if ppi_df is not None and len(ppi_df) >= 13:
            ppi_yoy = (ppi_df['value'].iloc[-1] / ppi_df['value'].iloc[-13] - 1) * 100

        # 추세 판단
        if cpi_yoy > 3:
            trend = '인플레이션 압력'
            outlook = '물가 상승 압력이 높습니다. 금리 인상 가능성.'
        elif cpi_yoy > 2:
            trend = '적정 수준'
            outlook = '물가가 목표 수준 내에서 관리되고 있습니다.'
        elif cpi_yoy > 0:
            trend = '안정적'
            outlook = '물가 안정 추세입니다.'
        else:
            trend = '디플레이션 우려'
            outlook = '물가 하락으로 경기 침체 우려가 있습니다.'

        return {
            'cpi_yoy': round(cpi_yoy, 2),
            'cpi_mom': round(cpi_mom, 2),
            'ppi_yoy': round(ppi_yoy, 2),
            'trend': trend,
            'outlook': outlook,
        }

    def get_interest_rate_analysis(self) -> Dict:
        """
        금리 분석

        Returns:
            금리 분석 결과
        """
        base_rate_df = self.get_indicator('base_rate', months=36)
        treasury_3y_df = self.get_indicator('treasury_3y', months=12)
        treasury_10y_df = self.get_indicator('treasury_10y', months=12)

        base_rate = base_rate_df['value'].iloc[-1] if base_rate_df is not None and not base_rate_df.empty else 3.5
        rate_3y = treasury_3y_df['value'].iloc[-1] if treasury_3y_df is not None and not treasury_3y_df.empty else 3.2
        rate_10y = treasury_10y_df['value'].iloc[-1] if treasury_10y_df is not None and not treasury_10y_df.empty else 3.5

        # 수익률 곡선 분석
        spread_10y_3y = rate_10y - rate_3y

        if spread_10y_3y < 0:
            curve_shape = '역전'
            curve_signal = '경기 침체 신호'
        elif spread_10y_3y < 0.5:
            curve_shape = '평탄화'
            curve_signal = '경기 둔화 신호'
        else:
            curve_shape = '정상'
            curve_signal = '정상적인 경기 상황'

        # 금리 방향 예측
        if base_rate_df is not None and len(base_rate_df) >= 3:
            recent_trend = base_rate_df['value'].iloc[-3:].mean()
            if base_rate > recent_trend:
                rate_outlook = '인상 추세'
            elif base_rate < recent_trend:
                rate_outlook = '인하 추세'
            else:
                rate_outlook = '동결 예상'
        else:
            rate_outlook = '동결 예상'

        return {
            'base_rate': base_rate,
            'treasury_3y': rate_3y,
            'treasury_10y': rate_10y,
            'spread_10y_3y': round(spread_10y_3y, 2),
            'curve_shape': curve_shape,
            'curve_signal': curve_signal,
            'rate_outlook': rate_outlook,
        }

    def get_economic_cycle_indicator(self) -> Dict:
        """
        경기 사이클 지표

        Returns:
            경기 사이클 분석
        """
        leading_df = self.get_indicator('leading_index', months=12)
        coincident_df = self.get_indicator('coincident_index', months=12)

        leading = leading_df['value'].iloc[-1] if leading_df is not None and not leading_df.empty else 100
        coincident = coincident_df['value'].iloc[-1] if coincident_df is not None and not coincident_df.empty else 100

        # 선행지수 추세
        if leading_df is not None and len(leading_df) >= 6:
            leading_6m_ago = leading_df['value'].iloc[-6]
            leading_trend = (leading - leading_6m_ago) / leading_6m_ago * 100
        else:
            leading_trend = 0

        # 동행지수 추세
        if coincident_df is not None and len(coincident_df) >= 6:
            coincident_6m_ago = coincident_df['value'].iloc[-6]
            coincident_trend = (coincident - coincident_6m_ago) / coincident_6m_ago * 100
        else:
            coincident_trend = 0

        # 경기 국면 판단
        if leading_trend > 2 and coincident_trend > 1:
            phase = '확장'
            description = '경기가 상승 국면에 있습니다.'
        elif leading_trend > 0 and coincident_trend < 0:
            phase = '회복'
            description = '경기가 저점을 지나 회복 중입니다.'
        elif leading_trend < -2 and coincident_trend > 0:
            phase = '후퇴'
            description = '경기가 정점을 지나 하강 중입니다.'
        elif leading_trend < 0 and coincident_trend < -1:
            phase = '수축'
            description = '경기가 하락 국면에 있습니다.'
        else:
            phase = '전환'
            description = '경기 전환기입니다.'

        return {
            'leading_index': leading,
            'coincident_index': coincident,
            'leading_trend': round(leading_trend, 2),
            'coincident_trend': round(coincident_trend, 2),
            'phase': phase,
            'description': description,
        }

    def get_korean_economy_report(self) -> str:
        """
        한국 경제 리포트 생성

        Returns:
            리포트 텍스트
        """
        summary = self.get_economic_summary()
        inflation = self.get_inflation_analysis()
        rates = self.get_interest_rate_analysis()
        cycle = self.get_economic_cycle_indicator()
        exchange = self.get_exchange_rates()

        report = f"""
🇰🇷 한국 경제 리포트
{'='*50}
📅 {datetime.now().strftime('%Y년 %m월 %d일')}

📊 주요 경제지표
{'─'*50}
  기준금리: {summary.get('base_rate', EconomicIndicator('', 0, '', '')).value}%
  소비자물가: {inflation['cpi_yoy']:+.1f}% (전년 대비)
  실업률: {summary.get('unemployment_rate', EconomicIndicator('', 0, '', '')).value}%
  원/달러: {exchange.get('usd_krw', 0):,.0f}원

💹 물가 분석
{'─'*50}
  CPI 전년비: {inflation['cpi_yoy']:+.1f}%
  CPI 전월비: {inflation['cpi_mom']:+.1f}%
  PPI 전년비: {inflation['ppi_yoy']:+.1f}%
  추세: {inflation['trend']}
  전망: {inflation['outlook']}

📈 금리 분석
{'─'*50}
  기준금리: {rates['base_rate']}%
  국고채 3년: {rates['treasury_3y']}%
  국고채 10년: {rates['treasury_10y']}%
  장단기 스프레드: {rates['spread_10y_3y']}%p
  수익률 곡선: {rates['curve_shape']} ({rates['curve_signal']})
  금리 전망: {rates['rate_outlook']}

🔄 경기 사이클
{'─'*50}
  선행지수: {cycle['leading_index']:.1f} ({cycle['leading_trend']:+.1f}%)
  동행지수: {cycle['coincident_index']:.1f} ({cycle['coincident_trend']:+.1f}%)
  경기 국면: {cycle['phase']}
  설명: {cycle['description']}

💱 환율
{'─'*50}
  원/달러: {exchange.get('usd_krw', 0):,.0f}원
  원/유로: {exchange.get('eur_krw', 0):,.0f}원
  원/100엔: {exchange.get('jpy_krw', 0) * 100:,.0f}원
  원/위안: {exchange.get('cny_krw', 0):,.0f}원
"""
        return report

    def get_status(self) -> Dict:
        """상태 확인"""
        return {
            'bok_api_enabled': self.enabled,
            'api_key_set': bool(self.api_key),
            'requests_available': REQUESTS_AVAILABLE,
        }


# 사용 예시
def example_usage():
    """사용 예시"""
    bok = BOKIndicators()

    # 경제 리포트
    print(bok.get_korean_economy_report())

    # 개별 지표
    summary = bok.get_economic_summary()
    for name, indicator in summary.items():
        print(f"{indicator.name}: {indicator.value}{indicator.unit} ({indicator.trend})")
