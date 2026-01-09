"""
error_handler 모듈 테스트
"""

import pytest
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.error_handler import (
    AppError, NetworkError, DataError, ValidationError, APIError, CalculationError,
    ErrorSeverity, ErrorCategory, ErrorCollector,
    safe_execute, handle_errors, retry_on_error, format_error_for_ui
)


class TestAppError:
    """AppError 클래스 테스트"""

    def test_basic_error(self):
        """기본 에러 생성"""
        error = AppError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.category == ErrorCategory.UNKNOWN
        assert error.severity == ErrorSeverity.ERROR

    def test_error_with_category(self):
        """카테고리 지정"""
        error = AppError("Network issue", category=ErrorCategory.NETWORK)
        assert error.category == ErrorCategory.NETWORK

    def test_error_with_original(self):
        """원본 에러 포함"""
        original = ValueError("Original error")
        error = AppError("Wrapped error", original_error=original)
        assert error.original_error == original

    def test_error_to_dict(self):
        """딕셔너리 변환"""
        error = AppError("Test error", category=ErrorCategory.API)
        result = error.to_dict()

        assert result['message'] == "Test error"
        assert result['category'] == "api"
        assert 'timestamp' in result


class TestSpecificErrors:
    """특정 에러 타입 테스트"""

    def test_network_error(self):
        """NetworkError"""
        error = NetworkError("Connection failed")
        assert error.category == ErrorCategory.NETWORK

    def test_data_error(self):
        """DataError"""
        error = DataError("Invalid data format")
        assert error.category == ErrorCategory.DATA

    def test_validation_error(self):
        """ValidationError"""
        error = ValidationError("Invalid input")
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.WARNING

    def test_api_error(self):
        """APIError"""
        error = APIError("API request failed")
        assert error.category == ErrorCategory.API

    def test_calculation_error(self):
        """CalculationError"""
        error = CalculationError("Division by zero")
        assert error.category == ErrorCategory.CALCULATION


class TestSafeExecute:
    """safe_execute 함수 테스트"""

    def test_successful_execution(self):
        """성공적인 실행"""
        def add(a, b):
            return a + b

        result = safe_execute(add, 2, 3)
        assert result == 5

    def test_failed_execution_returns_default(self):
        """실패 시 기본값 반환"""
        def fail():
            raise ValueError("Error")

        result = safe_execute(fail, default="fallback")
        assert result == "fallback"

    def test_failed_execution_raises(self):
        """실패 시 예외 발생"""
        def fail():
            raise ValueError("Error")

        with pytest.raises(AppError):
            safe_execute(fail, raise_errors=True)


class TestHandleErrorsDecorator:
    """handle_errors 데코레이터 테스트"""

    def test_successful_function(self):
        """성공하는 함수"""
        @handle_errors(default_return=None)
        def success():
            return "ok"

        assert success() == "ok"

    def test_failing_function_returns_default(self):
        """실패하는 함수 - 기본값 반환"""
        @handle_errors(default_return="default")
        def fail():
            raise ValueError("Error")

        assert fail() == "default"

    def test_failing_function_raises(self):
        """실패하는 함수 - 예외 발생"""
        @handle_errors(raise_errors=True)
        def fail():
            raise ValueError("Error")

        with pytest.raises(AppError):
            fail()

    def test_callable_default(self):
        """callable 기본값"""
        @handle_errors(default_return=lambda: [])
        def fail():
            raise ValueError("Error")

        result = fail()
        assert result == []

    def test_specific_exceptions(self):
        """특정 예외만 처리"""
        @handle_errors(default_return="handled", exceptions=(ValueError,))
        def fail():
            raise ValueError("Error")

        assert fail() == "handled"


class TestRetryOnError:
    """retry_on_error 데코레이터 테스트"""

    def test_success_on_first_try(self):
        """첫 시도 성공"""
        call_count = 0

        @retry_on_error(max_retries=3, delay=0.01)
        def success():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = success()
        assert result == "ok"
        assert call_count == 1

    def test_success_after_retries(self):
        """재시도 후 성공"""
        call_count = 0

        @retry_on_error(max_retries=3, delay=0.01)
        def succeed_on_third():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "ok"

        result = succeed_on_third()
        assert result == "ok"
        assert call_count == 3

    def test_all_retries_fail(self):
        """모든 재시도 실패"""
        call_count = 0

        @retry_on_error(max_retries=3, delay=0.01)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            always_fail()

        assert call_count == 4  # 초기 시도 + 3번 재시도


class TestErrorCollector:
    """ErrorCollector 클래스 테스트"""

    def test_add_error(self):
        """에러 추가"""
        collector = ErrorCollector()
        collector.add(ValueError("Error 1"))
        collector.add(TypeError("Error 2"))

        assert collector.has_errors()
        assert len(collector.get_errors()) == 2

    def test_empty_collector(self):
        """빈 컬렉터"""
        collector = ErrorCollector()
        assert not collector.has_errors()

    def test_get_messages(self):
        """메시지 목록"""
        collector = ErrorCollector()
        collector.add(ValueError("Error 1"))
        collector.add(TypeError("Error 2"))

        messages = collector.get_messages()
        assert "Error 1" in messages
        assert "Error 2" in messages

    def test_clear(self):
        """에러 초기화"""
        collector = ErrorCollector()
        collector.add(ValueError("Error"))

        collector.clear()
        assert not collector.has_errors()

    def test_raise_if_errors(self):
        """에러 있으면 예외 발생"""
        collector = ErrorCollector()
        collector.add(ValueError("Error"))

        with pytest.raises(AppError):
            collector.raise_if_errors()


class TestFormatErrorForUI:
    """format_error_for_ui 함수 테스트"""

    def test_validation_error(self):
        """ValidationError 포맷"""
        error = ValidationError("입력이 잘못되었습니다")
        result = format_error_for_ui(error)
        assert "입력 오류" in result

    def test_network_error(self):
        """NetworkError 포맷"""
        error = NetworkError("연결 실패")
        result = format_error_for_ui(error)
        assert "네트워크 오류" in result

    def test_data_error(self):
        """DataError 포맷"""
        error = DataError("데이터 형식 오류")
        result = format_error_for_ui(error)
        assert "데이터 오류" in result

    def test_api_error(self):
        """APIError 포맷"""
        error = APIError("API 호출 실패")
        result = format_error_for_ui(error)
        assert "API 오류" in result

    def test_generic_error(self):
        """일반 예외 포맷"""
        error = ValueError("일반 오류")
        result = format_error_for_ui(error)
        assert "오류가 발생했습니다" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
