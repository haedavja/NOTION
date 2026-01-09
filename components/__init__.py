"""
UI 컴포넌트 모듈
재사용 가능한 Streamlit UI 컴포넌트
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
