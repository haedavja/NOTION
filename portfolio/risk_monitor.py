"""
위험 모니터링 및 사전 경고 시스템
차트 기술적 분석과 거시경제 지표를 모니터링하여 위험 구간을 감지합니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

from .portfolio import Position, Portfolio


class AlertSeverity(Enum):
    """경고 심각도"""
    INFO = "info"           # 참고 사항
    WARNING = "warning"     # 주의 필요
    CRITICAL = "critical"   # 즉시 조치 필요
    EMERGENCY = "emergency" # 긴급 - 즉각 대응


class AlertType(Enum):
    """경고 유형"""
    # 기술적 경고
    RSI_OVERBOUGHT = "RSI 과매수"
    RSI_OVERSOLD = "RSI 과매도"
    PRICE_CRASH = "급락"
    PRICE_SPIKE = "급등"
    STOP_LOSS_NEAR = "손절가 근접"
    SUPPORT_BREAK = "지지선 붕괴"
    VOLUME_SPIKE = "거래량 급증"
    MA_DEATH_CROSS = "데드크로스"
    MA_GOLDEN_CROSS = "골든크로스"

    # 거시경제 경고
    VIX_HIGH = "VIX 급등"
    RATE_HIKE = "금리 인상"
    YIELD_INVERSION = "장단기금리역전"
    MARKET_CORRECTION = "시장 조정"

    # 투자 논리 경고
    THESIS_WEAKENING = "투자논리 약화"
    TARGET_NEAR = "목표가 근접"


@dataclass
class RiskAlert:
    """위험 경고"""
    alert_id: str
    timestamp: datetime
    symbol: str
    alert_type: AlertType
    severity: AlertSeverity

    title: str
    message: str

    # 상세 데이터
    current_value: float          # 현재 값 (가격, RSI 등)
    threshold_value: float        # 임계값
    triggered_by: str             # 트리거 조건

    # 권고 조치
    recommended_action: str

    # 상태
    is_acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None

    def to_dict(self) -> Dict:
        return {
            'alert_id': self.alert_id,
            'timestamp': self.timestamp.isoformat(),
            'symbol': self.symbol,
            'alert_type': self.alert_type.value,
            'severity': self.severity.value,
            'title': self.title,
            'message': self.message,
            'current_value': self.current_value,
            'threshold_value': self.threshold_value,
            'triggered_by': self.triggered_by,
            'recommended_action': self.recommended_action,
            'is_acknowledged': self.is_acknowledged,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None,
        }


class MacroDataFetcher:
    """거시경제 데이터 조회"""

    # 주요 거시경제 지표 티커
    MACRO_TICKERS = {
        'VIX': '^VIX',           # 변동성 지수
        'TNX': '^TNX',           # 10년물 국채 금리
        'IRX': '^IRX',           # 3개월 국채 금리
        'DXY': 'DX-Y.NYB',       # 달러 인덱스
        'SPY': 'SPY',            # S&P 500 ETF
        'QQQ': 'QQQ',            # 나스닥 100 ETF
        'GLD': 'GLD',            # 금 ETF
        'TLT': 'TLT',            # 장기채권 ETF
    }

    def __init__(self):
        self.cache = {}
        self.cache_time = {}
        self.cache_duration = timedelta(minutes=15)

    def get_vix(self) -> Optional[float]:
        """VIX (공포지수) 조회"""
        return self._get_latest_price('^VIX')

    def get_treasury_10y(self) -> Optional[float]:
        """10년물 국채 금리"""
        return self._get_latest_price('^TNX')

    def get_treasury_3m(self) -> Optional[float]:
        """3개월 국채 금리"""
        return self._get_latest_price('^IRX')

    def get_yield_spread(self) -> Optional[float]:
        """장단기 금리 스프레드 (10Y - 3M)"""
        t10y = self.get_treasury_10y()
        t3m = self.get_treasury_3m()
        if t10y is not None and t3m is not None:
            return t10y - t3m
        return None

    def get_sp500_return(self, days: int = 5) -> Optional[float]:
        """S&P 500 N일 수익률"""
        return self._get_return('SPY', days)

    def get_nasdaq_return(self, days: int = 5) -> Optional[float]:
        """나스닥 N일 수익률"""
        return self._get_return('QQQ', days)

    def get_dollar_index(self) -> Optional[float]:
        """달러 인덱스"""
        return self._get_latest_price('DX-Y.NYB')

    def _get_latest_price(self, ticker: str) -> Optional[float]:
        """최신 가격 조회"""
        if not YFINANCE_AVAILABLE:
            return None

        # 캐시 확인
        if ticker in self.cache and ticker in self.cache_time:
            if datetime.now() - self.cache_time[ticker] < self.cache_duration:
                return self.cache[ticker]

        try:
            t = yf.Ticker(ticker)
            hist = t.history(period='5d')
            if not hist.empty:
                price = float(hist['Close'].iloc[-1])
                self.cache[ticker] = price
                self.cache_time[ticker] = datetime.now()
                return price
        except Exception as e:
            print(f"거시경제 데이터 조회 실패 ({ticker}): {e}")

        return None

    def _get_return(self, ticker: str, days: int) -> Optional[float]:
        """N일 수익률 조회"""
        if not YFINANCE_AVAILABLE:
            return None

        try:
            t = yf.Ticker(ticker)
            hist = t.history(period=f'{days + 5}d')
            if len(hist) >= days:
                current = hist['Close'].iloc[-1]
                past = hist['Close'].iloc[-days] if days < len(hist) else hist['Close'].iloc[0]
                return (current / past - 1) * 100
        except Exception:
            pass

        return None

    def get_macro_summary(self) -> Dict:
        """거시경제 요약"""
        vix = self.get_vix()
        t10y = self.get_treasury_10y()
        yield_spread = self.get_yield_spread()
        sp500_5d = self.get_sp500_return(5)
        nasdaq_5d = self.get_nasdaq_return(5)

        # 위험 수준 평가
        risk_level = 'low'
        risk_factors = []

        if vix:
            if vix > 30:
                risk_level = 'high'
                risk_factors.append(f"VIX {vix:.1f} - 극도의 공포")
            elif vix > 20:
                risk_level = 'medium'
                risk_factors.append(f"VIX {vix:.1f} - 불안 심리")

        if yield_spread is not None and yield_spread < 0:
            risk_level = 'high'
            risk_factors.append(f"장단기금리역전 ({yield_spread:.2f}%) - 경기침체 신호")

        if sp500_5d and sp500_5d < -5:
            risk_level = 'high' if sp500_5d < -10 else 'medium'
            risk_factors.append(f"S&P 500 급락 ({sp500_5d:.1f}%)")

        return {
            'vix': vix,
            'treasury_10y': t10y,
            'yield_spread': yield_spread,
            'sp500_5d_return': sp500_5d,
            'nasdaq_5d_return': nasdaq_5d,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'timestamp': datetime.now().isoformat(),
        }


class RiskMonitor:
    """위험 모니터링 클래스"""

    # 기술적 분석 임계값
    THRESHOLDS = {
        'rsi_overbought': 75,        # RSI 과매수
        'rsi_oversold': 25,          # RSI 과매도
        'price_crash_1d': -5,        # 1일 급락 %
        'price_crash_5d': -10,       # 5일 급락 %
        'price_spike_1d': 10,        # 1일 급등 %
        'stop_loss_buffer': 3,       # 손절가 근접 (% 이내)
        'volume_spike': 3,           # 평균 대비 거래량 배수
        'vix_high': 25,              # VIX 경계선
        'vix_critical': 35,          # VIX 위험선
        'market_correction': -10,    # 시장 조정 기준
    }

    def __init__(self):
        self.macro_fetcher = MacroDataFetcher()
        self.alerts: List[RiskAlert] = []
        self.price_cache = {}

    def get_stock_data(self, symbol: str, period: str = '3mo') -> Optional[pd.DataFrame]:
        """주가 데이터 조회"""
        if not YFINANCE_AVAILABLE:
            return None

        try:
            ticker = yf.Ticker(symbol)
            return ticker.history(period=period)
        except Exception:
            return None

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """RSI 계산"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return float(rsi.iloc[-1]) if not rsi.empty else 50

    def check_position_risks(self, position: Position) -> List[RiskAlert]:
        """개별 포지션 위험 체크"""
        alerts = []
        data = self.get_stock_data(position.symbol)

        if data is None or data.empty:
            return alerts

        close = data['Close']
        volume = data['Volume']
        current_price = float(close.iloc[-1])

        import uuid

        # 1. RSI 체크
        rsi = self.calculate_rsi(close)

        if rsi > self.THRESHOLDS['rsi_overbought']:
            alerts.append(RiskAlert(
                alert_id=str(uuid.uuid4())[:8],
                timestamp=datetime.now(),
                symbol=position.symbol,
                alert_type=AlertType.RSI_OVERBOUGHT,
                severity=AlertSeverity.WARNING,
                title=f"⚠️ {position.symbol} RSI 과매수",
                message=f"RSI가 {rsi:.1f}로 과매수 구간입니다. 차익 실현 또는 추가 매수 자제를 고려하세요.",
                current_value=rsi,
                threshold_value=self.THRESHOLDS['rsi_overbought'],
                triggered_by="RSI > 75",
                recommended_action="부분 매도 또는 관망",
            ))
        elif rsi < self.THRESHOLDS['rsi_oversold']:
            alerts.append(RiskAlert(
                alert_id=str(uuid.uuid4())[:8],
                timestamp=datetime.now(),
                symbol=position.symbol,
                alert_type=AlertType.RSI_OVERSOLD,
                severity=AlertSeverity.INFO,
                title=f"📉 {position.symbol} RSI 과매도",
                message=f"RSI가 {rsi:.1f}로 과매도 구간입니다. 반등 가능성이 있으나 추가 하락도 가능합니다.",
                current_value=rsi,
                threshold_value=self.THRESHOLDS['rsi_oversold'],
                triggered_by="RSI < 25",
                recommended_action="투자 논리 유효 시 추가 매수 고려",
            ))

        # 2. 가격 급락 체크
        if len(close) >= 2:
            return_1d = (close.iloc[-1] / close.iloc[-2] - 1) * 100
            if return_1d < self.THRESHOLDS['price_crash_1d']:
                severity = AlertSeverity.CRITICAL if return_1d < -10 else AlertSeverity.WARNING
                alerts.append(RiskAlert(
                    alert_id=str(uuid.uuid4())[:8],
                    timestamp=datetime.now(),
                    symbol=position.symbol,
                    alert_type=AlertType.PRICE_CRASH,
                    severity=severity,
                    title=f"🔴 {position.symbol} 급락 경고",
                    message=f"오늘 {return_1d:.1f}% 하락했습니다. 원인을 파악하고 손절가를 확인하세요.",
                    current_value=return_1d,
                    threshold_value=self.THRESHOLDS['price_crash_1d'],
                    triggered_by=f"1일 수익률 < {self.THRESHOLDS['price_crash_1d']}%",
                    recommended_action="손절가 확인, 뉴스 체크, 투자 논리 재검토",
                ))

        if len(close) >= 6:
            return_5d = (close.iloc[-1] / close.iloc[-6] - 1) * 100
            if return_5d < self.THRESHOLDS['price_crash_5d']:
                alerts.append(RiskAlert(
                    alert_id=str(uuid.uuid4())[:8],
                    timestamp=datetime.now(),
                    symbol=position.symbol,
                    alert_type=AlertType.PRICE_CRASH,
                    severity=AlertSeverity.CRITICAL,
                    title=f"🚨 {position.symbol} 5일 연속 급락",
                    message=f"5거래일간 {return_5d:.1f}% 하락했습니다. 추세 전환 또는 펀더멘털 악화 가능성을 검토하세요.",
                    current_value=return_5d,
                    threshold_value=self.THRESHOLDS['price_crash_5d'],
                    triggered_by=f"5일 수익률 < {self.THRESHOLDS['price_crash_5d']}%",
                    recommended_action="비중 축소 또는 손절 고려",
                ))

        # 3. 손절가 근접 체크
        if position.stop_loss and current_price > 0:
            distance_to_stop = (current_price / position.stop_loss - 1) * 100
            if distance_to_stop < self.THRESHOLDS['stop_loss_buffer']:
                severity = AlertSeverity.EMERGENCY if distance_to_stop < 1 else AlertSeverity.CRITICAL
                alerts.append(RiskAlert(
                    alert_id=str(uuid.uuid4())[:8],
                    timestamp=datetime.now(),
                    symbol=position.symbol,
                    alert_type=AlertType.STOP_LOSS_NEAR,
                    severity=severity,
                    title=f"🛑 {position.symbol} 손절가 근접",
                    message=f"현재가 ${current_price:.2f}가 손절가 ${position.stop_loss:.2f}에 {distance_to_stop:.1f}% 근접했습니다.",
                    current_value=distance_to_stop,
                    threshold_value=self.THRESHOLDS['stop_loss_buffer'],
                    triggered_by=f"손절가까지 {self.THRESHOLDS['stop_loss_buffer']}% 이내",
                    recommended_action="손절 실행 또는 손절가 하향 검토",
                ))

        # 4. 목표가 근접 체크
        if position.target_price and current_price > 0:
            distance_to_target = (position.target_price / current_price - 1) * 100
            if distance_to_target < 5:
                alerts.append(RiskAlert(
                    alert_id=str(uuid.uuid4())[:8],
                    timestamp=datetime.now(),
                    symbol=position.symbol,
                    alert_type=AlertType.TARGET_NEAR,
                    severity=AlertSeverity.INFO,
                    title=f"🎯 {position.symbol} 목표가 근접",
                    message=f"현재가 ${current_price:.2f}가 목표가 ${position.target_price:.2f}에 {distance_to_target:.1f}% 근접했습니다.",
                    current_value=distance_to_target,
                    threshold_value=5,
                    triggered_by="목표가까지 5% 이내",
                    recommended_action="이익 실현 또는 목표가 상향 검토",
                ))

        # 5. 거래량 급증 체크
        if len(volume) >= 21:
            avg_volume = volume.iloc[-21:-1].mean()
            current_volume = volume.iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1

            if volume_ratio > self.THRESHOLDS['volume_spike']:
                alerts.append(RiskAlert(
                    alert_id=str(uuid.uuid4())[:8],
                    timestamp=datetime.now(),
                    symbol=position.symbol,
                    alert_type=AlertType.VOLUME_SPIKE,
                    severity=AlertSeverity.WARNING,
                    title=f"📊 {position.symbol} 거래량 급증",
                    message=f"거래량이 평균의 {volume_ratio:.1f}배입니다. 중요한 뉴스나 이벤트가 있는지 확인하세요.",
                    current_value=volume_ratio,
                    threshold_value=self.THRESHOLDS['volume_spike'],
                    triggered_by=f"거래량 > 평균의 {self.THRESHOLDS['volume_spike']}배",
                    recommended_action="뉴스/공시 확인",
                ))

        # 6. 이동평균 데드크로스 체크
        if len(close) >= 50:
            ma_20 = close.rolling(20).mean()
            ma_50 = close.rolling(50).mean()

            # 최근 데드크로스 발생
            if len(ma_20) >= 2 and len(ma_50) >= 2:
                prev_diff = ma_20.iloc[-2] - ma_50.iloc[-2]
                curr_diff = ma_20.iloc[-1] - ma_50.iloc[-1]

                if prev_diff > 0 and curr_diff < 0:
                    alerts.append(RiskAlert(
                        alert_id=str(uuid.uuid4())[:8],
                        timestamp=datetime.now(),
                        symbol=position.symbol,
                        alert_type=AlertType.MA_DEATH_CROSS,
                        severity=AlertSeverity.WARNING,
                        title=f"📉 {position.symbol} 데드크로스 발생",
                        message="20일선이 50일선을 하향 돌파했습니다. 중기 하락 추세 전환 신호입니다.",
                        current_value=curr_diff,
                        threshold_value=0,
                        triggered_by="MA20 < MA50 전환",
                        recommended_action="비중 축소 또는 손절가 상향 검토",
                    ))

        return alerts

    def check_macro_risks(self) -> List[RiskAlert]:
        """거시경제 위험 체크"""
        alerts = []
        macro = self.macro_fetcher.get_macro_summary()

        import uuid

        # VIX 체크
        vix = macro.get('vix')
        if vix:
            if vix > self.THRESHOLDS['vix_critical']:
                alerts.append(RiskAlert(
                    alert_id=str(uuid.uuid4())[:8],
                    timestamp=datetime.now(),
                    symbol="MACRO",
                    alert_type=AlertType.VIX_HIGH,
                    severity=AlertSeverity.EMERGENCY,
                    title=f"🚨 VIX 극단적 수준 ({vix:.1f})",
                    message="시장이 극도의 공포 상태입니다. 현금 비중 확대와 위험 자산 축소를 강력히 권고합니다.",
                    current_value=vix,
                    threshold_value=self.THRESHOLDS['vix_critical'],
                    triggered_by=f"VIX > {self.THRESHOLDS['vix_critical']}",
                    recommended_action="현금 비중 50% 이상, 신규 매수 금지",
                ))
            elif vix > self.THRESHOLDS['vix_high']:
                alerts.append(RiskAlert(
                    alert_id=str(uuid.uuid4())[:8],
                    timestamp=datetime.now(),
                    symbol="MACRO",
                    alert_type=AlertType.VIX_HIGH,
                    severity=AlertSeverity.WARNING,
                    title=f"⚠️ VIX 상승 ({vix:.1f})",
                    message="시장 불안 심리가 높아지고 있습니다. 리스크 관리에 주의하세요.",
                    current_value=vix,
                    threshold_value=self.THRESHOLDS['vix_high'],
                    triggered_by=f"VIX > {self.THRESHOLDS['vix_high']}",
                    recommended_action="손절가 점검, 현금 비중 점검",
                ))

        # 장단기 금리 역전 체크
        yield_spread = macro.get('yield_spread')
        if yield_spread is not None and yield_spread < 0:
            alerts.append(RiskAlert(
                alert_id=str(uuid.uuid4())[:8],
                timestamp=datetime.now(),
                symbol="MACRO",
                alert_type=AlertType.YIELD_INVERSION,
                severity=AlertSeverity.CRITICAL,
                title=f"🔴 장단기 금리 역전 ({yield_spread:.2f}%)",
                message="장단기 금리가 역전되었습니다. 역사적으로 경기침체의 선행 지표입니다. 방어적 포지션을 권고합니다.",
                current_value=yield_spread,
                threshold_value=0,
                triggered_by="10Y - 3M < 0",
                recommended_action="경기방어주/배당주 비중 확대, 성장주 비중 축소",
            ))

        # 시장 급락 체크
        sp500_5d = macro.get('sp500_5d_return')
        if sp500_5d and sp500_5d < self.THRESHOLDS['market_correction']:
            alerts.append(RiskAlert(
                alert_id=str(uuid.uuid4())[:8],
                timestamp=datetime.now(),
                symbol="MACRO",
                alert_type=AlertType.MARKET_CORRECTION,
                severity=AlertSeverity.CRITICAL,
                title=f"📉 시장 급락 (S&P 500 {sp500_5d:.1f}%)",
                message="시장이 단기간에 큰 폭으로 하락했습니다. 패닉 매도를 피하되, 손절가를 철저히 준수하세요.",
                current_value=sp500_5d,
                threshold_value=self.THRESHOLDS['market_correction'],
                triggered_by=f"S&P 500 5일 수익률 < {self.THRESHOLDS['market_correction']}%",
                recommended_action="손절가 준수, 추격 매도 금지, 현금 확보",
            ))

        return alerts

    def run_full_scan(self, portfolio: Portfolio) -> Dict:
        """포트폴리오 전체 위험 스캔"""
        all_alerts = []

        # 거시경제 위험 체크
        macro_alerts = self.check_macro_risks()
        all_alerts.extend(macro_alerts)

        # 개별 포지션 위험 체크
        for position in portfolio.positions:
            position_alerts = self.check_position_risks(position)
            all_alerts.extend(position_alerts)

        # 심각도별 분류
        emergency = [a for a in all_alerts if a.severity == AlertSeverity.EMERGENCY]
        critical = [a for a in all_alerts if a.severity == AlertSeverity.CRITICAL]
        warning = [a for a in all_alerts if a.severity == AlertSeverity.WARNING]
        info = [a for a in all_alerts if a.severity == AlertSeverity.INFO]

        # 전체 위험 수준 결정
        if emergency:
            overall_risk = 'emergency'
        elif critical:
            overall_risk = 'critical'
        elif warning:
            overall_risk = 'warning'
        else:
            overall_risk = 'normal'

        return {
            'timestamp': datetime.now().isoformat(),
            'overall_risk_level': overall_risk,
            'total_alerts': len(all_alerts),
            'by_severity': {
                'emergency': len(emergency),
                'critical': len(critical),
                'warning': len(warning),
                'info': len(info),
            },
            'emergency_alerts': [a.to_dict() for a in emergency],
            'critical_alerts': [a.to_dict() for a in critical],
            'warning_alerts': [a.to_dict() for a in warning],
            'info_alerts': [a.to_dict() for a in info],
            'all_alerts': all_alerts,
            'macro_summary': self.macro_fetcher.get_macro_summary(),
        }

    def get_risk_summary_message(self, scan_result: Dict) -> str:
        """위험 요약 메시지 생성"""
        level = scan_result['overall_risk_level']
        total = scan_result['total_alerts']
        by_severity = scan_result['by_severity']

        if level == 'emergency':
            header = "🚨 **긴급 경고**: 즉각적인 조치가 필요합니다!"
        elif level == 'critical':
            header = "🔴 **위험 경고**: 주의가 필요한 상황입니다."
        elif level == 'warning':
            header = "⚠️ **주의**: 모니터링을 강화하세요."
        else:
            header = "✅ **정상**: 현재 특별한 위험 신호가 없습니다."

        summary = f"{header}\n\n"
        summary += f"총 {total}건의 알림\n"
        summary += f"- 긴급: {by_severity['emergency']}건\n"
        summary += f"- 위험: {by_severity['critical']}건\n"
        summary += f"- 주의: {by_severity['warning']}건\n"
        summary += f"- 참고: {by_severity['info']}건"

        return summary
