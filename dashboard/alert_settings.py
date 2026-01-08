"""
알림 설정 UI
텔레그램/디스코드 연동 설정 및 테스트
"""

import streamlit as st
import os
from datetime import datetime


def render_alert_settings():
    """알림 설정 UI 렌더링"""
    st.subheader("🔔 알림 설정")

    # 알림 스케줄러 상태
    from alerts.alert_scheduler import alert_scheduler

    col1, col2 = st.columns([3, 1])
    with col1:
        st.write("**백그라운드 모니터링**")
    with col2:
        if alert_scheduler.running:
            st.success("🟢 실행 중")
        else:
            st.warning("🔴 중지됨")

    # 모니터링 시작/중지
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("▶️ 모니터링 시작", disabled=alert_scheduler.running):
            if 'portfolio' in st.session_state:
                alert_scheduler.start(st.session_state.portfolio)
                st.success("모니터링 시작됨!")
                st.rerun()
            else:
                st.warning("포트폴리오를 먼저 생성하세요")

    with col2:
        if st.button("⏹️ 모니터링 중지", disabled=not alert_scheduler.running):
            alert_scheduler.stop()
            st.info("모니터링 중지됨")
            st.rerun()

    with col3:
        interval = st.selectbox("체크 주기", [60, 300, 600, 1800], index=1,
                                format_func=lambda x: f"{x//60}분")
        alert_scheduler.check_interval = interval

    st.divider()

    # 텔레그램 설정
    st.markdown("#### 📱 텔레그램 알림")

    tg_enabled = st.checkbox("텔레그램 활성화",
                             value=alert_scheduler.settings.get('telegram_enabled', False))
    alert_scheduler.settings['telegram_enabled'] = tg_enabled

    if tg_enabled:
        col1, col2 = st.columns(2)
        with col1:
            tg_token = st.text_input("Bot Token",
                                     value=alert_scheduler.settings.get('telegram_token', '') or '',
                                     type="password",
                                     help="@BotFather에서 발급받은 토큰")
            alert_scheduler.settings['telegram_token'] = tg_token

        with col2:
            tg_chat = st.text_input("Chat ID",
                                    value=alert_scheduler.settings.get('telegram_chat_id', '') or '',
                                    help="@userinfobot에서 확인")
            alert_scheduler.settings['telegram_chat_id'] = tg_chat

        if st.button("📤 텔레그램 테스트", disabled=not (tg_token and tg_chat)):
            if _test_telegram(tg_token, tg_chat):
                st.success("✅ 텔레그램 전송 성공!")
            else:
                st.error("❌ 전송 실패 - 토큰/Chat ID 확인")

    st.divider()

    # 디스코드 설정
    st.markdown("#### 💬 디스코드 알림")

    dc_enabled = st.checkbox("디스코드 활성화",
                             value=alert_scheduler.settings.get('discord_enabled', False))
    alert_scheduler.settings['discord_enabled'] = dc_enabled

    if dc_enabled:
        dc_webhook = st.text_input("Webhook URL",
                                   value=alert_scheduler.settings.get('discord_webhook', '') or '',
                                   type="password",
                                   help="서버 설정 > 연동 > 웹후크에서 생성")
        alert_scheduler.settings['discord_webhook'] = dc_webhook

        if st.button("📤 디스코드 테스트", disabled=not dc_webhook):
            if _test_discord(dc_webhook):
                st.success("✅ 디스코드 전송 성공!")
            else:
                st.error("❌ 전송 실패 - Webhook URL 확인")

    st.divider()

    # 알림 필터
    st.markdown("#### ⚙️ 알림 필터")

    severity = st.selectbox("최소 심각도",
                            ['INFO', 'WARNING', 'CRITICAL', 'EMERGENCY'],
                            index=1,
                            help="이 수준 이상만 알림")
    alert_scheduler.settings['min_severity'] = severity

    st.divider()

    # 최근 알림 히스토리
    st.markdown("#### 📜 최근 알림")

    history = alert_scheduler.get_alert_history(10)
    if history:
        for alert in reversed(history):
            severity_icon = {
                'info': 'ℹ️', 'warning': '⚠️',
                'critical': '🔴', 'emergency': '🚨'
            }.get(alert['severity'], '📢')

            with st.expander(f"{severity_icon} {alert['title']} ({alert['timestamp'][:16]})"):
                st.write(f"**종목**: {alert['symbol']}")
                st.write(f"**내용**: {alert['message']}")
                st.write(f"**유형**: {alert['type']}")
    else:
        st.info("최근 알림이 없습니다")


def _test_telegram(token: str, chat_id: str) -> bool:
    """텔레그램 테스트 메시지 전송"""
    try:
        import requests
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': f"🔔 *테스트 알림*\n\n포트폴리오 알림 시스템이 정상적으로 연결되었습니다.\n\n시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            'parse_mode': 'Markdown'
        }
        resp = requests.post(url, data=data, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"Telegram test error: {e}")
        return False


def _test_discord(webhook_url: str) -> bool:
    """디스코드 테스트 메시지 전송"""
    try:
        import requests
        data = {
            'embeds': [{
                'title': '🔔 테스트 알림',
                'description': '포트폴리오 알림 시스템이 정상적으로 연결되었습니다.',
                'color': 0x00ff00,
                'timestamp': datetime.now().isoformat()
            }]
        }
        resp = requests.post(webhook_url, json=data, timeout=10)
        return resp.status_code in [200, 204]
    except Exception as e:
        print(f"Discord test error: {e}")
        return False
