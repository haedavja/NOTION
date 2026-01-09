"""
대시보드 입력 유효성 검사 모듈
Streamlit UI에 최적화된 입력 검증 및 보안
"""

import re
import html
import logging
from typing import Optional, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """유효성 검사 결과"""
    is_valid: bool
    value: Any  # 정제된 값
    error: Optional[str] = None


class DashboardValidator:
    """대시보드 입력 유효성 검사기"""

    # 허용된 티커 심볼 패턴
    TICKER_PATTERN = re.compile(r'^[A-Z0-9.\-]{1,15}$')

    # XSS 방지를 위한 위험 패턴
    XSS_PATTERNS = [
        re.compile(r'<script', re.IGNORECASE),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'on\w+\s*=', re.IGNORECASE),
        re.compile(r'<iframe', re.IGNORECASE),
    ]

    @staticmethod
    def sanitize_string(value: str, max_length: int = 500) -> str:
        """
        문자열 정제 (XSS 방지)

        Args:
            value: 입력 문자열
            max_length: 최대 길이

        Returns:
            정제된 문자열
        """
        if not value:
            return ""

        # 길이 제한
        value = str(value)[:max_length]

        # HTML 이스케이프
        value = html.escape(value)

        # 위험한 패턴 확인 및 제거
        for pattern in DashboardValidator.XSS_PATTERNS:
            if pattern.search(value):
                logger.warning(f"Potential XSS pattern detected and removed")
                value = pattern.sub('', value)

        return value.strip()

    @staticmethod
    def validate_ticker_symbol(symbol: str) -> ValidationResult:
        """
        티커 심볼 유효성 검사

        Args:
            symbol: 티커 심볼 (예: AAPL, 005930.KS)

        Returns:
            ValidationResult
        """
        if not symbol:
            return ValidationResult(False, None, "티커 심볼을 입력하세요.")

        # 정제
        cleaned = str(symbol).strip().upper()

        # 길이 확인
        if len(cleaned) > 15:
            return ValidationResult(False, None, "티커 심볼이 너무 깁니다 (최대 15자).")

        if len(cleaned) < 1:
            return ValidationResult(False, None, "티커 심볼을 입력하세요.")

        # 패턴 확인
        if not DashboardValidator.TICKER_PATTERN.match(cleaned):
            return ValidationResult(
                False, None,
                "유효하지 않은 티커 심볼입니다. 영문, 숫자, '.', '-'만 사용 가능합니다."
            )

        return ValidationResult(True, cleaned, None)

    @staticmethod
    def validate_quantity(value: Any) -> ValidationResult:
        """
        수량 유효성 검사

        Args:
            value: 수량 값

        Returns:
            ValidationResult
        """
        if value is None or value == '':
            return ValidationResult(False, None, "수량을 입력하세요.")

        try:
            quantity = float(value)

            if quantity <= 0:
                return ValidationResult(False, None, "수량은 0보다 커야 합니다.")

            if quantity > 1_000_000_000:
                return ValidationResult(False, None, "수량이 너무 큽니다 (최대 10억).")

            # 소수점 처리
            if quantity == int(quantity):
                quantity = int(quantity)

            return ValidationResult(True, quantity, None)

        except (ValueError, TypeError):
            return ValidationResult(False, None, "유효한 숫자를 입력하세요.")

    @staticmethod
    def validate_price(value: Any, field_name: str = "가격") -> ValidationResult:
        """
        가격 유효성 검사

        Args:
            value: 가격 값
            field_name: 필드 이름 (에러 메시지용)

        Returns:
            ValidationResult
        """
        if value is None or value == '':
            return ValidationResult(False, None, f"{field_name}을(를) 입력하세요.")

        try:
            price = float(value)

            if price < 0:
                return ValidationResult(False, None, f"{field_name}은(는) 0 이상이어야 합니다.")

            if price > 1_000_000_000:
                return ValidationResult(False, None, f"{field_name}이(가) 너무 큽니다.")

            return ValidationResult(True, round(price, 4), None)

        except (ValueError, TypeError):
            return ValidationResult(False, None, f"유효한 {field_name}을(를) 입력하세요.")

    @staticmethod
    def validate_percentage(value: Any, field_name: str = "비율") -> ValidationResult:
        """
        퍼센트 유효성 검사

        Args:
            value: 비율 값
            field_name: 필드 이름

        Returns:
            ValidationResult
        """
        if value is None or value == '':
            return ValidationResult(True, None, None)  # 선택적 필드

        try:
            pct = float(value)

            if pct < -100:
                return ValidationResult(False, None, f"{field_name}은(는) -100% 이상이어야 합니다.")

            if pct > 1000:
                return ValidationResult(False, None, f"{field_name}이(가) 너무 큽니다 (최대 1000%).")

            return ValidationResult(True, round(pct, 2), None)

        except (ValueError, TypeError):
            return ValidationResult(False, None, f"유효한 {field_name}을(를) 입력하세요.")

    @staticmethod
    def validate_name(value: str, max_length: int = 100) -> ValidationResult:
        """
        이름 유효성 검사 (종목명, 포트폴리오명 등)

        Args:
            value: 이름 문자열
            max_length: 최대 길이

        Returns:
            ValidationResult
        """
        if not value:
            return ValidationResult(False, None, "이름을 입력하세요.")

        cleaned = DashboardValidator.sanitize_string(value, max_length)

        if len(cleaned) < 1:
            return ValidationResult(False, None, "이름을 입력하세요.")

        return ValidationResult(True, cleaned, None)

    @staticmethod
    def validate_text(value: str, max_length: int = 1000, required: bool = False) -> ValidationResult:
        """
        일반 텍스트 유효성 검사

        Args:
            value: 텍스트
            max_length: 최대 길이
            required: 필수 여부

        Returns:
            ValidationResult
        """
        if not value:
            if required:
                return ValidationResult(False, None, "텍스트를 입력하세요.")
            return ValidationResult(True, "", None)

        cleaned = DashboardValidator.sanitize_string(value, max_length)
        return ValidationResult(True, cleaned, None)

    @staticmethod
    def validate_date_range(start_date, end_date) -> ValidationResult:
        """
        날짜 범위 유효성 검사

        Args:
            start_date: 시작일
            end_date: 종료일

        Returns:
            ValidationResult
        """
        if not start_date:
            return ValidationResult(False, None, "시작일을 선택하세요.")

        if not end_date:
            return ValidationResult(False, None, "종료일을 선택하세요.")

        if start_date > end_date:
            return ValidationResult(
                False, None,
                "시작일은 종료일보다 이전이어야 합니다."
            )

        return ValidationResult(True, (start_date, end_date), None)

    @staticmethod
    def validate_email(email: str) -> ValidationResult:
        """
        이메일 유효성 검사

        Args:
            email: 이메일 주소

        Returns:
            ValidationResult
        """
        if not email:
            return ValidationResult(False, None, "이메일을 입력하세요.")

        email = str(email).strip().lower()

        # 기본 이메일 패턴
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

        if not email_pattern.match(email):
            return ValidationResult(False, None, "유효한 이메일 주소를 입력하세요.")

        if len(email) > 254:
            return ValidationResult(False, None, "이메일 주소가 너무 깁니다.")

        return ValidationResult(True, email, None)


class PositionValidator:
    """포지션 입력 유효성 검사"""

    @staticmethod
    def validate_new_position(
        symbol: str,
        quantity: Any,
        avg_cost: Any,
        current_price: Any = None,
        target_price: Any = None,
        stop_loss: Any = None,
        name: str = None
    ) -> Tuple[bool, dict, list]:
        """
        새 포지션 전체 유효성 검사

        Returns:
            Tuple of (is_valid, validated_data, errors)
        """
        errors = []
        data = {}

        # 심볼 검증
        result = DashboardValidator.validate_ticker_symbol(symbol)
        if not result.is_valid:
            errors.append(result.error)
        else:
            data['symbol'] = result.value

        # 수량 검증
        result = DashboardValidator.validate_quantity(quantity)
        if not result.is_valid:
            errors.append(result.error)
        else:
            data['quantity'] = result.value

        # 평균 단가 검증
        result = DashboardValidator.validate_price(avg_cost, "평균 단가")
        if not result.is_valid:
            errors.append(result.error)
        else:
            data['avg_cost'] = result.value

        # 현재가 검증 (선택적)
        if current_price is not None and current_price != '':
            result = DashboardValidator.validate_price(current_price, "현재가")
            if not result.is_valid:
                errors.append(result.error)
            else:
                data['current_price'] = result.value

        # 목표가 검증 (선택적)
        if target_price is not None and target_price != '':
            result = DashboardValidator.validate_price(target_price, "목표가")
            if not result.is_valid:
                errors.append(result.error)
            else:
                data['target_price'] = result.value

        # 손절가 검증 (선택적)
        if stop_loss is not None and stop_loss != '':
            result = DashboardValidator.validate_price(stop_loss, "손절가")
            if not result.is_valid:
                errors.append(result.error)
            else:
                data['stop_loss'] = result.value

        # 이름 검증 (선택적)
        if name:
            result = DashboardValidator.validate_name(name)
            if result.is_valid:
                data['name'] = result.value

        is_valid = len(errors) == 0
        return is_valid, data, errors


# 간편 함수들
def sanitize(value: str, max_length: int = 500) -> str:
    """문자열 정제 (간편 함수)"""
    return DashboardValidator.sanitize_string(value, max_length)


def validate_ticker(symbol: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """티커 검증 (간편 함수) - (is_valid, cleaned_value, error)"""
    result = DashboardValidator.validate_ticker_symbol(symbol)
    return result.is_valid, result.value, result.error


def validate_number(value: Any, min_val: float = None, max_val: float = None) -> Tuple[bool, Optional[float], Optional[str]]:
    """숫자 검증 (간편 함수)"""
    try:
        num = float(value)
        if min_val is not None and num < min_val:
            return False, None, f"값은 {min_val} 이상이어야 합니다."
        if max_val is not None and num > max_val:
            return False, None, f"값은 {max_val} 이하이어야 합니다."
        return True, num, None
    except (ValueError, TypeError):
        return False, None, "유효한 숫자를 입력하세요."
