"""
설정 파일
API 키 및 기본 설정
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class APIConfig:
    """API 설정"""
    fred_api_key: Optional[str] = None
    news_api_key: Optional[str] = None

    def __post_init__(self):
        # 환경 변수에서 로드
        self.fred_api_key = self.fred_api_key or os.getenv('FRED_API_KEY')
        self.news_api_key = self.news_api_key or os.getenv('NEWS_API_KEY')


@dataclass
class AnalysisConfig:
    """분석 설정"""
    # 기본 분석 기간
    default_period: str = '5y'

    # 가중치
    macro_weight: float = 0.30
    flow_weight: float = 0.25
    sentiment_weight: float = 0.20
    technical_weight: float = 0.25

    # 이동평균 기간
    ma_short: int = 20
    ma_mid: int = 50
    ma_long: int = 200

    # RSI 설정
    rsi_period: int = 14
    rsi_oversold: int = 30
    rsi_overbought: int = 70

    # 볼린저 밴드
    bb_period: int = 20
    bb_std: float = 2.0


@dataclass
class DashboardConfig:
    """대시보드 설정"""
    port: int = 8501
    theme: str = 'light'
    cache_ttl: int = 3600  # 1시간


class Config:
    """전체 설정"""

    def __init__(self):
        self.api = APIConfig()
        self.analysis = AnalysisConfig()
        self.dashboard = DashboardConfig()

    @classmethod
    def from_env(cls):
        """환경 변수에서 설정 로드"""
        config = cls()

        # API 키
        config.api.fred_api_key = os.getenv('FRED_API_KEY')
        config.api.news_api_key = os.getenv('NEWS_API_KEY')

        # 분석 설정
        if os.getenv('MACRO_WEIGHT'):
            config.analysis.macro_weight = float(os.getenv('MACRO_WEIGHT'))
        if os.getenv('FLOW_WEIGHT'):
            config.analysis.flow_weight = float(os.getenv('FLOW_WEIGHT'))
        if os.getenv('SENTIMENT_WEIGHT'):
            config.analysis.sentiment_weight = float(os.getenv('SENTIMENT_WEIGHT'))
        if os.getenv('TECHNICAL_WEIGHT'):
            config.analysis.technical_weight = float(os.getenv('TECHNICAL_WEIGHT'))

        return config

    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            'api': {
                'fred_api_key': '***' if self.api.fred_api_key else None,
                'news_api_key': '***' if self.api.news_api_key else None,
            },
            'analysis': {
                'default_period': self.analysis.default_period,
                'macro_weight': self.analysis.macro_weight,
                'flow_weight': self.analysis.flow_weight,
                'sentiment_weight': self.analysis.sentiment_weight,
                'technical_weight': self.analysis.technical_weight,
            },
            'dashboard': {
                'port': self.dashboard.port,
                'theme': self.dashboard.theme,
            }
        }


# 기본 설정 인스턴스
config = Config.from_env()
