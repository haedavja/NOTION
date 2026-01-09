"""
중앙화된 상수 및 설정값
하드코딩된 값들을 한 곳에서 관리
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class Environment(Enum):
    """실행 환경"""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


# 현재 환경
CURRENT_ENV = Environment(os.getenv("APP_ENV", "development"))


@dataclass
class MarketConfig:
    """시장 관련 설정"""
    # 환율
    usd_krw_rate: float = float(os.getenv("USD_KRW_RATE", "1350"))

    # 무위험 이자율 (연간, 소수점)
    risk_free_rate: float = float(os.getenv("RISK_FREE_RATE", "0.04"))

    # 거래일 수
    trading_days_per_year: int = 252

    # 기본 수수료율
    default_commission_rate: float = 0.00015  # 0.015%

    # 세금
    stock_tax_rate: float = 0.0023  # 0.23%
    dividend_tax_rate: float = 0.154  # 15.4%
    capital_gains_tax_rate: float = 0.22  # 22%

    # 거래소 운영 시간 (KST)
    kr_market_open: str = "09:00"
    kr_market_close: str = "15:30"
    us_market_open: str = "23:30"  # KST
    us_market_close: str = "06:00"  # KST

    # 시장 지수 심볼
    kospi_symbol: str = "^KS11"
    kosdaq_symbol: str = "^KQ11"
    sp500_symbol: str = "^GSPC"
    nasdaq_symbol: str = "^IXIC"


@dataclass
class TechnicalConfig:
    """기술적 분석 설정"""
    # 이동평균 기간
    ma_short: int = 20
    ma_medium: int = 50
    ma_long: int = 200

    # RSI
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0

    # MACD
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

    # 볼린저 밴드
    bb_period: int = 20
    bb_std: float = 2.0

    # 스토캐스틱
    stoch_k: int = 14
    stoch_d: int = 3
    stoch_smooth: int = 3

    # ATR
    atr_period: int = 14


@dataclass
class PortfolioConfig:
    """포트폴리오 설정"""
    # 최적화
    min_weight: float = 0.0
    max_weight: float = 1.0
    default_target_return: float = 0.15  # 15%

    # 리밸런싱
    rebalance_threshold: float = 0.05  # 5% 이상 차이시 알림
    min_trade_amount: float = 10000  # 최소 거래 금액

    # 위험 관리
    max_single_stock_weight: float = 0.30  # 단일 종목 최대 비중
    max_sector_weight: float = 0.40  # 단일 섹터 최대 비중

    # 시뮬레이션
    monte_carlo_simulations: int = 5000
    efficient_frontier_points: int = 50


@dataclass
class BacktestConfig:
    """백테스트 설정"""
    default_initial_capital: float = 100000000  # 1억원
    default_commission: float = 0.00015
    default_slippage: float = 0.001
    min_history_days: int = 30
    max_history_years: int = 10


@dataclass
class AlertConfig:
    """알림 설정"""
    # 가격 모니터링
    check_interval_seconds: int = 60
    price_change_threshold: float = 0.05  # 5%

    # 알림 제한
    max_alerts_per_day: int = 100
    cooldown_minutes: int = 5

    # 히스토리
    history_retention_days: int = 90


@dataclass
class CacheConfig:
    """캐시 설정"""
    # TTL (초)
    price_cache_ttl: int = 60
    news_cache_ttl: int = 300
    financial_cache_ttl: int = 3600
    etf_cache_ttl: int = 3600

    # 크기 제한
    max_cache_size: int = 1000


@dataclass
class APIConfig:
    """API 설정"""
    # 요청 제한
    rate_limit_per_minute: int = 60
    request_timeout: int = 30

    # 재시도
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff: float = 2.0

    # 페이지네이션
    default_page_size: int = 20
    max_page_size: int = 100


@dataclass
class UIConfig:
    """UI 설정"""
    # 차트
    chart_height: int = 400
    chart_width: int = 800

    # 테이블
    default_rows_per_page: int = 20

    # 색상
    positive_color: str = "#22c55e"  # 녹색
    negative_color: str = "#ef4444"  # 빨간색
    neutral_color: str = "#6b7280"  # 회색

    # 숫자 포맷
    currency_format: str = "₩{:,.0f}"
    percent_format: str = "{:.2f}%"
    price_format: str = "${:,.2f}"


@dataclass
class DataConfig:
    """데이터 설정"""
    # 데이터 소스
    default_data_source: str = "yfinance"

    # 기간
    default_period: str = "1y"
    max_period: str = "10y"

    # 파일 경로
    data_dir: str = os.getenv("DATA_DIR", "data")
    backup_dir: str = os.getenv("BACKUP_DIR", "backups")
    logs_dir: str = os.getenv("LOGS_DIR", "logs")


class AppConfig:
    """통합 앱 설정"""

    _instance: Optional['AppConfig'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """설정 초기화"""
        self.env = CURRENT_ENV
        self.market = MarketConfig()
        self.technical = TechnicalConfig()
        self.portfolio = PortfolioConfig()
        self.backtest = BacktestConfig()
        self.alert = AlertConfig()
        self.cache = CacheConfig()
        self.api = APIConfig()
        self.ui = UIConfig()
        self.data = DataConfig()

    def reload(self):
        """설정 새로고침"""
        self._initialize()

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        from dataclasses import asdict
        return {
            "env": self.env.value,
            "market": asdict(self.market),
            "technical": asdict(self.technical),
            "portfolio": asdict(self.portfolio),
            "backtest": asdict(self.backtest),
            "alert": asdict(self.alert),
            "cache": asdict(self.cache),
            "api": asdict(self.api),
            "ui": asdict(self.ui),
            "data": asdict(self.data),
        }


# 싱글톤 인스턴스
config = AppConfig()


# 편의를 위한 직접 접근
MARKET = config.market
TECHNICAL = config.technical
PORTFOLIO = config.portfolio
BACKTEST = config.backtest
ALERT = config.alert
CACHE = config.cache
API = config.api
UI = config.ui
DATA = config.data


# 자주 사용하는 상수 직접 노출
EXCHANGE_RATE = config.market.usd_krw_rate
RISK_FREE_RATE = config.market.risk_free_rate
TRADING_DAYS = config.market.trading_days_per_year


# 포맷팅 함수
def format_currency(value: float, currency: str = "KRW") -> str:
    """통화 포맷팅"""
    if currency == "KRW":
        return f"₩{value:,.0f}"
    elif currency == "USD":
        return f"${value:,.2f}"
    else:
        return f"{value:,.2f} {currency}"


def format_percent(value: float, decimal_places: int = 2) -> str:
    """퍼센트 포맷팅"""
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimal_places}f}%"


def format_number(value: float, decimal_places: int = 0) -> str:
    """숫자 포맷팅"""
    return f"{value:,.{decimal_places}f}"


def format_large_number(value: float) -> str:
    """큰 숫자 포맷팅 (억, 조 단위)"""
    if abs(value) >= 1e12:
        return f"{value/1e12:.1f}조"
    elif abs(value) >= 1e8:
        return f"{value/1e8:.1f}억"
    elif abs(value) >= 1e4:
        return f"{value/1e4:.1f}만"
    else:
        return f"{value:,.0f}"
