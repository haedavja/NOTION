"""
pytest 설정 및 공통 fixtures
"""

import pytest
import sys
import tempfile
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def temp_dir():
    """임시 디렉토리"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_stock_data():
    """샘플 주식 데이터"""
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta

    dates = pd.date_range(
        start=datetime.now() - timedelta(days=100),
        periods=100,
        freq='D'
    )

    np.random.seed(42)
    prices = 100 * np.cumprod(1 + np.random.normal(0.001, 0.02, 100))

    return pd.DataFrame({
        'Open': prices * np.random.uniform(0.99, 1.01, 100),
        'High': prices * np.random.uniform(1.00, 1.03, 100),
        'Low': prices * np.random.uniform(0.97, 1.00, 100),
        'Close': prices,
        'Volume': np.random.randint(1000000, 5000000, 100)
    }, index=dates)


@pytest.fixture
def sample_portfolio():
    """샘플 포트폴리오 데이터"""
    return [
        {'symbol': 'AAPL', 'name': 'Apple Inc.', 'quantity': 10, 'avg_price': 150.0},
        {'symbol': 'MSFT', 'name': 'Microsoft', 'quantity': 5, 'avg_price': 300.0},
        {'symbol': 'GOOG', 'name': 'Google', 'quantity': 3, 'avg_price': 140.0},
    ]


@pytest.fixture
def memory_cache():
    """메모리 캐시 인스턴스"""
    from utils.cache import MemoryCache
    return MemoryCache(max_size=100, default_ttl=60)


@pytest.fixture
def file_cache(temp_dir):
    """파일 캐시 인스턴스"""
    from utils.cache import FileCache
    return FileCache(cache_dir=str(temp_dir), default_ttl=60)
