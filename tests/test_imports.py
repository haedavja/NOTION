"""
모듈 Import 테스트
pytest tests/test_imports.py -v
"""

import pytest
import sys
import importlib
from pathlib import Path

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestModuleImports:
    """각 모듈의 import 가능 여부 테스트"""

    @pytest.mark.parametrize("module_name", [
        "portfolio.portfolio",
        "portfolio.analyzer",
        "portfolio.data_store",
        "portfolio.thesis_evaluator",
        "portfolio.risk_monitor",
        "portfolio.journal",
    ])
    def test_portfolio_modules(self, module_name):
        """포트폴리오 모듈 import 테스트"""
        module = importlib.import_module(module_name)
        assert module is not None

    @pytest.mark.parametrize("module_name", [
        "alerts.price_monitor",
        "alerts.news_alert",
        "alerts.notification",
    ])
    def test_alert_modules(self, module_name):
        """알림 모듈 import 테스트"""
        module = importlib.import_module(module_name)
        assert module is not None

    @pytest.mark.parametrize("module_name", [
        "korea.krx_data",
        "korea.korean_stocks",
    ])
    def test_korea_modules(self, module_name):
        """한국 주식 모듈 import 테스트"""
        module = importlib.import_module(module_name)
        assert module is not None

    @pytest.mark.parametrize("module_name", [
        "utils.cache",
        "utils.validators",
    ])
    def test_utils_modules(self, module_name):
        """유틸리티 모듈 import 테스트"""
        module = importlib.import_module(module_name)
        assert module is not None


class TestTypingImports:
    """typing 관련 import 검증"""

    def test_news_alert_tuple(self):
        """news_alert의 Tuple import 확인"""
        from alerts.news_alert import NewsAlert
        # Tuple이 제대로 import 되었는지 확인
        import inspect
        source = inspect.getsourcefile(NewsAlert)
        with open(source, 'r') as f:
            content = f.read()
        assert 'from typing import' in content
        assert 'Tuple' in content

    def test_journal_timedelta(self):
        """journal의 timedelta import 확인"""
        from portfolio.journal import TradingJournal
        import inspect
        source = inspect.getsourcefile(TradingJournal)
        with open(source, 'r') as f:
            content = f.read()
        assert 'timedelta' in content


class TestKRXDataCollector:
    """KRX 데이터 수집기 테스트"""

    def test_krx_import(self):
        """KRXDataCollector import"""
        from korea.krx_data import KRXDataCollector
        collector = KRXDataCollector()
        assert collector is not None

    def test_search_stock_function(self):
        """search_korean_stock 함수 존재"""
        from korea.krx_data import search_korean_stock
        assert callable(search_korean_stock)

    def test_blue_chips_has_kepco(self):
        """한국전력이 blue_chips에 포함되어야 함"""
        from korea.krx_data import KRXDataCollector
        collector = KRXDataCollector()
        assert '015760' in collector.blue_chips
        assert collector.blue_chips['015760'] == '한국전력'

    def test_search_kepco(self):
        """한국전력 검색 테스트"""
        from korea.krx_data import KRXDataCollector
        collector = KRXDataCollector()
        results = collector.search_stock('한국전력')
        assert len(results) > 0
        assert any(r['name'] == '한국전력' for r in results)


class TestPortfolioPageImports:
    """portfolio_page.py의 한국 주식 매핑 테스트"""

    def test_korean_stocks_has_kepco(self):
        """KOREAN_STOCKS에 한국전력 포함"""
        from dashboard.portfolio_page import KOREAN_STOCKS
        assert '한국전력' in KOREAN_STOCKS
        assert KOREAN_STOCKS['한국전력'] == '015760.KS'

    def test_resolve_ticker_kepco(self):
        """resolve_ticker로 한국전력 변환"""
        from dashboard.portfolio_page import resolve_ticker
        ticker = resolve_ticker('한국전력')
        assert ticker == '015760.KS'

    def test_resolve_ticker_krx_fallback(self):
        """KRX 폴백으로 종목 검색"""
        from dashboard.portfolio_page import resolve_ticker
        # 딕셔너리에 없는 종목도 KRX에서 찾아야 함
        ticker = resolve_ticker('SK텔레콤')
        assert ticker is not None
        assert '017670' in ticker
