"""
성능 최적화 유틸리티
====================

데이터 로딩 최적화, 병렬 처리, 메모이제이션 등을 제공합니다.

주요 기능:
---------
- lazy_load: 지연 로딩 데코레이터
- batch_fetch: 배치 데이터 조회
- parallel_fetch: 병렬 데이터 조회
- memoize: 결과 메모이제이션

사용 예시:
---------
    @lazy_load
    def expensive_calculation():
        return calculate_something()

    # 배치 조회
    results = batch_fetch(['005930', '000660'], fetch_stock_data)
"""

import functools
import time
import logging
from typing import Callable, List, Dict, Any, TypeVar, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)

T = TypeVar('T')


# ============ 성능 측정 ============

@dataclass
class PerformanceMetrics:
    """성능 측정 결과"""
    function_name: str
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    last_call: Optional[datetime] = None

    @property
    def avg_time(self) -> float:
        return self.total_time / self.call_count if self.call_count > 0 else 0.0


class PerformanceTracker:
    """
    성능 추적기

    Usage:
        tracker = PerformanceTracker()

        @tracker.track
        def my_function():
            pass

        # 결과 확인
        tracker.report()
    """

    def __init__(self):
        self._metrics: Dict[str, PerformanceMetrics] = {}
        self._lock = threading.Lock()

    def track(self, func: Callable) -> Callable:
        """함수 성능 추적 데코레이터"""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                self._record(func.__name__, elapsed)
        return wrapper

    def _record(self, name: str, elapsed: float):
        """성능 기록"""
        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = PerformanceMetrics(function_name=name)

            m = self._metrics[name]
            m.call_count += 1
            m.total_time += elapsed
            m.min_time = min(m.min_time, elapsed)
            m.max_time = max(m.max_time, elapsed)
            m.last_call = datetime.now()

    def get_metrics(self, name: str) -> Optional[PerformanceMetrics]:
        """특정 함수 메트릭 조회"""
        return self._metrics.get(name)

    def report(self) -> Dict[str, Dict]:
        """전체 성능 리포트"""
        report = {}
        for name, m in self._metrics.items():
            report[name] = {
                'calls': m.call_count,
                'total_ms': round(m.total_time * 1000, 2),
                'avg_ms': round(m.avg_time * 1000, 2),
                'min_ms': round(m.min_time * 1000, 2),
                'max_ms': round(m.max_time * 1000, 2),
            }
        return report

    def reset(self):
        """메트릭 초기화"""
        with self._lock:
            self._metrics.clear()


# 전역 트래커
_performance_tracker = PerformanceTracker()


def get_performance_tracker() -> PerformanceTracker:
    """전역 성능 추적기 반환"""
    return _performance_tracker


def track_performance(func: Callable) -> Callable:
    """전역 성능 추적 데코레이터"""
    return _performance_tracker.track(func)


# ============ 지연 로딩 ============

class LazyValue:
    """
    지연 로딩 값

    값이 실제로 필요할 때까지 계산을 미룸
    """

    def __init__(self, func: Callable[[], T]):
        self._func = func
        self._value: Optional[T] = None
        self._computed = False
        self._lock = threading.Lock()

    @property
    def value(self) -> T:
        if not self._computed:
            with self._lock:
                if not self._computed:  # Double-check
                    self._value = self._func()
                    self._computed = True
        return self._value

    def reset(self):
        """값 재계산 강제"""
        with self._lock:
            self._computed = False
            self._value = None


def lazy_load(func: Callable[[], T]) -> LazyValue:
    """지연 로딩 데코레이터"""
    return LazyValue(func)


# ============ 배치 처리 ============

def batch_fetch(
    items: List[Any],
    fetch_func: Callable[[Any], T],
    batch_size: int = 10
) -> Dict[Any, T]:
    """
    배치 데이터 조회

    Args:
        items: 조회할 항목 리스트
        fetch_func: 개별 항목 조회 함수
        batch_size: 배치 크기

    Returns:
        {항목: 결과} 딕셔너리
    """
    results = {}

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        for item in batch:
            try:
                results[item] = fetch_func(item)
            except Exception as e:
                logger.warning(f"배치 조회 실패 ({item}): {e}")
                results[item] = None

    return results


def parallel_fetch(
    items: List[Any],
    fetch_func: Callable[[Any], T],
    max_workers: int = 5,
    timeout: float = 30.0
) -> Dict[Any, T]:
    """
    병렬 데이터 조회

    Args:
        items: 조회할 항목 리스트
        fetch_func: 개별 항목 조회 함수
        max_workers: 최대 워커 수
        timeout: 타임아웃 (초)

    Returns:
        {항목: 결과} 딕셔너리
    """
    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_item = {
            executor.submit(fetch_func, item): item
            for item in items
        }

        for future in as_completed(future_to_item, timeout=timeout):
            item = future_to_item[future]
            try:
                results[item] = future.result()
            except Exception as e:
                logger.warning(f"병렬 조회 실패 ({item}): {e}")
                results[item] = None

    return results


# ============ 메모이제이션 ============

def memoize(maxsize: int = 128, ttl: float = None):
    """
    결과 메모이제이션 데코레이터

    Args:
        maxsize: 최대 캐시 크기
        ttl: 캐시 유효 시간 (초, None이면 무제한)

    Usage:
        @memoize(maxsize=100, ttl=300)
        def expensive_func(x):
            return x ** 2
    """
    def decorator(func: Callable) -> Callable:
        cache: Dict[str, tuple] = {}
        cache_times: Dict[str, float] = {}
        lock = threading.Lock()

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # 캐시 키 생성
            key = str(args) + str(sorted(kwargs.items()))

            with lock:
                # TTL 체크
                if ttl and key in cache_times:
                    if time.time() - cache_times[key] > ttl:
                        del cache[key]
                        del cache_times[key]

                # 캐시 히트
                if key in cache:
                    return cache[key]

            # 캐시 미스 - 계산
            result = func(*args, **kwargs)

            with lock:
                # 크기 제한
                if len(cache) >= maxsize:
                    oldest = min(cache_times.keys(), key=lambda k: cache_times[k])
                    del cache[oldest]
                    del cache_times[oldest]

                cache[key] = result
                cache_times[key] = time.time()

            return result

        def clear_cache():
            with lock:
                cache.clear()
                cache_times.clear()

        wrapper.clear_cache = clear_cache
        return wrapper

    return decorator


# ============ 데이터 프리페칭 ============

class DataPrefetcher:
    """
    데이터 프리페처

    백그라운드에서 데이터를 미리 로드합니다.

    Usage:
        prefetcher = DataPrefetcher()
        prefetcher.prefetch('stock_data', fetch_stock_data, '005930')

        # 나중에 데이터 사용
        data = prefetcher.get('stock_data')
    """

    def __init__(self, max_workers: int = 3):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._futures: Dict[str, Any] = {}
        self._results: Dict[str, Any] = {}
        self._lock = threading.Lock()

    def prefetch(self, key: str, func: Callable, *args, **kwargs):
        """백그라운드 데이터 프리페칭"""
        with self._lock:
            if key not in self._futures and key not in self._results:
                future = self._executor.submit(func, *args, **kwargs)
                self._futures[key] = future

    def get(self, key: str, timeout: float = None) -> Optional[Any]:
        """프리페칭된 데이터 조회"""
        with self._lock:
            # 이미 완료된 결과
            if key in self._results:
                return self._results[key]

            # 진행 중인 작업
            if key in self._futures:
                future = self._futures[key]

        if key in self._futures:
            try:
                result = future.result(timeout=timeout)
                with self._lock:
                    self._results[key] = result
                    del self._futures[key]
                return result
            except Exception as e:
                logger.error(f"프리페칭 실패 ({key}): {e}")
                return None

        return None

    def is_ready(self, key: str) -> bool:
        """프리페칭 완료 여부"""
        with self._lock:
            if key in self._results:
                return True
            if key in self._futures:
                return self._futures[key].done()
        return False

    def clear(self):
        """캐시 정리"""
        with self._lock:
            self._results.clear()
            # 진행 중인 작업은 유지

    def shutdown(self):
        """종료"""
        self._executor.shutdown(wait=False)


# 전역 프리페처
_data_prefetcher: Optional[DataPrefetcher] = None


def get_data_prefetcher() -> DataPrefetcher:
    """전역 데이터 프리페처 반환"""
    global _data_prefetcher
    if _data_prefetcher is None:
        _data_prefetcher = DataPrefetcher()
    return _data_prefetcher


# ============ 청크 처리 ============

def chunked_process(
    items: List[Any],
    process_func: Callable[[List[Any]], List[T]],
    chunk_size: int = 100
) -> List[T]:
    """
    청크 단위 처리

    대량 데이터를 청크로 나눠서 처리합니다.

    Args:
        items: 처리할 항목 리스트
        process_func: 청크 처리 함수
        chunk_size: 청크 크기

    Returns:
        처리된 결과 리스트
    """
    results = []

    for i in range(0, len(items), chunk_size):
        chunk = items[i:i + chunk_size]
        try:
            chunk_results = process_func(chunk)
            results.extend(chunk_results)
        except Exception as e:
            logger.error(f"청크 처리 실패: {e}")

    return results
