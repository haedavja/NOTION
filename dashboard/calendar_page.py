"""
캘린더 및 워치리스트 대시보드 페이지
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

try:
    from data.economic_calendar import economic_calendar, EconomicEvent
    CALENDAR_AVAILABLE = True
except ImportError:
    CALENDAR_AVAILABLE = False

try:
    from portfolio.watchlist import watchlist_manager, WatchlistItem
    WATCHLIST_AVAILABLE = True
except ImportError:
    WATCHLIST_AVAILABLE = False

try:
    from analysis.chart_patterns import chart_analyzer
    import yfinance as yf
    PATTERNS_AVAILABLE = True
except ImportError:
    PATTERNS_AVAILABLE = False

try:
    from utils.backup import backup_manager
    BACKUP_AVAILABLE = True
except ImportError:
    BACKUP_AVAILABLE = False


def render_economic_calendar():
    """경제 캘린더 렌더링"""
    st.subheader("📅 경제 캘린더")

    if not CALENDAR_AVAILABLE:
        st.warning("경제 캘린더 모듈을 사용할 수 없습니다.")
        return

    # 필터
    col1, col2, col3 = st.columns(3)
    with col1:
        days = st.selectbox("기간", [7, 14, 30, 60], index=1)
    with col2:
        country = st.selectbox("국가", ["전체", "US", "KR"])
    with col3:
        importance = st.selectbox("중요도", ["전체", "high", "medium", "low"])

    # 이벤트 조회
    events = economic_calendar.get_upcoming_events(
        days=days,
        country=None if country == "전체" else country,
        importance=None if importance == "전체" else importance
    )

    if not events:
        st.info("예정된 이벤트가 없습니다.")
        return

    # 이벤트 표시
    for event in events:
        importance_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(event.importance, "⚪")
        country_flag = {"US": "🇺🇸", "KR": "🇰🇷"}.get(event.country, "🌐")

        with st.expander(f"{importance_emoji} {country_flag} {event.event} - {event.date}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**날짜:** {event.date}")
                st.write(f"**시간:** {event.time}")
            with col2:
                st.write(f"**국가:** {event.country}")
                st.write(f"**중요도:** {event.importance}")

            if event.previous:
                st.write(f"**이전:** {event.previous}")
            if event.forecast:
                st.write(f"**예상:** {event.forecast}")
            if event.actual:
                st.write(f"**실제:** {event.actual}")

    # FOMC 일정
    st.subheader("🏛️ FOMC 일정")
    fomc_events = economic_calendar.get_fomc_schedule()

    if fomc_events:
        fomc_df = pd.DataFrame([
            {"날짜": e.date, "시간": e.time, "이벤트": e.event}
            for e in fomc_events
        ])
        st.dataframe(fomc_df, use_container_width=True, hide_index=True)


def render_watchlist():
    """워치리스트 렌더링"""
    st.subheader("⭐ 워치리스트")

    if not WATCHLIST_AVAILABLE:
        st.warning("워치리스트 모듈을 사용할 수 없습니다.")
        return

    # 탭
    tab1, tab2, tab3 = st.tabs(["📋 종목 목록", "➕ 추가", "📊 비교 분석"])

    with tab1:
        # 그룹 선택
        groups = watchlist_manager.get_groups()
        group_options = ["전체"] + [f"{g.icon} {g.display_name}" for g in groups.values()]
        selected = st.selectbox("그룹", group_options)

        if selected == "전체":
            items = watchlist_manager.get_items()
        else:
            group_name = list(groups.keys())[group_options.index(selected) - 1]
            items = watchlist_manager.get_items(group_name)

        if not items:
            st.info("워치리스트가 비어있습니다.")
        else:
            # 가격 업데이트 버튼
            if st.button("🔄 가격 업데이트"):
                with st.spinner("가격 업데이트 중..."):
                    watchlist_manager.update_prices()
                st.rerun()

            # 테이블 표시
            df = pd.DataFrame([
                {
                    "종목": item.name,
                    "심볼": item.symbol,
                    "그룹": item.group,
                    "현재가": f"{item.current_price:,.0f}" if item.current_price else "-",
                    "변동률": f"{item.change_pct:+.2f}%" if item.change_pct else "-",
                    "추가일": item.added_date
                }
                for item in items
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)

            # 삭제
            with st.expander("종목 삭제"):
                del_symbol = st.selectbox(
                    "삭제할 종목",
                    [f"{item.name} ({item.symbol})" for item in items]
                )
                if st.button("삭제", type="secondary"):
                    symbol = del_symbol.split("(")[-1].rstrip(")")
                    watchlist_manager.remove_item(symbol)
                    st.success("삭제되었습니다.")
                    st.rerun()

    with tab2:
        st.markdown("### 종목 추가")

        col1, col2 = st.columns(2)
        with col1:
            new_symbol = st.text_input("심볼", placeholder="예: 005930.KS")
        with col2:
            new_name = st.text_input("종목명", placeholder="예: 삼성전자")

        new_group = st.selectbox(
            "그룹",
            options=list(groups.keys()),
            format_func=lambda x: f"{groups[x].icon} {groups[x].display_name}"
        )

        new_notes = st.text_area("메모", placeholder="투자 아이디어나 메모")

        if st.button("추가", type="primary"):
            if new_symbol and new_name:
                watchlist_manager.add_item(
                    symbol=new_symbol.upper(),
                    name=new_name,
                    group=new_group,
                    notes=new_notes
                )
                st.success(f"{new_name} 추가됨!")
                st.rerun()
            else:
                st.error("심볼과 종목명을 입력하세요.")

        # 커스텀 그룹 추가
        st.markdown("---")
        st.markdown("### 커스텀 그룹 추가")

        col1, col2 = st.columns(2)
        with col1:
            grp_name = st.text_input("그룹 ID", placeholder="my_group")
        with col2:
            grp_display = st.text_input("그룹명", placeholder="내 그룹")

        grp_icon = st.text_input("아이콘", value="📋")

        if st.button("그룹 추가"):
            if grp_name and grp_display:
                watchlist_manager.add_group(grp_name, grp_display, grp_icon)
                st.success("그룹 추가됨!")
                st.rerun()

    with tab3:
        st.markdown("### 종목 비교")

        items = watchlist_manager.get_items()
        if len(items) < 2:
            st.info("비교하려면 최소 2개 종목이 필요합니다.")
            return

        selected_items = st.multiselect(
            "비교할 종목",
            options=[f"{item.name} ({item.symbol})" for item in items],
            max_selections=5
        )

        period = st.selectbox("기간", ["1mo", "3mo", "6mo", "1y"], index=1)

        if st.button("비교 분석") and len(selected_items) >= 2:
            symbols = [s.split("(")[-1].rstrip(")") for s in selected_items]

            with st.spinner("데이터 조회 중..."):
                data = watchlist_manager.get_comparison_data(symbols, period)

            if data.get("summary"):
                st.markdown("#### 수익률 비교")

                df = pd.DataFrame(data["summary"])
                df = df.rename(columns={
                    "symbol": "심볼",
                    "name": "종목명",
                    "return_pct": "수익률(%)",
                    "current": "현재가"
                })

                st.dataframe(df, use_container_width=True, hide_index=True)


def render_pattern_analysis():
    """패턴 분석 렌더링"""
    st.subheader("📊 차트 패턴 분석")

    if not PATTERNS_AVAILABLE:
        st.warning("패턴 분석 모듈을 사용할 수 없습니다.")
        return

    symbol = st.text_input("심볼 입력", placeholder="예: AAPL, 005930.KS")

    if st.button("패턴 분석") and symbol:
        with st.spinner("분석 중..."):
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="6mo")

                if hist.empty:
                    st.error("데이터를 찾을 수 없습니다.")
                    return

                result = chart_analyzer.analyze(hist)

                # 현재 추세
                st.markdown(f"**현재 추세:** {result.get('trend', 'unknown')}")
                st.markdown(f"**현재가:** {result.get('current_price', 0):,.2f}")

                # 패턴
                patterns = result.get('patterns', [])
                if patterns:
                    st.markdown("### 감지된 패턴")
                    for pattern in patterns:
                        signal_emoji = {
                            "bullish": "🟢",
                            "bearish": "🔴",
                            "neutral": "🟡"
                        }.get(pattern.signal.value, "⚪")

                        with st.expander(
                            f"{signal_emoji} {pattern.pattern_type.value} "
                            f"(신뢰도: {pattern.confidence*100:.0f}%)"
                        ):
                            st.write(pattern.description)

                            if pattern.key_levels:
                                st.write("**주요 레벨:**")
                                for key, value in pattern.key_levels.items():
                                    st.write(f"  - {key}: {value:,.2f}")

                            if pattern.target_price:
                                st.write(f"**목표가:** {pattern.target_price:,.2f}")
                            if pattern.stop_loss:
                                st.write(f"**손절가:** {pattern.stop_loss:,.2f}")
                else:
                    st.info("현재 감지된 패턴이 없습니다.")

                # 지지/저항선
                sr_levels = result.get('support_resistance', [])
                if sr_levels:
                    st.markdown("### 지지/저항선")

                    support = [sr for sr in sr_levels if sr.type == "support"]
                    resistance = [sr for sr in sr_levels if sr.type == "resistance"]

                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**지지선**")
                        for sr in support[:5]:
                            st.write(f"  🟢 {sr.level:,.2f} (강도: {sr.strength})")

                    with col2:
                        st.markdown("**저항선**")
                        for sr in resistance[:5]:
                            st.write(f"  🔴 {sr.level:,.2f} (강도: {sr.strength})")

            except Exception as e:
                st.error(f"분석 실패: {e}")


def render_backup_restore():
    """백업/복원 렌더링"""
    st.subheader("💾 백업 및 복원")

    if not BACKUP_AVAILABLE:
        st.warning("백업 모듈을 사용할 수 없습니다.")
        return

    tab1, tab2 = st.tabs(["📦 백업 목록", "⚙️ 설정"])

    with tab1:
        # 백업 생성
        col1, col2 = st.columns([3, 1])
        with col1:
            description = st.text_input("백업 설명", placeholder="예: 중요 변경 전 백업")
        with col2:
            st.write("")  # 정렬용
            st.write("")
            if st.button("백업 생성", type="primary"):
                with st.spinner("백업 생성 중..."):
                    backup = backup_manager.create_backup(description)
                    st.success(f"백업 생성: {backup.filename}")
                    st.rerun()

        # 백업 목록
        st.markdown("### 백업 목록")
        backups = backup_manager.list_backups()

        if not backups:
            st.info("백업이 없습니다.")
        else:
            for backup in backups:
                size_mb = backup.size / (1024 * 1024)
                with st.expander(
                    f"📦 {backup.filename} - {backup.created_at[:10]} ({size_mb:.2f}MB)"
                ):
                    st.write(f"**ID:** {backup.id}")
                    st.write(f"**생성일:** {backup.created_at}")
                    st.write(f"**파일 수:** {backup.file_count}")
                    if backup.description:
                        st.write(f"**설명:** {backup.description}")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("복원", key=f"restore_{backup.id}"):
                            with st.spinner("복원 중..."):
                                if backup_manager.restore_backup(backup.id):
                                    st.success("복원 완료!")
                                else:
                                    st.error("복원 실패")
                    with col2:
                        if st.button("삭제", key=f"delete_{backup.id}", type="secondary"):
                            if backup_manager.delete_backup(backup.id):
                                st.success("삭제됨")
                                st.rerun()

        # 저장소 사용량
        st.markdown("### 저장소 사용량")
        usage = backup_manager.get_storage_usage()
        st.metric("총 용량", f"{usage['total_size_mb']:.2f} MB")
        st.progress(usage['backup_count'] / usage['max_backups'])
        st.caption(f"백업 수: {usage['backup_count']} / {usage['max_backups']}")

    with tab2:
        st.markdown("### 백업 설정")

        config = backup_manager.config

        auto_backup = st.checkbox("자동 백업", value=config.auto_backup)
        interval = st.number_input("백업 간격 (시간)", value=config.backup_interval_hours, min_value=1)
        max_backups = st.number_input("최대 백업 수", value=config.max_backups, min_value=1)
        include_logs = st.checkbox("로그 포함", value=config.include_logs)
        compress = st.checkbox("압축", value=config.compress)

        if st.button("설정 저장"):
            backup_manager.config.auto_backup = auto_backup
            backup_manager.config.backup_interval_hours = interval
            backup_manager.config.max_backups = max_backups
            backup_manager.config.include_logs = include_logs
            backup_manager.config.compress = compress
            backup_manager._save_config()
            st.success("설정 저장됨!")


def render_calendar_watchlist_page():
    """캘린더 & 워치리스트 페이지"""
    st.title("📅 캘린더 & 워치리스트")

    tab1, tab2, tab3, tab4 = st.tabs([
        "📅 경제 캘린더",
        "⭐ 워치리스트",
        "📊 패턴 분석",
        "💾 백업/복원"
    ])

    with tab1:
        render_economic_calendar()

    with tab2:
        render_watchlist()

    with tab3:
        render_pattern_analysis()

    with tab4:
        render_backup_restore()
