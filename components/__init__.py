"""
UI 컴포넌트 모듈
==================

재사용 가능한 Streamlit UI 컴포넌트들을 제공합니다.

모듈 구성:
---------
- stock_search: 종목 검색 자동완성
- watchlist: 관심 종목 저장/관리
- price_alert: 가격 알림 설정
- easy_explanation: 초보자용 쉬운 설명

사용 예시:
---------
    from components import render_stock_search, add_to_watchlist

    # 종목 검색 UI 렌더링
    selected = render_stock_search()
    if selected:
        add_to_watchlist(selected['code'], selected['name'])

데이터 저장 위치:
---------------
- 워치리스트: data/watchlists/*.json
- 알림: data/alerts.json

유지보수 노트:
------------
- 새 컴포넌트 추가 시 이 파일에 import 추가
- __all__ 리스트 업데이트 필수
"""

from components.stock_search import (
    render_stock_search,
    render_stock_selector,
    render_multi_stock_selector,
    search_stocks,
    get_stock_display_name,
    POPULAR_STOCKS
)

from components.watchlist import (
    render_watchlist_manager,
    render_watchlist_quick_view,
    render_add_to_watchlist_button,
    add_to_watchlist,
    remove_from_watchlist,
    is_in_watchlist,
    get_watchlist_codes,
    Watchlist,
    WatchlistItem
)

from components.price_alert import (
    render_alert_creator,
    render_alert_list,
    render_alert_notification,
    render_alert_badge,
    create_alert,
    delete_alert,
    get_active_alerts,
    check_and_trigger_alerts,
    AlertType,
    AlertStatus,
    PriceAlert
)

from components.easy_explanation import (
    render_easy_explanation,
    get_score_explanation,
    get_grade_explanation,
    get_market_phase_explanation,
    get_investment_summary,
    render_beginner_mode_toggle,
    METRIC_EXPLANATIONS,
    EasyExplanation,
    ExplanationLevel
)

__all__ = [
    # stock_search
    'render_stock_search',
    'render_stock_selector',
    'render_multi_stock_selector',
    'search_stocks',
    'get_stock_display_name',
    'POPULAR_STOCKS',
    # watchlist
    'render_watchlist_manager',
    'render_watchlist_quick_view',
    'render_add_to_watchlist_button',
    'add_to_watchlist',
    'remove_from_watchlist',
    'is_in_watchlist',
    'get_watchlist_codes',
    'Watchlist',
    'WatchlistItem',
    # price_alert
    'render_alert_creator',
    'render_alert_list',
    'render_alert_notification',
    'render_alert_badge',
    'create_alert',
    'delete_alert',
    'get_active_alerts',
    'check_and_trigger_alerts',
    'AlertType',
    'AlertStatus',
    'PriceAlert',
    # easy_explanation
    'render_easy_explanation',
    'get_score_explanation',
    'get_grade_explanation',
    'get_market_phase_explanation',
    'get_investment_summary',
    'render_beginner_mode_toggle',
    'METRIC_EXPLANATIONS',
    'EasyExplanation',
    'ExplanationLevel',
]
