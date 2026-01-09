"""
스모크 테스트
주요 모듈 import 및 기본 동작 확인
"""

import pytest
import sys
import os

# 프로젝트 루트 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestModuleImports:
    """모듈 import 테스트"""

    def test_analysis_modules(self):
        """분석 모듈 import"""
        from analysis.macro_analysis import MacroAnalyzer
        from analysis.flow_analysis import FlowAnalyzer
        from analysis.sentiment import SentimentAnalyzer
        from analysis.technical import TechnicalAnalyzer

        assert MacroAnalyzer is not None
        assert FlowAnalyzer is not None
        assert SentimentAnalyzer is not None
        assert TechnicalAnalyzer is not None

    def test_rally_analyzer(self):
        """급등 분석기 import"""
        from analysis.rally_analyzer import RallyAnalyzer, RallyDetector
        assert RallyAnalyzer is not None
        assert RallyDetector is not None

    def test_decline_analyzer(self):
        """하락 분석기 import"""
        from analysis.decline_analyzer import DeclineAnalyzer, DeclineDetector
        assert DeclineAnalyzer is not None
        assert DeclineDetector is not None

    def test_potential_analyzer(self):
        """잠재적 요인 분석기 import"""
        from analysis.potential_analyzer import PotentialAnalyzer, PotentialScreener
        assert PotentialAnalyzer is not None
        assert PotentialScreener is not None

    def test_prediction_modules(self):
        """예측 모듈 import"""
        from prediction.probability_model import ProbabilityModel
        from prediction.scenarios import ScenarioAnalyzer

        assert ProbabilityModel is not None
        assert ScenarioAnalyzer is not None

    def test_data_modules(self):
        """데이터 모듈 import"""
        from data.macro_indicators import MacroIndicators
        from data.market_data import MarketData

        assert MacroIndicators is not None
        assert MarketData is not None

    def test_korea_modules(self):
        """한국 주식 모듈 import"""
        from korea.krx_data import KRXDataCollector
        assert KRXDataCollector is not None

    def test_portfolio_modules(self):
        """포트폴리오 모듈 import"""
        from portfolio.portfolio import Portfolio, Position
        from portfolio.analyzer import PortfolioAnalyzer

        assert Portfolio is not None
        assert Position is not None
        assert PortfolioAnalyzer is not None

    def test_navigation_module(self):
        """네비게이션 모듈 import (Streamlit 없이)"""
        # Streamlit이 없어도 데이터 구조는 import 가능
        try:
            from dashboard.navigation import MENU_STRUCTURE, MenuCategory
            assert MENU_STRUCTURE is not None
            assert MenuCategory is not None
        except ImportError as e:
            if "streamlit" in str(e).lower():
                pytest.skip("Streamlit not installed")
            raise


class TestAnalyzerInstantiation:
    """분석기 인스턴스 생성 테스트"""

    def test_rally_detector_init(self):
        """RallyDetector 초기화"""
        from analysis.rally_analyzer import RallyDetector
        detector = RallyDetector()
        assert hasattr(detector, 'detect_rallying_stocks')

    def test_decline_detector_init(self):
        """DeclineDetector 초기화"""
        from analysis.decline_analyzer import DeclineDetector
        detector = DeclineDetector()
        assert hasattr(detector, 'detect_declining_stocks')

    def test_potential_screener_init(self):
        """PotentialScreener 초기화"""
        from analysis.potential_analyzer import PotentialScreener
        screener = PotentialScreener()
        assert hasattr(screener, 'screen_bullish_candidates')
        assert hasattr(screener, 'screen_bearish_candidates')

    def test_krx_collector_init(self):
        """KRXDataCollector 초기화"""
        from korea.krx_data import KRXDataCollector
        collector = KRXDataCollector()
        assert hasattr(collector, 'get_stock_list')
        assert hasattr(collector, 'get_stock_price')


class TestDataStructures:
    """데이터 구조 테스트"""

    def test_menu_structure_valid(self):
        """메뉴 구조 유효성"""
        try:
            from dashboard.navigation import MENU_STRUCTURE, MenuCategory

            assert len(MENU_STRUCTURE) > 0, "Menu structure is empty"

            for category, data in MENU_STRUCTURE.items():
                assert isinstance(category, MenuCategory)
                assert "name" in data
                assert "icon" in data
                assert "items" in data
                assert len(data["items"]) > 0
        except ImportError:
            pytest.skip("Streamlit not installed")

    def test_rally_info_dataclass(self):
        """RallyInfo 데이터클래스"""
        from analysis.rally_analyzer import RallyInfo

        rally = RallyInfo(
            symbol="005930",
            name="삼성전자",
            sector="반도체",
            current_price=70000,
            change_1d=2.5,
            change_5d=5.0,
            change_1m=10.0,
            volume_ratio=1.5,
            foreign_net_buy=1000000,
            inst_net_buy=500000,
            rsi=65.0
        )

        assert rally.symbol == "005930"
        assert rally.change_1d == 2.5


class TestSyntaxOnly:
    """문법 검사 (실행 없이)"""

    def test_all_py_files_syntax(self):
        """모든 .py 파일 문법 검사"""
        import py_compile
        import glob

        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        errors = []

        for pattern in ['*.py', '*/*.py', '*/*/*.py']:
            for filepath in glob.glob(os.path.join(root_dir, pattern)):
                if '__pycache__' in filepath:
                    continue
                try:
                    py_compile.compile(filepath, doraise=True)
                except py_compile.PyCompileError as e:
                    errors.append(f"{filepath}: {e}")

        assert not errors, f"Syntax errors found:\n" + "\n".join(errors)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
