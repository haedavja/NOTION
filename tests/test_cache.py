"""
cache 모듈 테스트
"""

import pytest
import time
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.cache import (
    MemoryCache, FileCache, CacheEntry,
    cached, memoize, get_memory_cache, get_file_cache, clear_all_caches
)


class TestCacheEntry:
    """CacheEntry 클래스 테스트"""

    def test_not_expired(self):
        """만료되지 않은 엔트리"""
        entry = CacheEntry(
            value="test",
            created_at=time.time(),
            expires_at=time.time() + 100
        )
        assert not entry.is_expired

    def test_expired(self):
        """만료된 엔트리"""
        entry = CacheEntry(
            value="test",
            created_at=time.time() - 200,
            expires_at=time.time() - 100
        )
        assert entry.is_expired


class TestMemoryCache:
    """MemoryCache 클래스 테스트"""

    def test_set_and_get(self):
        """저장 및 조회"""
        cache = MemoryCache(max_size=10, default_ttl=60)
        cache.set("key1", "value1")

        result = cache.get("key1")
        assert result == "value1"

    def test_get_nonexistent(self):
        """존재하지 않는 키"""
        cache = MemoryCache()
        result = cache.get("nonexistent")
        assert result is None

    def test_expiration(self):
        """만료 테스트"""
        cache = MemoryCache(default_ttl=1)
        cache.set("key1", "value1", ttl=1)

        # 즉시 조회
        assert cache.get("key1") == "value1"

        # 만료 후 조회
        time.sleep(1.5)
        assert cache.get("key1") is None

    def test_lru_eviction(self):
        """LRU 제거 테스트"""
        cache = MemoryCache(max_size=3, default_ttl=60)

        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # key1 접근 (LRU 업데이트)
        cache.get("key1")

        # 새 항목 추가 (key2가 제거되어야 함)
        cache.set("key4", "value4")

        assert cache.get("key1") == "value1"  # 최근 접근
        assert cache.get("key2") is None      # LRU로 제거됨
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_delete(self):
        """삭제 테스트"""
        cache = MemoryCache()
        cache.set("key1", "value1")

        assert cache.delete("key1")
        assert cache.get("key1") is None
        assert not cache.delete("nonexistent")

    def test_clear(self):
        """전체 삭제 테스트"""
        cache = MemoryCache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_get_or_set(self):
        """get_or_set 테스트"""
        cache = MemoryCache()

        # 처음: factory 호출
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return "computed_value"

        result1 = cache.get_or_set("key1", factory)
        result2 = cache.get_or_set("key1", factory)

        assert result1 == "computed_value"
        assert result2 == "computed_value"
        assert call_count == 1  # factory는 한 번만 호출

    def test_stats(self):
        """통계 테스트"""
        cache = MemoryCache()
        cache.set("key1", "value1")

        cache.get("key1")  # hit
        cache.get("key2")  # miss

        stats = cache.get_stats()

        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['size'] == 1

    def test_cleanup_expired(self):
        """만료 항목 정리 테스트"""
        cache = MemoryCache(default_ttl=1)
        cache.set("key1", "value1", ttl=1)
        cache.set("key2", "value2", ttl=100)

        time.sleep(1.5)
        removed = cache.cleanup_expired()

        assert removed == 1
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"


class TestCachedDecorator:
    """cached 데코레이터 테스트"""

    def test_caching_function_result(self):
        """함수 결과 캐싱"""
        call_count = 0

        @cached(ttl=60)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = expensive_function(5)
        result2 = expensive_function(5)

        assert result1 == 10
        assert result2 == 10
        assert call_count == 1  # 한 번만 호출

    def test_different_args_cached_separately(self):
        """다른 인자는 별도로 캐싱"""
        call_count = 0

        @cached(ttl=60)
        def func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        func(5)
        func(10)
        func(5)  # 캐시에서

        assert call_count == 2

    def test_invalidate(self):
        """캐시 무효화"""
        @cached(ttl=60)
        def func(x):
            return x * 2

        result1 = func(5)
        func.invalidate(5)  # 무효화
        result2 = func(5)   # 다시 계산

        assert result1 == result2


class TestMemoize:
    """memoize 데코레이터 테스트"""

    def test_memoization(self):
        """메모이제이션"""
        call_count = 0

        @memoize
        def fibonacci(n):
            nonlocal call_count
            call_count += 1
            if n <= 1:
                return n
            return fibonacci(n-1) + fibonacci(n-2)

        result = fibonacci(10)
        assert result == 55

        # 메모이제이션 없이는 수백 번 호출됨
        # 메모이제이션으로 11번만 호출
        assert call_count == 11


class TestFileCache:
    """FileCache 클래스 테스트"""

    def test_set_and_get(self, tmp_path):
        """저장 및 조회"""
        cache = FileCache(cache_dir=str(tmp_path), default_ttl=60)
        cache.set("key1", {"data": "value1"})

        result = cache.get("key1")
        assert result == {"data": "value1"}

    def test_get_nonexistent(self, tmp_path):
        """존재하지 않는 키"""
        cache = FileCache(cache_dir=str(tmp_path))
        result = cache.get("nonexistent")
        assert result is None

    def test_delete(self, tmp_path):
        """삭제"""
        cache = FileCache(cache_dir=str(tmp_path))
        cache.set("key1", "value1")

        assert cache.delete("key1")
        assert cache.get("key1") is None

    def test_clear(self, tmp_path):
        """전체 삭제"""
        cache = FileCache(cache_dir=str(tmp_path))
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None


class TestGlobalCacheFunctions:
    """전역 캐시 함수 테스트"""

    def test_get_memory_cache(self):
        """메모리 캐시 인스턴스"""
        cache = get_memory_cache()
        assert isinstance(cache, MemoryCache)

    def test_get_file_cache(self):
        """파일 캐시 인스턴스"""
        cache = get_file_cache()
        assert isinstance(cache, FileCache)

    def test_clear_all_caches(self):
        """모든 캐시 정리"""
        result = clear_all_caches()
        assert 'memory_cleaned' in result
        assert 'file_cleaned' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
