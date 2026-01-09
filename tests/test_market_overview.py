"""
시장 종합 현황 페이지 테스트
===========================

market_overview_page.py의 핵심 함수들을 테스트합니다.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TestCalculateMarketMetrics:
    """calculate_market_metrics 함수 테스트"""

    def test_empty_dataframe_returns_empty_dict(self):
        """빈 DataFrame 입력 시 빈 딕셔너리 반환"""
        from dashboard.market_overview_page import calculate_market_metrics

        empty_df = pd.DataFrame()
        result = calculate_market_metrics(empty_df)

        assert result == {}

    def test_insufficient_data_returns_empty_dict(self):
        """데이터가 20개 미만일 때 빈 딕셔너리 반환"""
        from dashboard.market_overview_page import calculate_market_metrics

        short_df = pd.DataFrame({
            'Close': [100, 101, 102, 103, 104]  # 5개만
        })
        result = calculate_market_metrics(short_df)

        assert result == {}

    def test_valid_data_returns_all_metrics(self):
        """정상 데이터 입력 시 모든 지표 반환"""
        from dashboard.market_overview_page import calculate_market_metrics

        # 100일 데이터 생성
        np.random.seed(42)
        dates = pd.date_range(end=datetime.now(), periods=100, freq='B')
        prices = 2500 + np.cumsum(np.random.randn(100) * 10)

        df = pd.DataFrame({'Close': prices}, index=dates)
        result = calculate_market_metrics(df)

        # 필수 키 확인
        required_keys = [
            'current', 'return_1d', 'return_1w', 'return_1m',
            'ma20', 'ma60', 'rsi', 'volatility',
            'high_52w', 'low_52w', 'from_high', 'from_low',
            'above_ma20', 'above_ma60'
        ]

        for key in required_keys:
            assert key in result, f"Missing key: {key}"

    def test_rsi_range(self):
        """RSI가 0-100 범위 내인지 확인"""
        from dashboard.market_overview_page import calculate_market_metrics

        np.random.seed(42)
        dates = pd.date_range(end=datetime.now(), periods=100, freq='B')
        prices = 2500 + np.cumsum(np.random.randn(100) * 10)

        df = pd.DataFrame({'Close': prices}, index=dates)
        result = calculate_market_metrics(df)

        assert 0 <= result['rsi'] <= 100


class TestAnalyzeMarketCondition:
    """analyze_market_condition 함수 테스트"""

    def test_strong_uptrend(self):
        """강한 상승 추세 감지"""
        from dashboard.market_overview_page import analyze_market_condition

        metrics = {
            'above_ma20': True,
            'above_ma60': True,
            'above_ma120': True,
            'rsi': 65,
            'from_high': -3,
            'volatility': 15
        }

        result = analyze_market_condition(metrics)

        assert result['trend'] == '강한 상승 추세'
        assert result['trend_score'] >= 80

    def test_downtrend(self):
        """하락 추세 감지"""
        from dashboard.market_overview_page import analyze_market_condition

        metrics = {
            'above_ma20': False,
            'above_ma60': False,
            'above_ma120': False,
            'rsi': 35,
            'from_high': -20,
            'volatility': 25
        }

        result = analyze_market_condition(metrics)

        assert '하락' in result['trend']
        assert result['trend_score'] < 50

    def test_overbought_warning(self):
        """과매수 경고 감지"""
        from dashboard.market_overview_page import analyze_market_condition

        metrics = {
            'above_ma20': True,
            'above_ma60': True,
            'rsi': 75,  # 과매수
            'from_high': -2,
            'volatility': 20
        }

        result = analyze_market_condition(metrics)

        assert result['momentum_warning'] is True
        assert '과매수' in result['momentum']


class TestGenerateSnsMarketDiscussion:
    """generate_sns_market_discussion 함수 테스트"""

    def test_returns_six_posts(self):
        """6개의 포스트 반환 확인"""
        from dashboard.market_overview_page import generate_sns_market_discussion

        metrics = {
            'return_1m': 5.0,
            'return_1w': 1.5,
            'rsi': 55,
            'from_high': -10,
            'volatility': 20,
            'ma20': 2500,
            'ma60': 2450,
            'above_ma20': True,
            'above_ma60': True
        }
        condition = {'trend': '상승 추세'}

        posts = generate_sns_market_discussion(metrics, condition)

        assert len(posts) == 6

    def test_each_post_has_required_fields(self):
        """각 포스트가 필수 필드를 포함하는지 확인"""
        from dashboard.market_overview_page import generate_sns_market_discussion

        metrics = {
            'return_1m': 5.0,
            'return_1w': 1.5,
            'rsi': 55,
            'from_high': -10,
            'volatility': 20,
            'ma20': 2500,
            'ma60': 2450,
            'above_ma20': True,
            'above_ma60': True
        }
        condition = {'trend': '상승 추세'}

        posts = generate_sns_market_discussion(metrics, condition)

        required_fields = ['persona', 'message', 'timestamp', 'likes',
                           'comments', 'validity', 'conditions', 'invalidate']

        for post in posts:
            for field in required_fields:
                assert field in post, f"Missing field: {field}"

    def test_confidence_can_be_none(self):
        """신뢰도(confidence)가 None일 수 있는지 확인 (개미투자자)"""
        from dashboard.market_overview_page import generate_sns_market_discussion

        metrics = {
            'return_1m': 5.0,
            'return_1w': 1.5,
            'rsi': 55,
            'from_high': -10,
            'volatility': 20,
            'ma20': 2500,
            'ma60': 2450,
            'above_ma20': True,
            'above_ma60': True
        }
        condition = {'trend': '상승 추세'}
        gainers = [{'name': '삼성전자', 'code': '005930', 'change': 3.5}]

        posts = generate_sns_market_discussion(metrics, condition, gainers=gainers)

        # 개미투자자(retail_voice)는 confidence가 None
        retail_post = next((p for p in posts if p['persona']['avatar'] == '🐜'), None)
        assert retail_post is not None
        assert retail_post.get('confidence') is None


class TestIdentifyRisks:
    """identify_risks 함수 테스트"""

    def test_high_rsi_risk(self):
        """높은 RSI에서 리스크 감지"""
        from dashboard.market_overview_page import identify_risks

        metrics = {'rsi': 75, 'from_high': -5, 'volatility': 15}
        condition = {'momentum_warning': True, 'trend_score': 70}

        risks = identify_risks(metrics, condition)

        risk_factors = [r['factor'] for r in risks]
        assert any('과열' in f for f in risk_factors)

    def test_high_volatility_risk(self):
        """높은 변동성에서 리스크 감지"""
        from dashboard.market_overview_page import identify_risks

        metrics = {'rsi': 50, 'from_high': -15, 'volatility': 35}
        condition = {'momentum_warning': False, 'trend_score': 50}

        risks = identify_risks(metrics, condition)

        risk_factors = [r['factor'] for r in risks]
        assert any('변동성' in f for f in risk_factors)

    def test_no_risks_returns_safe_message(self):
        """리스크 없을 때 안정 메시지 반환"""
        from dashboard.market_overview_page import identify_risks

        metrics = {'rsi': 50, 'from_high': -15, 'volatility': 15}
        condition = {'momentum_warning': False, 'trend_score': 55}

        risks = identify_risks(metrics, condition)

        assert len(risks) >= 1
        assert any(r['level'] == '낮음' for r in risks)


class TestCalculatePotentialTargets:
    """calculate_potential_targets 함수 테스트"""

    def test_returns_resistances_and_supports(self):
        """저항선과 지지선 반환 확인"""
        from dashboard.market_overview_page import calculate_potential_targets

        metrics = {
            'current': 2500,
            'ma20': 2480,
            'ma60': 2450,
            'ma120': 2400,
            'high_52w': 2700,
            'low_52w': 2200
        }
        condition = {}

        result = calculate_potential_targets(metrics, condition)

        assert 'current' in result
        assert 'resistances' in result
        assert 'supports' in result
        assert isinstance(result['resistances'], list)
        assert isinstance(result['supports'], list)

    def test_resistances_above_current(self):
        """저항선이 현재가 위에 있는지 확인"""
        from dashboard.market_overview_page import calculate_potential_targets

        metrics = {
            'current': 2500,
            'ma20': 2480,
            'ma60': 2600,  # 현재가 위
            'ma120': 2400,
            'high_52w': 2700,
            'low_52w': 2200
        }
        condition = {}

        result = calculate_potential_targets(metrics, condition)

        for r in result['resistances']:
            assert r['price'] > metrics['current']


class TestTraderPersonas:
    """TRADER_PERSONAS 상수 테스트"""

    def test_six_personas_defined(self):
        """6개의 페르소나가 정의되어 있는지 확인"""
        from dashboard.market_overview_page import TRADER_PERSONAS

        assert len(TRADER_PERSONAS) == 6

    def test_each_persona_has_required_fields(self):
        """각 페르소나가 필수 필드를 포함하는지 확인"""
        from dashboard.market_overview_page import TRADER_PERSONAS

        required_fields = ['name', 'avatar', 'style', 'color', 'bio']

        for key, persona in TRADER_PERSONAS.items():
            for field in required_fields:
                assert field in persona, f"Persona {key} missing field: {field}"

    def test_unique_colors(self):
        """각 페르소나 색상이 고유한지 확인"""
        from dashboard.market_overview_page import TRADER_PERSONAS

        colors = [p['color'] for p in TRADER_PERSONAS.values()]
        assert len(colors) == len(set(colors)), "Duplicate colors found"
