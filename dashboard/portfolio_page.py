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

from portfolio.portfolio import Portfolio, Position, AssetType, InvestmentThesis
from portfolio.analyzer import PortfolioAnalyzer
from portfolio.thesis_evaluator import ThesisEvaluator, ThesisRating

# yfinance import (선택적)
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

# 기본 환율 (USD/KRW)
DEFAULT_EXCHANGE_RATE = 1350.0


def get_exchange_rate():
    """환율 조회"""
    if 'exchange_rate' not in st.session_state:
        st.session_state.exchange_rate = DEFAULT_EXCHANGE_RATE
    return st.session_state.exchange_rate


def format_currency(value, currency='USD', exchange_rate=None):
    """통화 포맷팅 (달러/원화 병기)"""
    if exchange_rate is None:
        exchange_rate = get_exchange_rate()

    if currency == 'BOTH':
        krw_value = value * exchange_rate
        return f"${value:,.0f} (₩{krw_value:,.0f})"
    elif currency == 'KRW':
        krw_value = value * exchange_rate
        return f"₩{krw_value:,.0f}"
    else:
        return f"${value:,.0f}"


def get_realtime_price(symbol: str):
    """실시간 가격 조회 (단일 종목)"""
    if not YFINANCE_AVAILABLE or not symbol:
        return None

    try:
        ticker = yf.Ticker(symbol.strip().upper())
        hist = ticker.history(period='1d')
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
        # 1일 데이터 없으면 5일로 재시도
        hist = ticker.history(period='5d')
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
        return None
    except Exception:
        return None


def get_batch_prices(symbols: list):
    """여러 종목 가격 일괄 조회"""
    if not YFINANCE_AVAILABLE or not symbols:
        return {}

    prices = {}
    try:
        # yfinance 일괄 조회
        tickers_str = ' '.join([s.upper() for s in symbols])
        data = yf.download(tickers_str, period='1d', progress=False, threads=True)

        if data.empty:
            # 개별 조회로 fallback
            for sym in symbols:
                price = get_realtime_price(sym)
                if price:
                    prices[sym.upper()] = price
        else:
            # 단일 종목인 경우
            if len(symbols) == 1:
                if 'Close' in data.columns:
                    prices[symbols[0].upper()] = float(data['Close'].iloc[-1])
            else:
                # 여러 종목인 경우
                if 'Close' in data.columns:
                    for sym in symbols:
                        sym_upper = sym.upper()
                        try:
                            if sym_upper in data['Close'].columns:
                                val = data['Close'][sym_upper].iloc[-1]
                                if pd.notna(val):
                                    prices[sym_upper] = float(val)
                        except Exception:
                            pass
    except Exception as e:
        print(f"Batch price error: {e}")
        # 개별 조회로 fallback
        for sym in symbols:
            price = get_realtime_price(sym)
            if price:
                prices[sym.upper()] = price

    return prices


def update_portfolio_prices(portfolio: Portfolio):
    """포트폴리오 전체 종목 현재가 업데이트"""
    if not portfolio.positions:
        return 0

    symbols = [p.symbol for p in portfolio.positions]
    prices = get_batch_prices(symbols)

    updated = 0
    for position in portfolio.positions:
        if position.symbol in prices:
            position.current_price = prices[position.symbol]
            updated += 1

    portfolio.update_weights()
    return updated


# 한국 주요 종목 매핑 (이름 -> 티커)
KOREAN_STOCKS = {
    '삼성전자': '005930.KS',
    '삼성': '005930.KS',
    '현대차': '005380.KS',
    '현대자동차': '005380.KS',
    '현대': '005380.KS',
    'SK하이닉스': '000660.KS',
    '하이닉스': '000660.KS',
    'LG에너지솔루션': '373220.KS',
    'LG엔솔': '373220.KS',
    '네이버': '035420.KS',
    'NAVER': '035420.KS',
    '카카오': '035720.KS',
    '셀트리온': '068270.KS',
    '기아': '000270.KS',
    '기아차': '000270.KS',
    'POSCO홀딩스': '005490.KS',
    '포스코': '005490.KS',
    'KB금융': '105560.KS',
    '신한지주': '055550.KS',
    '현대모비스': '012330.KS',
    'LG화학': '051910.KS',
    '삼성SDI': '006400.KS',
    '삼성바이오로직스': '207940.KS',
    '삼성바이오': '207940.KS',
    '카카오뱅크': '323410.KS',
    '크래프톤': '259960.KS',
    '두산에너빌리티': '034020.KS',
    'HD현대중공업': '329180.KS',
    '한화에어로스페이스': '012450.KS',
    '한화에어로': '012450.KS',
}

# 미국 주요 종목 매핑
US_STOCKS = {
    '애플': 'AAPL',
    '마이크로소프트': 'MSFT',
    'MS': 'MSFT',
    '구글': 'GOOGL',
    '알파벳': 'GOOGL',
    '아마존': 'AMZN',
    '테슬라': 'TSLA',
    '엔비디아': 'NVDA',
    '메타': 'META',
    '페이스북': 'META',
    '넷플릭스': 'NFLX',
}


def resolve_ticker(query: str):
    """종목명/티커 검색 -> 티커 반환"""
    if not query:
        return None

    query = query.strip()

    # 한국 종목 매핑 확인
    if query in KOREAN_STOCKS:
        return KOREAN_STOCKS[query]

    # 미국 종목 매핑 확인
    if query in US_STOCKS:
        return US_STOCKS[query]

    # 이미 티커 형식인 경우
    return query.upper()


def search_stock(symbol: str):
    """종목 검색 및 정보 조회"""
    if not YFINANCE_AVAILABLE:
        return None

    if not symbol or not symbol.strip():
        return None

    # 종목명 -> 티커 변환
    ticker_symbol = resolve_ticker(symbol)

    try:
        ticker = yf.Ticker(ticker_symbol)

        # 가격 히스토리 먼저 조회 (더 안정적)
        hist = ticker.history(period='5d')

        if hist.empty:
            # 다시 시도 (1개월)
            hist = ticker.history(period='1mo')
            if hist.empty:
                return None

        current_price = float(hist['Close'].iloc[-1])

        # 종목 정보 조회
        try:
            info = ticker.info
            name = info.get('longName') or info.get('shortName') or ticker_symbol
            sector = info.get('sector', '')
            industry = info.get('industry', '')
            currency = info.get('currency', 'USD')
            market_cap = info.get('marketCap')
        except Exception:
            # info 조회 실패해도 가격은 있으면 반환
            name = ticker_symbol
            sector = ''
            industry = ''
            currency = 'USD'
            market_cap = None

        return {
            'symbol': ticker_symbol,
            'name': name,
            'current_price': round(current_price, 2),
            'currency': currency,
            'sector': sector,
            'industry': industry,
            'market_cap': market_cap,
        }
    except Exception as e:
        print(f"search_stock error for {ticker_symbol}: {e}")
        return None


def render_portfolio_input():
    """포트폴리오 입력 UI - 간단한 버전"""
    st.subheader("📝 포트폴리오 입력")

    # 세션 상태 초기화
    if 'portfolio' not in st.session_state:
        st.session_state.portfolio = Portfolio(name="My Portfolio")
    if 'last_price_update' not in st.session_state:
        st.session_state.last_price_update = None
    if 'searched_stock' not in st.session_state:
        st.session_state.searched_stock = None

    # 설정 영역
    col1, col2, col3 = st.columns([1, 1.5, 2])

    with col1:
        if st.button("🗑️ 초기화", key="reset_portfolio_btn"):
            st.session_state.portfolio = Portfolio(name="My Portfolio")
            st.session_state.last_price_update = None
            st.session_state.searched_stock = None

    with col2:
        # 실시간 가격 업데이트 버튼
        if st.button("🔄 전체 가격 새로고침", key="update_prices_btn"):
            if st.session_state.portfolio.positions:
                with st.spinner("가격 조회 중..."):
                    updated = update_portfolio_prices(st.session_state.portfolio)
                    st.session_state.last_price_update = datetime.now()
                    if updated > 0:
                        st.success(f"✅ {updated}개 종목 업데이트!")

    with col3:
        c1, c2 = st.columns(2)
        with c1:
            currency_display = st.selectbox("통화", ["USD", "KRW", "BOTH"], index=0, key="currency_display")
        with c2:
            st.session_state.exchange_rate = st.number_input("환율", 1000.0, 2000.0, get_exchange_rate(), 10.0, key="exchange_rate_input")

    if st.session_state.last_price_update:
        st.caption(f"📡 마지막 업데이트: {st.session_state.last_price_update.strftime('%H:%M:%S')}")

    st.divider()

    # ===== 새 포지션 추가 =====
    st.subheader("➕ 새 포지션 추가")

    # 종목 검색
    col_search, col_btn = st.columns([4, 1])
    with col_search:
        stock_query = st.text_input(
            "종목 검색",
            placeholder="현대차, 삼성전자, AAPL, TSLA 등",
            key="stock_query",
            label_visibility="collapsed"
        )
    with col_btn:
        search_btn = st.button("🔍 검색", key="search_stock_btn", use_container_width=True)

    # 검색 버튼 클릭 시
    if search_btn and stock_query:
        with st.spinner(f"'{stock_query}' 검색 중..."):
            info = search_stock(stock_query)
            if info:
                st.session_state.searched_stock = info
            else:
                st.session_state.searched_stock = None
                st.error(f"❌ '{stock_query}' 종목을 찾을 수 없습니다.")

    # 검색 결과가 있으면 표시
    if st.session_state.searched_stock:
        info = st.session_state.searched_stock
        price = info['current_price']
        currency = info.get('currency', 'USD')

        # 가격 표시
        if currency == 'KRW':
            price_str = f"₩{price:,.0f}"
        else:
            price_str = f"${price:,.2f} (₩{price * st.session_state.exchange_rate:,.0f})"

        st.success(f"✅ **{info['name']}** ({info['symbol']}) | 현재가: **{price_str}**")

        # 포지션 추가 폼
        with st.form("add_position_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)

            with col1:
                quantity = st.number_input("수량", min_value=1.0, value=10.0, step=1.0)
                # 매수가 기본값 = 현재가
                avg_cost = st.number_input("매수가", min_value=0.01, value=float(price), step=0.01, format="%.2f")

            with col2:
                target_pct = st.number_input("목표 수익률 (%)", min_value=0.0, value=20.0, step=5.0)
                stop_loss_pct = st.number_input("손절 비율 (%)", min_value=0.0, value=10.0, step=1.0)

            with col3:
                thesis_type = st.selectbox("투자 논리", [t.value for t in InvestmentThesis])
                thesis_custom = st.text_input("투자 논리 (직접 입력)", placeholder="예: AI 성장주, 배당 투자, 실적 턴어라운드 등")
                time_horizon = st.selectbox("투자 기간", ["단기", "중기", "장기"])

            # 목표가/손절가 미리보기
            target_p = avg_cost * (1 + target_pct / 100)
            stop_p = avg_cost * (1 - stop_loss_pct / 100)
            if currency == 'KRW':
                st.caption(f"📊 목표가: ₩{target_p:,.0f} (+{target_pct:.0f}%) | 손절가: ₩{stop_p:,.0f} (-{stop_loss_pct:.0f}%)")
            else:
                st.caption(f"📊 목표가: ${target_p:,.2f} (+{target_pct:.0f}%) | 손절가: ${stop_p:,.2f} (-{stop_loss_pct:.0f}%)")

            if st.form_submit_button("✅ 포지션 추가", use_container_width=True, type="primary"):
                thesis_enum = next((t for t in InvestmentThesis if t.value == thesis_type), InvestmentThesis.OTHER)

                position = Position(
                    symbol=info['symbol'],
                    name=info['name'],
                    quantity=quantity,
                    avg_cost=avg_cost,
                    current_price=price,
                    asset_type=AssetType.STOCK,
                    thesis_type=thesis_enum,
                    thesis_description=thesis_custom if thesis_custom else "",
                    target_price=target_p if target_pct > 0 else None,
                    stop_loss=stop_p if stop_loss_pct > 0 else None,
                    time_horizon=time_horizon,
                )

                st.session_state.portfolio.add_position(position)
                st.session_state.searched_stock = None
                st.success(f"✅ {info['symbol']} 추가 완료!")
                st.rerun()
    else:
        st.info("💡 종목명(현대차, 삼성) 또는 티커(AAPL, TSLA)를 입력하고 검색 버튼을 누르세요")

    return st.session_state.portfolio


def render_portfolio_summary(portfolio: Portfolio):
    """포트폴리오 요약"""
    st.subheader("📊 포트폴리오 요약")

    currency = st.session_state.get('currency_display', 'BOTH')

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "총 평가금액",
            format_currency(portfolio.total_market_value, currency),
        )

    with col2:
        st.metric(
            "총 투자원금",
            format_currency(portfolio.total_cost_basis, currency),
        )

    with col3:
        pnl = portfolio.total_unrealized_pnl
        pnl_pct = portfolio.total_unrealized_pnl_pct
        st.metric(
            "미실현 손익",
            format_currency(pnl, currency),
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

    currency = st.session_state.get('currency_display', 'BOTH')
    exchange_rate = get_exchange_rate()

    # 데이터프레임 생성
    data = []
    for p in portfolio.positions:
        # 목표가/손절가 퍼센트 계산
        target_pct = ((p.target_price / p.avg_cost - 1) * 100) if p.target_price and p.avg_cost > 0 else None
        stop_pct = ((1 - p.stop_loss / p.avg_cost) * 100) if p.stop_loss and p.avg_cost > 0 else None

        # 손익률 계산
        pnl_pct = p.unrealized_pnl_pct if p.unrealized_pnl_pct else 0
        pnl_emoji = "🟢" if pnl_pct > 0 else ("🔴" if pnl_pct < 0 else "⚪")

        # 가격 포맷팅
        if currency == 'BOTH':
            avg_cost_str = f"${p.avg_cost:.2f}"
            current_str = f"${p.current_price:.2f}" if p.current_price else "-"
            pnl_str = f"${p.unrealized_pnl:+,.0f}" if p.unrealized_pnl else "-"
        elif currency == 'KRW':
            avg_cost_str = f"₩{p.avg_cost * exchange_rate:,.0f}"
            current_str = f"₩{p.current_price * exchange_rate:,.0f}" if p.current_price else "-"
            pnl_str = f"₩{p.unrealized_pnl * exchange_rate:+,.0f}" if p.unrealized_pnl else "-"
        else:
            avg_cost_str = f"${p.avg_cost:.2f}"
            current_str = f"${p.current_price:.2f}" if p.current_price else "-"
            pnl_str = f"${p.unrealized_pnl:+,.0f}" if p.unrealized_pnl else "-"

        data.append({
            '': pnl_emoji,
            '티커': p.symbol,
            '종목명': p.name[:10] + '..' if len(p.name) > 12 else p.name,
            '수량': f"{p.quantity:.0f}",
            '매수가': avg_cost_str,
            '현재가': current_str,
            '손익': pnl_str,
            '수익률': f"{pnl_pct:+.1f}%",
            '목표': f"+{target_pct:.0f}%" if target_pct else "-",
            '손절': f"-{stop_pct:.0f}%" if stop_pct else "-",
            '비중': f"{p.weight:.1f}%" if p.weight else "-",
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 삭제 버튼
    with st.expander("포지션 삭제"):
        symbols = [p.symbol for p in portfolio.positions]
        symbol_to_delete = st.selectbox("삭제할 종목", symbols, key="delete_symbol_select")
        if st.button("삭제", key="delete_position_btn"):
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
