"""
한국 주식 분석 모듈
개별 종목 및 포트폴리오 분석
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd
import numpy as np

from .krx_data import KRXDataCollector

try:
    from pykrx import stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False


@dataclass
class StockFundamentals:
    """펀더멘털 데이터"""
    code: str
    name: str
    price: float
    market_cap: float
    per: Optional[float]
    pbr: Optional[float]
    eps: Optional[float]
    bps: Optional[float]
    dividend_yield: Optional[float]
    roe: Optional[float]


@dataclass
class StockAnalysis:
    """종목 분석 결과"""
    code: str
    name: str
    fundamentals: StockFundamentals
    technical: Dict
    foreign_trend: Dict
    recommendation: str
    score: float


class KoreanStockAnalyzer:
    """한국 주식 분석기"""

    def __init__(self):
        """초기화"""
        self.data_collector = KRXDataCollector()
        self.enabled = PYKRX_AVAILABLE

    def get_fundamentals(self, code: str) -> Optional[StockFundamentals]:
        """
        펀더멘털 데이터 조회

        Args:
            code: 종목 코드

        Returns:
            펀더멘털 데이터
        """
        if not self.enabled:
            return self._get_sample_fundamentals(code)

        try:
            today = datetime.now().strftime('%Y%m%d')
            name = stock.get_market_ticker_name(code)

            # 현재가
            ohlcv = stock.get_market_ohlcv_by_date(today, today, code)
            price = ohlcv['종가'].iloc[-1] if not ohlcv.empty else 0

            # 시가총액
            cap_info = self.data_collector.get_market_cap(code)
            market_cap = cap_info['market_cap'] if cap_info else 0

            # 투자지표 (PER, PBR, EPS, BPS, DIV)
            fundamental = stock.get_market_fundamental_by_date(today, today, code)

            if fundamental.empty:
                return StockFundamentals(
                    code=code, name=name, price=price,
                    market_cap=market_cap, per=None, pbr=None,
                    eps=None, bps=None, dividend_yield=None, roe=None
                )

            return StockFundamentals(
                code=code,
                name=name,
                price=price,
                market_cap=market_cap,
                per=fundamental['PER'].iloc[-1] if 'PER' in fundamental.columns else None,
                pbr=fundamental['PBR'].iloc[-1] if 'PBR' in fundamental.columns else None,
                eps=fundamental['EPS'].iloc[-1] if 'EPS' in fundamental.columns else None,
                bps=fundamental['BPS'].iloc[-1] if 'BPS' in fundamental.columns else None,
                dividend_yield=fundamental['DIV'].iloc[-1] if 'DIV' in fundamental.columns else None,
                roe=None,  # 별도 계산 필요
            )

        except Exception as e:
            print(f"펀더멘털 조회 오류 ({code}): {e}")
            return self._get_sample_fundamentals(code)

    def _get_sample_fundamentals(self, code: str) -> StockFundamentals:
        """샘플 펀더멘털"""
        samples = {
            '005930': StockFundamentals(
                code='005930', name='삼성전자', price=72000,
                market_cap=430_000_000_000_000, per=15.2, pbr=1.3,
                eps=4750, bps=55000, dividend_yield=2.1, roe=8.5
            ),
            '000660': StockFundamentals(
                code='000660', name='SK하이닉스', price=135000,
                market_cap=98_000_000_000_000, per=8.5, pbr=1.8,
                eps=15900, bps=75000, dividend_yield=1.2, roe=21.0
            ),
        }

        if code in samples:
            return samples[code]

        return StockFundamentals(
            code=code, name=f'종목 {code}', price=50000,
            market_cap=10_000_000_000_000, per=12.0, pbr=1.5,
            eps=4167, bps=33333, dividend_yield=1.5, roe=12.5
        )

    def analyze_technical(self, code: str, days: int = 60) -> Dict:
        """
        기술적 분석

        Args:
            code: 종목 코드
            days: 분석 기간

        Returns:
            기술적 분석 결과
        """
        df = self.data_collector.get_stock_price(
            code,
            (datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d'),
            datetime.now().strftime('%Y%m%d')
        )

        if df.empty:
            return {'error': '데이터 없음'}

        close = df['Close']
        volume = df['Volume']

        # 이동평균
        ma_5 = close.rolling(5).mean().iloc[-1]
        ma_20 = close.rolling(20).mean().iloc[-1]
        ma_60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else None

        current_price = close.iloc[-1]

        # RSI
        delta = close.diff()
        gain = delta.where(delta > 0, 0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        # ZeroDivisionError 방지
        loss_adj = loss.replace(0, 1e-10)
        rs = gain / loss_adj
        rsi = 100 - (100 / (1 + rs)).iloc[-1]

        # MACD
        exp12 = close.ewm(span=12).mean()
        exp26 = close.ewm(span=26).mean()
        macd = exp12 - exp26
        signal = macd.ewm(span=9).mean()
        macd_value = macd.iloc[-1]
        signal_value = signal.iloc[-1]

        # 볼린저 밴드
        bb_ma = close.rolling(20).mean()
        bb_std = close.rolling(20).std()
        upper_band = (bb_ma + 2 * bb_std).iloc[-1]
        lower_band = (bb_ma - 2 * bb_std).iloc[-1]

        # 거래량 분석
        avg_volume = volume.rolling(20).mean().iloc[-1]
        current_volume = volume.iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1

        # 추세 판단
        if current_price > ma_20 > (ma_60 or ma_20):
            trend = '상승'
        elif current_price < ma_20 < (ma_60 or ma_20):
            trend = '하락'
        else:
            trend = '횡보'

        # 신호
        signals = []
        if current_price < lower_band:
            signals.append('과매도 (볼린저 하단)')
        elif current_price > upper_band:
            signals.append('과매수 (볼린저 상단)')

        if rsi < 30:
            signals.append('과매도 (RSI)')
        elif rsi > 70:
            signals.append('과매수 (RSI)')

        if macd_value > signal_value:
            signals.append('MACD 매수 신호')
        else:
            signals.append('MACD 매도 신호')

        if volume_ratio > 2:
            signals.append('거래량 급증')

        return {
            'price': current_price,
            'ma_5': round(ma_5, 0),
            'ma_20': round(ma_20, 0),
            'ma_60': round(ma_60, 0) if ma_60 else None,
            'rsi': round(rsi, 1),
            'macd': round(macd_value, 0),
            'macd_signal': round(signal_value, 0),
            'bb_upper': round(upper_band, 0),
            'bb_lower': round(lower_band, 0),
            'volume_ratio': round(volume_ratio, 2),
            'trend': trend,
            'signals': signals,
            'change_1w': round((current_price / close.iloc[-5] - 1) * 100, 2) if len(close) >= 5 else None,
            'change_1m': round((current_price / close.iloc[-22] - 1) * 100, 2) if len(close) >= 22 else None,
        }

    def analyze_foreign_trend(self, code: str, days: int = 20) -> Dict:
        """
        외국인/기관 매매 동향 분석

        Args:
            code: 종목 코드
            days: 분석 기간

        Returns:
            매매 동향
        """
        if not self.enabled:
            return self._get_sample_investor_trend()

        try:
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d')

            # 투자자별 매매 동향
            df = stock.get_market_trading_value_by_date(
                start_date, end_date, code
            )

            if df.empty:
                return self._get_sample_investor_trend()

            # 최근 5일 순매수
            recent = df.tail(5)

            foreign_net = recent['외국인'].sum() if '외국인' in recent.columns else 0
            institution_net = recent['기관합계'].sum() if '기관합계' in recent.columns else 0
            individual_net = recent['개인'].sum() if '개인' in recent.columns else 0

            # 추세 판단
            if foreign_net > 0 and institution_net > 0:
                trend = '수급 양호'
            elif foreign_net < 0 and institution_net < 0:
                trend = '수급 불량'
            else:
                trend = '수급 혼조'

            return {
                'foreign_5d': foreign_net,
                'institution_5d': institution_net,
                'individual_5d': individual_net,
                'trend': trend,
                'foreign_buying': foreign_net > 0,
                'institution_buying': institution_net > 0,
            }

        except Exception as e:
            print(f"투자자 동향 조회 오류: {e}")
            return self._get_sample_investor_trend()

    def _get_sample_investor_trend(self) -> Dict:
        """샘플 투자자 동향"""
        return {
            'foreign_5d': 50_000_000_000,
            'institution_5d': -20_000_000_000,
            'individual_5d': -30_000_000_000,
            'trend': '외국인 매수세',
            'foreign_buying': True,
            'institution_buying': False,
        }

    def analyze_stock(self, code: str) -> StockAnalysis:
        """
        종목 종합 분석

        Args:
            code: 종목 코드

        Returns:
            종합 분석 결과
        """
        fundamentals = self.get_fundamentals(code)
        technical = self.analyze_technical(code)
        investor_trend = self.analyze_foreign_trend(code)

        # 점수 계산 (0-100)
        score = 50  # 기본 점수

        # 펀더멘털 점수
        if fundamentals.per and fundamentals.per < 15:
            score += 10
        elif fundamentals.per and fundamentals.per > 30:
            score -= 10

        if fundamentals.pbr and fundamentals.pbr < 1:
            score += 5

        if fundamentals.dividend_yield and fundamentals.dividend_yield > 2:
            score += 5

        # 기술적 점수
        if technical.get('trend') == '상승':
            score += 10
        elif technical.get('trend') == '하락':
            score -= 10

        if technical.get('rsi'):
            if technical['rsi'] < 30:
                score += 10  # 과매도 = 매수 기회
            elif technical['rsi'] > 70:
                score -= 10  # 과매수 = 위험

        # 수급 점수
        if investor_trend.get('foreign_buying'):
            score += 10
        if investor_trend.get('institution_buying'):
            score += 5

        # 점수 범위 제한
        score = max(0, min(100, score))

        # 추천
        if score >= 70:
            recommendation = '매수 고려'
        elif score >= 50:
            recommendation = '중립'
        elif score >= 30:
            recommendation = '관망'
        else:
            recommendation = '매도 고려'

        return StockAnalysis(
            code=code,
            name=fundamentals.name,
            fundamentals=fundamentals,
            technical=technical,
            foreign_trend=investor_trend,
            recommendation=recommendation,
            score=score,
        )

    def compare_stocks(self, codes: List[str]) -> pd.DataFrame:
        """
        종목 비교

        Args:
            codes: 종목 코드 리스트

        Returns:
            비교 테이블
        """
        data = []

        for code in codes:
            analysis = self.analyze_stock(code)

            data.append({
                '종목코드': code,
                '종목명': analysis.name,
                '현재가': analysis.fundamentals.price,
                'PER': analysis.fundamentals.per,
                'PBR': analysis.fundamentals.pbr,
                '배당수익률': analysis.fundamentals.dividend_yield,
                'RSI': analysis.technical.get('rsi'),
                '추세': analysis.technical.get('trend'),
                '외국인': '매수' if analysis.foreign_trend.get('foreign_buying') else '매도',
                '점수': analysis.score,
                '추천': analysis.recommendation,
            })

        return pd.DataFrame(data)

    def screen_stocks(self,
                      market: str = 'ALL',
                      min_market_cap: float = 1_000_000_000_000,
                      max_per: float = 20,
                      min_dividend: float = 1.0) -> List[str]:
        """
        종목 스크리닝

        Args:
            market: 시장 (KOSPI, KOSDAQ, ALL)
            min_market_cap: 최소 시가총액
            max_per: 최대 PER
            min_dividend: 최소 배당수익률

        Returns:
            스크리닝 통과 종목 코드 리스트
        """
        stock_list = self.data_collector.get_stock_list(market)

        passed_stocks = []

        for _, row in stock_list.head(50).iterrows():  # 상위 50개만 분석
            try:
                fundamentals = self.get_fundamentals(row['code'])

                if fundamentals.market_cap < min_market_cap:
                    continue
                if fundamentals.per and fundamentals.per > max_per:
                    continue
                if fundamentals.dividend_yield and fundamentals.dividend_yield < min_dividend:
                    continue

                passed_stocks.append(row['code'])

            except Exception:
                continue

        return passed_stocks

    def get_daily_report(self, codes: List[str]) -> str:
        """
        일일 리포트 생성

        Args:
            codes: 관심 종목 코드 리스트

        Returns:
            리포트 텍스트
        """
        market_summary = self.data_collector.get_market_summary()

        report = f"""
📊 한국 시장 일일 리포트
{'='*50}
📅 {datetime.now().strftime('%Y년 %m월 %d일')}

📈 시장 현황
"""
        for market, data in market_summary.items():
            emoji = '🔺' if data['change'] > 0 else '🔻' if data['change'] < 0 else '➖'
            report += f"  {market}: {data['close']:,.2f} {emoji} {data['change_pct']:+.2f}%\n"

        report += f"\n{'─'*50}\n📌 관심 종목 분석\n"

        for code in codes[:5]:  # 최대 5개
            analysis = self.analyze_stock(code)
            emoji = '🟢' if analysis.score >= 60 else '🟡' if analysis.score >= 40 else '🔴'

            report += f"""
{emoji} {analysis.name} ({code})
   현재가: {analysis.fundamentals.price:,}원
   PER: {analysis.fundamentals.per or 'N/A'} | PBR: {analysis.fundamentals.pbr or 'N/A'}
   RSI: {analysis.technical.get('rsi', 'N/A')} | 추세: {analysis.technical.get('trend', 'N/A')}
   외국인: {'매수' if analysis.foreign_trend.get('foreign_buying') else '매도'}
   종합 점수: {analysis.score}/100 | 추천: {analysis.recommendation}
"""

        return report

    def get_status(self) -> Dict:
        """상태 확인"""
        return {
            'pykrx_available': PYKRX_AVAILABLE,
            'data_collector_enabled': self.data_collector.enabled,
        }


# 사용 예시
def example_usage():
    """사용 예시"""
    analyzer = KoreanStockAnalyzer()

    # 삼성전자 분석
    analysis = analyzer.analyze_stock('005930')
    print(f"종목: {analysis.name}")
    print(f"점수: {analysis.score}")
    print(f"추천: {analysis.recommendation}")

    # 일일 리포트
    report = analyzer.get_daily_report(['005930', '000660', '035420'])
    print(report)
