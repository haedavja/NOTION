"""
알림 푸시 서비스
================

브라우저 알림, 이메일 알림, 인앱 알림을 관리합니다.

주요 기능:
---------
- NotificationService: 알림 전송 서비스
- NotificationCenter: 알림 센터 UI
- EmailNotifier: 이메일 알림 (선택적)
- BrowserNotifier: 브라우저 푸시 알림

사용 예시:
---------
    from utils.notification_service import NotificationService, render_notification_center

    # 알림 서비스 초기화
    notifier = NotificationService()

    # 알림 전송
    notifier.send(
        title="목표가 도달",
        message="삼성전자가 80,000원에 도달했습니다",
        type="success",
        category="price_alert"
    )

    # 알림 센터 렌더링
    render_notification_center()
"""

import streamlit as st
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging
import threading
import time

logger = logging.getLogger(__name__)


# ============ 설정 ============

NOTIFICATIONS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'notifications.json'
)

NOTIFICATION_SETTINGS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'notification_settings.json'
)

MAX_NOTIFICATIONS = 100  # 최대 저장 알림 수


# ============ 열거형 ============

class NotificationType(Enum):
    """알림 유형"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class NotificationCategory(Enum):
    """알림 카테고리"""
    PRICE_ALERT = "price_alert"     # 가격 알림
    MARKET_NEWS = "market_news"     # 시장 뉴스
    SYSTEM = "system"               # 시스템 알림
    ANALYSIS = "analysis"           # 분석 완료
    PORTFOLIO = "portfolio"         # 포트폴리오 변동


class NotificationChannel(Enum):
    """알림 채널"""
    IN_APP = "in_app"           # 인앱 알림
    BROWSER = "browser"         # 브라우저 알림
    EMAIL = "email"             # 이메일


# ============ 데이터 클래스 ============

@dataclass
class Notification:
    """알림 데이터"""
    id: str
    title: str
    message: str
    type: str = "info"
    category: str = "system"
    created_at: str = ""
    read: bool = False
    data: Dict = field(default_factory=dict)  # 추가 데이터
    action_url: str = ""  # 클릭 시 이동 URL

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.id:
            self.id = f"notif_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


@dataclass
class NotificationSettings:
    """알림 설정"""
    enabled: bool = True
    channels: List[str] = field(default_factory=lambda: ["in_app"])
    categories: Dict[str, bool] = field(default_factory=lambda: {
        "price_alert": True,
        "market_news": True,
        "system": True,
        "analysis": True,
        "portfolio": True
    })
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"
    email_address: str = ""


# ============ 저장/로드 함수 ============

def ensure_data_dir():
    """데이터 디렉토리 확인"""
    data_dir = os.path.dirname(NOTIFICATIONS_FILE)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)


def load_notifications() -> List[Notification]:
    """알림 로드"""
    try:
        ensure_data_dir()
        if not os.path.exists(NOTIFICATIONS_FILE):
            return []

        with open(NOTIFICATIONS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return [Notification(**n) for n in data]
    except Exception as e:
        logger.error(f"알림 로드 실패: {e}")
        return []


def save_notifications(notifications: List[Notification]) -> bool:
    """알림 저장"""
    try:
        ensure_data_dir()
        # 최대 개수 제한
        notifications = notifications[-MAX_NOTIFICATIONS:]
        data = [asdict(n) for n in notifications]

        with open(NOTIFICATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return True
    except Exception as e:
        logger.error(f"알림 저장 실패: {e}")
        return False


def load_notification_settings() -> NotificationSettings:
    """알림 설정 로드"""
    try:
        ensure_data_dir()
        if not os.path.exists(NOTIFICATION_SETTINGS_FILE):
            return NotificationSettings()

        with open(NOTIFICATION_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return NotificationSettings(**data)
    except Exception as e:
        logger.error(f"알림 설정 로드 실패: {e}")
        return NotificationSettings()


def save_notification_settings(settings: NotificationSettings) -> bool:
    """알림 설정 저장"""
    try:
        ensure_data_dir()
        with open(NOTIFICATION_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(asdict(settings), f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"알림 설정 저장 실패: {e}")
        return False


# ============ 알림 서비스 ============

class NotificationService:
    """
    알림 서비스

    Usage:
        notifier = NotificationService()
        notifier.send("제목", "메시지", type="success")
    """

    def __init__(self):
        self.settings = load_notification_settings()
        self._handlers: Dict[str, List[Callable]] = {}

    def send(
        self,
        title: str,
        message: str,
        type: str = "info",
        category: str = "system",
        data: Dict = None,
        action_url: str = ""
    ) -> Optional[Notification]:
        """
        알림 전송

        Args:
            title: 알림 제목
            message: 알림 메시지
            type: 알림 유형 (info, success, warning, error)
            category: 카테고리
            data: 추가 데이터
            action_url: 클릭 시 이동 URL

        Returns:
            생성된 알림 객체
        """
        if not self.settings.enabled:
            return None

        # 카테고리 활성화 확인
        if not self.settings.categories.get(category, True):
            return None

        # 방해 금지 시간 확인
        if self._is_quiet_hours():
            return None

        notification = Notification(
            id="",
            title=title,
            message=message,
            type=type,
            category=category,
            data=data or {},
            action_url=action_url
        )

        # 저장
        notifications = load_notifications()
        notifications.append(notification)
        save_notifications(notifications)

        # 채널별 전송
        for channel in self.settings.channels:
            self._send_to_channel(channel, notification)

        # 핸들러 호출
        self._trigger_handlers(category, notification)

        return notification

    def _is_quiet_hours(self) -> bool:
        """방해 금지 시간 확인"""
        if not self.settings.quiet_hours_enabled:
            return False

        try:
            now = datetime.now().time()
            start = datetime.strptime(self.settings.quiet_hours_start, "%H:%M").time()
            end = datetime.strptime(self.settings.quiet_hours_end, "%H:%M").time()

            if start <= end:
                return start <= now <= end
            else:  # 자정을 넘는 경우
                return now >= start or now <= end
        except Exception:
            return False

    def _send_to_channel(self, channel: str, notification: Notification):
        """채널별 알림 전송"""
        if channel == NotificationChannel.BROWSER.value:
            self._send_browser_notification(notification)
        elif channel == NotificationChannel.EMAIL.value:
            self._send_email_notification(notification)
        # IN_APP은 자동 저장됨

    def _send_browser_notification(self, notification: Notification):
        """브라우저 알림 전송 (JavaScript 사용)"""
        # Streamlit에서는 직접적인 브라우저 알림이 제한적
        # 세션 상태에 저장하여 프론트엔드에서 처리
        if 'pending_browser_notifications' not in st.session_state:
            st.session_state['pending_browser_notifications'] = []

        st.session_state['pending_browser_notifications'].append({
            'title': notification.title,
            'body': notification.message,
            'icon': self._get_notification_icon(notification.type)
        })

    def _send_email_notification(self, notification: Notification):
        """이메일 알림 전송"""
        if not self.settings.email_address:
            return

        # 이메일 전송 로직 (실제 구현 시 SMTP 설정 필요)
        logger.info(f"이메일 알림 전송 예정: {notification.title} -> {self.settings.email_address}")

    def _get_notification_icon(self, type: str) -> str:
        """알림 유형별 아이콘"""
        icons = {
            'success': '/static/icons/success.png',
            'error': '/static/icons/error.png',
            'warning': '/static/icons/warning.png',
            'info': '/static/icons/info.png'
        }
        return icons.get(type, icons['info'])

    def register_handler(self, category: str, handler: Callable):
        """알림 핸들러 등록"""
        if category not in self._handlers:
            self._handlers[category] = []
        self._handlers[category].append(handler)

    def _trigger_handlers(self, category: str, notification: Notification):
        """핸들러 호출"""
        handlers = self._handlers.get(category, []) + self._handlers.get('*', [])
        for handler in handlers:
            try:
                handler(notification)
            except Exception as e:
                logger.error(f"알림 핸들러 오류: {e}")

    def get_unread_count(self) -> int:
        """읽지 않은 알림 수"""
        notifications = load_notifications()
        return len([n for n in notifications if not n.read])

    def mark_as_read(self, notification_id: str) -> bool:
        """알림 읽음 처리"""
        notifications = load_notifications()
        for n in notifications:
            if n.id == notification_id:
                n.read = True
                break
        return save_notifications(notifications)

    def mark_all_as_read(self) -> bool:
        """모든 알림 읽음 처리"""
        notifications = load_notifications()
        for n in notifications:
            n.read = True
        return save_notifications(notifications)

    def delete_notification(self, notification_id: str) -> bool:
        """알림 삭제"""
        notifications = load_notifications()
        notifications = [n for n in notifications if n.id != notification_id]
        return save_notifications(notifications)

    def clear_all(self) -> bool:
        """모든 알림 삭제"""
        return save_notifications([])


# ============ 전역 인스턴스 ============

_notification_service: Optional[NotificationService] = None


def get_notification_service() -> NotificationService:
    """전역 알림 서비스 반환"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


def send_notification(
    title: str,
    message: str,
    type: str = "info",
    category: str = "system",
    **kwargs
) -> Optional[Notification]:
    """알림 전송 헬퍼 함수"""
    return get_notification_service().send(
        title=title,
        message=message,
        type=type,
        category=category,
        **kwargs
    )


# ============ UI 컴포넌트 ============

def render_notification_bell():
    """알림 벨 아이콘 (사이드바용)"""
    service = get_notification_service()
    unread = service.get_unread_count()

    if unread > 0:
        st.sidebar.markdown(
            f"""
            <div style="
                position: relative;
                display: inline-block;
                cursor: pointer;
            ">
                <span style="font-size: 24px;">🔔</span>
                <span style="
                    position: absolute;
                    top: -5px;
                    right: -10px;
                    background: #ef4444;
                    color: white;
                    border-radius: 50%;
                    padding: 2px 6px;
                    font-size: 10px;
                    font-weight: bold;
                ">{unread if unread < 100 else '99+'}</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.sidebar.markdown("🔔", unsafe_allow_html=True)


def render_notification_center():
    """알림 센터 UI"""
    st.subheader("🔔 알림 센터")

    service = get_notification_service()
    notifications = load_notifications()

    # 필터 및 액션
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        filter_type = st.selectbox(
            "필터",
            options=['전체', '읽지 않음', NotificationCategory.PRICE_ALERT.value,
                     NotificationCategory.MARKET_NEWS.value, NotificationCategory.SYSTEM.value],
            key="notification_filter"
        )

    with col2:
        if st.button("모두 읽음", key="mark_all_read"):
            service.mark_all_as_read()
            st.rerun()

    with col3:
        if st.button("전체 삭제", key="clear_all_notifications"):
            service.clear_all()
            st.rerun()

    # 필터링
    filtered = notifications
    if filter_type == '읽지 않음':
        filtered = [n for n in notifications if not n.read]
    elif filter_type in [c.value for c in NotificationCategory]:
        filtered = [n for n in notifications if n.category == filter_type]

    # 알림 목록 (최신순)
    filtered = sorted(filtered, key=lambda x: x.created_at, reverse=True)

    if not filtered:
        st.info("알림이 없습니다")
        return

    for notif in filtered:
        _render_notification_item(notif, service)


def _render_notification_item(notification: Notification, service: NotificationService):
    """개별 알림 아이템 렌더링"""
    type_icons = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️'
    }

    category_labels = {
        'price_alert': '가격 알림',
        'market_news': '시장 뉴스',
        'system': '시스템',
        'analysis': '분석',
        'portfolio': '포트폴리오'
    }

    icon = type_icons.get(notification.type, 'ℹ️')
    category_label = category_labels.get(notification.category, notification.category)

    # 시간 포맷
    try:
        created = datetime.fromisoformat(notification.created_at)
        time_str = _format_relative_time(created)
    except Exception:
        time_str = notification.created_at

    # 읽지 않은 알림 스타일
    bg_color = "#f0f9ff" if not notification.read else "#ffffff"
    border_color = "#3b82f6" if not notification.read else "#e5e7eb"

    with st.container():
        st.markdown(
            f"""
            <div style="
                background: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                padding: 12px;
                margin-bottom: 8px;
            ">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <span style="font-size: 18px; margin-right: 8px;">{icon}</span>
                        <strong>{notification.title}</strong>
                        <span style="
                            background: #e5e7eb;
                            color: #374151;
                            padding: 2px 8px;
                            border-radius: 4px;
                            font-size: 11px;
                            margin-left: 8px;
                        ">{category_label}</span>
                    </div>
                    <span style="color: #6b7280; font-size: 12px;">{time_str}</span>
                </div>
                <p style="color: #4b5563; margin: 8px 0 0 26px;">{notification.message}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("🗑️", key=f"del_{notification.id}", help="삭제"):
                service.delete_notification(notification.id)
                st.rerun()


def _format_relative_time(dt: datetime) -> str:
    """상대 시간 포맷"""
    now = datetime.now()
    diff = now - dt

    if diff.days > 7:
        return dt.strftime("%m/%d")
    elif diff.days > 0:
        return f"{diff.days}일 전"
    elif diff.seconds >= 3600:
        return f"{diff.seconds // 3600}시간 전"
    elif diff.seconds >= 60:
        return f"{diff.seconds // 60}분 전"
    else:
        return "방금 전"


def render_notification_settings():
    """알림 설정 UI"""
    st.subheader("⚙️ 알림 설정")

    settings = load_notification_settings()

    # 알림 활성화
    settings.enabled = st.toggle("알림 활성화", value=settings.enabled)

    st.markdown("### 카테고리별 설정")

    col1, col2 = st.columns(2)

    with col1:
        settings.categories['price_alert'] = st.checkbox(
            "🎯 가격 알림",
            value=settings.categories.get('price_alert', True)
        )
        settings.categories['market_news'] = st.checkbox(
            "📰 시장 뉴스",
            value=settings.categories.get('market_news', True)
        )
        settings.categories['system'] = st.checkbox(
            "⚙️ 시스템 알림",
            value=settings.categories.get('system', True)
        )

    with col2:
        settings.categories['analysis'] = st.checkbox(
            "📊 분석 완료",
            value=settings.categories.get('analysis', True)
        )
        settings.categories['portfolio'] = st.checkbox(
            "💼 포트폴리오",
            value=settings.categories.get('portfolio', True)
        )

    st.markdown("### 방해 금지 시간")

    settings.quiet_hours_enabled = st.checkbox(
        "방해 금지 시간 설정",
        value=settings.quiet_hours_enabled
    )

    if settings.quiet_hours_enabled:
        col1, col2 = st.columns(2)
        with col1:
            settings.quiet_hours_start = st.time_input(
                "시작 시간",
                value=datetime.strptime(settings.quiet_hours_start, "%H:%M").time()
            ).strftime("%H:%M")
        with col2:
            settings.quiet_hours_end = st.time_input(
                "종료 시간",
                value=datetime.strptime(settings.quiet_hours_end, "%H:%M").time()
            ).strftime("%H:%M")

    st.markdown("### 이메일 알림")

    settings.email_address = st.text_input(
        "이메일 주소",
        value=settings.email_address,
        placeholder="example@email.com"
    )

    if settings.email_address:
        if 'email' not in settings.channels:
            settings.channels.append('email')
    else:
        if 'email' in settings.channels:
            settings.channels.remove('email')

    # 저장
    if st.button("설정 저장", type="primary"):
        if save_notification_settings(settings):
            st.success("설정이 저장되었습니다")
        else:
            st.error("설정 저장에 실패했습니다")


def render_browser_notification_script():
    """브라우저 알림 스크립트 (페이지에 삽입)"""
    # 대기 중인 브라우저 알림 처리
    pending = st.session_state.get('pending_browser_notifications', [])

    if pending:
        for notif in pending:
            st.markdown(
                f"""
                <script>
                if (Notification.permission === 'granted') {{
                    new Notification('{notif["title"]}', {{
                        body: '{notif["body"]}',
                        icon: '{notif.get("icon", "")}'
                    }});
                }} else if (Notification.permission !== 'denied') {{
                    Notification.requestPermission();
                }}
                </script>
                """,
                unsafe_allow_html=True
            )

        st.session_state['pending_browser_notifications'] = []


def request_browser_notification_permission():
    """브라우저 알림 권한 요청"""
    st.markdown(
        """
        <script>
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission();
        }
        </script>
        """,
        unsafe_allow_html=True
    )
