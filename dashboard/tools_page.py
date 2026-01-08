"""
투자 도구 대시보드 페이지
가격 알림, 공시, 배당, 리밸런싱, 세금, 종목비교
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime


def render_price_alerts():
    """가격 알림 UI"""
    st.subheader("🔔 가격 알림")

    try:
        from alerts.price_monitor import price_monitor, AlertCondition

        # 새 알림 추가
        with st.expander("➕ 새 알림 추가", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                symbol = st.text_input("종목 코드", placeholder="005930.KS")
                name = st.text_input("종목명", placeholder="삼성전자")
            with col2:
                condition = st.selectbox("조건", [
                    "목표가 이상", "손절가 이하", "상승률 초과", "하락률 초과"
                ])
                target = st.number_input("기준값", value=0.0)

            if st.button("알림 추가"):
                cond_map = {
                    "목표가 이상": AlertCondition.ABOVE,
                    "손절가 이하": AlertCondition.BELOW,
                    "상승률 초과": AlertCondition.CHANGE_UP,
                    "하락률 초과": AlertCondition.CHANGE_DOWN
                }
                alert = price_monitor.add_alert(
                    symbol, name, cond_map[condition], target
                )
                st.success(f"알림 추가: {name} {condition} {target}")

        # 활성 알림 목록
        st.markdown("#### 활성 알림")
        alerts = price_monitor.get_alerts(active_only=True)

        if not alerts:
            st.info("등록된 알림이 없습니다.")
        else:
            for alert in alerts:
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    cond_name = {
                        AlertCondition.ABOVE: "이상",
                        AlertCondition.BELOW: "이하",
                        AlertCondition.CHANGE_UP: "상승",
                        AlertCondition.CHANGE_DOWN: "하락"
                    }.get(alert.condition, "")
                    st.write(f"**{alert.name}** ({alert.symbol})")
                with col2:
                    if alert.condition in [AlertCondition.CHANGE_UP, AlertCondition.CHANGE_DOWN]:
                        st.write(f"{alert.target_value:+.1f}% {cond_name}")
                    else:
                        st.write(f"₩{alert.target_value:,.0f} {cond_name}")
                with col3:
                    if st.button("삭제", key=f"del_alert_{alert.id}"):
                        price_monitor.remove_alert(alert.id)
                        st.rerun()

        # 발동 이력
        st.markdown("#### 최근 발동 이력")
        history = price_monitor.get_triggered_history(days=7)
        if history:
            for item in history[:10]:
                st.write(f"🔔 {item.message} ({item.timestamp.strftime('%m-%d %H:%M')})")
        else:
            st.info("최근 발동된 알림이 없습니다.")

    except Exception as e:
        st.error(f"가격 알림 오류: {e}")


def render_disclosures():
    """공시 모니터링 UI"""
    st.subheader("📋 공시 모니터링")

    try:
        from korea.dart_monitor import dart_monitor

        # 검색
        col1, col2 = st.columns([3, 1])
        with col1:
            corp_name = st.text_input("회사명 검색", placeholder="삼성전자")
        with col2:
            days = st.selectbox("기간", [7, 14, 30], format_func=lambda x: f"{x}일")

        # 포트폴리오 종목 공시
        if 'portfolio' in st.session_state and st.session_state.portfolio.positions:
            st.markdown("#### 보유 종목 공시")
            symbols = [{'symbol': p.symbol, 'name': p.name}
                      for p in st.session_state.portfolio.positions]

            with st.spinner("공시 조회 중..."):
                disclosures = dart_monitor.get_portfolio_disclosures(symbols, days)

            if disclosures:
                for d in disclosures[:15]:
                    icon = "🔴" if d.importance == 'high' else "📄"
                    with st.container():
                        st.markdown(f"""
                        {icon} **{d.corp_name}** - {d.report_name}
                        <small style="color:gray">{d.submit_date.strftime('%Y-%m-%d')} | {d.report_type}</small>
                        """, unsafe_allow_html=True)
                        if d.url:
                            st.markdown(f"[공시 원문 보기]({d.url})")
                        st.divider()
            else:
                st.info("최근 공시가 없습니다.")

        # 검색 결과
        elif corp_name:
            with st.spinner("공시 검색 중..."):
                disclosures = dart_monitor.get_recent_disclosures(corp_name, days)

            if disclosures:
                for d in disclosures[:10]:
                    icon = "🔴" if d.importance == 'high' else "📄"
                    st.write(f"{icon} **{d.report_name}** ({d.submit_date.strftime('%Y-%m-%d')})")
            else:
                st.info("검색 결과가 없습니다.")

    except Exception as e:
        st.error(f"공시 조회 오류: {e}")


def render_dividends():
    """배당 캘린더 UI"""
    st.subheader("💰 배당 캘린더")

    try:
        from korea.dividend_calendar import dividend_calendar

        if 'portfolio' not in st.session_state or not st.session_state.portfolio.positions:
            st.info("포트폴리오에 종목을 추가하면 배당 정보를 볼 수 있습니다.")
            return

        positions = [{'symbol': p.symbol, 'name': p.name, 'quantity': p.quantity}
                    for p in st.session_state.portfolio.positions]

        # 예상 배당 수익
        with st.spinner("배당 정보 조회 중..."):
            income = dividend_calendar.calculate_expected_income(positions)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("연간 예상 배당", f"₩{income['total_expected']:,.0f}")
        with col2:
            st.metric("평균 배당수익률", f"{income['average_yield']:.2f}%")
        with col3:
            st.metric("배당 종목 수", f"{len(income['by_stock'])}개")

        # 종목별 배당
        st.markdown("#### 종목별 예상 배당")
        for item in income['by_stock']:
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                st.write(f"**{item['name']}**")
            with col2:
                st.write(f"₩{item['expected']:,.0f}")
            with col3:
                st.write(f"{item['yield']:.2f}%")

        # 월별 배당 차트
        st.markdown("#### 월별 예상 배당")
        months = list(income['by_month'].keys())
        values = list(income['by_month'].values())

        fig = go.Figure(go.Bar(
            x=[f"{m}월" for m in months],
            y=values,
            marker_color='green'
        ))
        fig.update_layout(height=300, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)

        # 배당 일정
        st.markdown("#### 향후 배당 일정")
        calendar = dividend_calendar.get_calendar(positions, months_ahead=6)
        if calendar:
            for entry in calendar[:10]:
                event_icon = {'ex_dividend': '📅', 'record': '📝', 'payment': '💵'}.get(entry.event_type, '📌')
                event_name = {'ex_dividend': '배당락일', 'record': '기준일', 'payment': '지급일'}.get(entry.event_type, '')
                st.write(f"{event_icon} {entry.date.strftime('%Y-%m-%d')} - {entry.dividend_info.name} {event_name}")
        else:
            st.info("향후 6개월 내 배당 일정이 없습니다.")

    except Exception as e:
        st.error(f"배당 정보 오류: {e}")


def render_rebalancing():
    """리밸런싱 UI"""
    st.subheader("⚖️ 포트폴리오 리밸런싱")

    try:
        from portfolio.rebalancer import rebalancer

        if 'portfolio' not in st.session_state or not st.session_state.portfolio.positions:
            st.info("포트폴리오에 종목을 추가하면 리밸런싱 분석을 할 수 있습니다.")
            return

        # 목표 비중 설정
        with st.expander("🎯 목표 비중 설정", expanded=False):
            targets = rebalancer.get_targets()

            for pos in st.session_state.portfolio.positions:
                current_target = next((t.target_weight for t in targets if t.symbol == pos.symbol), 0)
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write(f"**{pos.name}**")
                with col2:
                    new_target = st.number_input(
                        "목표 %", value=current_target, min_value=0.0, max_value=100.0,
                        key=f"target_{pos.symbol}", label_visibility="collapsed"
                    )
                with col3:
                    if st.button("설정", key=f"set_{pos.symbol}"):
                        rebalancer.set_target(pos.symbol, pos.name, new_target)
                        st.success(f"{pos.name}: {new_target}%")

            # 유효성 검사
            valid, msg = rebalancer.validate_targets()
            if not valid:
                st.warning(msg)

        # 리밸런싱 분석
        positions = [{
            'symbol': p.symbol,
            'name': p.name,
            'quantity': p.quantity,
            'current_price': p.current_price,
            'value': p.current_price * p.quantity
        } for p in st.session_state.portfolio.positions]

        report = rebalancer.analyze(positions)

        # 요약
        col1, col2, col3 = st.columns(3)
        with col1:
            color = "🟢" if not report.needs_rebalance else "🔴"
            st.metric("리밸런싱 필요", f"{color} {'예' if report.needs_rebalance else '아니오'}")
        with col2:
            st.metric("최대 괴리율", f"{report.max_deviation:.1f}%")
        with col3:
            st.metric("예상 순현금", f"₩{report.net_cash_flow:,.0f}")

        # 액션
        st.markdown("#### 리밸런싱 액션")
        for action in report.actions:
            if action.action == 'hold':
                continue

            icon = "🟢" if action.action == 'buy' else "🔴"
            action_kr = "매수" if action.action == 'buy' else "매도"

            col1, col2, col3 = st.columns([2, 2, 2])
            with col1:
                st.write(f"{icon} **{action.name}** {action_kr}")
            with col2:
                st.write(f"{action.quantity}주 (₩{action.amount:,.0f})")
            with col3:
                st.write(f"현재 {action.current_weight:.1f}% → 목표 {action.target_weight:.1f}%")

    except Exception as e:
        st.error(f"리밸런싱 오류: {e}")


def render_tax_calculator():
    """세금 계산기 UI"""
    st.subheader("🧾 세금 계산기")

    try:
        from portfolio.tax_calculator import tax_calculator, MarketType

        market = st.radio("시장", ["해외주식", "국내주식"], horizontal=True)
        market_type = MarketType.OVERSEAS if market == "해외주식" else MarketType.KOREA_LISTED

        # 포트폴리오 기반 계산
        if 'portfolio' in st.session_state and st.session_state.portfolio.positions:
            st.markdown("#### 포트폴리오 기준 예상 세금")

            positions = [{
                'symbol': p.symbol,
                'name': p.name,
                'quantity': p.quantity,
                'avg_cost': p.avg_cost,
                'current_price': p.current_price
            } for p in st.session_state.portfolio.positions]

            estimate = tax_calculator.estimate_from_positions(positions, market_type)
            tax_info = estimate['estimated_tax']

            col1, col2, col3 = st.columns(3)
            with col1:
                pnl_color = "normal" if estimate['total_unrealized_pnl'] >= 0 else "inverse"
                st.metric("미실현 손익", f"₩{estimate['total_unrealized_pnl']:,.0f}", delta_color=pnl_color)
            with col2:
                st.metric("기본공제", f"₩{tax_info['deduction']:,.0f}")
            with col3:
                st.metric("예상 세금 (전량 매도 시)", f"₩{estimate['tax_if_all_sold']:,.0f}")

            # 이익/손실 종목
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**📈 이익 종목**")
                for item in estimate['unrealized_gains'][:5]:
                    st.write(f"• {item['name']}: +₩{item['profit']:,.0f}")
            with col2:
                st.markdown("**📉 손실 종목**")
                for item in estimate['unrealized_losses'][:5]:
                    st.write(f"• {item['name']}: -₩{item['loss']:,.0f}")

            # 절세 전략
            st.markdown("#### 💡 절세 전략")
            optimizations = tax_calculator.optimize_tax(positions, 0, market_type)

            for opt in optimizations:
                with st.expander(f"💡 {opt.strategy}"):
                    st.write(opt.description)
                    st.write(f"**예상 절감액**: ₩{opt.potential_savings:,.0f}")
                    st.markdown("**실행 방법:**")
                    for action in opt.actions:
                        st.write(f"• {action}")

        # 수동 계산
        st.markdown("#### 직접 계산")
        col1, col2 = st.columns(2)
        with col1:
            gain = st.number_input("양도차익 (원)", value=0, step=100000)
        with col2:
            loss = st.number_input("양도손실 (원)", value=0, step=100000)

        if st.button("세금 계산"):
            trades = [{'buy_price': 100, 'sell_price': 100 + gain, 'quantity': 1}]
            if loss > 0:
                trades.append({'buy_price': 100, 'sell_price': 100 - loss, 'quantity': 1})

            result = tax_calculator.calculate_tax(trades, market_type)

            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("순 양도차익", f"₩{result.net_gain:,.0f}")
            with col2:
                st.metric("과세표준", f"₩{result.taxable_gain:,.0f}")
            with col3:
                st.metric("납부 세액", f"₩{result.total_tax:,.0f}")

    except Exception as e:
        st.error(f"세금 계산 오류: {e}")


def render_stock_compare():
    """종목 비교 UI"""
    st.subheader("📊 종목 비교")

    try:
        from analysis.stock_comparator import stock_comparator

        col1, col2 = st.columns([2, 3])
        with col1:
            base_symbol = st.text_input("기준 종목", value="005930.KS", placeholder="005930.KS")
        with col2:
            compare_input = st.text_input("비교 종목 (쉼표 구분)", placeholder="000660.KS, 035420.KS")

        compare_symbols = [s.strip() for s in compare_input.split(',') if s.strip()] if compare_input else None

        if st.button("비교 분석"):
            with st.spinner("분석 중..."):
                result = stock_comparator.compare(base_symbol, compare_symbols)

            if not result:
                st.error("데이터를 불러올 수 없습니다.")
                return

            # 요약
            st.markdown("#### 분석 요약")
            for key, value in result.summary.items():
                st.info(value)

            # 비교 테이블
            st.markdown("#### 지표 비교")
            all_symbols = [result.base_stock.symbol] + [s.symbol for s in result.compared_stocks]
            table = stock_comparator.get_comparison_table(all_symbols)
            st.dataframe(table, use_container_width=True, hide_index=True)

            # 순위
            st.markdown("#### 지표별 순위")
            col1, col2 = st.columns(2)

            metric_names = {
                'per': 'PER', 'pbr': 'PBR', 'roe': 'ROE',
                'profit_margin': '이익률', 'revenue_growth': '매출성장',
                'dividend_yield': '배당수익률', 'debt_to_equity': '부채비율'
            }

            for i, (metric, rankings) in enumerate(result.rankings.items()):
                with col1 if i % 2 == 0 else col2:
                    st.markdown(f"**{metric_names.get(metric, metric)}**")
                    for symbol, value, rank in rankings:
                        medal = {1: '🥇', 2: '🥈', 3: '🥉'}.get(rank, f'{rank}.')
                        highlight = "**" if symbol == base_symbol else ""
                        st.write(f"{medal} {highlight}{symbol}{highlight}: {value:.2f}")

            # 가격 차트 비교
            st.markdown("#### 가격 추이 비교")
            price_df = stock_comparator.get_price_comparison(all_symbols, "1y")

            if price_df is not None and not price_df.empty:
                fig = go.Figure()
                for col in price_df.columns:
                    fig.add_trace(go.Scatter(
                        x=price_df.index, y=price_df[col],
                        mode='lines', name=col
                    ))
                fig.update_layout(
                    height=400,
                    yaxis_title="수익률 (%)",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02)
                )
                st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"종목 비교 오류: {e}")


def render_tools_page():
    """투자 도구 메인 페이지"""
    st.title("🛠️ 투자 도구")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🔔 가격 알림", "📋 공시", "💰 배당", "⚖️ 리밸런싱", "🧾 세금", "📊 종목 비교"
    ])

    with tab1:
        render_price_alerts()

    with tab2:
        render_disclosures()

    with tab3:
        render_dividends()

    with tab4:
        render_rebalancing()

    with tab5:
        render_tax_calculator()

    with tab6:
        render_stock_compare()
