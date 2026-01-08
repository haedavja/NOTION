"""
통합 로깅 모듈
파일 및 콘솔 로깅, 로그 레벨 관리
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


class LoggerManager:
    """로거 관리자"""

    _loggers: dict = {}
    _log_dir: str = ""
    _log_level: int = logging.INFO
    _initialized: bool = False

    @classmethod
    def init(cls, log_dir: str = None, log_level: str = "INFO"):
        """로거 초기화"""
        if cls._initialized:
            return

        # 로그 디렉토리 설정
        if log_dir is None:
            log_dir = os.path.join(os.path.expanduser("~"), ".notion_portfolio", "logs")

        cls._log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

        # 로그 레벨 설정
        cls._log_level = getattr(logging, log_level.upper(), logging.INFO)

        # 루트 로거 설정
        root_logger = logging.getLogger()
        root_logger.setLevel(cls._log_level)

        # 기존 핸들러 제거
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        cls._initialized = True

    @classmethod
    def get_logger(cls, name: str = "notion") -> logging.Logger:
        """로거 반환"""
        if not cls._initialized:
            cls.init()

        if name in cls._loggers:
            return cls._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(cls._log_level)

        # 기존 핸들러 제거
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # 포매터
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 콘솔 핸들러
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(cls._log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 파일 핸들러 (일별 로테이션)
        log_file = os.path.join(cls._log_dir, f"{name}.log")
        file_handler = TimedRotatingFileHandler(
            log_file,
            when='midnight',
            interval=1,
            backupCount=30,
            encoding='utf-8'
        )
        file_handler.setLevel(cls._log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # 에러 전용 파일
        error_file = os.path.join(cls._log_dir, f"{name}_error.log")
        error_handler = RotatingFileHandler(
            error_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)

        cls._loggers[name] = logger
        return logger

    @classmethod
    def set_level(cls, level: str):
        """전역 로그 레벨 변경"""
        cls._log_level = getattr(logging, level.upper(), logging.INFO)

        for logger in cls._loggers.values():
            logger.setLevel(cls._log_level)
            for handler in logger.handlers:
                if not isinstance(handler, logging.FileHandler) or 'error' not in handler.baseFilename:
                    handler.setLevel(cls._log_level)


# 편의 함수
def get_logger(name: str = "notion") -> logging.Logger:
    """로거 반환"""
    return LoggerManager.get_logger(name)


def init_logging(log_dir: str = None, log_level: str = "INFO"):
    """로깅 초기화"""
    LoggerManager.init(log_dir, log_level)


# 모듈별 로거
class ModuleLogger:
    """모듈별 로거 래퍼"""

    def __init__(self, module_name: str):
        self.logger = get_logger(module_name)

    def debug(self, msg: str, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        self.logger.exception(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)


# 기본 로거들
app_logger = ModuleLogger("app")
api_logger = ModuleLogger("api")
data_logger = ModuleLogger("data")
alert_logger = ModuleLogger("alert")
portfolio_logger = ModuleLogger("portfolio")
analysis_logger = ModuleLogger("analysis")
