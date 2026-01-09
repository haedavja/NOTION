"""
오프라인 캐시 데이터 강화 모듈
네트워크 연결 없이도 기본 데이터 제공
"""

import os
import json
import pickle
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

# 캐시 디렉토리
CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'cache')

# 기본 데이터 디렉토리
DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'defaults')


def ensure_dirs():
    """디렉토리 생성"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(DEFAULT_DATA_DIR, exist_ok=True)


def get_cache_key(key: str) -> str:
    """캐시 키 해시"""
    return hashlib.md5(key.encode()).hexdigest()[:16]


def get_cache_path(key: str) -> str:
    """캐시 파일 경로"""
    ensure_dirs()
    return os.path.join(CACHE_DIR, f"{get_cache_key(key)}.pkl")


def save_to_cache(key: str, data: Any, ttl_hours: int = 24) -> bool:
    """
    데이터를 캐시에 저장

    Args:
        key: 캐시 키
        data: 저장할 데이터
        ttl_hours: 유효 시간 (시간 단위)

    Returns:
        성공 여부
    """
    try:
        path = get_cache_path(key)
        cache_data = {
            'key': key,
            'data': data,
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(hours=ttl_hours)).isoformat()
        }

        with open(path, 'wb') as f:
            pickle.dump(cache_data, f)

        return True
    except Exception as e:
        logger.error(f"캐시 저장 실패: {e}")
        return False


def load_from_cache(key: str, ignore_expiry: bool = False) -> Optional[Any]:
    """
    캐시에서 데이터 로드

    Args:
        key: 캐시 키
        ignore_expiry: 만료 무시 여부 (오프라인 모드)

    Returns:
        캐시된 데이터 또는 None
    """
    try:
        path = get_cache_path(key)
        if not os.path.exists(path):
            return None

        with open(path, 'rb') as f:
            cache_data = pickle.load(f)

        # 만료 체크
        if not ignore_expiry:
            expires_at = datetime.fromisoformat(cache_data['expires_at'])
            if datetime.now() > expires_at:
                return None

        return cache_data['data']
    except Exception as e:
        logger.error(f"캐시 로드 실패: {e}")
        return None


def clear_cache(older_than_hours: int = None) -> int:
    """
    캐시 정리

    Args:
        older_than_hours: 지정 시간보다 오래된 캐시만 삭제 (None이면 전체)

    Returns:
        삭제된 파일 수
    """
    ensure_dirs()
    deleted = 0

    for filename in os.listdir(CACHE_DIR):
        if not filename.endswith('.pkl'):
            continue

        filepath = os.path.join(CACHE_DIR, filename)

        try:
            if older_than_hours is None:
                os.remove(filepath)
                deleted += 1
            else:
                mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
                if datetime.now() - mtime > timedelta(hours=older_than_hours):
                    os.remove(filepath)
                    deleted += 1
        except Exception as e:
            logger.error(f"캐시 파일 삭제 실패: {e}")

    return deleted


def get_cache_stats() -> Dict:
    """캐시 통계"""
    ensure_dirs()

    stats = {
        'total_files': 0,
        'total_size_kb': 0,
        'expired_files': 0,
        'valid_files': 0
    }

    for filename in os.listdir(CACHE_DIR):
        if not filename.endswith('.pkl'):
            continue

        filepath = os.path.join(CACHE_DIR, filename)
        stats['total_files'] += 1
        stats['total_size_kb'] += os.path.getsize(filepath) / 1024

        try:
            with open(filepath, 'rb') as f:
                cache_data = pickle.load(f)

            expires_at = datetime.fromisoformat(cache_data['expires_at'])
            if datetime.now() > expires_at:
                stats['expired_files'] += 1
            else:
                stats['valid_files'] += 1
        except Exception:
            pass

    stats['total_size_kb'] = round(stats['total_size_kb'], 2)
    return stats


# ============ 기본 데이터 (오프라인 폴백용) ============

# 주요 종목 기본 정보
DEFAULT_STOCKS = {
    '005930': {'name': '삼성전자', 'market': 'KOSPI', 'sector': '반도체', 'base_price': 70000},
    '000660': {'name': 'SK하이닉스', 'market': 'KOSPI', 'sector': '반도체', 'base_price': 130000},
    '035420': {'name': 'NAVER', 'market': 'KOSPI', 'sector': 'IT', 'base_price': 200000},
    '035720': {'name': '카카오', 'market': 'KOSPI', 'sector': 'IT', 'base_price': 50000},
    '051910': {'name': 'LG화학', 'market': 'KOSPI', 'sector': '화학', 'base_price': 400000},
    '006400': {'name': '삼성SDI', 'market': 'KOSPI', 'sector': '2차전지', 'base_price': 400000},
    '005380': {'name': '현대차', 'market': 'KOSPI', 'sector': '자동차', 'base_price': 200000},
    '000270': {'name': '기아', 'market': 'KOSPI', 'sector': '자동차', 'base_price': 100000},
    '373220': {'name': 'LG에너지솔루션', 'market': 'KOSPI', 'sector': '2차전지', 'base_price': 400000},
    '207940': {'name': '삼성바이오로직스', 'market': 'KOSPI', 'sector': '바이오', 'base_price': 800000},
    '068270': {'name': '셀트리온', 'market': 'KOSPI', 'sector': '바이오', 'base_price': 180000},
    '247540': {'name': '에코프로비엠', 'market': 'KOSDAQ', 'sector': '2차전지', 'base_price': 200000},
    '086520': {'name': '에코프로', 'market': 'KOSDAQ', 'sector': '2차전지', 'base_price': 100000},
    '196170': {'name': '알테오젠', 'market': 'KOSDAQ', 'sector': '바이오', 'base_price': 200000},
    '352820': {'name': '하이브', 'market': 'KOSPI', 'sector': '엔터', 'base_price': 200000},
    '003550': {'name': 'LG', 'market': 'KOSPI', 'sector': '지주', 'base_price': 80000},
    '105560': {'name': 'KB금융', 'market': 'KOSPI', 'sector': '금융', 'base_price': 60000},
    '055550': {'name': '신한지주', 'market': 'KOSPI', 'sector': '금융', 'base_price': 40000},
    '096770': {'name': 'SK이노베이션', 'market': 'KOSPI', 'sector': '에너지', 'base_price': 100000},
    '028260': {'name': '삼성물산', 'market': 'KOSPI', 'sector': '건설', 'base_price': 120000},
}

# 섹터별 평균 지표
DEFAULT_SECTOR_METRICS = {
    '반도체': {'per': 15, 'pbr': 1.5, 'roe': 15, 'growth': 20},
    'IT': {'per': 25, 'pbr': 3.0, 'roe': 12, 'growth': 15},
    '2차전지': {'per': 40, 'pbr': 4.0, 'roe': 10, 'growth': 30},
    '바이오': {'per': 50, 'pbr': 5.0, 'roe': 5, 'growth': 25},
    '자동차': {'per': 8, 'pbr': 0.8, 'roe': 10, 'growth': 8},
    '화학': {'per': 10, 'pbr': 1.0, 'roe': 8, 'growth': 5},
    '금융': {'per': 6, 'pbr': 0.5, 'roe': 10, 'growth': 5},
    '건설': {'per': 8, 'pbr': 0.7, 'roe': 8, 'growth': 3},
    '에너지': {'per': 10, 'pbr': 0.8, 'roe': 7, 'growth': 5},
    '엔터': {'per': 20, 'pbr': 2.5, 'roe': 15, 'growth': 15},
    '지주': {'per': 10, 'pbr': 0.6, 'roe': 8, 'growth': 5},
}

# 시장 지수 기본값
DEFAULT_INDEX_VALUES = {
    'KOSPI': 2500,
    'KOSDAQ': 850,
    'KOSPI200': 330,
}

# 환율/금리 기본값
DEFAULT_ECONOMIC_DATA = {
    'usd_krw': 1350,
    'interest_rate': 3.5,
    'cpi': 3.0,
    'gdp_growth': 2.0,
}


def get_default_stock_info(code: str) -> Optional[Dict]:
    """기본 종목 정보 반환"""
    return DEFAULT_STOCKS.get(code)


def get_default_sector_metrics(sector: str) -> Dict:
    """섹터별 기본 지표 반환"""
    return DEFAULT_SECTOR_METRICS.get(sector, DEFAULT_SECTOR_METRICS['IT'])


def get_all_default_stocks() -> Dict:
    """모든 기본 종목 정보"""
    return DEFAULT_STOCKS


def search_default_stocks(query: str, limit: int = 10) -> List[Dict]:
    """기본 종목 검색"""
    results = []
    query_lower = query.lower()

    for code, info in DEFAULT_STOCKS.items():
        if (query_lower in info['name'].lower() or
            query in code):
            results.append({
                'code': code,
                'name': info['name'],
                'market': info['market'],
                'sector': info['sector']
            })
            if len(results) >= limit:
                break

    return results


class OfflineCacheManager:
    """
    오프라인 캐시 관리자

    Usage:
        cache = OfflineCacheManager()

        # 온라인일 때 데이터 저장
        cache.store('stock_005930', data, ttl_hours=24)

        # 오프라인일 때 데이터 로드 (만료 무시)
        data = cache.get('stock_005930', offline_mode=True)

        # 기본값과 함께 사용
        data = cache.get_with_default('stock_005930', default_data)
    """

    def __init__(self, namespace: str = "default"):
        self.namespace = namespace

    def _make_key(self, key: str) -> str:
        """네임스페이스 포함 키 생성"""
        return f"{self.namespace}:{key}"

    def store(self, key: str, data: Any, ttl_hours: int = 24) -> bool:
        """데이터 저장"""
        return save_to_cache(self._make_key(key), data, ttl_hours)

    def get(self, key: str, offline_mode: bool = False) -> Optional[Any]:
        """데이터 로드"""
        return load_from_cache(self._make_key(key), ignore_expiry=offline_mode)

    def get_with_default(self, key: str, default: Any, offline_mode: bool = False) -> Any:
        """데이터 로드 (기본값 포함)"""
        data = self.get(key, offline_mode)
        return data if data is not None else default

    def delete(self, key: str) -> bool:
        """데이터 삭제"""
        try:
            path = get_cache_path(self._make_key(key))
            if os.path.exists(path):
                os.remove(path)
                return True
            return False
        except Exception:
            return False


# 전역 캐시 매니저
stock_cache = OfflineCacheManager(namespace="stock")
market_cache = OfflineCacheManager(namespace="market")
analysis_cache = OfflineCacheManager(namespace="analysis")


def is_online() -> bool:
    """네트워크 연결 상태 확인 (간단한 체크)"""
    import socket
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False


def get_data_with_fallback(
    key: str,
    fetch_func,
    default_value: Any = None,
    ttl_hours: int = 24,
    cache_manager: OfflineCacheManager = None
) -> Any:
    """
    데이터 조회 (캐시/온라인/오프라인 폴백)

    Args:
        key: 캐시 키
        fetch_func: 온라인 데이터 조회 함수
        default_value: 기본값
        ttl_hours: 캐시 유효 시간
        cache_manager: 캐시 매니저

    Returns:
        데이터
    """
    cache = cache_manager or stock_cache

    # 1. 유효한 캐시 확인
    cached = cache.get(key, offline_mode=False)
    if cached is not None:
        return cached

    # 2. 온라인이면 새로 조회
    if is_online():
        try:
            data = fetch_func()
            if data is not None:
                cache.store(key, data, ttl_hours)
                return data
        except Exception as e:
            logger.warning(f"온라인 조회 실패: {e}")

    # 3. 만료된 캐시라도 사용 (오프라인 모드)
    cached = cache.get(key, offline_mode=True)
    if cached is not None:
        logger.info(f"만료된 캐시 사용 (오프라인): {key}")
        return cached

    # 4. 기본값 반환
    return default_value


# 자주 사용되는 데이터 프리로드
def preload_essential_data():
    """필수 데이터 프리로드 (앱 시작 시 호출)"""
    logger.info("필수 데이터 프리로드 시작")

    # 기본 종목 정보 캐시
    for code, info in DEFAULT_STOCKS.items():
        stock_cache.store(f"info_{code}", info, ttl_hours=24*7)

    # 섹터 정보 캐시
    for sector, metrics in DEFAULT_SECTOR_METRICS.items():
        market_cache.store(f"sector_{sector}", metrics, ttl_hours=24*7)

    logger.info("필수 데이터 프리로드 완료")
