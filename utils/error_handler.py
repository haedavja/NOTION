"""
중앙화된 에러 핸들러
일관된 예외 처리 및 로깅
"""

import logging
import traceback
import functools
from typing import Optional, Any, Callable, TypeVar, Type, Union, Tuple
from datetime import datetime
from enum import Enum

# 로거 설정
logger = logging.getLogger("notion_portfolio")


class ErrorSeverity(Enum):
    """에러 심각도"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """에러 카테고리"""
    NETWORK = "network"
    DATA = "data"
    VALIDATION = "validation"
    API = "api"
    DATABASE = "database"
    CALCULATION = "calculation"
    UI = "ui"
    UNKNOWN = "unknown"


class AppError(Exception):
    """애플리케이션 커스텀 예외"""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        original_error: Optional[Exception] = None,
        context: Optional[dict] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.original_error = original_error
        self.context = context or {}
        self.timestamp = datetime.now()

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "original_error": str(self.original_error) if self.original_error else None
        }


class NetworkError(AppError):
    """네트워크 관련 오류"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.NETWORK, **kwargs)


class DataError(AppError):
    """데이터 처리 오류"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.DATA, **kwargs)


class ValidationError(AppError):
    """유효성 검사 오류"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.VALIDATION, severity=ErrorSeverity.WARNING, **kwargs)


class APIError(AppError):
    """API 관련 오류"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.API, **kwargs)


class CalculationError(AppError):
    """계산 오류"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, category=ErrorCategory.CALCULATION, **kwargs)


def log_error(
    error: Exception,
    context: Optional[dict] = None,
    severity: ErrorSeverity = ErrorSeverity.ERROR
) -> None:
    """에러 로깅"""
    error_info = {
        "type": type(error).__name__,
        "message": str(error),
        "context": context or {},
        "traceback": traceback.format_exc()
    }

    if isinstance(error, AppError):
        error_info["category"] = error.category.value
        error_info["app_context"] = error.context

    log_func = getattr(logger, severity.value, logger.error)
    log_func(f"[{error_info['type']}] {error_info['message']}", extra=error_info)


T = TypeVar('T')


def safe_execute(
    func: Callable[..., T],
    *args,
    default: T = None,
    error_message: str = "",
    log_errors: bool = True,
    raise_errors: bool = False,
    error_category: ErrorCategory = ErrorCategory.UNKNOWN,
    **kwargs
) -> T:
    """
    안전한 함수 실행

    Args:
        func: 실행할 함수
        default: 에러 시 반환할 기본값
        error_message: 커스텀 에러 메시지
        log_errors: 에러 로깅 여부
        raise_errors: 에러 다시 발생 여부
        error_category: 에러 카테고리
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if log_errors:
            msg = error_message or f"Error in {func.__name__}"
            log_error(e, context={"function": func.__name__, "args": str(args)[:100]})

        if raise_errors:
            raise AppError(
                message=error_message or str(e),
                category=error_category,
                original_error=e
            )

        return default


def handle_errors(
    default_return: Any = None,
    log_errors: bool = True,
    raise_errors: bool = False,
    error_category: ErrorCategory = ErrorCategory.UNKNOWN,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    에러 핸들링 데코레이터

    Args:
        default_return: 에러 시 반환할 기본값
        log_errors: 에러 로깅 여부
        raise_errors: 에러 다시 발생 여부
        error_category: 에러 카테고리
        exceptions: 처리할 예외 타입들
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                if log_errors:
                    log_error(
                        e,
                        context={
                            "function": func.__name__,
                            "module": func.__module__
                        }
                    )

                if raise_errors:
                    if isinstance(e, AppError):
                        raise
                    raise AppError(
                        message=str(e),
                        category=error_category,
                        original_error=e
                    )

                # callable default
                if callable(default_return):
                    return default_return()
                return default_return

        return wrapper
    return decorator


def retry_on_error(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    log_retries: bool = True
):
    """
    재시도 데코레이터

    Args:
        max_retries: 최대 재시도 횟수
        delay: 초기 대기 시간 (초)
        backoff: 대기 시간 증가 배수
        exceptions: 재시도할 예외 타입들
        log_retries: 재시도 로깅 여부
    """
    import time

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        if log_retries:
                            logger.warning(
                                f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e}"
                            )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        if log_retries:
                            logger.error(
                                f"All {max_retries} retries failed for {func.__name__}: {e}"
                            )

            raise last_exception

        return wrapper
    return decorator


class ErrorCollector:
    """여러 에러를 수집하고 관리"""

    def __init__(self):
        self.errors: list = []

    def add(self, error: Exception, context: Optional[dict] = None) -> None:
        """에러 추가"""
        self.errors.append({
            "error": error,
            "context": context or {},
            "timestamp": datetime.now()
        })

    def has_errors(self) -> bool:
        """에러 존재 여부"""
        return len(self.errors) > 0

    def get_errors(self) -> list:
        """모든 에러 반환"""
        return self.errors

    def get_messages(self) -> list:
        """에러 메시지 목록"""
        return [str(e["error"]) for e in self.errors]

    def clear(self) -> None:
        """에러 초기화"""
        self.errors = []

    def raise_if_errors(self, message: str = "Multiple errors occurred") -> None:
        """에러가 있으면 예외 발생"""
        if self.has_errors():
            raise AppError(
                message=f"{message}: {len(self.errors)} errors",
                context={"errors": self.get_messages()}
            )


def format_error_for_ui(error: Exception) -> str:
    """UI 표시용 에러 메시지 포맷팅"""
    if isinstance(error, ValidationError):
        return f"⚠️ 입력 오류: {error.message}"
    elif isinstance(error, NetworkError):
        return f"🌐 네트워크 오류: {error.message}"
    elif isinstance(error, DataError):
        return f"📊 데이터 오류: {error.message}"
    elif isinstance(error, APIError):
        return f"🔌 API 오류: {error.message}"
    elif isinstance(error, AppError):
        return f"❌ 오류: {error.message}"
    else:
        return f"❌ 오류가 발생했습니다: {str(error)}"


class StreamlitErrorHandler:
    """Streamlit 전용 에러 핸들러"""

    def __init__(self):
        self._error_count = 0
        self._last_errors = []
        self._max_errors = 10

    def show_error(self, error: Exception, show_details: bool = False) -> None:
        """Streamlit에 에러 표시"""
        try:
            import streamlit as st

            message = format_error_for_ui(error)
            st.error(message)

            if show_details and isinstance(error, AppError):
                with st.expander("상세 정보"):
                    st.json(error.to_dict())

            # 에러 기록
            self._record_error(error)

        except ImportError:
            # Streamlit 없으면 로그만
            log_error(error)

    def show_warning(self, message: str) -> None:
        """경고 표시"""
        try:
            import streamlit as st
            st.warning(f"⚠️ {message}")
        except ImportError:
            logger.warning(message)

    def show_info(self, message: str) -> None:
        """정보 표시"""
        try:
            import streamlit as st
            st.info(f"ℹ️ {message}")
        except ImportError:
            logger.info(message)

    def _record_error(self, error: Exception) -> None:
        """에러 기록"""
        self._error_count += 1
        self._last_errors.append({
            'error': str(error),
            'type': type(error).__name__,
            'timestamp': datetime.now()
        })
        if len(self._last_errors) > self._max_errors:
            self._last_errors.pop(0)

    def get_error_stats(self) -> dict:
        """에러 통계"""
        return {
            'total_errors': self._error_count,
            'recent_errors': len(self._last_errors),
            'last_errors': self._last_errors[-5:]
        }


class GracefulExecution:
    """
    컨텍스트 매니저: 안전한 코드 실행

    Usage:
        with GracefulExecution("데이터 로드", default_value=[]):
            data = load_data()
            process(data)
    """

    def __init__(
        self,
        operation_name: str,
        default_value: Any = None,
        show_error: bool = True,
        log_error: bool = True
    ):
        self.operation_name = operation_name
        self.default_value = default_value
        self.show_error = show_error
        self.log_error = log_error
        self.error = None
        self.success = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.success = False
            self.error = exc_val

            if self.log_error:
                log_error(
                    exc_val,
                    context={'operation': self.operation_name}
                )

            if self.show_error:
                try:
                    import streamlit as st
                    st.error(f"❌ {self.operation_name} 중 오류가 발생했습니다: {exc_val}")
                except ImportError:
                    pass

            # 예외 억제
            return True

        return False


def streamlit_safe(
    operation_name: str = "작업",
    default_value: Any = None,
    show_spinner: bool = True
):
    """
    Streamlit 안전 실행 데코레이터

    Args:
        operation_name: 작업 이름 (에러 메시지에 표시)
        default_value: 에러 시 반환할 기본값
        show_spinner: 스피너 표시 여부
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                import streamlit as st

                if show_spinner:
                    with st.spinner(f"{operation_name} 중..."):
                        return func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)

            except Exception as e:
                log_error(e, context={'operation': operation_name})

                try:
                    import streamlit as st
                    st.error(f"❌ {operation_name} 실패: {e}")
                except ImportError:
                    pass

                if callable(default_value):
                    return default_value()
                return default_value

        return wrapper
    return decorator


def validate_input(
    value: Any,
    name: str,
    validator: Callable[[Any], bool],
    error_message: str = None
) -> Any:
    """
    입력값 검증

    Args:
        value: 검증할 값
        name: 필드명
        validator: 검증 함수 (True/False 반환)
        error_message: 커스텀 에러 메시지

    Returns:
        검증된 값

    Raises:
        ValidationError: 검증 실패 시
    """
    if not validator(value):
        msg = error_message or f"'{name}' 값이 유효하지 않습니다: {value}"
        raise ValidationError(msg, context={'field': name, 'value': str(value)[:100]})
    return value


def require_not_empty(value: Any, name: str) -> Any:
    """값이 비어있지 않은지 검증"""
    if value is None or (hasattr(value, '__len__') and len(value) == 0):
        raise ValidationError(f"'{name}' 값이 필요합니다.", context={'field': name})
    return value


def require_positive(value: float, name: str) -> float:
    """양수인지 검증"""
    if value is None or value <= 0:
        raise ValidationError(f"'{name}'은(는) 양수여야 합니다.", context={'field': name, 'value': value})
    return value


def require_in_range(value: float, name: str, min_val: float, max_val: float) -> float:
    """범위 내 값인지 검증"""
    if value is None or not (min_val <= value <= max_val):
        raise ValidationError(
            f"'{name}'은(는) {min_val}~{max_val} 범위여야 합니다.",
            context={'field': name, 'value': value, 'range': (min_val, max_val)}
        )
    return value


# 전역 Streamlit 에러 핸들러 인스턴스
st_error_handler = StreamlitErrorHandler()
