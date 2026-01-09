"""
캐싱 유틸리티
데이터 캐싱 및 성능 최적화
"""

import time
import functools
import hashlib
import json
import pickle
import logging
from typing import Any, Callable, Optional, Dict, TypeVar, Generic
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from collections import OrderedDict

logger = logging.getLogger(__name__)

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """캐시 엔트리"""
    value: T
    created_at: float
    expires_at: float
    hits: int = 0

    @property
    def is_expired(self) -> bool:
        """만료 여부"""
        return time.time() > self.expires_at


class MemoryCache:
    """인메모리 캐시 (LRU 방식)"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._stats = {'hits': 0, 'misses': 0, 'evictions': 0}

    def get(self, key: str) -> Optional[Any]:
        """값 조회"""
        with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats['misses'] += 1
                return None

            if entry.is_expired:
                del self._cache[key]
                self._stats['misses'] += 1
                return None

            # LRU: 최근 사용한 항목을 맨 뒤로
            self._cache.move_to_end(key)
            entry.hits += 1
            self._stats['hits'] += 1

            return entry.value

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """값 저장"""
        ttl = ttl or self.default_ttl
        now = time.time()

        with self._lock:
            # 크기 제한 체크
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
                self._stats['evictions'] += 1

            self._cache[key] = CacheEntry(
                value=value,
                created_at=now,
                expires_at=now + ttl
            )

    def delete(self, key: str) -> bool:
        """값 삭제"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """전체 삭제"""
        with self._lock:
            self._cache.clear()

    def get_or_set(self, key: str, factory: Callable[[], T], ttl: int = None) -> T:
        """값이 없으면 생성하여 저장"""
        value = self.get(key)
        if value is not None:
            return value

        value = factory()
        self.set(key, value, ttl)
        return value

    def get_stats(self) -> Dict[str, Any]:
        """통계 조회"""
        with self._lock:
            total = self._stats['hits'] + self._stats['misses']
            hit_rate = (self._stats['hits'] / total * 100) if total > 0 else 0

            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._stats['hits'],
                'misses': self._stats['misses'],
                'hit_rate': f"{hit_rate:.1f}%",
                'evictions': self._stats['evictions']
            }

    def cleanup_expired(self) -> int:
        """만료된 항목 정리"""
        removed = 0
        with self._lock:
            expired_keys = [
                k for k, v in self._cache.items()
                if v.is_expired
            ]
            for key in expired_keys:
                del self._cache[key]
                removed += 1

        return removed


class FileCache:
    """파일 기반 캐시"""

    def __init__(self, cache_dir: str = None, default_ttl: int = 3600):
        if cache_dir is None:
            cache_dir = Path.home() / ".notion_portfolio" / "cache"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl = default_ttl

    def _get_path(self, key: str) -> Path:
        """키에 해당하는 파일 경로"""
        # 키를 해시하여 파일명 생성
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{hash_key}.cache"

    def get(self, key: str) -> Optional[Any]:
        """값 조회"""
        path = self._get_path(key)

        if not path.exists():
            return None

        try:
            with open(path, 'rb') as f:
                entry = pickle.load(f)

            if entry.is_expired:
                path.unlink()
                return None

            return entry.value

        except Exception as e:
            logger.debug(f"캐시 읽기 실패 ({key}): {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """값 저장"""
        ttl = ttl or self.default_ttl
        now = time.time()

        entry = CacheEntry(
            value=value,
            created_at=now,
            expires_at=now + ttl
        )

        path = self._get_path(key)

        try:
            with open(path, 'wb') as f:
                pickle.dump(entry, f)
        except Exception as e:
            logger.warning(f"캐시 저장 실패 ({key}): {e}")

    def delete(self, key: str) -> bool:
        """값 삭제"""
        path = self._get_path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def clear(self) -> None:
        """전체 삭제"""
        for path in self.cache_dir.glob("*.cache"):
            try:
                path.unlink()
            except Exception:
                pass

    def cleanup_expired(self) -> int:
        """만료된 캐시 정리"""
        removed = 0

        for path in self.cache_dir.glob("*.cache"):
            try:
                with open(path, 'rb') as f:
                    entry = pickle.load(f)

                if entry.is_expired:
                    path.unlink()
                    removed += 1

            except Exception:
                # 손상된 캐시 파일 삭제
                try:
                    path.unlink()
                    removed += 1
                except Exception:
                    pass

        return removed


# 전역 캐시 인스턴스
_memory_cache = MemoryCache(max_size=1000, default_ttl=300)
_file_cache = FileCache(default_ttl=3600)


def cached(ttl: int = 300, cache_type: str = "memory"):
    """
    캐싱 데코레이터

    Args:
        ttl: 캐시 유효 시간 (초)
        cache_type: 캐시 타입 ('memory' 또는 'file')

    Example:
        @cached(ttl=60)
        def get_stock_price(symbol):
            return fetch_from_api(symbol)
    """
    cache = _memory_cache if cache_type == "memory" else _file_cache

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            key_parts = [func.__module__, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)

            # 캐시 조회
            result = cache.get(cache_key)
            if result is not None:
                return result

            # 함수 실행 및 캐시 저장
            result = func(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result, ttl)

            return result

        # 캐시 무효화 메서드 추가
        def invalidate(*args, **kwargs):
            key_parts = [func.__module__, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)
            cache.delete(cache_key)

        wrapper.invalidate = invalidate
        wrapper.cache = cache

        return wrapper

    return decorator


def memoize(func: Callable) -> Callable:
    """
    간단한 메모이제이션 (영구 캐시)
    """
    cache = {}

    @functools.wraps(func)
    def wrapper(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]

    wrapper.cache = cache
    wrapper.clear = cache.clear

    return wrapper


def get_memory_cache() -> MemoryCache:
    """메모리 캐시 인스턴스"""
    return _memory_cache


def get_file_cache() -> FileCache:
    """파일 캐시 인스턴스"""
    return _file_cache


def clear_all_caches() -> Dict[str, int]:
    """모든 캐시 정리"""
    memory_removed = _memory_cache.cleanup_expired()
    file_removed = _file_cache.cleanup_expired()

    return {
        'memory_cleaned': memory_removed,
        'file_cleaned': file_removed
    }
