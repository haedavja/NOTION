"""
포트폴리오 분석 대시보드 페이지
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from portfolio.portfolio import Portfolio, Position, AssetType, InvestmentThesis, create_sample_portfolio
from portfolio.analyzer import PortfolioAnalyzer
from portfolio.thesis_evaluator import ThesisEvaluator, ThesisRating


def render_portfolio_input():
    """포트폴리오 입력 UI"""
    st.subheader("📝 포트폴리오 입력")

    # 세션 상태 초기화 (빈 포트폴리오로 시작)
    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = Portfolio(name="My Portfolio")

    # 샘플 로드 버튼
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("샘플 포트폴리오 로드"):
            st.session_state.portfolio = create_sample_portfolio()
            st.rerun()

    with col2:
        if st.button("포트폴리오 초기화"):
            st.session_state.portfolio = Portfolio(name="My Portfolio")
            st.rerun()

    st.divider()

    # 새 포지션 추가 폼
    with st.expander("➕ 새 포지션 추가", expanded=False):
        with st.form("add_position"):
            col1, col2, col3 = st.columns(3)

            with col1:
                symbol = st.text_input("티커 심볼", placeholder="예: AAPL")
                name = st.text_input("종목명", placeholder="예: Apple Inc.")
                quantity = st.number_input("수량", min_value=0.0, value=10.0)

            with col2:
                avg_cost = st.number_input("평균 매수가", min_value=0.0, value=100.0)
                target_price = st.number_input("목표가 (선택)", min_value=0.0, value=0.0)
                stop_loss = st.number_input("손절가 (선택)", min_value=0.0, value=0.0)

            with col3:
                asset_type = st.selectbox("자산 유형", [t.value for t in AssetType])
                thesis_type = st.selectbox("투자 논리 유형", [t.value for t in InvestmentThesis])
                time_horizon = st.selectbox("투자 기간", ["단기", "중기", "장기"])

            thesis_description = st.text_area(
                "📌 매수 이유 (왜 이 종목을 샀나요?)",
                placeholder="예: AI 칩 시장 독점적 지위. 데이터센터 GPU 수요 급증 예상...",
                height=100
            )

            submitted = st.form_submit_button("포지션 추가")

            if submitted and symbol:
                # 자산 유형/투자 논리 변환
                asset_type_enum = next((t for t in AssetType if t.value == asset_type), AssetType.STOCK)
                thesis_type_enum = next((t for t in InvestmentThesis if t.value == thesis_type), InvestmentThesis.OTHER)

                position = Position(
                    symbol=symbol.upper(),
                    name=name or symbol.upper(),
                    quantity=quantity,
                    avg_cost=avg_cost,
                    asset_type=asset_type_enum,
                    thesis_type=thesis_type_enum,
                    thesis_description=thesis_description,
                    target_price=target_price if target_price > 0 else None,
                    stop_loss=stop_loss if stop_loss > 0 else None,
                    time_horizon=time_horizon,
                )

                st.session_state.portfolio.add_position(position)
                st.success(f"{symbol.upper()} 추가됨!")
                st.rerun()

    return st.session_state.portfolio


def render_portfolio_summary(portfolio: Portfolio):
    """포트폴리오 요약"""
    st.subheader("📊 포트폴리오 요약")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "총 평가금액",
            f"${portfolio.total_market_value:,.0f}",
        )

    with col2:
        st.metric(
            "총 투자원금",
            f"${portfolio.total_cost_basis:,.0f}",
        )

    with col3:
        pnl = portfolio.total_unrealized_pnl
        pnl_pct = portfolio.total_unrealized_pnl_pct
        st.metric(
            "미실현 손익",
            f"${pnl:,.0f}",
            delta=f"{pnl_pct:+.2f}%"
        )

    with col4:
        st.metric(
            "보유 종목 수",
            f"{len(portfolio.positions)}개",
        )


def render_positions_table(portfolio: Portfolio):
    """포지션 테이블"""
    st.subheader("📋 보유 포지션")

    if not portfolio.positions:
        st.info("포지션이 없습니다. 위에서 포지션을 추가하세요.")
        return

    # 데이터프레임 생성
    data = []
    for p in portfolio.positions:
        data.append({
            '티커': p.symbol,
            '종목명': p.name,
            '수량': p.quantity,
            '평균단가': f"${p.avg_cost:.2f}",
            '현재가': f"${p.current_price:.2f}" if p.current_price else "-",
            '평가금액': f"${p.market_value:,.0f}" if p.market_value else "-",
            '손익': f"${p.unrealized_pnl:,.0f}" if p.unrealized_pnl else "-",
            '손익률': f"{p.unrealized_pnl_pct:+.2f}%" if p.unrealized_pnl_pct else "-",
            '비중': f"{p.weight:.1f}%" if p.weight else "-",
            '투자논리': p.thesis_type.value,
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 삭제 버튼
    with st.expander("포지션 삭제"):
        symbols = [p.symbol for p in portfolio.positions]
        symbol_to_delete = st.selectbox("삭제할 종목", symbols)
        if st.button("삭제"):
            portfolio.remove_position(symbol_to_delete)
            st.success(f"{symbol_to_delete} 삭제됨")
            st.rerun()


def render_allocation_charts(portfolio: Portfolio):
    """자산 배분 차트"""
    st.subheader("📈 자산 배분")

    col1, col2 = st.columns(2)

    with col1:
        # 종목별 비중
        labels = [p.symbol for p in portfolio.positions]
        values = [p.weight or 0 for p in portfolio.positions]

        if values and sum(values) > 0:
            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)])
            fig.update_layout(title="종목별 비중", height=350)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        # 투자 논리별 비중
        thesis_allocation = portfolio.get_allocation_by_thesis()
        if thesis_allocation:
            labels = list(thesis_allocation.keys())
            values = list(thesis_allocation.values())

            fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4)])
            fig.update_layout(title="투자논리별 비중", height=350)
            st.plotly_chart(fig, use_container_width=True)


def render_thesis_evaluation(portfolio: Portfolio):
    """투자 논리 평가"""
    st.subheader("🎯 투자 논리 평가")

    if not portfolio.positions:
        st.info("평가할 포지션이 없습니다.")
        return

    evaluator = ThesisEvaluator()

    # 평가할 종목 선택
    symbols = [p.symbol for p in portfolio.positions]
    selected_symbol = st.selectbox("평가할 종목 선택", symbols)

    position = portfolio.get_position(selected_symbol)
    if not position:
        return

    # 투자 논리 표시
    st.markdown("### 📌 당신의 투자 논리")
    st.info(f"**{position.thesis_type.value}**: {position.thesis_description}")

    if position.target_price:
        st.write(f"🎯 목표가: ${position.target_price:.2f}")
    if position.stop_loss:
        st.write(f"🛑 손절가: ${position.stop_loss:.2f}")

    # 평가 실행
    if st.button("🔍 투자 논리 분석 실행", key="eval_btn"):
        with st.spinner("분석 중..."):
            try:
                evaluation = evaluator.evaluate(position)

                # 평가 등급 표시
                st.markdown("---")
                st.markdown("### 📊 객관적 평가 결과")

                rating_colors = {
                    ThesisRating.STRONG: "🟢",
                    ThesisRating.POSITIVE: "🟢",
                    ThesisRating.NEUTRAL: "🟡",
                    ThesisRating.NEGATIVE: "🔴",
                    ThesisRating.WEAK: "🔴",
                }

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(
                        "평가 등급",
                        f"{rating_colors.get(evaluation.rating, '⚪')} {evaluation.rating.value}"
                    )

                with col2:
                    score_pct = (evaluation.score + 1) / 2 * 100  # -1~1을 0~100으로
                    st.metric("종합 점수", f"{score_pct:.0f}/100")

                with col3:
                    st.metric("신뢰도", f"{evaluation.confidence*100:.0f}%")

                # 강점/약점
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("#### ✅ 강점 (논리 지지 요소)")
                    for s in evaluation.strengths[:5]:
                        st.success(s)

                with col2:
                    st.markdown("#### ❌ 약점 (위험 요소)")
                    for w in evaluation.weaknesses[:5]:
                        st.error(w)

                # 확률적 분석
                st.markdown("### 🎲 확률적 전망")
                prob = evaluation.probability_assessment

                col1, col2, col3 = st.columns(3)

                with col1:
                    if 'target_probability' in prob:
                        st.metric(
                            "목표가 도달 확률",
                            f"{prob['target_probability']:.0f}%"
                        )

                with col2:
                    if 'upside_potential' in prob:
                        st.metric(
                            "상승 여력",
                            f"{prob['upside_potential']:.1f}%"
                        )

                with col3:
                    if 'risk_reward_ratio' in prob:
                        st.metric(
                            "리스크/리워드 비율",
                            f"1:{prob['risk_reward_ratio']:.1f}"
                        )

                if 'expected_return' in prob:
                    st.info(f"📈 기대 수익률: {prob['expected_return']:.1f}%")

                # 기술적 지표
                st.markdown("### 📉 기술적 분석")
                tech = evaluation.technical_check.get('indicators', {})

                if tech:
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        if 'rsi' in tech:
                            rsi = tech['rsi']
                            rsi_status = "과매수" if rsi > 70 else ("과매도" if rsi < 30 else "중립")
                            st.metric("RSI", f"{rsi:.1f}", delta=rsi_status)

                    with col2:
                        if 'return_1m' in tech:
                            st.metric("1개월 수익률", f"{tech['return_1m']:.1f}%")

                    with col3:
                        if 'return_3m' in tech:
                            st.metric("3개월 수익률", f"{tech['return_3m']:.1f}%")

                    with col4:
                        if 'from_52w_high' in tech:
                            st.metric("52주 고점 대비", f"{tech['from_52w_high']:.1f}%")

                # 리스크 평가
                st.markdown("### ⚠️ 리스크 평가")
                risk = evaluation.risk_assessment

                risk_color = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}
                st.write(f"**전체 리스크 수준**: {risk_color.get(risk['overall_risk'], '⚪')} {risk['overall_risk'].upper()}")

                if risk.get('risks'):
                    for r in risk['risks']:
                        st.warning(r)

                # 권고사항
                st.markdown("### 💡 권고사항")
                for rec in evaluation.recommendations:
                    st.info(rec)

            except Exception as e:
                st.error(f"분석 중 오류 발생: {e}")
                st.info("실시간 데이터 조회가 불가능한 경우 샘플 분석 결과를 표시합니다.")


def render_risk_return_analysis(portfolio: Portfolio):
    """리스크/리턴 분석"""
    st.subheader("📊 리스크/리턴 분석")

    if not portfolio.positions:
        st.info("분석할 포지션이 없습니다.")
        return

    # 샘플 데이터로 분석 (실제로는 API 데이터 사용)
    st.markdown("### 리스크 지표")

    col1, col2, col3, col4 = st.columns(4)

    # 샘플 값 (실제로는 PortfolioAnalyzer에서 계산)
    with col1:
        st.metric("연간 변동성", "18.5%", help="포트폴리오 수익률의 표준편차")

    with col2:
        st.metric("베타", "1.12", help="시장 대비 민감도")

    with col3:
        st.metric("95% VaR", "-2.3%", help="하루 최대 예상 손실 (95% 신뢰)")

    with col4:
        st.metric("최대 낙폭", "-15.2%", help="고점 대비 최대 하락폭")

    st.markdown("### 수익률 지표")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("샤프 비율", "1.25", help="위험 대비 초과 수익")

    with col2:
        st.metric("연환산 수익률", "12.3%")

    with col3:
        st.metric("YTD 수익률", "8.5%")

    with col4:
        st.metric("승률", "58%", help="수익 월 비율")

    # 스트레스 테스트
    st.markdown("### 🔥 스트레스 테스트")

    stress_scenarios = {
        '시장 급락 (-20%)': -15.8,
        '조정 (-10%)': -8.2,
        '약세 (-5%)': -4.1,
        '강세 (+10%)': 8.5,
        '급등 (+20%)': 17.2,
    }

    stress_df = pd.DataFrame({
        '시나리오': list(stress_scenarios.keys()),
        '포트폴리오 영향 (%)': list(stress_scenarios.values()),
    })

    fig = px.bar(stress_df, x='시나리오', y='포트폴리오 영향 (%)',
                 color='포트폴리오 영향 (%)',
                 color_continuous_scale=['red', 'yellow', 'green'])
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

    # 집중도 분석
    st.markdown("### 🎯 집중도 분석")

    col1, col2 = st.columns(2)

    with col1:
        weights = [p.weight or 0 for p in portfolio.positions]
        sorted_weights = sorted(weights, reverse=True)

        top_3 = sum(sorted_weights[:3])
        st.metric("상위 3종목 집중도", f"{top_3:.1f}%",
                 delta="높음" if top_3 > 70 else ("보통" if top_3 > 50 else "낮음"))

    with col2:
        effective_n = 1 / sum((w/100)**2 for w in weights if w > 0) if weights else 0
        st.metric("유효 종목 수", f"{effective_n:.1f}개",
                 help="HHI 지수 기반 실질 분산 종목 수")


def render_portfolio_recommendations(portfolio: Portfolio):
    """포트폴리오 개선 권고"""
    st.subheader("💡 포트폴리오 개선 권고")

    recommendations = []

    # 집중도 체크
    weights = [p.weight or 0 for p in portfolio.positions]
    if weights:
        sorted_weights = sorted(weights, reverse=True)
        if sorted_weights[0] > 30:
            recommendations.append({
                'type': 'warning',
                'message': f"단일 종목 비중이 {sorted_weights[0]:.1f}%로 높습니다. 분산투자를 고려하세요."
            })

        if sum(sorted_weights[:3]) > 70:
            recommendations.append({
                'type': 'warning',
                'message': "상위 3개 종목 비중이 70%를 초과합니다. 집중 리스크가 높습니다."
            })

    # 투자 논리 다양성 체크
    thesis_types = set(p.thesis_type for p in portfolio.positions)
    if len(thesis_types) == 1:
        recommendations.append({
            'type': 'info',
            'message': "모든 종목이 같은 투자 논리입니다. 다양한 전략 분산을 고려하세요."
        })

    # 목표가/손절가 체크
    no_target = [p.symbol for p in portfolio.positions if not p.target_price]
    if no_target:
        recommendations.append({
            'type': 'info',
            'message': f"목표가 미설정: {', '.join(no_target[:3])}{'...' if len(no_target) > 3 else ''}"
        })

    no_stop = [p.symbol for p in portfolio.positions if not p.stop_loss]
    if no_stop:
        recommendations.append({
            'type': 'warning',
            'message': f"손절가 미설정: {', '.join(no_stop[:3])}{'...' if len(no_stop) > 3 else ''}"
        })

    # 좋은 점
    if len(portfolio.positions) >= 5:
        recommendations.append({
            'type': 'success',
            'message': "적절한 종목 수로 분산투자하고 있습니다."
        })

    if not recommendations:
        recommendations.append({
            'type': 'success',
            'message': "포트폴리오가 전반적으로 양호합니다!"
        })

    # 권고사항 표시
    for rec in recommendations:
        if rec['type'] == 'warning':
            st.warning(rec['message'])
        elif rec['type'] == 'info':
            st.info(rec['message'])
        else:
            st.success(rec['message'])


def render_portfolio_page():
    """포트폴리오 분석 페이지 메인"""
    st.title("💼 포트폴리오 분석")

    # 포트폴리오 입력
    portfolio = render_portfolio_input()

    if not portfolio.positions:
        st.warning("포트폴리오에 종목을 추가해주세요.")
        return

    # 현재가 업데이트 (샘플에서는 이미 설정됨)
    portfolio.update_weights()

    # 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 요약",
        "🎯 투자논리 평가",
        "📈 리스크/리턴",
        "💡 권고사항"
    ])

    with tab1:
        render_portfolio_summary(portfolio)
        st.divider()
        render_positions_table(portfolio)
        st.divider()
        render_allocation_charts(portfolio)

    with tab2:
        render_thesis_evaluation(portfolio)

    with tab3:
        render_risk_return_analysis(portfolio)

    with tab4:
        render_portfolio_recommendations(portfolio)


if __name__ == "__main__":
    st.set_page_config(page_title="포트폴리오 분석", layout="wide")
    render_portfolio_page()
