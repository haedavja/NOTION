"""
포트폴리오 분석 대시보드 페이지
"""

import streamlit as st
import pandas as pd
import numpy as np
import logging
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from portfolio.portfolio import Portfolio, Position, AssetType, InvestmentThesis
from portfolio.analyzer import PortfolioAnalyzer
from portfolio.thesis_evaluator import (
    ThesisEvaluator, ThesisRating, ThesisReport,
    ThesisReportHistory, ThesisReportManager
)
from portfolio.risk_monitor import RiskMonitor, AlertSeverity, AlertType
from dashboard.input_validators import (
    DashboardValidator, PositionValidator, sanitize
)

logger = logging.getLogger(__name__)

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
        logger.warning(f"Batch price error: {e}")
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
    # 추가 종목
    '한국전력': '015760.KS',
    '한전': '015760.KS',
    'SK텔레콤': '017670.KS',
    'SKT': '017670.KS',
    'KT': '030200.KS',
    'LG유플러스': '032640.KS',
    '한국가스공사': '036460.KS',
    '가스공사': '036460.KS',
    '하나금융지주': '086790.KS',
    '하나금융': '086790.KS',
    '우리금융지주': '316140.KS',
    '우리금융': '316140.KS',
    '기업은행': '024110.KS',
    'IBK': '024110.KS',
    'LG전자': '066570.KS',
    'LG': '003550.KS',
    'SK': '034730.KS',
    'SK이노베이션': '096770.KS',
    '한화오션': '042660.KS',
    '한국조선해양': '009540.KS',
    '고려아연': '010130.KS',
    '에코프로': '086520.KS',
    '에코프로비엠': '247540.KS',
    'SK바이오팜': '326030.KS',
    '한미약품': '128940.KS',
    '유한양행': '000100.KS',
    '하이브': '352820.KS',
    'JYP': '035900.KQ',
    '카카오게임즈': '293490.KQ',
    '펄어비스': '263750.KQ',
    '알테오젠': '196170.KQ',
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
    """종목명/티커 검색 -> 티커 반환 (KRX 검색 지원)"""
    if not query:
        return None

    query = query.strip()

    # 한국 종목 매핑 확인 (빠른 경로)
    if query in KOREAN_STOCKS:
        return KOREAN_STOCKS[query]

    # 미국 종목 매핑 확인
    if query in US_STOCKS:
        return US_STOCKS[query]

    # KRX 검색으로 한국 종목 찾기
    try:
        from korea.krx_data import KRXDataCollector
        krx = KRXDataCollector()
        results = krx.search_stock(query, limit=1)
        if results:
            code = results[0]['code']
            market = results[0].get('market', 'KOSPI')
            suffix = '.KQ' if market == 'KOSDAQ' else '.KS'
            return f"{code}{suffix}"
    except Exception as e:
        logger.debug(f"KRX 검색 실패: {e}")

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
        logger.warning(f"search_stock error for {ticker_symbol}: {e}")
        return None


def render_portfolio_input():
    """포트폴리오 입력 UI - 간단한 버전"""
    st.subheader("📝 포트폴리오 입력")

    # 데이터 저장소 초기화
    from portfolio.data_store import data_store

    # 세션 상태 초기화
    if 'portfolio' not in st.session_state:
        # 저장된 포트폴리오 로드 시도
        loaded = data_store.load_portfolio()
        if loaded and loaded.positions:
            st.session_state.portfolio = loaded
            st.toast("💾 저장된 포트폴리오를 불러왔습니다!")
        else:
            st.session_state.portfolio = Portfolio(name="My Portfolio")
    if 'last_price_update' not in st.session_state:
        st.session_state.last_price_update = None
    if 'searched_stock' not in st.session_state:
        st.session_state.searched_stock = None

    # 설정 영역
    col1, col2, col3, col4 = st.columns([1, 1, 1.5, 1.5])

    with col1:
        if st.button("🗑️ 초기화", key="reset_portfolio_btn"):
            st.session_state.portfolio = Portfolio(name="My Portfolio")
            st.session_state.last_price_update = None
            st.session_state.searched_stock = None

    with col2:
        # 저장/불러오기 버튼
        c1, c2 = st.columns(2)
        with c1:
            if st.button("💾 저장", key="save_portfolio_btn"):
                if data_store.save_portfolio(st.session_state.portfolio):
                    st.success("저장됨!")
                else:
                    st.error("저장 실패")
        with c2:
            if st.button("📂 불러오기", key="load_portfolio_btn"):
                loaded = data_store.load_portfolio()
                if loaded:
                    st.session_state.portfolio = loaded
                    st.success("불러옴!")
                    st.rerun()
                else:
                    st.warning("저장된 데이터 없음")

    with col3:
        # 실시간 가격 업데이트 버튼
        if st.button("🔄 전체 가격 새로고침", key="update_prices_btn"):
            if st.session_state.portfolio.positions:
                with st.spinner("가격 조회 중..."):
                    updated = update_portfolio_prices(st.session_state.portfolio)
                    st.session_state.last_price_update = datetime.now()
                    if updated > 0:
                        st.success(f"✅ {updated}개 종목 업데이트!")

    with col4:
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

    # 검색 실행 함수
    def do_search():
        query = st.session_state.get('stock_query_input', '')
        if query:
            # 입력값 정제 (XSS 방지)
            sanitized_query = sanitize(query, max_length=50)
            if not sanitized_query:
                st.session_state.search_error = "유효한 종목명을 입력하세요."
                return

            info = search_stock(sanitized_query)
            if info:
                st.session_state.searched_stock = info
                st.session_state.search_error = None
            else:
                st.session_state.searched_stock = None
                st.session_state.search_error = f"❌ '{sanitized_query}' 종목을 찾을 수 없습니다."
        else:
            st.session_state.search_error = None

    # 세션 상태 초기화
    if 'search_error' not in st.session_state:
        st.session_state.search_error = None

    # 종목 검색 (콜백 방식 - 탭 유지)
    col_search, col_btn = st.columns([4, 1])
    with col_search:
        st.text_input(
            "종목 검색",
            placeholder="현대차, 삼성전자, AAPL, TSLA 등",
            key="stock_query_input",
            label_visibility="collapsed",
            on_change=do_search
        )
    with col_btn:
        if st.button("🔍 검색", key="search_stock_btn", use_container_width=True):
            do_search()

    # 에러 표시
    if st.session_state.search_error:
        st.error(st.session_state.search_error)

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
                # 입력 유효성 검사
                errors = []

                # 수량 검증
                qty_result = DashboardValidator.validate_quantity(quantity)
                if not qty_result.is_valid:
                    errors.append(qty_result.error)

                # 평균 단가 검증
                cost_result = DashboardValidator.validate_price(avg_cost, "매수가")
                if not cost_result.is_valid:
                    errors.append(cost_result.error)

                # 투자 논리 텍스트 정제 (XSS 방지)
                sanitized_thesis = sanitize(thesis_custom, max_length=500) if thesis_custom else ""

                if errors:
                    for err in errors:
                        st.error(err)
                else:
                    thesis_enum = next((t for t in InvestmentThesis if t.value == thesis_type), InvestmentThesis.OTHER)

                    position = Position(
                        symbol=info['symbol'],
                        name=info['name'],
                        quantity=qty_result.value,
                        avg_cost=cost_result.value,
                        current_price=price,
                        asset_type=AssetType.STOCK,
                        thesis_type=thesis_enum,
                        thesis_description=sanitized_thesis,
                        target_price=target_p if target_pct > 0 else None,
                        stop_loss=stop_p if stop_loss_pct > 0 else None,
                        time_horizon=time_horizon,
                    )

                    st.session_state.portfolio.add_position(position)
                    st.session_state.searched_stock = None
                    logger.info(f"Position added: {info['symbol']}")
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

    # 세션 상태에 리포트 매니저 초기화
    if 'report_manager' not in st.session_state:
        st.session_state.report_manager = ThesisReportManager()

    evaluator = ThesisEvaluator()
    report_manager = st.session_state.report_manager

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

    # 기존 보고서 히스토리 확인
    history = report_manager.get_history(selected_symbol)
    if history and history.reports:
        st.caption(f"📜 이 종목의 축적된 보고서: {len(history.reports)}건")

    # 평가 및 보고서 생성 버튼
    col1, col2 = st.columns(2)

    with col1:
        eval_btn = st.button("🔍 투자 논리 분석 실행", key="eval_btn", use_container_width=True)

    with col2:
        report_btn = st.button("📊 잠재적 보고서 생성 & 축적", key="report_btn", type="primary", use_container_width=True)

    # 평가 실행
    if eval_btn or report_btn:
        with st.spinner("분석 중..."):
            try:
                evaluation = evaluator.evaluate(position)

                # 보고서 생성 및 저장
                if report_btn:
                    previous = report_manager.get_latest_report(selected_symbol)
                    new_report = evaluator.generate_potential_report(position, evaluation, previous)
                    report_manager.add_report(new_report)
                    st.success(f"✅ 잠재적 보고서가 생성되고 축적되었습니다! (총 {len(report_manager.get_history(selected_symbol).reports)}건)")

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

                def parse_metadata(text):
                    """텍스트에서 신뢰도/출처 메타데이터 분리"""
                    import re
                    # 패턴: (신뢰도 XX%) 또는 [출처: XXX] 또는 (출처: XXX)
                    conf_match = re.search(r'\(신뢰도\s*(\d+)%\)', text)
                    source_match = re.search(r'[\[\(]출처:\s*([^\]\)]+)[\]\)]', text)

                    main_text = text
                    confidence = None
                    source = None

                    if conf_match:
                        main_text = main_text.replace(conf_match.group(0), '').strip()
                        confidence = int(conf_match.group(1))
                    if source_match:
                        main_text = main_text.replace(source_match.group(0), '').strip()
                        source = source_match.group(1).strip()

                    return main_text.strip(' -'), confidence, source

                def display_item_with_metadata(text, item_type='info', idx=0):
                    """메타데이터를 오른쪽에 간략히 표시 (마우스 오버 시 출처)"""
                    main_text, confidence, source = parse_metadata(text)

                    if confidence is not None:
                        # 신뢰도 색상
                        if confidence >= 80:
                            conf_color, bg_color = "🟢", "#d4edda"
                        elif confidence >= 60:
                            conf_color, bg_color = "🟡", "#fff3cd"
                        else:
                            conf_color, bg_color = "🔴", "#f8d7da"

                        # 툴팁 텍스트
                        tooltip = f"신뢰도: {confidence}%"
                        if source:
                            tooltip += f" | 출처: {source}"

                        # 본문 + 신뢰도 배지 (마우스 오버 시 출처 표시)
                        badge_html = f'<span title="{tooltip}" style="background:{bg_color};padding:2px 6px;border-radius:4px;font-size:0.8em;cursor:help;margin-left:8px;">{conf_color} {confidence}%</span>'

                        if item_type == 'success':
                            st.success(main_text)
                            st.markdown(f"<div style='text-align:right;margin-top:-15px;'>{badge_html}</div>", unsafe_allow_html=True)
                        elif item_type == 'error':
                            st.error(main_text)
                            st.markdown(f"<div style='text-align:right;margin-top:-15px;'>{badge_html}</div>", unsafe_allow_html=True)
                        elif item_type == 'warning':
                            st.warning(main_text)
                            st.markdown(f"<div style='text-align:right;margin-top:-15px;'>{badge_html}</div>", unsafe_allow_html=True)
                        else:
                            st.info(main_text)
                            st.markdown(f"<div style='text-align:right;margin-top:-15px;'>{badge_html}</div>", unsafe_allow_html=True)
                    else:
                        if item_type == 'success':
                            st.success(main_text)
                        elif item_type == 'error':
                            st.error(main_text)
                        elif item_type == 'warning':
                            st.warning(main_text)
                        else:
                            st.info(main_text)

                with col1:
                    st.markdown("#### ✅ 강점 (논리 지지 요소)")
                    for s in evaluation.strengths[:5]:
                        display_item_with_metadata(s, 'success')

                with col2:
                    st.markdown("#### ❌ 약점 (위험 요소)")
                    for w in evaluation.weaknesses[:5]:
                        display_item_with_metadata(w, 'error')

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
                        display_item_with_metadata(r, 'warning')

                # 권고사항
                st.markdown("### 💡 권고사항")

                def render_with_clickable_confidence(text):
                    """신뢰도 배지를 클릭 가능한 HTML로 변환"""
                    import re
                    # 패턴: 🟢85%{{출처:xxx}} 또는 🟡70%{{출처:xxx}}
                    pattern = r'([🟢🟡🟠🔴])(\d+)%\{\{출처:([^}]+)\}\}'

                    def replace_badge(match):
                        icon = match.group(1)
                        conf = match.group(2)
                        source = match.group(3)
                        # 배경색
                        if icon == '🟢':
                            bg = '#d4edda'
                        elif icon == '🟡':
                            bg = '#fff3cd'
                        elif icon == '🟠':
                            bg = '#ffe0b2'
                        else:
                            bg = '#f8d7da'
                        return f'<span title="출처: {source}" style="background:{bg};padding:1px 5px;border-radius:3px;font-size:0.85em;cursor:help;">{icon}{conf}%</span>'

                    # 출처 없는 패턴도 처리: 🟢85%
                    pattern_no_source = r'([🟢🟡🟠🔴])(\d+)%(?!\{)'

                    def replace_badge_no_source(match):
                        icon = match.group(1)
                        conf = match.group(2)
                        if icon == '🟢':
                            bg = '#d4edda'
                        elif icon == '🟡':
                            bg = '#fff3cd'
                        elif icon == '🟠':
                            bg = '#ffe0b2'
                        else:
                            bg = '#f8d7da'
                        return f'<span style="background:{bg};padding:1px 5px;border-radius:3px;font-size:0.85em;">{icon}{conf}%</span>'

                    result = re.sub(pattern, replace_badge, text)
                    result = re.sub(pattern_no_source, replace_badge_no_source, result)
                    return result

                for rec in evaluation.recommendations:
                    # 마크다운 블록은 HTML로 변환하여 표시
                    if '\n' in rec:
                        processed = render_with_clickable_confidence(rec)
                        st.markdown(processed, unsafe_allow_html=True)
                    else:
                        display_item_with_metadata(rec, 'info')

            except Exception as e:
                st.error(f"분석 중 오류 발생: {e}")
                st.info("실시간 데이터 조회가 불가능한 경우 샘플 분석 결과를 표시합니다.")


def render_potential_reports(portfolio: Portfolio):
    """잠재적 보고서 히스토리 및 상황 보고서"""
    st.subheader("📜 잠재적 보고서 (축적된 리스크/리턴 분석)")

    if not portfolio.positions:
        st.info("포지션이 없습니다.")
        return

    # 세션 상태에 리포트 매니저 초기화
    if 'report_manager' not in st.session_state:
        st.session_state.report_manager = ThesisReportManager()

    evaluator = ThesisEvaluator()
    report_manager = st.session_state.report_manager

    # 추적 중인 종목 확인
    tracked_symbols = report_manager.get_all_symbols()
    portfolio_symbols = [p.symbol for p in portfolio.positions]

    # 전체 요약
    if tracked_symbols:
        st.markdown("### 📊 전체 추적 현황")
        portfolio_summary = report_manager.get_portfolio_summary()

        if portfolio_summary.get('status') != 'no_data':
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("추적 중인 종목", f"{portfolio_summary.get('total_positions', 0)}개")

            with col2:
                avg_score = portfolio_summary.get('average_score', 0)
                avg_pct = (avg_score + 1) / 2 * 100
                st.metric("평균 논리 점수", f"{avg_pct:.0f}/100")

            with col3:
                status_dist = portfolio_summary.get('status_distribution', {})
                active_count = status_dist.get('active', 0)
                st.metric("활성 포지션", f"{active_count}개")

            with col4:
                best = portfolio_summary.get('best_position')
                if best:
                    st.metric("최고 점수", f"{best['symbol']}")

        st.divider()

    # 종목별 상세 보고서
    st.markdown("### 📋 종목별 상황 보고서")

    # 종목 선택
    symbols_with_reports = [s for s in portfolio_symbols if s in tracked_symbols]
    symbols_without_reports = [s for s in portfolio_symbols if s not in tracked_symbols]

    if symbols_with_reports:
        selected_symbol = st.selectbox(
            "보고서 조회할 종목",
            symbols_with_reports,
            key="report_symbol_select"
        )

        position = portfolio.get_position(selected_symbol)
        history = report_manager.get_history(selected_symbol)

        if position and history and history.reports:
            # 상황 보고서 생성
            situation_report = evaluator.generate_ongoing_situation_report(history, position)
            st.markdown(situation_report)

            # 히스토리 차트
            st.markdown("### 📈 점수 추이")
            if len(history.reports) >= 2:
                import plotly.graph_objects as go

                dates = [r.timestamp for r in history.reports]
                scores = [(r.score + 1) / 2 * 100 for r in history.reports]  # 0-100 스케일
                prices = [r.price_at_report for r in history.reports]

                fig = make_subplots(specs=[[{"secondary_y": True}]])

                fig.add_trace(
                    go.Scatter(x=dates, y=scores, name="투자논리 점수", line=dict(color='blue')),
                    secondary_y=False,
                )

                fig.add_trace(
                    go.Scatter(x=dates, y=prices, name="가격", line=dict(color='orange', dash='dot')),
                    secondary_y=True,
                )

                fig.update_layout(
                    title=f"{selected_symbol} 추적 히스토리",
                    height=350,
                )
                fig.update_yaxes(title_text="논리 점수 (0-100)", secondary_y=False)
                fig.update_yaxes(title_text="가격", secondary_y=True)

                st.plotly_chart(fig, use_container_width=True)

            # 상세 히스토리 테이블
            with st.expander("📜 보고서 히스토리 상세"):
                history_data = []
                for r in reversed(history.reports[-10:]):  # 최근 10개
                    history_data.append({
                        '날짜': r.timestamp.strftime('%Y-%m-%d %H:%M'),
                        '상태': r.status,
                        '점수': f"{(r.score + 1) / 2 * 100:.0f}",
                        '등급': r.rating,
                        '가격': f"${r.price_at_report:.2f}",
                        '수익률': f"{r.price_change_from_buy:+.1f}%",
                        '목표확률': f"{r.target_probability:.0f}%",
                    })
                st.dataframe(pd.DataFrame(history_data), use_container_width=True, hide_index=True)

    # 아직 추적 안 되는 종목
    if symbols_without_reports:
        st.markdown("### ℹ️ 추적 시작이 필요한 종목")
        st.caption(f"다음 종목들은 아직 보고서가 없습니다: {', '.join(symbols_without_reports)}")
        st.info("💡 '투자논리 평가' 탭에서 '잠재적 보고서 생성 & 축적' 버튼을 눌러 추적을 시작하세요.")

    if not tracked_symbols:
        st.info("📝 아직 축적된 보고서가 없습니다. '투자논리 평가' 탭에서 보고서를 생성해주세요.")


def render_risk_alerts(portfolio: Portfolio):
    """위험 경고 및 모니터링"""
    st.subheader("🚨 위험 모니터링")

    if not portfolio.positions:
        st.info("포지션이 없습니다.")
        return

    # 리스크 모니터 초기화
    if 'risk_monitor' not in st.session_state:
        st.session_state.risk_monitor = RiskMonitor()
    if 'last_risk_scan' not in st.session_state:
        st.session_state.last_risk_scan = None

    monitor = st.session_state.risk_monitor

    # 스캔 버튼
    col1, col2 = st.columns([2, 1])
    with col1:
        scan_btn = st.button("🔍 전체 위험 스캔 실행", key="risk_scan_btn", type="primary", use_container_width=True)
    with col2:
        if st.session_state.last_risk_scan:
            st.caption(f"마지막 스캔: {st.session_state.last_risk_scan.get('timestamp', '-')[:19]}")

    if scan_btn:
        with st.spinner("포트폴리오 위험 분석 중..."):
            scan_result = monitor.run_full_scan(portfolio)
            st.session_state.last_risk_scan = scan_result

    # 스캔 결과 표시
    if st.session_state.last_risk_scan:
        scan = st.session_state.last_risk_scan
        level = scan['overall_risk_level']
        by_severity = scan['by_severity']

        # 전체 위험 수준 표시
        st.markdown("### 📊 전체 위험 수준")

        if level == 'emergency':
            st.error("🚨 **긴급**: 즉각적인 조치가 필요합니다!")
        elif level == 'critical':
            st.warning("🔴 **위험**: 주의가 필요한 상황입니다.")
        elif level == 'warning':
            st.info("⚠️ **주의**: 모니터링을 강화하세요.")
        else:
            st.success("✅ **정상**: 특별한 위험 신호가 없습니다.")

        # 경고 수 표시
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("긴급", f"{by_severity['emergency']}건",
                     delta="위험" if by_severity['emergency'] > 0 else None,
                     delta_color="inverse")
        with col2:
            st.metric("위험", f"{by_severity['critical']}건",
                     delta="주의" if by_severity['critical'] > 0 else None,
                     delta_color="inverse")
        with col3:
            st.metric("주의", f"{by_severity['warning']}건")
        with col4:
            st.metric("참고", f"{by_severity['info']}건")

        st.divider()

        # 거시경제 현황
        macro = scan.get('macro_summary', {})
        if macro:
            st.markdown("### 🌍 거시경제 현황")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                vix = macro.get('vix')
                if vix:
                    vix_status = "위험" if vix > 30 else ("주의" if vix > 20 else "정상")
                    vix_color = "inverse" if vix > 25 else "normal"
                    st.metric("VIX (공포지수)", f"{vix:.1f}", delta=vix_status, delta_color=vix_color)

            with col2:
                t10y = macro.get('treasury_10y')
                if t10y:
                    st.metric("10년물 금리", f"{t10y:.2f}%")

            with col3:
                spread = macro.get('yield_spread')
                if spread is not None:
                    status = "역전!" if spread < 0 else "정상"
                    st.metric("장단기 스프레드", f"{spread:.2f}%", delta=status,
                             delta_color="inverse" if spread < 0 else "normal")

            with col4:
                sp500 = macro.get('sp500_5d_return')
                if sp500:
                    st.metric("S&P 500 (5일)", f"{sp500:+.1f}%",
                             delta_color="inverse" if sp500 < -5 else "normal")

            st.divider()

        # 긴급/위험 경고 상세
        emergency_alerts = scan.get('emergency_alerts', [])
        critical_alerts = scan.get('critical_alerts', [])

        if emergency_alerts or critical_alerts:
            st.markdown("### 🔴 즉시 확인 필요")

            for alert in emergency_alerts:
                with st.container():
                    st.error(f"**{alert['title']}**")
                    st.write(alert['message'])
                    st.caption(f"💡 권고: {alert['recommended_action']}")
                    st.caption(f"트리거: {alert['triggered_by']} | 현재값: {alert['current_value']:.2f}")

            for alert in critical_alerts:
                with st.container():
                    st.warning(f"**{alert['title']}**")
                    st.write(alert['message'])
                    st.caption(f"💡 권고: {alert['recommended_action']}")
                    st.caption(f"트리거: {alert['triggered_by']} | 현재값: {alert['current_value']:.2f}")

        # 주의/참고 경고
        warning_alerts = scan.get('warning_alerts', [])
        info_alerts = scan.get('info_alerts', [])

        if warning_alerts:
            with st.expander(f"⚠️ 주의 사항 ({len(warning_alerts)}건)", expanded=False):
                for alert in warning_alerts:
                    st.info(f"**{alert['title']}**\n\n{alert['message']}\n\n💡 {alert['recommended_action']}")

        if info_alerts:
            with st.expander(f"ℹ️ 참고 사항 ({len(info_alerts)}건)", expanded=False):
                for alert in info_alerts:
                    st.success(f"**{alert['title']}**\n\n{alert['message']}")

        # 종목별 경고 요약
        st.markdown("### 📋 종목별 경고 현황")
        all_alerts = scan.get('all_alerts', [])

        if all_alerts:
            # 종목별로 그룹화
            by_symbol = {}
            for alert in all_alerts:
                symbol = alert.symbol
                if symbol not in by_symbol:
                    by_symbol[symbol] = []
                by_symbol[symbol].append(alert)

            alert_data = []
            for symbol, alerts in by_symbol.items():
                if symbol == "MACRO":
                    continue
                severities = [a.severity.value for a in alerts]
                worst = 'emergency' if 'emergency' in severities else (
                    'critical' if 'critical' in severities else (
                        'warning' if 'warning' in severities else 'info'
                    )
                )
                emoji = {'emergency': '🚨', 'critical': '🔴', 'warning': '⚠️', 'info': 'ℹ️'}
                alert_data.append({
                    '상태': emoji.get(worst, ''),
                    '종목': symbol,
                    '경고 수': len(alerts),
                    '주요 경고': alerts[0].alert_type.value if alerts else '-',
                })

            if alert_data:
                st.dataframe(pd.DataFrame(alert_data), use_container_width=True, hide_index=True)
        else:
            st.success("모든 종목이 정상 범위 내에 있습니다.")

    else:
        st.info("💡 '전체 위험 스캔 실행' 버튼을 눌러 포트폴리오 위험을 분석하세요.")

        # 간단한 거시경제 현황 미리보기
        st.markdown("### 🌍 거시경제 간략 현황")
        with st.spinner("데이터 로딩 중..."):
            macro_preview = monitor.macro_fetcher.get_macro_summary()

        if macro_preview.get('vix'):
            col1, col2 = st.columns(2)
            with col1:
                vix = macro_preview['vix']
                if vix > 30:
                    st.error(f"VIX: {vix:.1f} - 극단적 공포")
                elif vix > 20:
                    st.warning(f"VIX: {vix:.1f} - 불안")
                else:
                    st.success(f"VIX: {vix:.1f} - 안정")

            with col2:
                spread = macro_preview.get('yield_spread')
                if spread is not None:
                    if spread < 0:
                        st.error(f"장단기 스프레드: {spread:.2f}% (역전)")
                    else:
                        st.success(f"장단기 스프레드: {spread:.2f}%")


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
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 요약",
        "🚨 위험 경고",
        "🎯 투자논리 평가",
        "📜 잠재적 보고서",
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
        render_risk_alerts(portfolio)

    with tab3:
        render_thesis_evaluation(portfolio)

    with tab4:
        render_potential_reports(portfolio)

    with tab5:
        render_risk_return_analysis(portfolio)

    with tab6:
        render_portfolio_recommendations(portfolio)


if __name__ == "__main__":
    st.set_page_config(page_title="포트폴리오 분석", layout="wide")
    render_portfolio_page()
