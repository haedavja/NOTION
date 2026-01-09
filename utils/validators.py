"""
입력 유효성 검사 모듈
폼 입력, API 요청, 데이터 검증
"""

import re
from typing import Optional, List, Any, Union, Callable, TypeVar
from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal, InvalidOperation


@dataclass
class ValidationResult:
    """유효성 검사 결과"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    sanitized_value: Any = None

    def add_error(self, message: str) -> None:
        """에러 추가"""
        self.errors.append(message)
        self.is_valid = False

    @property
    def error_message(self) -> str:
        """첫 번째 에러 메시지"""
        return self.errors[0] if self.errors else ""

    @property
    def all_errors(self) -> str:
        """모든 에러 메시지 (줄바꿈 구분)"""
        return "\n".join(self.errors)


class Validator:
    """기본 Validator 클래스"""

    @staticmethod
    def required(value: Any, field_name: str = "값") -> ValidationResult:
        """필수 값 검사"""
        result = ValidationResult(is_valid=True, sanitized_value=value)

        if value is None or (isinstance(value, str) and not value.strip()):
            result.add_error(f"{field_name}은(는) 필수 입력 항목입니다.")

        return result

    @staticmethod
    def string(
        value: Any,
        field_name: str = "값",
        min_length: int = 0,
        max_length: int = 10000,
        pattern: Optional[str] = None,
        allow_empty: bool = True
    ) -> ValidationResult:
        """문자열 검사"""
        result = ValidationResult(is_valid=True)

        if value is None:
            if not allow_empty:
                result.add_error(f"{field_name}은(는) 필수입니다.")
            result.sanitized_value = ""
            return result

        if not isinstance(value, str):
            value = str(value)

        # 공백 정리
        value = value.strip()
        result.sanitized_value = value

        if not allow_empty and not value:
            result.add_error(f"{field_name}은(는) 비어있을 수 없습니다.")
            return result

        if len(value) < min_length:
            result.add_error(f"{field_name}은(는) 최소 {min_length}자 이상이어야 합니다.")

        if len(value) > max_length:
            result.add_error(f"{field_name}은(는) 최대 {max_length}자까지 입력 가능합니다.")

        if pattern and value and not re.match(pattern, value):
            result.add_error(f"{field_name}의 형식이 올바르지 않습니다.")

        return result

    @staticmethod
    def number(
        value: Any,
        field_name: str = "값",
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        allow_zero: bool = True,
        allow_negative: bool = True,
        as_int: bool = False
    ) -> ValidationResult:
        """숫자 검사"""
        result = ValidationResult(is_valid=True)

        if value is None or value == "":
            result.add_error(f"{field_name}은(는) 필수입니다.")
            return result

        try:
            if as_int:
                num_value = int(float(value))
            else:
                num_value = float(value)

            result.sanitized_value = num_value

            if not allow_zero and num_value == 0:
                result.add_error(f"{field_name}은(는) 0이 될 수 없습니다.")

            if not allow_negative and num_value < 0:
                result.add_error(f"{field_name}은(는) 음수가 될 수 없습니다.")

            if min_value is not None and num_value < min_value:
                result.add_error(f"{field_name}은(는) {min_value} 이상이어야 합니다.")

            if max_value is not None and num_value > max_value:
                result.add_error(f"{field_name}은(는) {max_value} 이하여야 합니다.")

        except (ValueError, TypeError):
            result.add_error(f"{field_name}은(는) 유효한 숫자여야 합니다.")

        return result

    @staticmethod
    def percentage(
        value: Any,
        field_name: str = "비율",
        min_value: float = 0.0,
        max_value: float = 100.0
    ) -> ValidationResult:
        """퍼센트 검사 (0-100)"""
        return Validator.number(
            value,
            field_name=field_name,
            min_value=min_value,
            max_value=max_value,
            allow_negative=False
        )

    @staticmethod
    def email(value: str, field_name: str = "이메일") -> ValidationResult:
        """이메일 형식 검사"""
        result = ValidationResult(is_valid=True)

        if not value:
            result.add_error(f"{field_name}은(는) 필수입니다.")
            return result

        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

        if not re.match(email_pattern, value):
            result.add_error(f"{field_name} 형식이 올바르지 않습니다.")
        else:
            result.sanitized_value = value.lower().strip()

        return result

    @staticmethod
    def stock_symbol(
        value: str,
        field_name: str = "종목코드",
        allow_korean: bool = True
    ) -> ValidationResult:
        """주식 심볼 검사"""
        result = ValidationResult(is_valid=True)

        if not value:
            result.add_error(f"{field_name}은(는) 필수입니다.")
            return result

        value = value.strip().upper()
        result.sanitized_value = value

        # 미국 주식: 1-5자 알파벳
        us_pattern = r'^[A-Z]{1,5}$'

        # 한국 주식: 6자리 숫자 + .KS/.KQ
        kr_pattern = r'^\d{6}\.(KS|KQ)$'

        if re.match(us_pattern, value):
            return result

        if allow_korean and re.match(kr_pattern, value):
            return result

        # 숫자만 있는 경우 (한국 주식코드)
        if allow_korean and re.match(r'^\d{6}$', value):
            result.sanitized_value = f"{value}.KS"
            return result

        result.add_error(f"{field_name} 형식이 올바르지 않습니다. (예: AAPL 또는 005930.KS)")
        return result

    @staticmethod
    def date(
        value: Any,
        field_name: str = "날짜",
        min_date: Optional[date] = None,
        max_date: Optional[date] = None,
        formats: List[str] = None
    ) -> ValidationResult:
        """날짜 검사"""
        result = ValidationResult(is_valid=True)

        if formats is None:
            formats = ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%Y.%m.%d"]

        if value is None:
            result.add_error(f"{field_name}은(는) 필수입니다.")
            return result

        # 이미 date 타입인 경우
        if isinstance(value, date):
            result.sanitized_value = value
        elif isinstance(value, datetime):
            result.sanitized_value = value.date()
        elif isinstance(value, str):
            parsed = None
            for fmt in formats:
                try:
                    parsed = datetime.strptime(value.strip(), fmt).date()
                    break
                except ValueError:
                    continue

            if parsed is None:
                result.add_error(f"{field_name} 형식이 올바르지 않습니다. (예: YYYY-MM-DD)")
                return result

            result.sanitized_value = parsed
        else:
            result.add_error(f"{field_name}은(는) 유효한 날짜여야 합니다.")
            return result

        # 범위 검사
        if result.sanitized_value:
            if min_date and result.sanitized_value < min_date:
                result.add_error(f"{field_name}은(는) {min_date} 이후여야 합니다.")

            if max_date and result.sanitized_value > max_date:
                result.add_error(f"{field_name}은(는) {max_date} 이전이어야 합니다.")

        return result

    @staticmethod
    def list_of(
        value: Any,
        item_validator: Callable[[Any], ValidationResult],
        field_name: str = "목록",
        min_items: int = 0,
        max_items: int = 1000
    ) -> ValidationResult:
        """리스트 항목 검사"""
        result = ValidationResult(is_valid=True)

        if not isinstance(value, (list, tuple)):
            result.add_error(f"{field_name}은(는) 목록이어야 합니다.")
            return result

        if len(value) < min_items:
            result.add_error(f"{field_name}은(는) 최소 {min_items}개 항목이 필요합니다.")

        if len(value) > max_items:
            result.add_error(f"{field_name}은(는) 최대 {max_items}개 항목까지 가능합니다.")

        sanitized = []
        for i, item in enumerate(value):
            item_result = item_validator(item)
            if not item_result.is_valid:
                for error in item_result.errors:
                    result.add_error(f"{field_name}[{i}]: {error}")
            else:
                sanitized.append(item_result.sanitized_value)

        result.sanitized_value = sanitized
        return result

    @staticmethod
    def in_choices(
        value: Any,
        choices: List[Any],
        field_name: str = "값"
    ) -> ValidationResult:
        """선택 항목 검사"""
        result = ValidationResult(is_valid=True, sanitized_value=value)

        if value not in choices:
            choices_str = ", ".join(str(c) for c in choices[:10])
            if len(choices) > 10:
                choices_str += f" 외 {len(choices) - 10}개"
            result.add_error(f"{field_name}은(는) 다음 중 하나여야 합니다: {choices_str}")

        return result

    @staticmethod
    def currency(
        value: Any,
        field_name: str = "금액",
        min_value: float = 0,
        max_value: float = 1e15
    ) -> ValidationResult:
        """통화 금액 검사"""
        result = ValidationResult(is_valid=True)

        if value is None or value == "":
            result.add_error(f"{field_name}은(는) 필수입니다.")
            return result

        # 쉼표, 원화 기호 제거
        if isinstance(value, str):
            value = value.replace(",", "").replace("₩", "").replace("$", "").strip()

        try:
            amount = Decimal(str(value))
            result.sanitized_value = float(amount)

            if amount < min_value:
                result.add_error(f"{field_name}은(는) {min_value:,.0f} 이상이어야 합니다.")

            if amount > max_value:
                result.add_error(f"{field_name}은(는) {max_value:,.0f} 이하여야 합니다.")

        except (InvalidOperation, ValueError):
            result.add_error(f"{field_name}은(는) 유효한 금액이어야 합니다.")

        return result

    @staticmethod
    def url(value: str, field_name: str = "URL") -> ValidationResult:
        """URL 형식 검사"""
        result = ValidationResult(is_valid=True)

        if not value:
            result.add_error(f"{field_name}은(는) 필수입니다.")
            return result

        url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'

        if not re.match(url_pattern, value, re.IGNORECASE):
            result.add_error(f"{field_name} 형식이 올바르지 않습니다.")
        else:
            result.sanitized_value = value.strip()

        return result


class FormValidator:
    """폼 전체 검증"""

    def __init__(self):
        self.errors: dict = {}
        self.sanitized: dict = {}

    def validate(
        self,
        field_name: str,
        result: ValidationResult
    ) -> 'FormValidator':
        """필드 검증 결과 추가"""
        if not result.is_valid:
            self.errors[field_name] = result.errors

        if result.sanitized_value is not None:
            self.sanitized[field_name] = result.sanitized_value

        return self

    @property
    def is_valid(self) -> bool:
        """전체 유효성"""
        return len(self.errors) == 0

    def get_errors(self) -> dict:
        """모든 에러"""
        return self.errors

    def get_all_error_messages(self) -> List[str]:
        """모든 에러 메시지 목록"""
        messages = []
        for field, errors in self.errors.items():
            messages.extend(errors)
        return messages

    def get_sanitized(self) -> dict:
        """정제된 데이터"""
        return self.sanitized


def validate_portfolio_input(
    symbol: str,
    quantity: Any,
    price: Any,
    name: str = ""
) -> FormValidator:
    """포트폴리오 입력 검증"""
    validator = FormValidator()

    validator.validate("symbol", Validator.stock_symbol(symbol))
    validator.validate("quantity", Validator.number(
        quantity,
        field_name="수량",
        min_value=0.001,
        allow_negative=False
    ))
    validator.validate("price", Validator.currency(
        price,
        field_name="가격",
        min_value=0.01
    ))

    if name:
        validator.validate("name", Validator.string(
            name,
            field_name="종목명",
            max_length=100
        ))

    return validator


def validate_alert_input(
    symbol: str,
    target_value: Any,
    condition: str
) -> FormValidator:
    """알림 입력 검증"""
    validator = FormValidator()

    validator.validate("symbol", Validator.stock_symbol(symbol))
    validator.validate("target_value", Validator.number(
        target_value,
        field_name="목표값",
        min_value=0.01,
        allow_negative=False
    ))
    validator.validate("condition", Validator.in_choices(
        condition,
        ["above", "below", "change"],
        field_name="조건"
    ))

    return validator


def validate_backtest_input(
    symbols: List[str],
    start_date: Any,
    end_date: Any,
    initial_capital: Any
) -> FormValidator:
    """백테스트 입력 검증"""
    validator = FormValidator()

    validator.validate("symbols", Validator.list_of(
        symbols,
        lambda s: Validator.stock_symbol(s),
        field_name="종목",
        min_items=1,
        max_items=50
    ))
    validator.validate("start_date", Validator.date(start_date, field_name="시작일"))
    validator.validate("end_date", Validator.date(end_date, field_name="종료일"))
    validator.validate("initial_capital", Validator.currency(
        initial_capital,
        field_name="초기 자본",
        min_value=10000
    ))

    return validator
