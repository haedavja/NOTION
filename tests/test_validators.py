"""
validators 모듈 테스트
"""

import pytest
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.validators import (
    Validator, FormValidator, ValidationResult,
    validate_portfolio_input, validate_alert_input, validate_backtest_input
)


class TestValidator:
    """Validator 클래스 테스트"""

    def test_required_valid(self):
        """필수 값 검증 - 유효한 경우"""
        result = Validator.required("test", "테스트")
        assert result.is_valid
        assert result.sanitized_value == "test"

    def test_required_empty(self):
        """필수 값 검증 - 빈 값"""
        result = Validator.required("", "테스트")
        assert not result.is_valid
        assert "필수 입력" in result.error_message

    def test_required_none(self):
        """필수 값 검증 - None"""
        result = Validator.required(None, "테스트")
        assert not result.is_valid

    def test_string_valid(self):
        """문자열 검증 - 유효한 경우"""
        result = Validator.string("  hello world  ", min_length=5, max_length=20)
        assert result.is_valid
        assert result.sanitized_value == "hello world"

    def test_string_too_short(self):
        """문자열 검증 - 너무 짧음"""
        result = Validator.string("hi", field_name="이름", min_length=5)
        assert not result.is_valid
        assert "최소 5자" in result.error_message

    def test_string_too_long(self):
        """문자열 검증 - 너무 김"""
        result = Validator.string("a" * 50, field_name="이름", max_length=10)
        assert not result.is_valid
        assert "최대 10자" in result.error_message

    def test_number_valid(self):
        """숫자 검증 - 유효한 경우"""
        result = Validator.number("123.45", min_value=0, max_value=500)
        assert result.is_valid
        assert result.sanitized_value == 123.45

    def test_number_as_int(self):
        """숫자 검증 - 정수 변환"""
        result = Validator.number("123.99", as_int=True)
        assert result.is_valid
        assert result.sanitized_value == 123

    def test_number_invalid(self):
        """숫자 검증 - 유효하지 않은 값"""
        result = Validator.number("not_a_number")
        assert not result.is_valid
        assert "유효한 숫자" in result.error_message

    def test_number_negative_not_allowed(self):
        """숫자 검증 - 음수 불허"""
        result = Validator.number(-10, allow_negative=False)
        assert not result.is_valid
        assert "음수" in result.error_message

    def test_percentage_valid(self):
        """퍼센트 검증"""
        result = Validator.percentage(50)
        assert result.is_valid
        assert result.sanitized_value == 50.0

    def test_percentage_out_of_range(self):
        """퍼센트 검증 - 범위 초과"""
        result = Validator.percentage(150)
        assert not result.is_valid

    def test_email_valid(self):
        """이메일 검증 - 유효"""
        result = Validator.email("test@example.com")
        assert result.is_valid
        assert result.sanitized_value == "test@example.com"

    def test_email_invalid(self):
        """이메일 검증 - 유효하지 않음"""
        result = Validator.email("not_an_email")
        assert not result.is_valid
        assert "형식이 올바르지" in result.error_message

    def test_stock_symbol_us(self):
        """주식 심볼 검증 - 미국"""
        result = Validator.stock_symbol("AAPL")
        assert result.is_valid
        assert result.sanitized_value == "AAPL"

    def test_stock_symbol_korean(self):
        """주식 심볼 검증 - 한국"""
        result = Validator.stock_symbol("005930.KS")
        assert result.is_valid
        assert result.sanitized_value == "005930.KS"

    def test_stock_symbol_korean_convert(self):
        """주식 심볼 검증 - 한국 코드만 입력"""
        result = Validator.stock_symbol("005930")
        assert result.is_valid
        assert result.sanitized_value == "005930.KS"

    def test_stock_symbol_invalid(self):
        """주식 심볼 검증 - 유효하지 않음"""
        result = Validator.stock_symbol("invalid!@#")
        assert not result.is_valid

    def test_date_valid_string(self):
        """날짜 검증 - 문자열"""
        result = Validator.date("2024-01-15")
        assert result.is_valid
        assert result.sanitized_value.year == 2024
        assert result.sanitized_value.month == 1
        assert result.sanitized_value.day == 15

    def test_date_invalid(self):
        """날짜 검증 - 유효하지 않음"""
        result = Validator.date("not-a-date")
        assert not result.is_valid

    def test_currency_valid(self):
        """통화 검증 - 유효"""
        result = Validator.currency("1,000,000")
        assert result.is_valid
        assert result.sanitized_value == 1000000.0

    def test_currency_with_symbol(self):
        """통화 검증 - 통화 기호 포함"""
        result = Validator.currency("₩50,000")
        assert result.is_valid
        assert result.sanitized_value == 50000.0

    def test_in_choices_valid(self):
        """선택 항목 검증 - 유효"""
        result = Validator.in_choices("apple", ["apple", "banana", "orange"])
        assert result.is_valid

    def test_in_choices_invalid(self):
        """선택 항목 검증 - 유효하지 않음"""
        result = Validator.in_choices("grape", ["apple", "banana", "orange"])
        assert not result.is_valid

    def test_list_of_valid(self):
        """리스트 검증 - 유효"""
        result = Validator.list_of(
            ["AAPL", "MSFT", "GOOG"],
            Validator.stock_symbol,
            min_items=1
        )
        assert result.is_valid
        assert len(result.sanitized_value) == 3

    def test_list_of_invalid_items(self):
        """리스트 검증 - 유효하지 않은 항목"""
        result = Validator.list_of(
            ["AAPL", "invalid!@#"],
            Validator.stock_symbol
        )
        assert not result.is_valid


class TestFormValidator:
    """FormValidator 클래스 테스트"""

    def test_form_validation_success(self):
        """폼 검증 성공"""
        form = FormValidator()
        form.validate("name", Validator.string("John", min_length=2))
        form.validate("age", Validator.number(25, min_value=0))

        assert form.is_valid
        assert form.sanitized["name"] == "John"
        assert form.sanitized["age"] == 25.0

    def test_form_validation_failure(self):
        """폼 검증 실패"""
        form = FormValidator()
        form.validate("name", Validator.string("", allow_empty=False))
        form.validate("age", Validator.number(-5, allow_negative=False))

        assert not form.is_valid
        assert len(form.get_all_error_messages()) == 2


class TestPortfolioValidation:
    """포트폴리오 입력 검증 테스트"""

    def test_valid_portfolio_input(self):
        """유효한 포트폴리오 입력"""
        result = validate_portfolio_input(
            symbol="AAPL",
            quantity=10,
            price=150.0
        )
        assert result.is_valid

    def test_invalid_symbol(self):
        """유효하지 않은 심볼"""
        result = validate_portfolio_input(
            symbol="",
            quantity=10,
            price=150.0
        )
        assert not result.is_valid

    def test_invalid_quantity(self):
        """유효하지 않은 수량"""
        result = validate_portfolio_input(
            symbol="AAPL",
            quantity=-10,
            price=150.0
        )
        assert not result.is_valid


class TestAlertValidation:
    """알림 입력 검증 테스트"""

    def test_valid_alert_input(self):
        """유효한 알림 입력"""
        result = validate_alert_input(
            symbol="005930.KS",
            target_value=70000,
            condition="above"
        )
        assert result.is_valid

    def test_invalid_condition(self):
        """유효하지 않은 조건"""
        result = validate_alert_input(
            symbol="AAPL",
            target_value=150,
            condition="invalid_condition"
        )
        assert not result.is_valid


class TestBacktestValidation:
    """백테스트 입력 검증 테스트"""

    def test_valid_backtest_input(self):
        """유효한 백테스트 입력"""
        result = validate_backtest_input(
            symbols=["AAPL", "MSFT"],
            start_date="2023-01-01",
            end_date="2024-01-01",
            initial_capital=1000000
        )
        assert result.is_valid

    def test_empty_symbols(self):
        """빈 종목 리스트"""
        result = validate_backtest_input(
            symbols=[],
            start_date="2023-01-01",
            end_date="2024-01-01",
            initial_capital=1000000
        )
        assert not result.is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
