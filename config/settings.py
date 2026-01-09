"""
통합 설정 관리 모듈
환경변수, YAML 설정, 기본값 관리
"""

import os
import yaml
import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from functools import lru_cache

logger = logging.getLogger(__name__)


@dataclass
class CacheConfig:
    """캐시 설정"""
    default_ttl: int = 300  # 5분
    price_ttl: int = 60     # 1분
    news_ttl: int = 600     # 10분
    analysis_ttl: int = 3600  # 1시간


@dataclass
class APIConfig:
    """API 설정"""
    openai_api_key: str = ""
    dart_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    discord_webhook_url: str = ""

    # 레이트 리미팅
    requests_per_minute: int = 60
    retry_count: int = 3
    retry_delay: float = 1.0


@dataclass
class AlertConfig:
    """알림 설정"""
    price_check_interval: int = 60  # 초
    risk_check_interval: int = 300
    enable_telegram: bool = False
    enable_discord: bool = False
    enable_email: bool = False


@dataclass
class PortfolioConfig:
    """포트폴리오 설정"""
    default_currency: str = "KRW"
    tax_rate_overseas: float = 0.22
    tax_rate_domestic: float = 0.22
    basic_deduction: float = 2500000
    commission_rate: float = 0.00015
    rebalance_threshold: float = 5.0


@dataclass
class UIConfig:
    """UI 설정"""
    theme: str = "light"
    language: str = "ko"
    date_format: str = "%Y-%m-%d"
    number_format: str = ",.0f"
    refresh_interval: int = 30


@dataclass
class Settings:
    """전체 설정"""
    cache: CacheConfig = field(default_factory=CacheConfig)
    api: APIConfig = field(default_factory=APIConfig)
    alert: AlertConfig = field(default_factory=AlertConfig)
    portfolio: PortfolioConfig = field(default_factory=PortfolioConfig)
    ui: UIConfig = field(default_factory=UIConfig)

    # 데이터 디렉토리
    data_dir: str = ""
    log_dir: str = ""
    config_file: str = ""

    def __post_init__(self):
        if not self.data_dir:
            self.data_dir = os.path.join(os.path.expanduser("~"), ".notion_portfolio")
        if not self.log_dir:
            self.log_dir = os.path.join(self.data_dir, "logs")
        if not self.config_file:
            self.config_file = os.path.join(self.data_dir, "config.yaml")

        # 디렉토리 생성
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)


class ConfigManager:
    """설정 관리자 (스레드 안전)"""

    _instance: Optional['ConfigManager'] = None
    _settings: Optional[Settings] = None
    _lock: threading.Lock = threading.Lock()
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._settings = Settings()
                    self._load_env()
                    self._load_yaml()
                    ConfigManager._initialized = True

    def _load_env(self):
        """환경변수 로드"""
        # .env 파일 로드 (있는 경우)
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        if os.path.exists(env_file):
            self._parse_env_file(env_file)

        # API 키
        self._settings.api.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        self._settings.api.dart_api_key = os.getenv('DART_API_KEY', '')
        self._settings.api.telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self._settings.api.telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        self._settings.api.discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL', '')

    def _parse_env_file(self, filepath: str):
        """env 파일 파싱"""
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip().strip('"\'')
        except Exception:
            pass

    def _load_yaml(self):
        """YAML 설정 로드"""
        config_file = self._settings.config_file

        if not os.path.exists(config_file):
            self._save_yaml()  # 기본 설정 저장
            return

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}

            # 캐시 설정
            if 'cache' in config:
                for key, value in config['cache'].items():
                    if hasattr(self._settings.cache, key):
                        setattr(self._settings.cache, key, value)

            # 알림 설정
            if 'alert' in config:
                for key, value in config['alert'].items():
                    if hasattr(self._settings.alert, key):
                        setattr(self._settings.alert, key, value)

            # 포트폴리오 설정
            if 'portfolio' in config:
                for key, value in config['portfolio'].items():
                    if hasattr(self._settings.portfolio, key):
                        setattr(self._settings.portfolio, key, value)

            # UI 설정
            if 'ui' in config:
                for key, value in config['ui'].items():
                    if hasattr(self._settings.ui, key):
                        setattr(self._settings.ui, key, value)

        except Exception as e:
            logger.warning(f"설정 파일 로드 실패: {e}")

    def _save_yaml(self):
        """YAML 설정 저장"""
        config = {
            'cache': {
                'default_ttl': self._settings.cache.default_ttl,
                'price_ttl': self._settings.cache.price_ttl,
                'news_ttl': self._settings.cache.news_ttl,
                'analysis_ttl': self._settings.cache.analysis_ttl,
            },
            'alert': {
                'price_check_interval': self._settings.alert.price_check_interval,
                'risk_check_interval': self._settings.alert.risk_check_interval,
                'enable_telegram': self._settings.alert.enable_telegram,
                'enable_discord': self._settings.alert.enable_discord,
            },
            'portfolio': {
                'default_currency': self._settings.portfolio.default_currency,
                'tax_rate_overseas': self._settings.portfolio.tax_rate_overseas,
                'basic_deduction': self._settings.portfolio.basic_deduction,
                'commission_rate': self._settings.portfolio.commission_rate,
                'rebalance_threshold': self._settings.portfolio.rebalance_threshold,
            },
            'ui': {
                'theme': self._settings.ui.theme,
                'language': self._settings.ui.language,
                'refresh_interval': self._settings.ui.refresh_interval,
            }
        }

        try:
            with open(self._settings.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        except Exception as e:
            logger.error(f"설정 파일 저장 실패: {e}")

    @property
    def settings(self) -> Settings:
        """현재 설정 반환"""
        return self._settings

    def get(self, key: str, default: Any = None) -> Any:
        """설정값 조회"""
        parts = key.split('.')
        value = self._settings

        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> bool:
        """설정값 변경"""
        parts = key.split('.')
        obj = self._settings

        for part in parts[:-1]:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                return False

        if hasattr(obj, parts[-1]):
            setattr(obj, parts[-1], value)
            self._save_yaml()
            return True

        return False

    def reload(self):
        """설정 재로드"""
        self._load_env()
        self._load_yaml()


# 전역 인스턴스
config_manager = ConfigManager()


def get_config() -> Settings:
    """현재 설정 반환"""
    return config_manager.settings


def get_setting(key: str, default: Any = None) -> Any:
    """설정값 조회"""
    return config_manager.get(key, default)


def set_setting(key: str, value: Any) -> bool:
    """설정값 변경"""
    return config_manager.set(key, value)
