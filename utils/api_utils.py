"""
API 유틸리티
캐싱, 재시도 로직, 레이트 리미팅
"""

import time
import functools
from datetime import datetime, timedelta
from typing import Dict, Any, Callable, Optional
import hashlib
import json


class APICache:
    """간단한 메모리 캐시"""

    def __init__(self, default_ttl: int = 300):  # 기본 5분
        self._cache: Dict[str, Dict] = {}
        self.default_ttl = default_ttl

    def _make_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """캐시 키 생성"""
        key_data = f"{func_name}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """캐시에서 가져오기"""
        if key in self._cache:
            entry = self._cache[key]
            if datetime.now() < entry['expires']:
                return entry['data']
            else:
                del self._cache[key]
        return None

    def set(self, key: str, data: Any, ttl: int = None):
        """캐시에 저장"""
        ttl = ttl or self.default_ttl
        self._cache[key] = {
            'data': data,
            'expires': datetime.now() + timedelta(seconds=ttl),
            'created': datetime.now()
        }

    def clear(self):
        """캐시 비우기"""
        self._cache.clear()

    def cleanup(self):
        """만료된 항목 정리"""
        now = datetime.now()
        expired = [k for k, v in self._cache.items() if now >= v['expires']]
        for k in expired:
            del self._cache[k]


# 전역 캐시 인스턴스
_cache = APICache()


def cached(ttl: int = 300):
    """캐싱 데코레이터"""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = _cache._make_key(func.__name__, args, kwargs)
            cached_result = _cache.get(key)

            if cached_result is not None:
                return cached_result

            result = func(*args, **kwargs)
            _cache.set(key, result, ttl)
            return result
        return wrapper
    return decorator


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """재시도 데코레이터 (지수 백오프)"""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        sleep_time = delay * (backoff ** attempt)
                        print(f"[Retry] {func.__name__} 실패 (시도 {attempt + 1}/{max_retries}), {sleep_time:.1f}초 후 재시도...")
                        time.sleep(sleep_time)

            raise last_exception
        return wrapper
    return decorator


class RateLimiter:
    """레이트 리미터"""

    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self._call_times: list = []

    def wait_if_needed(self):
        """필요 시 대기"""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)

        # 1분 이전 호출 제거
        self._call_times = [t for t in self._call_times if t > minute_ago]

        if len(self._call_times) >= self.calls_per_minute:
            # 대기 필요
            oldest = self._call_times[0]
            wait_time = (oldest + timedelta(minutes=1) - now).total_seconds()
            if wait_time > 0:
                print(f"[RateLimit] {wait_time:.1f}초 대기...")
                time.sleep(wait_time)

        self._call_times.append(now)


def rate_limited(calls_per_minute: int = 60):
    """레이트 리미팅 데코레이터"""
    limiter = RateLimiter(calls_per_minute)

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            limiter.wait_if_needed()
            return func(*args, **kwargs)
        return wrapper
    return decorator


# 복합 데코레이터: 캐싱 + 재시도 + 레이트 리미팅
def robust_api_call(ttl: int = 300, max_retries: int = 3, calls_per_minute: int = 60):
    """강건한 API 호출 데코레이터"""
    def decorator(func: Callable):
        # 순서: 캐시 체크 -> 레이트 리밋 -> 재시도 -> 실행
        @cached(ttl)
        @rate_limited(calls_per_minute)
        @retry_on_failure(max_retries)
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator


def clear_cache():
    """전역 캐시 비우기"""
    _cache.clear()


def cleanup_cache():
    """만료된 캐시 정리"""
    _cache.cleanup()
