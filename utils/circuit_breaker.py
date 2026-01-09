"""
Circuit Breaker 패턴 구현
API 호출 실패 시 자동 복구 메커니즘
"""

import time
import threading
import logging
from enum import Enum
from typing import Callable, Optional, Any, Dict
from functools import wraps
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit Breaker 상태"""
    CLOSED = "closed"      # 정상 - 요청 통과
    OPEN = "open"          # 차단 - 요청 거부
    HALF_OPEN = "half_open"  # 테스트 - 일부 요청 허용


@dataclass
class CircuitStats:
    """Circuit Breaker 통계"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changes: list = field(default_factory=list)


class CircuitBreakerError(Exception):
    """Circuit Breaker가 열렸을 때 발생하는 예외"""
    def __init__(self, message: str, circuit_name: str, retry_after: float):
        super().__init__(message)
        self.circuit_name = circuit_name
        self.retry_after = retry_after


class CircuitBreaker:
    """
    Circuit Breaker 구현

    사용법:
        breaker = CircuitBreaker(name="api", failure_threshold=5)

        @breaker
        def call_api():
            return requests.get(url)
    """

    def __init__(
        self,
        name: str = "default",
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: float = 30.0,
        excluded_exceptions: tuple = ()
    ):
        """
        Args:
            name: Circuit Breaker 이름
            failure_threshold: OPEN 상태로 전환되는 실패 횟수
            success_threshold: HALF_OPEN에서 CLOSED로 전환되는 성공 횟수
            timeout: OPEN 상태 유지 시간(초)
            excluded_exceptions: 실패로 카운트하지 않을 예외
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout = timeout
        self.excluded_exceptions = excluded_exceptions

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()
        self._stats = CircuitStats()

    @property
    def state(self) -> CircuitState:
        """현재 상태"""
        with self._lock:
            if self._state == CircuitState.OPEN:
                # 타임아웃 확인
                if self._should_attempt_reset():
                    self._transition_to(CircuitState.HALF_OPEN)
            return self._state

    @property
    def is_closed(self) -> bool:
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        return self.state == CircuitState.HALF_OPEN

    def _should_attempt_reset(self) -> bool:
        """HALF_OPEN으로 전환 여부 확인"""
        if self._last_failure_time is None:
            return False
        return time.time() - self._last_failure_time >= self.timeout

    def _transition_to(self, new_state: CircuitState):
        """상태 전환"""
        old_state = self._state
        self._state = new_state

        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._success_count = 0

        self._stats.state_changes.append({
            'from': old_state.value,
            'to': new_state.value,
            'timestamp': datetime.now().isoformat()
        })

        logger.info(f"Circuit '{self.name}': {old_state.value} -> {new_state.value}")

    def _handle_success(self):
        """성공 처리"""
        with self._lock:
            self._stats.successful_calls += 1
            self._stats.last_success_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
            elif self._state == CircuitState.CLOSED:
                # 성공 시 실패 카운트 감소
                self._failure_count = max(0, self._failure_count - 1)

    def _handle_failure(self, exception: Exception):
        """실패 처리"""
        # 제외된 예외인지 확인
        if isinstance(exception, self.excluded_exceptions):
            return

        with self._lock:
            self._stats.failed_calls += 1
            self._stats.last_failure_time = time.time()
            self._last_failure_time = time.time()
            self._failure_count += 1

            if self._state == CircuitState.HALF_OPEN:
                # HALF_OPEN에서 실패하면 즉시 OPEN
                self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    self._transition_to(CircuitState.OPEN)

    def _can_execute(self) -> bool:
        """실행 가능 여부"""
        state = self.state  # property 호출로 상태 업데이트

        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.OPEN:
            return False
        elif state == CircuitState.HALF_OPEN:
            return True

        return False

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """함수 호출"""
        with self._lock:
            self._stats.total_calls += 1

        if not self._can_execute():
            with self._lock:
                self._stats.rejected_calls += 1

            retry_after = self.timeout
            if self._last_failure_time:
                retry_after = max(0, self.timeout - (time.time() - self._last_failure_time))

            raise CircuitBreakerError(
                f"Circuit '{self.name}' is OPEN. Retry after {retry_after:.1f}s",
                self.name,
                retry_after
            )

        try:
            result = func(*args, **kwargs)
            self._handle_success()
            return result
        except Exception as e:
            self._handle_failure(e)
            raise

    def __call__(self, func: Callable) -> Callable:
        """데코레이터로 사용"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)

        # 메타데이터 추가
        wrapper.circuit_breaker = self
        return wrapper

    def reset(self):
        """수동 리셋"""
        with self._lock:
            self._transition_to(CircuitState.CLOSED)
            self._failure_count = 0
            self._success_count = 0
            self._last_failure_time = None
            logger.info(f"Circuit '{self.name}' manually reset")

    def get_stats(self) -> Dict:
        """통계 조회"""
        with self._lock:
            return {
                'name': self.name,
                'state': self._state.value,
                'failure_count': self._failure_count,
                'success_count': self._success_count,
                'total_calls': self._stats.total_calls,
                'successful_calls': self._stats.successful_calls,
                'failed_calls': self._stats.failed_calls,
                'rejected_calls': self._stats.rejected_calls,
                'last_failure_time': self._stats.last_failure_time,
                'last_success_time': self._stats.last_success_time,
                'state_changes': self._stats.state_changes[-10:]  # 최근 10개
            }


class CircuitBreakerRegistry:
    """Circuit Breaker 레지스트리 (싱글톤)"""

    _instance: Optional['CircuitBreakerRegistry'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._breakers: Dict[str, CircuitBreaker] = {}
                    cls._instance._registry_lock = threading.Lock()
        return cls._instance

    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: float = 30.0
    ) -> CircuitBreaker:
        """Circuit Breaker 가져오기 또는 생성"""
        with self._registry_lock:
            if name not in self._breakers:
                self._breakers[name] = CircuitBreaker(
                    name=name,
                    failure_threshold=failure_threshold,
                    success_threshold=success_threshold,
                    timeout=timeout
                )
            return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Circuit Breaker 가져오기"""
        with self._registry_lock:
            return self._breakers.get(name)

    def get_all_stats(self) -> Dict[str, Dict]:
        """모든 Circuit Breaker 통계"""
        with self._registry_lock:
            return {
                name: breaker.get_stats()
                for name, breaker in self._breakers.items()
            }

    def reset_all(self):
        """모든 Circuit Breaker 리셋"""
        with self._registry_lock:
            for breaker in self._breakers.values():
                breaker.reset()


# 전역 레지스트리
registry = CircuitBreakerRegistry()


def circuit_breaker(
    name: str = "default",
    failure_threshold: int = 5,
    success_threshold: int = 2,
    timeout: float = 30.0
):
    """
    Circuit Breaker 데코레이터

    사용법:
        @circuit_breaker(name="api", failure_threshold=3)
        def call_api():
            return requests.get(url)
    """
    breaker = registry.get_or_create(
        name=name,
        failure_threshold=failure_threshold,
        success_threshold=success_threshold,
        timeout=timeout
    )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)

        wrapper.circuit_breaker = breaker
        return wrapper

    return decorator


def get_circuit_status(name: str) -> Optional[Dict]:
    """Circuit Breaker 상태 조회"""
    breaker = registry.get(name)
    if breaker:
        return breaker.get_stats()
    return None


def reset_circuit(name: str) -> bool:
    """Circuit Breaker 리셋"""
    breaker = registry.get(name)
    if breaker:
        breaker.reset()
        return True
    return False


def get_all_circuit_stats() -> Dict[str, Dict]:
    """모든 Circuit Breaker 통계"""
    return registry.get_all_stats()
