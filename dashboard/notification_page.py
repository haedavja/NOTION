"""
알림 대시보드
알림 통합 관리 및 규칙 설정
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any
from utils.validators import validate_alert_input

try:
    from alerts.notification import notification_manager, NotificationMessage
    NOTIFICATION_AVAILABLE = True
except ImportError:
    NOTIFICATION_AVAILABLE = False

try:
    from alerts.price_monitor import price_monitor
    PRICE_MONITOR_AVAILABLE = True
except ImportError:
    PRICE_MONITOR_AVAILABLE = False


def render_notification_history():
    """알림 히스토리"""
    st.subheader("📜 알림 히스토리")

    if not NOTIFICATION_AVAILABLE:
        st.warning("알림 모듈을 사용할 수 없습니다.")
        return

    history = notification_manager.get_history(limit=100)

    if not history:
        st.info("알림 히스토리가 없습니다.")
        return

    # 필터
    col1, col2, col3 = st.columns(3)
    with col1:
        type_filter = st.selectbox(
            "유형",
            ["전체", "info", "alert", "warning", "error"],
            key="history_type_filter"
        )
    with col2:
        days_filter = st.selectbox(
            "기간",
            [("최근 7일", 7), ("최근 30일", 30), ("전체", 365)],
            format_func=lambda x: x[0],
            key="history_days_filter"
        )
    with col3:
        keyword = st.text_input("검색", placeholder="키워드", key="history_keyword")

    # 필터링
    filtered = history

    if type_filter != "전체":
        filtered = [h for h in filtered if h.get('type') == type_filter]

    if days_filter[1] < 365:
        cutoff = (datetime.now() - timedelta(days=days_filter[1])).isoformat()
        filtered = [h for h in filtered if h.get('timestamp', '') >= cutoff]

    if keyword:
        keyword_lower = keyword.lower()
        filtered = [h for h in filtered
                    if keyword_lower in h.get('title', '').lower() or
                       keyword_lower in h.get('body', '').lower()]

    # 통계
    st.markdown(f"**총 {len(filtered)}개 알림**")

    col1, col2, col3, col4 = st.columns(4)
    type_counts = {}
    for h in filtered:
        t = h.get('type', 'unknown')
        type_counts[t] = type_counts.get(t, 0) + 1

    with col1:
        st.metric("ℹ️ 정보", type_counts.get('info', 0))
    with col2:
        st.metric("🔔 알림", type_counts.get('alert', 0))
    with col3:
        st.metric("⚠️ 경고", type_counts.get('warning', 0))
    with col4:
        st.metric("🚨 에러", type_counts.get('error', 0))

    # 히스토리 목록
    st.markdown("---")

    for item in filtered[:50]:
        type_emoji = {
            "info": "ℹ️",
            "alert": "🔔",
            "warning": "⚠️",
            "error": "🚨"
        }.get(item.get('type'), "📢")

        timestamp = item.get('timestamp', '')[:16].replace('T', ' ')
        title = item.get('title', 'No Title')

        with st.expander(f"{type_emoji} [{timestamp}] {title}"):
            st.write(item.get('body', ''))

            if item.get('symbol'):
                st.write(f"**종목:** {item['symbol']}")

            if item.get('data'):
                st.write("**상세 정보:**")
                for key, value in item['data'].items():
                    st.write(f"  - {key}: {value}")

            results = item.get('results', {})
            if results:
                st.write("**전송 결과:**")
                for channel, success in results.items():
                    status = "✅" if success else "❌"
                    st.write(f"  - {channel}: {status}")


def render_alert_rules():
    """알림 규칙 관리"""
    st.subheader("📋 알림 규칙")

    if not PRICE_MONITOR_AVAILABLE:
        st.warning("가격 모니터 모듈을 사용할 수 없습니다.")
        return

    # 현재 알림 규칙
    alerts = price_monitor.get_alerts()

    if alerts:
        st.markdown(f"**활성 알림: {len(alerts)}개**")

        for alert in alerts:
            col1, col2, col3 = st.columns([3, 2, 1])

            with col1:
                condition_text = {
                    "above": "이상",
                    "below": "이하",
                    "change": "변동"
                }.get(alert.condition.value, alert.condition.value)

                st.write(f"**{alert.name}** ({alert.symbol})")
                st.caption(f"조건: {alert.target_value:,.0f}원 {condition_text}")

            with col2:
                status = "🟢 활성" if alert.is_active else "⚪ 비활성"
                st.write(status)
                if alert.triggered_at:
                    st.caption(f"발동: {alert.triggered_at[:10]}")

            with col3:
                if st.button("삭제", key=f"del_{alert.id}"):
                    price_monitor.remove_alert(alert.id)
                    st.rerun()
    else:
        st.info("등록된 알림 규칙이 없습니다.")

    # 새 알림 추가
    st.markdown("---")
    st.markdown("### ➕ 새 알림 추가")

    col1, col2 = st.columns(2)
    with col1:
        new_symbol = st.text_input("심볼", placeholder="005930.KS", key="alert_new_symbol")
        new_name = st.text_input("종목명", placeholder="삼성전자", key="alert_new_name")
    with col2:
        new_condition = st.selectbox(
            "조건",
            [("이상 도달", "above"), ("이하 도달", "below"), ("변동률", "change")],
            format_func=lambda x: x[0],
            key="alert_new_condition"
        )
        new_target = st.number_input("목표값", min_value=0.0, step=100.0, key="alert_new_target")

    if st.button("알림 추가", type="primary"):
        # 입력 검증
        validation = validate_alert_input(
            symbol=new_symbol,
            target_value=new_target,
            condition=new_condition[1]
        )

        if not validation.is_valid:
            for error in validation.get_all_error_messages():
                st.error(error)
        else:
            try:
                from alerts.price_monitor import AlertCondition
                price_monitor.add_alert(
                    symbol=validation.sanitized.get('symbol', new_symbol),
                    name=new_name or new_symbol,
                    condition=AlertCondition(new_condition[1]),
                    target_value=validation.sanitized.get('target_value', new_target)
                )
                st.success("알림이 추가되었습니다.")
                st.rerun()
            except Exception as e:
                st.error(f"추가 실패: {e}")


def render_channel_settings():
    """채널 설정"""
    st.subheader("🔧 알림 채널 설정")

    if not NOTIFICATION_AVAILABLE:
        st.warning("알림 모듈을 사용할 수 없습니다.")
        return

    # 채널 상태
    status = notification_manager.get_channel_status()

    st.markdown("### 채널 상태")

    channels = [
        ("TelegramChannel", "텔레그램", "🔵"),
        ("SlackChannel", "슬랙", "🟣"),
        ("EmailChannel", "이메일", "🟠")
    ]

    for channel_name, display_name, emoji in channels:
        is_active = status.get(channel_name, False)
        status_text = "✅ 연결됨" if is_active else "❌ 미연결"
        st.write(f"{emoji} **{display_name}**: {status_text}")

    # 테스트
    st.markdown("---")
    st.markdown("### 테스트 알림")

    if st.button("테스트 알림 전송"):
        with st.spinner("전송 중..."):
            results = notification_manager.test_channels()

        if results:
            st.success("테스트 알림 전송 완료")
            for channel, success in results.items():
                status = "✅ 성공" if success else "❌ 실패"
                st.write(f"  - {channel}: {status}")
        else:
            st.warning("전송할 채널이 없습니다.")

    # 설정 안내
    st.markdown("---")
    st.markdown("### 설정 방법")

    with st.expander("텔레그램 설정"):
        st.markdown("""
        1. [@BotFather](https://t.me/BotFather)에서 봇 생성
        2. 봇 토큰 획득
        3. `.env` 파일에 설정:
        ```
        TELEGRAM_BOT_TOKEN=your-bot-token
        TELEGRAM_CHAT_ID=your-chat-id
        ```
        4. 챗 ID는 [@userinfobot](https://t.me/userinfobot)에서 확인
        """)

    with st.expander("슬랙 설정"):
        st.markdown("""
        1. [Slack API](https://api.slack.com/apps)에서 앱 생성
        2. Incoming Webhooks 활성화
        3. 채널에 웹훅 추가
        4. `.env` 파일에 설정:
        ```
        SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
        ```
        """)

    with st.expander("이메일 설정"):
        st.markdown("""
        Gmail 앱 비밀번호 사용 권장:
        1. Google 계정 → 보안 → 2단계 인증 활성화
        2. 앱 비밀번호 생성
        3. `.env` 파일에 설정:
        ```
        SMTP_USERNAME=your-email@gmail.com
        SMTP_PASSWORD=your-app-password
        EMAIL_TO=recipient@example.com
        ```
        """)


def render_notification_stats():
    """알림 통계"""
    st.subheader("📊 알림 통계")

    if not NOTIFICATION_AVAILABLE:
        st.warning("알림 모듈을 사용할 수 없습니다.")
        return

    history = notification_manager.get_history(limit=500)

    if not history:
        st.info("통계를 위한 데이터가 없습니다.")
        return

    # 일별 알림 수
    daily_counts = {}
    type_counts = {}
    symbol_counts = {}

    for item in history:
        date = item.get('timestamp', '')[:10]
        msg_type = item.get('type', 'unknown')
        symbol = item.get('symbol')

        daily_counts[date] = daily_counts.get(date, 0) + 1
        type_counts[msg_type] = type_counts.get(msg_type, 0) + 1
        if symbol:
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1

    # 일별 차트
    if daily_counts:
        st.markdown("### 일별 알림 수")
        df = pd.DataFrame([
            {"날짜": k, "알림 수": v}
            for k, v in sorted(daily_counts.items())[-30:]
        ])
        st.bar_chart(df.set_index("날짜"))

    # 유형별 분포
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 유형별 분포")
        type_df = pd.DataFrame([
            {"유형": k, "건수": v}
            for k, v in type_counts.items()
        ])
        if not type_df.empty:
            st.bar_chart(type_df.set_index("유형"))

    with col2:
        st.markdown("### 종목별 알림 (Top 10)")
        symbol_df = pd.DataFrame([
            {"종목": k, "건수": v}
            for k, v in sorted(symbol_counts.items(),
                               key=lambda x: x[1], reverse=True)[:10]
        ])
        if not symbol_df.empty:
            st.dataframe(symbol_df, use_container_width=True, hide_index=True)


def render_notification_dashboard():
    """알림 대시보드 메인"""
    st.title("🔔 알림 대시보드")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📜 히스토리",
        "📋 알림 규칙",
        "🔧 채널 설정",
        "📊 통계"
    ])

    with tab1:
        render_notification_history()

    with tab2:
        render_alert_rules()

    with tab3:
        render_channel_settings()

    with tab4:
        render_notification_stats()
