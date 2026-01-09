"""
UI/UX 헬퍼 유틸리티
==================

로딩 상태, 에러 표시, 사용자 피드백 등 공통 UI 컴포넌트를 제공합니다.

주요 기능:
---------
- show_loading: 로딩 스피너 표시
- show_error: 에러 메시지 표시
- show_success: 성공 메시지 표시
- show_info: 정보 메시지 표시
- show_empty_state: 빈 상태 표시
- render_progress_bar: 진행률 표시
- render_skeleton: 스켈레톤 로딩

사용 예시:
---------
    from utils.ui_helpers import show_loading, show_error, with_loading

    # 로딩 표시
    with show_loading("데이터를 불러오는 중..."):
        data = fetch_data()

    # 에러 표시
    show_error("데이터를 불러올 수 없습니다", retry_callback=retry_func)

    # 데코레이터 사용
    @with_loading("분석 중...")
    def analyze_stock(code):
        return perform_analysis(code)
"""

import streamlit as st
from typing import Callable, Optional, Any
from contextlib import contextmanager
from functools import wraps
import time


# ============ 색상 상수 ============

COLORS = {
    'success': '#22c55e',
    'error': '#ef4444',
    'warning': '#f59e0b',
    'info': '#3b82f6',
    'muted': '#6b7280',
    'primary': '#8b5cf6',
}


# ============ 로딩 상태 ============

@contextmanager
def show_loading(message: str = "로딩 중...", spinner_type: str = "default"):
    """
    로딩 스피너 컨텍스트 매니저

    Args:
        message: 로딩 메시지
        spinner_type: 스피너 타입 ("default", "dots", "bars")

    Usage:
        with show_loading("데이터 불러오는 중..."):
            data = fetch_data()
    """
    with st.spinner(message):
        yield


def with_loading(message: str = "처리 중..."):
    """
    로딩 표시 데코레이터

    Usage:
        @with_loading("분석 중...")
        def analyze():
            return heavy_computation()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with st.spinner(message):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def render_skeleton(height: int = 100, count: int = 1):
    """
    스켈레톤 로딩 UI 렌더링

    Args:
        height: 스켈레톤 높이 (px)
        count: 스켈레톤 개수
    """
    skeleton_css = f"""
    <style>
    @keyframes skeleton-loading {{
        0% {{ background-position: -200px 0; }}
        100% {{ background-position: calc(200px + 100%) 0; }}
    }}
    .skeleton {{
        background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
        background-size: 200px 100%;
        animation: skeleton-loading 1.5s infinite;
        border-radius: 8px;
        height: {height}px;
        margin-bottom: 10px;
    }}
    </style>
    """
    st.markdown(skeleton_css, unsafe_allow_html=True)

    for _ in range(count):
        st.markdown('<div class="skeleton"></div>', unsafe_allow_html=True)


def render_progress_bar(
    progress: float,
    label: str = "",
    color: str = None,
    show_percentage: bool = True
):
    """
    커스텀 진행률 바 렌더링

    Args:
        progress: 진행률 (0.0 ~ 1.0)
        label: 레이블
        color: 바 색상
        show_percentage: 퍼센트 표시 여부
    """
    progress = max(0, min(1, progress))
    percentage = int(progress * 100)
    bar_color = color or COLORS['primary']

    percentage_text = f"{percentage}%" if show_percentage else ""

    html = f"""
    <div style="margin: 10px 0;">
        {f'<div style="margin-bottom: 5px; color: #374151;">{label}</div>' if label else ''}
        <div style="background: #e5e7eb; border-radius: 10px; height: 20px; overflow: hidden;">
            <div style="
                background: {bar_color};
                width: {percentage}%;
                height: 100%;
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 12px;
                font-weight: bold;
                transition: width 0.3s ease;
            ">{percentage_text}</div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ============ 메시지 표시 ============

def show_error(
    message: str,
    title: str = "오류 발생",
    details: str = None,
    retry_callback: Callable = None
):
    """
    에러 메시지 표시

    Args:
        message: 에러 메시지
        title: 제목
        details: 상세 내용 (접을 수 있음)
        retry_callback: 재시도 콜백 함수
    """
    with st.container():
        st.error(f"**{title}**\n\n{message}")

        if details:
            with st.expander("상세 정보 보기"):
                st.code(details)

        if retry_callback:
            if st.button("🔄 다시 시도", key=f"retry_{hash(message)}"):
                retry_callback()


def show_success(message: str, title: str = "완료", icon: str = "✅"):
    """
    성공 메시지 표시

    Args:
        message: 메시지
        title: 제목
        icon: 아이콘
    """
    st.success(f"{icon} **{title}**\n\n{message}")


def show_info(message: str, title: str = None, icon: str = "ℹ️"):
    """
    정보 메시지 표시

    Args:
        message: 메시지
        title: 제목 (선택)
        icon: 아이콘
    """
    if title:
        st.info(f"{icon} **{title}**\n\n{message}")
    else:
        st.info(f"{icon} {message}")


def show_warning(message: str, title: str = "주의", icon: str = "⚠️"):
    """
    경고 메시지 표시

    Args:
        message: 메시지
        title: 제목
        icon: 아이콘
    """
    st.warning(f"{icon} **{title}**\n\n{message}")


# ============ 빈 상태 ============

def show_empty_state(
    message: str = "데이터가 없습니다",
    icon: str = "📭",
    action_label: str = None,
    action_callback: Callable = None
):
    """
    빈 상태 표시

    Args:
        message: 메시지
        icon: 아이콘
        action_label: 액션 버튼 레이블
        action_callback: 액션 콜백
    """
    html = f"""
    <div style="
        text-align: center;
        padding: 40px 20px;
        background: #f9fafb;
        border-radius: 12px;
        margin: 20px 0;
    ">
        <div style="font-size: 48px; margin-bottom: 16px;">{icon}</div>
        <div style="color: #6b7280; font-size: 16px;">{message}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)

    if action_label and action_callback:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button(action_label, use_container_width=True):
                action_callback()


def show_unavailable_feature(
    feature_name: str,
    reason: str = "이 기능은 현재 사용할 수 없습니다"
):
    """
    사용 불가능한 기능 표시

    Args:
        feature_name: 기능 이름
        reason: 사용 불가 이유
    """
    html = f"""
    <div style="
        text-align: center;
        padding: 60px 20px;
        background: linear-gradient(135deg, #f5f5f5 0%, #e8e8e8 100%);
        border-radius: 16px;
        margin: 20px 0;
    ">
        <div style="font-size: 64px; margin-bottom: 20px; opacity: 0.5;">🔒</div>
        <h3 style="color: #374151; margin-bottom: 12px;">{feature_name}</h3>
        <p style="color: #6b7280;">{reason}</p>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ============ 토스트 알림 ============

def show_toast(message: str, type: str = "info", duration: int = 3):
    """
    토스트 알림 표시

    Args:
        message: 메시지
        type: 타입 ("success", "error", "warning", "info")
        duration: 표시 시간 (초)
    """
    color = COLORS.get(type, COLORS['info'])
    icon_map = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️'
    }
    icon = icon_map.get(type, 'ℹ️')

    toast_id = f"toast_{int(time.time() * 1000)}"

    html = f"""
    <style>
    @keyframes toast-slide-in {{
        from {{ transform: translateX(100%); opacity: 0; }}
        to {{ transform: translateX(0); opacity: 1; }}
    }}
    @keyframes toast-fade-out {{
        from {{ opacity: 1; }}
        to {{ opacity: 0; }}
    }}
    #{toast_id} {{
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        background: white;
        border-left: 4px solid {color};
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 9999;
        animation: toast-slide-in 0.3s ease, toast-fade-out 0.3s ease {duration}s forwards;
    }}
    </style>
    <div id="{toast_id}">
        <span style="margin-right: 8px;">{icon}</span>
        <span>{message}</span>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


# ============ 확인 대화상자 ============

def confirm_action(
    message: str,
    confirm_label: str = "확인",
    cancel_label: str = "취소",
    key: str = None
) -> bool:
    """
    확인 대화상자

    Args:
        message: 확인 메시지
        confirm_label: 확인 버튼 레이블
        cancel_label: 취소 버튼 레이블
        key: 고유 키

    Returns:
        확인 여부
    """
    unique_key = key or f"confirm_{hash(message)}"

    with st.container():
        st.warning(f"⚠️ {message}")

        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            confirmed = st.button(
                confirm_label,
                key=f"{unique_key}_confirm",
                type="primary"
            )

        with col2:
            cancelled = st.button(
                cancel_label,
                key=f"{unique_key}_cancel"
            )

        return confirmed and not cancelled


# ============ 카드 컴포넌트 ============

def render_metric_card(
    title: str,
    value: str,
    delta: str = None,
    delta_color: str = None,
    icon: str = None
):
    """
    메트릭 카드 렌더링

    Args:
        title: 제목
        value: 값
        delta: 변화량
        delta_color: 변화량 색상 ("up", "down", "neutral")
        icon: 아이콘
    """
    delta_colors = {
        'up': COLORS['success'],
        'down': COLORS['error'],
        'neutral': COLORS['muted']
    }

    delta_html = ""
    if delta:
        color = delta_colors.get(delta_color, COLORS['muted'])
        delta_html = f'<div style="color: {color}; font-size: 14px;">{delta}</div>'

    icon_html = f'<span style="font-size: 24px; margin-right: 8px;">{icon}</span>' if icon else ''

    html = f"""
    <div style="
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid #e5e7eb;
    ">
        <div style="color: #6b7280; font-size: 14px; margin-bottom: 8px;">
            {icon_html}{title}
        </div>
        <div style="font-size: 28px; font-weight: bold; color: #111827;">
            {value}
        </div>
        {delta_html}
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_status_badge(status: str, label: str = None):
    """
    상태 배지 렌더링

    Args:
        status: 상태 ("success", "error", "warning", "info", "pending")
        label: 레이블
    """
    colors = {
        'success': ('#dcfce7', '#166534'),
        'error': ('#fee2e2', '#991b1b'),
        'warning': ('#fef3c7', '#92400e'),
        'info': ('#dbeafe', '#1e40af'),
        'pending': ('#f3f4f6', '#374151'),
    }

    bg_color, text_color = colors.get(status, colors['info'])
    display_label = label or status.capitalize()

    html = f"""
    <span style="
        display: inline-block;
        padding: 4px 12px;
        background: {bg_color};
        color: {text_color};
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 500;
    ">{display_label}</span>
    """
    st.markdown(html, unsafe_allow_html=True)


# ============ 데이터 로딩 헬퍼 ============

def safe_data_load(
    load_func: Callable,
    error_message: str = "데이터를 불러올 수 없습니다",
    default_value: Any = None,
    show_error_ui: bool = True
) -> Any:
    """
    안전한 데이터 로딩

    Args:
        load_func: 데이터 로딩 함수
        error_message: 에러 메시지
        default_value: 기본값
        show_error_ui: 에러 UI 표시 여부

    Returns:
        로딩된 데이터 또는 기본값
    """
    try:
        return load_func()
    except Exception as e:
        if show_error_ui:
            show_error(error_message, details=str(e))
        return default_value


def with_error_handling(error_message: str = "오류가 발생했습니다"):
    """
    에러 처리 데코레이터

    Usage:
        @with_error_handling("데이터 로딩 실패")
        def load_data():
            return fetch_from_api()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                show_error(error_message, details=str(e))
                return None
        return wrapper
    return decorator


# ============ 페이지네이션 ============

def render_pagination(
    total_items: int,
    items_per_page: int = 10,
    current_page: int = 1,
    key: str = "pagination"
) -> int:
    """
    페이지네이션 렌더링

    Args:
        total_items: 전체 항목 수
        items_per_page: 페이지당 항목 수
        current_page: 현재 페이지
        key: 고유 키

    Returns:
        선택된 페이지 번호
    """
    total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)

    col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])

    with col1:
        if st.button("⏮️", key=f"{key}_first", disabled=current_page <= 1):
            return 1

    with col2:
        if st.button("◀️", key=f"{key}_prev", disabled=current_page <= 1):
            return current_page - 1

    with col3:
        st.markdown(
            f"<div style='text-align: center; padding: 8px;'>"
            f"페이지 {current_page} / {total_pages}</div>",
            unsafe_allow_html=True
        )

    with col4:
        if st.button("▶️", key=f"{key}_next", disabled=current_page >= total_pages):
            return current_page + 1

    with col5:
        if st.button("⏭️", key=f"{key}_last", disabled=current_page >= total_pages):
            return total_pages

    return current_page
