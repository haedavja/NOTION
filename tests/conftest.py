"""
Pytest 설정 및 공통 fixture
"""

import pytest
import sys
import os

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_prices():
    """테스트용 가격 데이터"""
    import pandas as pd
    return pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
                     110, 112, 111, 113, 115, 114, 116, 118, 117, 119])


@pytest.fixture
def sample_stock_code():
    """테스트용 종목 코드"""
    return "005930"


@pytest.fixture
def sample_ohlcv():
    """테스트용 OHLCV 데이터"""
    import pandas as pd
    import numpy as np
    from datetime import datetime, timedelta

    dates = pd.date_range(end=datetime.now(), periods=100, freq='B')
    base = 70000

    return pd.DataFrame({
        'Open': base + np.random.randn(100) * 1000,
        'High': base + abs(np.random.randn(100) * 1500),
        'Low': base - abs(np.random.randn(100) * 1500),
        'Close': base + np.cumsum(np.random.randn(100) * 500),
        'Volume': np.random.randint(1000000, 10000000, 100)
    }, index=dates)
