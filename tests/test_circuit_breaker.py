"""
circuit_breaker 모듈 테스트
"""

import pytest
import time
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.circuit_breaker import (
    CircuitBreaker, CircuitState, CircuitBreakerError,
    CircuitBreakerRegistry, circuit_breaker,
    get_circuit_status, reset_circuit, get_all_circuit_stats
)


class TestCircuitBreaker:
    """CircuitBreaker 클래스 테스트"""

    def test_initial_state_is_closed(self):
        """초기 상태는 CLOSED"""
        breaker = CircuitBreaker(name="test1")
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed

    def test_successful_calls_stay_closed(self):
        """성공하는 호출은 CLOSED 유지"""
        breaker = CircuitBreaker(name="test2", failure_threshold=3)

        @breaker
        def success():
            return "ok"

        for _ in range(10):
            result = success()
            assert result == "ok"

        assert breaker.is_closed

    def test_failures_open_circuit(self):
        """실패가 임계값에 도달하면 OPEN"""
        breaker = CircuitBreaker(name="test3", failure_threshold=3)

        @breaker
        def fail():
            raise ValueError("Error")

        # 3번 실패
        for _ in range(3):
            with pytest.raises(ValueError):
                fail()

        assert breaker.is_open

    def test_open_circuit_rejects_calls(self):
        """OPEN 상태에서 호출 거부"""
        breaker = CircuitBreaker(name="test4", failure_threshold=2, timeout=10)

        @breaker
        def fail():
            raise ValueError("Error")

        # 2번 실패해서 OPEN
        for _ in range(2):
            with pytest.raises(ValueError):
                fail()

        assert breaker.is_open

        # 이후 호출은 CircuitBreakerError
        with pytest.raises(CircuitBreakerError) as exc_info:
            fail()

        assert exc_info.value.circuit_name == "test4"
        assert exc_info.value.retry_after > 0

    def test_timeout_transitions_to_half_open(self):
        """타임아웃 후 HALF_OPEN으로 전환"""
        breaker = CircuitBreaker(name="test5", failure_threshold=2, timeout=0.5)

        @breaker
        def fail():
            raise ValueError("Error")

        # OPEN으로 전환
        for _ in range(2):
            with pytest.raises(ValueError):
                fail()

        assert breaker.is_open

        # 타임아웃 대기
        time.sleep(0.6)

        # HALF_OPEN으로 전환
        assert breaker.is_half_open

    def test_half_open_success_closes_circuit(self):
        """HALF_OPEN에서 성공하면 CLOSED"""
        breaker = CircuitBreaker(
            name="test6",
            failure_threshold=2,
            success_threshold=2,
            timeout=0.1
        )

        fail_count = 0

        @breaker
        def maybe_fail():
            nonlocal fail_count
            if fail_count < 2:
                fail_count += 1
                raise ValueError("Error")
            return "ok"

        # OPEN으로 전환
        for _ in range(2):
            with pytest.raises(ValueError):
                maybe_fail()

        assert breaker.is_open

        # 타임아웃 대기
        time.sleep(0.15)

        # HALF_OPEN에서 성공
        assert maybe_fail() == "ok"
        assert maybe_fail() == "ok"

        # success_threshold 달성 -> CLOSED
        assert breaker.is_closed

    def test_half_open_failure_reopens_circuit(self):
        """HALF_OPEN에서 실패하면 다시 OPEN"""
        breaker = CircuitBreaker(
            name="test7",
            failure_threshold=2,
            timeout=0.1
        )

        @breaker
        def fail():
            raise ValueError("Error")

        # OPEN으로 전환
        for _ in range(2):
            with pytest.raises(ValueError):
                fail()

        # 타임아웃 대기
        time.sleep(0.15)

        assert breaker.is_half_open

        # HALF_OPEN에서 실패
        with pytest.raises(ValueError):
            fail()

        # 다시 OPEN
        assert breaker.is_open

    def test_manual_reset(self):
        """수동 리셋"""
        breaker = CircuitBreaker(name="test8", failure_threshold=2, timeout=60)

        @breaker
        def fail():
            raise ValueError("Error")

        # OPEN으로 전환
        for _ in range(2):
            with pytest.raises(ValueError):
                fail()

        assert breaker.is_open

        # 수동 리셋
        breaker.reset()
        assert breaker.is_closed

    def test_excluded_exceptions_not_counted(self):
        """제외된 예외는 실패로 카운트 안함"""
        breaker = CircuitBreaker(
            name="test9",
            failure_threshold=2,
            excluded_exceptions=(KeyError,)
        )

        @breaker
        def raise_key_error():
            raise KeyError("Not counted")

        @breaker
        def raise_value_error():
            raise ValueError("Counted")

        # KeyError는 카운트 안됨
        for _ in range(5):
            with pytest.raises(KeyError):
                raise_key_error()

        assert breaker.is_closed  # 여전히 CLOSED

        # ValueError는 카운트됨
        for _ in range(2):
            with pytest.raises(ValueError):
                raise_value_error()

        assert breaker.is_open

    def test_stats(self):
        """통계 테스트"""
        breaker = CircuitBreaker(name="test10", failure_threshold=5)

        @breaker
        def success():
            return "ok"

        @breaker
        def fail():
            raise ValueError("Error")

        # 성공 호출
        for _ in range(3):
            success()

        # 실패 호출
        for _ in range(2):
            with pytest.raises(ValueError):
                fail()

        stats = breaker.get_stats()

        assert stats['total_calls'] == 5
        assert stats['successful_calls'] == 3
        assert stats['failed_calls'] == 2
        assert stats['state'] == 'closed'


class TestCircuitBreakerRegistry:
    """CircuitBreakerRegistry 테스트"""

    def test_get_or_create(self):
        """get_or_create 테스트"""
        registry = CircuitBreakerRegistry()

        breaker1 = registry.get_or_create("reg_test1", failure_threshold=5)
        breaker2 = registry.get_or_create("reg_test1", failure_threshold=10)  # 같은 이름

        # 같은 인스턴스
        assert breaker1 is breaker2
        assert breaker1.failure_threshold == 5  # 첫 번째 값 유지

    def test_get_nonexistent(self):
        """존재하지 않는 breaker 조회"""
        registry = CircuitBreakerRegistry()
        assert registry.get("nonexistent") is None

    def test_get_all_stats(self):
        """모든 통계 조회"""
        registry = CircuitBreakerRegistry()
        registry.get_or_create("stats_test1")
        registry.get_or_create("stats_test2")

        stats = registry.get_all_stats()

        assert "stats_test1" in stats
        assert "stats_test2" in stats


class TestCircuitBreakerDecorator:
    """circuit_breaker 데코레이터 테스트"""

    def test_decorator_usage(self):
        """데코레이터 사용"""
        @circuit_breaker(name="decorator_test", failure_threshold=3)
        def api_call():
            return "response"

        result = api_call()
        assert result == "response"

        # 메타데이터 확인
        assert hasattr(api_call, 'circuit_breaker')


class TestHelperFunctions:
    """헬퍼 함수 테스트"""

    def test_get_circuit_status(self):
        """get_circuit_status 테스트"""
        @circuit_breaker(name="helper_test1")
        def func():
            pass

        func()

        status = get_circuit_status("helper_test1")
        assert status is not None
        assert status['name'] == "helper_test1"

    def test_reset_circuit(self):
        """reset_circuit 테스트"""
        breaker = CircuitBreakerRegistry().get_or_create(
            "helper_test2",
            failure_threshold=1,
            timeout=60
        )

        @breaker
        def fail():
            raise ValueError()

        with pytest.raises(ValueError):
            fail()

        assert breaker.is_open

        # 리셋
        assert reset_circuit("helper_test2")
        assert breaker.is_closed

    def test_reset_nonexistent(self):
        """존재하지 않는 circuit 리셋"""
        assert not reset_circuit("nonexistent_circuit")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
