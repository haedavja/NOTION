"""
UI 컴포넌트 테스트
==================

components 모듈의 핵심 함수들을 테스트합니다.
"""

import pytest
import os
import json
import tempfile
from datetime import datetime


class TestStockSearch:
    """stock_search 모듈 테스트"""

    def test_popular_stocks_defined(self):
        """인기 종목 리스트가 정의되어 있는지 확인"""
        from components.stock_search import POPULAR_STOCKS

        assert len(POPULAR_STOCKS) > 0
        assert all('code' in s and 'name' in s for s in POPULAR_STOCKS)

    def test_search_stocks_by_name(self):
        """이름으로 종목 검색"""
        from components.stock_search import search_stocks

        results = search_stocks('삼성')

        assert len(results) > 0
        assert any('삼성' in r['name'] for r in results)

    def test_search_stocks_by_code(self):
        """코드로 종목 검색"""
        from components.stock_search import search_stocks

        results = search_stocks('005930')

        assert len(results) > 0
        assert any(r['code'] == '005930' for r in results)

    def test_search_empty_query_returns_empty(self):
        """빈 쿼리는 빈 결과 반환"""
        from components.stock_search import search_stocks

        results = search_stocks('')
        assert results == []

    def test_get_stock_display_name(self):
        """종목 표시명 반환"""
        from components.stock_search import get_stock_display_name

        display = get_stock_display_name('005930')

        assert '삼성전자' in display
        assert '005930' in display


class TestWatchlist:
    """watchlist 모듈 테스트"""

    @pytest.fixture
    def temp_watchlist_dir(self, tmp_path):
        """임시 워치리스트 디렉토리"""
        import components.watchlist as wl
        original_dir = wl.WATCHLIST_DIR
        wl.WATCHLIST_DIR = str(tmp_path / 'watchlists')
        os.makedirs(wl.WATCHLIST_DIR, exist_ok=True)
        yield wl.WATCHLIST_DIR
        wl.WATCHLIST_DIR = original_dir

    def test_watchlist_item_creation(self):
        """WatchlistItem 생성"""
        from components.watchlist import WatchlistItem

        item = WatchlistItem(
            code='005930',
            name='삼성전자',
            added_date=datetime.now().isoformat()
        )

        assert item.code == '005930'
        assert item.name == '삼성전자'
        assert item.target_price is None

    def test_watchlist_creation(self):
        """Watchlist 생성"""
        from components.watchlist import Watchlist, WatchlistItem

        now = datetime.now().isoformat()
        items = [
            WatchlistItem(code='005930', name='삼성전자', added_date=now)
        ]

        watchlist = Watchlist(
            name='테스트',
            items=items,
            created_date=now,
            modified_date=now
        )

        assert watchlist.name == '테스트'
        assert len(watchlist.items) == 1

    def test_save_and_load_watchlist(self, temp_watchlist_dir):
        """워치리스트 저장 및 로드"""
        from components.watchlist import (
            Watchlist, WatchlistItem,
            save_watchlist, load_watchlist
        )

        now = datetime.now().isoformat()
        items = [
            WatchlistItem(code='005930', name='삼성전자', added_date=now)
        ]

        original = Watchlist(
            name='테스트저장',
            items=items,
            created_date=now,
            modified_date=now
        )

        # 저장
        assert save_watchlist(original) is True

        # 로드
        loaded = load_watchlist('테스트저장')

        assert loaded is not None
        assert loaded.name == original.name
        assert len(loaded.items) == 1
        assert loaded.items[0].code == '005930'


class TestPriceAlert:
    """price_alert 모듈 테스트"""

    @pytest.fixture
    def temp_alerts_file(self, tmp_path):
        """임시 알림 파일"""
        import components.price_alert as pa
        original_file = pa.ALERTS_FILE
        pa.ALERTS_FILE = str(tmp_path / 'alerts.json')
        yield pa.ALERTS_FILE
        pa.ALERTS_FILE = original_file

    def test_alert_type_enum(self):
        """AlertType 열거형 확인"""
        from components.price_alert import AlertType

        assert AlertType.TARGET_PRICE.value == "목표가"
        assert AlertType.STOP_LOSS.value == "손절가"
        assert AlertType.PERCENT_CHANGE.value == "등락률"

    def test_alert_status_enum(self):
        """AlertStatus 열거형 확인"""
        from components.price_alert import AlertStatus

        assert AlertStatus.ACTIVE.value == "활성"
        assert AlertStatus.TRIGGERED.value == "발동됨"

    def test_create_alert(self, temp_alerts_file):
        """알림 생성"""
        from components.price_alert import create_alert, AlertType, load_alerts

        alert = create_alert(
            stock_code='005930',
            stock_name='삼성전자',
            alert_type=AlertType.TARGET_PRICE,
            condition='above',
            target_value=80000
        )

        assert alert is not None
        assert alert.stock_code == '005930'
        assert alert.target_value == 80000

        # 저장 확인
        alerts = load_alerts()
        assert len(alerts) == 1

    def test_check_alert_condition_above(self):
        """이상 조건 체크"""
        from components.price_alert import check_alert_condition, PriceAlert

        alert = PriceAlert(
            id='test1',
            stock_code='005930',
            stock_name='삼성전자',
            alert_type='목표가',
            condition='above',
            target_value=80000
        )

        assert check_alert_condition(alert, 85000) is True
        assert check_alert_condition(alert, 75000) is False

    def test_check_alert_condition_below(self):
        """이하 조건 체크"""
        from components.price_alert import check_alert_condition, PriceAlert

        alert = PriceAlert(
            id='test2',
            stock_code='005930',
            stock_name='삼성전자',
            alert_type='손절가',
            condition='below',
            target_value=60000
        )

        assert check_alert_condition(alert, 55000) is True
        assert check_alert_condition(alert, 65000) is False

    def test_check_alert_condition_percent(self):
        """등락률 조건 체크"""
        from components.price_alert import check_alert_condition, PriceAlert

        alert = PriceAlert(
            id='test3',
            stock_code='005930',
            stock_name='삼성전자',
            alert_type='등락률',
            condition='percent_up',
            target_value=5.0,
            base_price=70000
        )

        # 5% 상승 = 73,500원
        assert check_alert_condition(alert, 74000) is True
        assert check_alert_condition(alert, 72000) is False


class TestEasyExplanation:
    """easy_explanation 모듈 테스트"""

    def test_metric_explanations_defined(self):
        """지표 설명이 정의되어 있는지 확인"""
        from components.easy_explanation import METRIC_EXPLANATIONS

        assert 'value' in METRIC_EXPLANATIONS
        assert 'rsi' in METRIC_EXPLANATIONS
        assert 'foreign_net' in METRIC_EXPLANATIONS

    def test_get_score_explanation(self):
        """점수 설명 생성"""
        from components.easy_explanation import get_score_explanation

        explanation = get_score_explanation(85, 'value')

        assert explanation is not None
        assert explanation.title is not None
        assert explanation.simple_summary is not None

    def test_get_grade_explanation(self):
        """등급 설명 생성"""
        from components.easy_explanation import get_grade_explanation

        for grade in ['A', 'B+', 'B', 'C', 'D', 'F']:
            explanation = get_grade_explanation(grade)
            assert explanation is not None
            assert explanation.title is not None

    def test_explanation_level_enum(self):
        """ExplanationLevel 열거형 확인"""
        from components.easy_explanation import ExplanationLevel

        assert ExplanationLevel.BEGINNER.value == "초급"
        assert ExplanationLevel.INTERMEDIATE.value == "중급"
        assert ExplanationLevel.EXPERT.value == "전문가"
