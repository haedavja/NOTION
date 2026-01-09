"""
목표가 알림 컴포넌트
가격 알림 설정 및 관리
"""

import streamlit as st
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# 알림 저장 경로
ALERTS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'alerts.json'
)


class AlertType(Enum):
    """알림 유형"""
    TARGET_PRICE = "목표가"
    STOP_LOSS = "손절가"
    PERCENT_CHANGE = "등락률"
    VOLUME_SPIKE = "거래량급증"


class AlertStatus(Enum):
    """알림 상태"""
    ACTIVE = "활성"
    TRIGGERED = "발동됨"
    EXPIRED = "만료"
    DISABLED = "비활성"


@dataclass
class PriceAlert:
    """가격 알림"""
    id: str
    stock_code: str
    stock_name: str
    alert_type: str
    condition: str  # 'above', 'below', 'percent_up', 'percent_down'
    target_value: float
    base_price: Optional[float] = None  # 기준가 (등락률 계산용)
    created_at: str = ""
    triggered_at: Optional[str] = None
    status: str = "active"
    memo: str = ""


def ensure_data_dir():
    """데이터 디렉토리 확인"""
    data_dir = os.path.dirname(ALERTS_FILE)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)


def load_alerts() -> List[PriceAlert]:
    """모든 알림 로드"""
    try:
        ensure_data_dir()
        if not os.path.exists(ALERTS_FILE):
            return []

        with open(ALERTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return [PriceAlert(**alert) for alert in data]
    except Exception as e:
        logger.error(f"알림 로드 실패: {e}")
        return []


def save_alerts(alerts: List[PriceAlert]) -> bool:
    """모든 알림 저장"""
    try:
        ensure_data_dir()
        data = [asdict(alert) for alert in alerts]

        with open(ALERTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return True
    except Exception as e:
        logger.error(f"알림 저장 실패: {e}")
        return False


def generate_alert_id() -> str:
    """알림 ID 생성"""
    return f"alert_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def create_alert(
    stock_code: str,
    stock_name: str,
    alert_type: AlertType,
    condition: str,
    target_value: float,
    base_price: float = None,
    memo: str = ""
) -> Optional[PriceAlert]:
    """알림 생성"""
    try:
        alert = PriceAlert(
            id=generate_alert_id(),
            stock_code=stock_code,
            stock_name=stock_name,
            alert_type=alert_type.value,
            condition=condition,
            target_value=target_value,
            base_price=base_price,
            created_at=datetime.now().isoformat(),
            memo=memo
        )

        alerts = load_alerts()
        alerts.append(alert)
        save_alerts(alerts)

        return alert
    except Exception as e:
        logger.error(f"알림 생성 실패: {e}")
        return None


def delete_alert(alert_id: str) -> bool:
    """알림 삭제"""
    alerts = load_alerts()
    alerts = [a for a in alerts if a.id != alert_id]
    return save_alerts(alerts)


def update_alert_status(alert_id: str, status: AlertStatus) -> bool:
    """알림 상태 업데이트"""
    alerts = load_alerts()

    for alert in alerts:
        if alert.id == alert_id:
            alert.status = status.value
            if status == AlertStatus.TRIGGERED:
                alert.triggered_at = datetime.now().isoformat()
            break

    return save_alerts(alerts)


def get_active_alerts(stock_code: str = None) -> List[PriceAlert]:
    """활성 알림 조회"""
    alerts = load_alerts()
    active = [a for a in alerts if a.status == AlertStatus.ACTIVE.value]

    if stock_code:
        active = [a for a in active if a.stock_code == stock_code]

    return active


def check_alert_condition(alert: PriceAlert, current_price: float) -> bool:
    """알림 조건 확인"""
    if alert.condition == 'above':
        return current_price >= alert.target_value
    elif alert.condition == 'below':
        return current_price <= alert.target_value
    elif alert.condition == 'percent_up' and alert.base_price:
        change = (current_price - alert.base_price) / alert.base_price * 100
        return change >= alert.target_value
    elif alert.condition == 'percent_down' and alert.base_price:
        change = (current_price - alert.base_price) / alert.base_price * 100
        return change <= -alert.target_value

    return False


def check_and_trigger_alerts(stock_prices: Dict[str, float]) -> List[PriceAlert]:
    """
    알림 조건 확인 및 발동

    Args:
        stock_prices: {종목코드: 현재가} 딕셔너리

    Returns:
        발동된 알림 리스트
    """
    triggered = []
    alerts = load_alerts()
    changed = False

    for alert in alerts:
        if alert.status != AlertStatus.ACTIVE.value:
            continue

        current_price = stock_prices.get(alert.stock_code)
        if current_price is None:
            continue

        if check_alert_condition(alert, current_price):
            alert.status = AlertStatus.TRIGGERED.value
            alert.triggered_at = datetime.now().isoformat()
            triggered.append(alert)
            changed = True

    if changed:
        save_alerts(alerts)

    return triggered


def render_alert_creator(stock_code: str, stock_name: str, current_price: float = None):
    """알림 생성 UI"""
    st.markdown(f"### 🔔 {stock_name} 알림 설정")

    col1, col2 = st.columns(2)

    with col1:
        alert_type = st.selectbox(
            "알림 유형",
            options=[AlertType.TARGET_PRICE, AlertType.STOP_LOSS, AlertType.PERCENT_CHANGE],
            format_func=lambda x: x.value,
            key=f"alert_type_{stock_code}"
        )

    with col2:
        if alert_type == AlertType.PERCENT_CHANGE:
            condition = st.selectbox(
                "조건",
                options=['percent_up', 'percent_down'],
                format_func=lambda x: {'percent_up': '상승 시', 'percent_down': '하락 시'}[x],
                key=f"alert_cond_{stock_code}"
            )
        else:
            condition = st.selectbox(
                "조건",
                options=['above', 'below'],
                format_func=lambda x: {'above': '이상이면', 'below': '이하이면'}[x],
                key=f"alert_cond_{stock_code}"
            )

    # 목표값 입력
    if alert_type == AlertType.PERCENT_CHANGE:
        target_value = st.number_input(
            "등락률 (%)",
            min_value=0.1,
            max_value=100.0,
            value=5.0,
            step=0.5,
            key=f"alert_target_{stock_code}"
        )
        label_text = f"현재가 대비 {target_value}% {'상승' if condition == 'percent_up' else '하락'} 시 알림"
    else:
        default_val = current_price or 50000
        if alert_type == AlertType.TARGET_PRICE:
            default_val = int(default_val * 1.1)
        else:
            default_val = int(default_val * 0.9)

        target_value = st.number_input(
            "목표가 (원)",
            min_value=100,
            value=default_val,
            step=1000,
            format="%d",
            key=f"alert_target_{stock_code}"
        )
        label_text = f"{target_value:,}원 {'이상' if condition == 'above' else '이하'} 시 알림"

    st.caption(label_text)

    memo = st.text_input(
        "메모 (선택)",
        placeholder="알림 이유를 기록하세요",
        key=f"alert_memo_{stock_code}"
    )

    if st.button("🔔 알림 설정", key=f"create_alert_{stock_code}", use_container_width=True):
        alert = create_alert(
            stock_code=stock_code,
            stock_name=stock_name,
            alert_type=alert_type,
            condition=condition,
            target_value=target_value,
            base_price=current_price,
            memo=memo
        )

        if alert:
            st.success("알림이 설정되었습니다!")
            st.rerun()
        else:
            st.error("알림 설정에 실패했습니다.")


def render_alert_list():
    """알림 목록 UI"""
    st.subheader("🔔 가격 알림 관리")

    alerts = load_alerts()

    if not alerts:
        st.info("설정된 알림이 없습니다. 종목 분석 페이지에서 알림을 설정하세요!")
        return

    # 상태별 필터
    status_filter = st.selectbox(
        "상태 필터",
        options=['전체', AlertStatus.ACTIVE.value, AlertStatus.TRIGGERED.value, AlertStatus.DISABLED.value],
        key="alert_status_filter"
    )

    filtered = alerts
    if status_filter != '전체':
        filtered = [a for a in alerts if a.status == status_filter]

    # 알림 목록
    for alert in filtered:
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 1.5, 1])

            # 상태 아이콘
            status_icon = {
                AlertStatus.ACTIVE.value: '🟢',
                AlertStatus.TRIGGERED.value: '🔴',
                AlertStatus.DISABLED.value: '⚪',
                AlertStatus.EXPIRED.value: '⚫'
            }.get(alert.status, '❓')

            with col1:
                st.markdown(f"{status_icon} **{alert.stock_name}**")
                st.caption(f"{alert.stock_code}")

            with col2:
                # 조건 표시
                if alert.alert_type == AlertType.PERCENT_CHANGE.value:
                    cond_text = f"{alert.target_value}% {'상승' if alert.condition == 'percent_up' else '하락'}"
                else:
                    cond_text = f"{alert.target_value:,.0f}원 {'이상' if alert.condition == 'above' else '이하'}"

                st.markdown(f"**{alert.alert_type}**: {cond_text}")
                if alert.memo:
                    st.caption(f"📝 {alert.memo}")

            with col3:
                if alert.status == AlertStatus.TRIGGERED.value and alert.triggered_at:
                    triggered_dt = datetime.fromisoformat(alert.triggered_at)
                    st.caption(f"발동: {triggered_dt.strftime('%m/%d %H:%M')}")
                else:
                    created_dt = datetime.fromisoformat(alert.created_at)
                    st.caption(f"생성: {created_dt.strftime('%m/%d')}")

            with col4:
                # 액션 버튼
                if alert.status == AlertStatus.ACTIVE.value:
                    if st.button("⏸️", key=f"pause_{alert.id}", help="비활성화"):
                        update_alert_status(alert.id, AlertStatus.DISABLED)
                        st.rerun()
                elif alert.status == AlertStatus.DISABLED.value:
                    if st.button("▶️", key=f"resume_{alert.id}", help="활성화"):
                        update_alert_status(alert.id, AlertStatus.ACTIVE)
                        st.rerun()

                if st.button("🗑️", key=f"delete_{alert.id}", help="삭제"):
                    delete_alert(alert.id)
                    st.rerun()

            st.divider()

    # 통계
    st.markdown("### 📊 알림 통계")
    col1, col2, col3 = st.columns(3)

    with col1:
        active_count = len([a for a in alerts if a.status == AlertStatus.ACTIVE.value])
        st.metric("활성 알림", f"{active_count}개")

    with col2:
        triggered_count = len([a for a in alerts if a.status == AlertStatus.TRIGGERED.value])
        st.metric("발동된 알림", f"{triggered_count}개")

    with col3:
        st.metric("전체 알림", f"{len(alerts)}개")

    # 일괄 작업
    st.markdown("### ⚙️ 일괄 작업")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🔄 발동된 알림 초기화", use_container_width=True):
            for alert in alerts:
                if alert.status == AlertStatus.TRIGGERED.value:
                    alert.status = AlertStatus.ACTIVE.value
                    alert.triggered_at = None
            save_alerts(alerts)
            st.success("발동된 알림을 다시 활성화했습니다.")
            st.rerun()

    with col2:
        if st.button("⏸️ 모두 비활성화", use_container_width=True):
            for alert in alerts:
                if alert.status == AlertStatus.ACTIVE.value:
                    alert.status = AlertStatus.DISABLED.value
            save_alerts(alerts)
            st.rerun()

    with col3:
        if st.button("🗑️ 모두 삭제", use_container_width=True, type="secondary"):
            if st.session_state.get('confirm_delete_alerts'):
                save_alerts([])
                st.session_state['confirm_delete_alerts'] = False
                st.rerun()
            else:
                st.session_state['confirm_delete_alerts'] = True
                st.warning("한번 더 클릭하면 전체 삭제됩니다.")


def render_alert_notification(triggered_alerts: List[PriceAlert]):
    """발동된 알림 표시"""
    if not triggered_alerts:
        return

    for alert in triggered_alerts:
        if alert.alert_type == AlertType.TARGET_PRICE.value:
            msg = f"🎯 {alert.stock_name}이(가) 목표가 {alert.target_value:,.0f}원에 도달했습니다!"
            st.success(msg)
        elif alert.alert_type == AlertType.STOP_LOSS.value:
            msg = f"⚠️ {alert.stock_name}이(가) 손절가 {alert.target_value:,.0f}원에 도달했습니다!"
            st.warning(msg)
        else:
            msg = f"🔔 {alert.stock_name} 알림이 발동되었습니다!"
            st.info(msg)


def get_alert_summary() -> Dict[str, int]:
    """알림 요약"""
    alerts = load_alerts()
    return {
        'total': len(alerts),
        'active': len([a for a in alerts if a.status == AlertStatus.ACTIVE.value]),
        'triggered': len([a for a in alerts if a.status == AlertStatus.TRIGGERED.value])
    }


def render_alert_badge():
    """사이드바용 알림 배지"""
    summary = get_alert_summary()

    if summary['triggered'] > 0:
        st.sidebar.warning(f"🔴 {summary['triggered']}개 알림 발동!")

    if summary['active'] > 0:
        st.sidebar.caption(f"🔔 활성 알림: {summary['active']}개")
