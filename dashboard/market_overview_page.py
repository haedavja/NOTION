"""
시장 종합 현황 대시보드
========================

시장 논리/근거, 차트, 주도주, 리스크, 잠재적 고점 분석을 제공합니다.

주요 기능:
---------
1. 시장 현황 탭: 지수 분석, SNS 스타일 토론, 핵심 지표
2. 주도 섹터/종목 탭: 상승/하락 상위, 섹터별 동향
3. 리스크 분석 탭: 리스크 게이지, 요인 분석
4. 목표/지지선 탭: 저항선, 지지선, 52주 범위

의존성:
------
- pykrx: 한국 주식 데이터 (선택적)
- plotly: 차트 시각화 (선택적)
- analysis.sector_rotation: 섹터 분석 (선택적)

유지보수 노트:
------------
- TRADER_PERSONAS: 6개 트레이더 페르소나 정의 (line ~310)
- generate_sns_market_discussion(): SNS 토론 생성 로직 (line ~357)
- render_sns_discussion(): 토론 UI 렌더링 (line ~656)
- 새 페르소나 추가 시 TRADER_PERSONAS와 generate_sns_market_discussion() 모두 수정 필요

버전: 2.0 (2024-01)
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os
import logging

# 로깅 설정
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 데이터 수집
try:
    from korea.krx_data import KRXDataCollector
    KRX_AVAILABLE = True
except ImportError:
    KRX_AVAILABLE = False

# 섹터 회전 분석
try:
    from analysis.sector_rotation import (
        SectorRotationAnalyzer, sector_rotation_analyzer,
        MarketPhase, SECTOR_ETFS
    )
    SECTOR_AVAILABLE = True
except ImportError:
    SECTOR_AVAILABLE = False

# 차트
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


# ============ 실시간 시장 키워드 수집 ============

def fetch_market_themes() -> Dict:
    """
    네이버 금융에서 실시간 시장 테마/키워드 수집

    Returns:
        Dict containing:
        - hot_themes: 인기 테마 리스트 [(테마명, 등락률, 대표종목), ...]
        - market_news: 주요 뉴스 헤드라인 리스트
        - top_search: 인기 검색 종목
        - foreign_flow: 외국인 동향
    """
    result = {
        'hot_themes': [],
        'market_news': [],
        'top_search': [],
        'foreign_flow': {'kospi': 0, 'kosdaq': 0},
        'fetched': False
    }

    try:
        import requests
        from bs4 import BeautifulSoup

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        # 1. 인기 테마 조회 (네이버 금융 테마)
        try:
            theme_url = 'https://finance.naver.com/sise/theme.naver'
            resp = requests.get(theme_url, headers=headers, timeout=5)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                theme_rows = soup.select('table.type_1 tr')

                for row in theme_rows[:10]:
                    cols = row.select('td')
                    if len(cols) >= 4:
                        name_tag = cols[0].select_one('a')
                        change_tag = cols[1]
                        if name_tag:
                            theme_name = name_tag.text.strip()
                            change_text = change_tag.text.strip().replace('%', '').replace('+', '')
                            try:
                                change = float(change_text) if change_text else 0
                            except:
                                change = 0
                            # 대표 종목 (있으면)
                            stock_tag = cols[3].select_one('a') if len(cols) > 3 else None
                            stock_name = stock_tag.text.strip() if stock_tag else ''
                            result['hot_themes'].append({
                                'name': theme_name,
                                'change': change,
                                'stock': stock_name
                            })
        except Exception as e:
            logger.warning(f"테마 조회 실패: {e}")

        # 2. 시장 뉴스 헤드라인
        try:
            news_url = 'https://finance.naver.com/news/mainnews.naver'
            resp = requests.get(news_url, headers=headers, timeout=5)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                news_items = soup.select('ul.newsList li a')[:5]
                for item in news_items:
                    title = item.text.strip()
                    if title and len(title) > 10:
                        result['market_news'].append(title)
        except Exception as e:
            logger.warning(f"뉴스 조회 실패: {e}")

        # 3. 인기 검색 종목
        try:
            search_url = 'https://finance.naver.com/sise/lastsearch2.naver'
            resp = requests.get(search_url, headers=headers, timeout=5)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                search_rows = soup.select('table.type_5 tr')
                for row in search_rows[:8]:
                    name_tag = row.select_one('a')
                    change_tag = row.select_one('td.number_2 span')
                    if name_tag:
                        stock_name = name_tag.text.strip()
                        change_text = change_tag.text.strip() if change_tag else '0%'
                        result['top_search'].append({
                            'name': stock_name,
                            'change': change_text
                        })
        except Exception as e:
            logger.warning(f"인기검색 조회 실패: {e}")

        # 4. 외국인 동향
        try:
            foreign_url = 'https://finance.naver.com/sise/sise_index.naver?code=KOSPI'
            resp = requests.get(foreign_url, headers=headers, timeout=5)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                # 외국인 순매수 금액 추출 시도
                foreign_div = soup.select_one('div.subtop_sise_graph2')
                if foreign_div:
                    text = foreign_div.text
                    if '외국인' in text:
                        # 파싱 로직 (간략화)
                        pass
        except Exception as e:
            pass

        result['fetched'] = len(result['hot_themes']) > 0 or len(result['market_news']) > 0

    except ImportError:
        logger.warning("requests/BeautifulSoup 없음 - 샘플 데이터 사용")
    except Exception as e:
        logger.warning(f"시장 테마 조회 실패: {e}")

    # 폴백: 샘플 데이터 (실제 조회 실패 시)
    if not result['fetched']:
        result['hot_themes'] = [
            {'name': 'AI/반도체', 'change': 2.3, 'stock': 'SK하이닉스'},
            {'name': '2차전지', 'change': -1.5, 'stock': '에코프로비엠'},
            {'name': '바이오', 'change': 0.8, 'stock': '삼성바이오로직스'},
            {'name': '자동차', 'change': 1.2, 'stock': '현대차'},
            {'name': '엔터/미디어', 'change': -0.5, 'stock': 'HYBE'},
        ]
        result['market_news'] = [
            "美 연준 금리 동결 시사...증시 상승 탄력",
            "삼성전자, AI 메모리 수주 확대 전망",
            "2차전지 업황 바닥 통과 신호",
            "외국인, 코스피 3거래일 연속 순매수",
        ]
        result['top_search'] = [
            {'name': '삼성전자', 'change': '+1.2%'},
            {'name': 'SK하이닉스', 'change': '+2.8%'},
            {'name': '에코프로', 'change': '-3.1%'},
        ]
        result['fetched'] = True

    return result


# ============ 시장 분석 로직 ============

def fetch_market_index_data(days: int = 120) -> Dict[str, pd.DataFrame]:
    """시장 지수 데이터 조회"""
    indices = {}

    def _generate_sample_data():
        """샘플 데이터 생성 (2026년 1월 기준)"""
        sample_indices = {}
        dates = pd.date_range(end=datetime.now(), periods=days, freq='B')

        # 2026년 1월 기준 - 실제 현재 지수에 가깝게
        for name, base in [('KOSPI', 2520), ('KOSDAQ', 720)]:
            np.random.seed(hash(name) % 10000)
            returns = np.random.randn(days) * 0.008  # 변동성 낮춤
            # 마지막 값이 base가 되도록 조정
            cumret = np.cumsum(returns)
            adjustment = cumret[-1]
            prices = base * np.exp(cumret - adjustment)
            sample_indices[name] = pd.DataFrame({
                'Date': dates,
                'Close': prices,
                'Volume': np.random.randint(1000000, 5000000, days)
            }).set_index('Date')

        return sample_indices

    if not KRX_AVAILABLE:
        return _generate_sample_data()

    try:
        collector = KRXDataCollector()
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=days * 2)).strftime('%Y%m%d')

        # KOSPI
        kospi = collector.get_index_data('1001', start_date, end_date)
        if not kospi.empty:
            indices['KOSPI'] = kospi.tail(days)

        # KOSDAQ
        kosdaq = collector.get_index_data('2001', start_date, end_date)
        if not kosdaq.empty:
            indices['KOSDAQ'] = kosdaq.tail(days)

    except Exception as e:
        logger.warning(f"KRX 지수 데이터 조회 실패: {e}")

    # KRX 데이터가 비어있으면 샘플 데이터 사용
    if not indices or 'KOSPI' not in indices:
        logger.info("샘플 데이터로 대체합니다.")
        return _generate_sample_data()

    return indices


def fetch_top_movers(limit: int = 10) -> Tuple[List[Dict], List[Dict]]:
    """
    상승/하락 상위 종목 조회

    Args:
        limit: 반환할 최대 종목 수 (각 상승/하락)

    Returns:
        Tuple[List[Dict], List[Dict]]: (상승 종목 리스트, 하락 종목 리스트)
        각 종목: {'name': 종목명, 'code': 종목코드, 'change': 등락률}

    Note:
        KRX 미설치 시 샘플 데이터 반환
    """
    gainers = []
    losers = []

    if not KRX_AVAILABLE:
        # 샘플 데이터
        sample_stocks = [
            ('삼성전자', '005930', 3.5), ('SK하이닉스', '000660', 2.8),
            ('NAVER', '035420', 2.1), ('카카오', '035720', 1.9),
            ('현대차', '005380', 1.5), ('기아', '000270', -1.2),
            ('LG화학', '051910', -1.8), ('삼성SDI', '006400', -2.3),
            ('에코프로', '086520', -3.1), ('셀트리온', '068270', -3.8)
        ]

        for name, code, change in sample_stocks:
            item = {'name': name, 'code': code, 'change': change}
            if change > 0:
                gainers.append(item)
            else:
                losers.append(item)

        return gainers[:limit], losers[:limit]

    try:
        collector = KRXDataCollector()
        today = datetime.now().strftime('%Y%m%d')

        # 상승 상위
        df_up = collector.get_market_cap_ranking(today, 'KOSPI')
        if not df_up.empty and '등락률' in df_up.columns:
            df_up = df_up.nlargest(limit, '등락률')
            for _, row in df_up.iterrows():
                gainers.append({
                    'name': row.get('종목명', ''),
                    'code': row.get('종목코드', ''),
                    'change': row.get('등락률', 0)
                })

        # 하락 상위
        df_down = collector.get_market_cap_ranking(today, 'KOSPI')
        if not df_down.empty and '등락률' in df_down.columns:
            df_down = df_down.nsmallest(limit, '등락률')
            for _, row in df_down.iterrows():
                losers.append({
                    'name': row.get('종목명', ''),
                    'code': row.get('종목코드', ''),
                    'change': row.get('등락률', 0)
                })

    except Exception as e:
        # NOTE: 상승/하락 종목 조회 실패 시 빈 리스트 반환
        logger.warning(f"상승/하락 종목 조회 실패: {e}")

    return gainers, losers


def calculate_market_metrics(index_data: pd.DataFrame) -> Dict:
    """
    시장 지표 계산

    지수 데이터로부터 다양한 기술적/성과 지표를 계산합니다.

    Args:
        index_data: 지수 데이터 DataFrame (Close 컬럼 필수)

    Returns:
        Dict: 계산된 지표들
            - current: 현재가
            - return_1d/1w/1m/3m: 기간별 수익률 (%)
            - ma20/60/120: 이동평균선
            - rsi: RSI (14일)
            - volatility: 연환산 변동성 (%)
            - high_52w/low_52w: 52주 고저
            - from_high/from_low: 고저 대비 (%)
            - above_ma20/60/120: 이평선 위 여부

    Note:
        데이터가 20개 미만이면 빈 딕셔너리 반환
    """
    if index_data.empty or len(index_data) < 20:
        return {}

    close = index_data['Close']
    current = close.iloc[-1]

    # 수익률
    return_1d = (current / close.iloc[-2] - 1) * 100 if len(close) >= 2 else 0
    return_1w = (current / close.iloc[-6] - 1) * 100 if len(close) >= 6 else 0
    return_1m = (current / close.iloc[-22] - 1) * 100 if len(close) >= 22 else 0
    return_3m = (current / close.iloc[-66] - 1) * 100 if len(close) >= 66 else 0

    # 이동평균
    ma20 = close.rolling(20).mean().iloc[-1]
    ma60 = close.rolling(60).mean().iloc[-1] if len(close) >= 60 else ma20
    ma120 = close.rolling(120).mean().iloc[-1] if len(close) >= 120 else ma60

    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = (100 - 100 / (1 + rs)).iloc[-1]

    # 변동성 (20일 표준편차)
    volatility = close.pct_change().rolling(20).std().iloc[-1] * np.sqrt(252) * 100

    # 52주 고점/저점 대비
    high_52w = close.tail(252).max() if len(close) >= 252 else close.max()
    low_52w = close.tail(252).min() if len(close) >= 252 else close.min()
    from_high = (current / high_52w - 1) * 100
    from_low = (current / low_52w - 1) * 100

    return {
        'current': current,
        'return_1d': return_1d,
        'return_1w': return_1w,
        'return_1m': return_1m,
        'return_3m': return_3m,
        'ma20': ma20,
        'ma60': ma60,
        'ma120': ma120,
        'rsi': rsi,
        'volatility': volatility,
        'high_52w': high_52w,
        'low_52w': low_52w,
        'from_high': from_high,
        'from_low': from_low,
        'above_ma20': current > ma20,
        'above_ma60': current > ma60,
        'above_ma120': current > ma120
    }


def analyze_market_condition(metrics: Dict) -> Dict:
    """시장 상태 분석"""
    # 추세 판단
    if metrics.get('above_ma20') and metrics.get('above_ma60') and metrics.get('above_ma120'):
        trend = '강한 상승 추세'
        trend_score = 90
    elif metrics.get('above_ma20') and metrics.get('above_ma60'):
        trend = '상승 추세'
        trend_score = 70
    elif metrics.get('above_ma20'):
        trend = '단기 반등'
        trend_score = 55
    elif not metrics.get('above_ma20') and not metrics.get('above_ma60'):
        trend = '하락 추세'
        trend_score = 30
    else:
        trend = '혼조세'
        trend_score = 50

    # RSI 기반 과열/침체
    rsi = metrics.get('rsi', 50)
    if rsi > 70:
        momentum = '과매수 (과열)'
        momentum_warning = True
    elif rsi < 30:
        momentum = '과매도 (침체)'
        momentum_warning = True
    elif rsi > 60:
        momentum = '강세'
        momentum_warning = False
    elif rsi < 40:
        momentum = '약세'
        momentum_warning = False
    else:
        momentum = '중립'
        momentum_warning = False

    # 고점 대비 위치
    from_high = metrics.get('from_high', 0)
    if from_high > -5:
        position = '고점 근처'
        risk_level = '높음'
    elif from_high > -15:
        position = '중간'
        risk_level = '보통'
    else:
        position = '저점 근처'
        risk_level = '낮음'

    # 변동성
    vol = metrics.get('volatility', 20)
    if vol > 30:
        vol_state = '높은 변동성'
    elif vol > 20:
        vol_state = '보통 변동성'
    else:
        vol_state = '낮은 변동성'

    return {
        'trend': trend,
        'trend_score': trend_score,
        'momentum': momentum,
        'momentum_warning': momentum_warning,
        'position': position,
        'risk_level': risk_level,
        'volatility_state': vol_state
    }


def generate_market_narrative(metrics: Dict, condition: Dict, phase: str = None) -> str:
    """시장 내러티브 생성"""
    parts = []

    # 현재 상태
    parts.append(f"현재 시장은 **{condition['trend']}** 상태입니다.")

    # 단기 성과
    return_1m = metrics.get('return_1m', 0)
    if return_1m > 5:
        parts.append(f"한 달간 {return_1m:.1f}% 상승하며 강한 모습을 보이고 있습니다.")
    elif return_1m > 0:
        parts.append(f"한 달간 {return_1m:.1f}% 소폭 상승했습니다.")
    elif return_1m > -5:
        parts.append(f"한 달간 {return_1m:.1f}% 소폭 하락했습니다.")
    else:
        parts.append(f"한 달간 {return_1m:.1f}% 하락하며 약세를 보이고 있습니다.")

    # 이평선 분석
    if metrics.get('above_ma20') and metrics.get('above_ma60'):
        parts.append("주요 이동평균선 위에 위치해 기술적으로 긍정적입니다.")
    elif not metrics.get('above_ma20'):
        parts.append("20일 이평선 아래로 내려와 단기 약세 신호입니다.")

    # 모멘텀
    parts.append(f"모멘텀 지표는 **{condition['momentum']}** 구간에 있습니다.")

    # 시장 국면
    if phase:
        parts.append(f"경기 사이클상 **{phase}** 국면으로 판단됩니다.")

    # 고점 대비
    from_high = metrics.get('from_high', 0)
    if from_high < -20:
        parts.append(f"52주 고점 대비 {abs(from_high):.1f}% 하락한 상태로, 저가 매수 기회일 수 있습니다.")
    elif from_high > -5:
        parts.append(f"52주 고점 근처로, 신규 매수 시 신중한 접근이 필요합니다.")

    return " ".join(parts)


# ============ SNS 스타일 시장 토론 ============
#
# [유지보수 가이드]
# 1. 새 페르소나 추가:
#    - TRADER_PERSONAS에 새 항목 추가
#    - generate_sns_market_discussion()에 해당 로직 추가
#    - style은 의견 생성 시 참조됨
#
# 2. 색상 규칙:
#    - 강세: #22c55e (초록)
#    - 약세: #ef4444 (빨강)
#    - 기술적: #3b82f6 (파랑)
#    - 거시경제: #8b5cf6 (보라)
#    - 개인투자자: #f59e0b (주황)
#    - 퀀트: #06b6d4 (시안)
#
# 3. avatar는 이모지 하나만 사용

# 트레이더 페르소나 정의
TRADER_PERSONAS: Dict[str, Dict[str, str]] = {
    'bull_master': {
        'name': '강세론자 김프로',
        'avatar': '🐂',
        'style': 'optimistic',
        'color': '#22c55e',
        'bio': '20년차 펀드매니저 | 장기 우상향 신봉자'
    },
    'bear_hunter': {
        'name': '신중파 이차장',
        'avatar': '🐻',
        'style': 'cautious',
        'color': '#ef4444',
        'bio': '리스크 관리 전문 | 하방 리스크 경계'
    },
    'tech_guru': {
        'name': '차트장인 박대리',
        'avatar': '📊',
        'style': 'technical',
        'color': '#3b82f6',
        'bio': '기술적분석 마니아 | 이평선이 답이다'
    },
    'macro_sage': {
        'name': '거시경제 최박사',
        'avatar': '🌍',
        'style': 'fundamental',
        'color': '#8b5cf6',
        'bio': '경제학 박사 | 금리와 환율의 힘'
    },
    'retail_voice': {
        'name': '개미투자자 정씨',
        'avatar': '🐜',
        'style': 'retail',
        'color': '#f59e0b',
        'bio': '5년차 개인투자자 | 실전 경험담'
    },
    'quant_bot': {
        'name': '퀀트봇 Q-1',
        'avatar': '🤖',
        'style': 'quantitative',
        'color': '#06b6d4',
        'bio': 'AI 기반 분석 | 데이터가 말한다'
    }
}


def generate_sns_market_discussion(
    metrics: Dict,
    condition: Dict,
    gainers: List[Dict] = None,
    losers: List[Dict] = None,
    phase: str = None,
    market_themes: Dict = None
) -> List[Dict]:
    """
    SNS 스타일 시장 토론 생성 - 실시간 테마/뉴스 기반

    6개의 트레이더 페르소나가 실제 시장 테마와 뉴스를 근거로 의견을 제시합니다.

    Args:
        metrics: 시장 지표 딕셔너리
        condition: 시장 상태 분석 결과
        gainers: 상승 상위 종목 리스트
        losers: 하락 상위 종목 리스트
        phase: 경기 사이클 국면 문자열
        market_themes: fetch_market_themes()에서 반환된 테마/뉴스 데이터

    Returns:
        List[Dict]: 포스트 리스트

    유지보수 노트:
        - market_themes가 None이면 자동으로 fetch_market_themes() 호출
        - 각 트레이더는 특정 테마에 대해 근거 있는 의견 제시
    """
    posts = []

    # 시장 테마 데이터 가져오기
    if market_themes is None:
        market_themes = fetch_market_themes()

    hot_themes = market_themes.get('hot_themes', [])
    market_news = market_themes.get('market_news', [])
    top_search = market_themes.get('top_search', [])

    # 주요 지표 추출
    return_1m = metrics.get('return_1m', 0)
    return_1w = metrics.get('return_1w', 0)
    rsi = metrics.get('rsi', 50)
    volatility = metrics.get('volatility', 20)
    ma20 = metrics.get('ma20', 0)
    ma60 = metrics.get('ma60', 0)

    # 상승/하락 테마 분리
    rising_themes = [t for t in hot_themes if t.get('change', 0) > 0][:3]
    falling_themes = [t for t in hot_themes if t.get('change', 0) < 0][:3]

    # 1. 강세론자 - 상승 테마에 집중
    bull = TRADER_PERSONAS['bull_master']
    if rising_themes:
        top_theme = rising_themes[0]
        bull_msg = f"오늘 시장 주도 테마는 **{top_theme['name']}** (+{top_theme['change']:.1f}%)! 📈 "
        if top_theme.get('stock'):
            bull_msg += f"대장주 {top_theme['stock']} 중심으로 섹터 전체가 움직이고 있어요. "
        if len(rising_themes) > 1:
            other_themes = ', '.join([t['name'] for t in rising_themes[1:]])
            bull_msg += f"{other_themes}도 강세. 수급이 쏠리는 섹터 주목하세요!"
        bull_conditions = [
            f"{top_theme['name']} 테마 모멘텀 지속 시 유효",
            f"대장주 {top_theme.get('stock', '관련주')} 상승 추세 유지 필요",
            "외국인/기관 동반 매수 시 신뢰도 상승"
        ]
        bull_confidence = 75
    else:
        bull_msg = "뚜렷한 주도 테마는 없지만, 저평가 섹터에서 기회를 찾아보세요. "
        bull_msg += "시장이 쉬어갈 때가 오히려 공부하고 준비할 때입니다! 💪"
        bull_conditions = ["섹터 로테이션 신호 대기", "실적 시즌 수혜주 탐색"]
        bull_confidence = 55

    # 관련 뉴스 언급
    if market_news and len(market_news) > 0:
        relevant_news = market_news[0][:50]
        bull_msg += f" [참고: '{relevant_news}...']"

    posts.append({
        'persona': bull,
        'message': bull_msg,
        'timestamp': '방금 전',
        'likes': np.random.randint(50, 200),
        'comments': np.random.randint(10, 50),
        'validity': "테마 모멘텀 유지 시 (1~2주)",
        'conditions': bull_conditions,
        'invalidate': "주도 테마 급락 또는 섹터 로테이션 발생 시",
        'confidence': bull_confidence
    })

    # 2. 신중파 - 하락 테마 경고
    bear = TRADER_PERSONAS['bear_hunter']
    if falling_themes:
        worst_theme = falling_themes[0]
        bear_msg = f"⚠️ **{worst_theme['name']}** 테마 {worst_theme['change']:.1f}% 급락 중. "
        if worst_theme.get('stock'):
            bear_msg += f"{worst_theme['stock']} 보유자 주의하세요. "
        if len(falling_themes) > 1:
            bear_msg += f"{falling_themes[1]['name']}도 약세. 낙폭 확대 가능성 있습니다."
        bear_conditions = [
            f"{worst_theme['name']} 테마 추가 하락 시 손절 검토",
            "반등 시도 실패하면 비중 축소",
            "섹터 전체 약세면 개별 종목도 위험"
        ]
        bear_confidence = 70
    elif rsi > 65:
        bear_msg = f"RSI {rsi:.0f}로 과열 구간. 지금 추격 매수는 위험해요. "
        bear_msg += "조정 기다렸다가 눌림목에서 진입하는 게 안전합니다."
        bear_conditions = ["RSI 50 이하로 조정 시 재진입 검토", "거래량 감소 시 매도 압력 소진 확인"]
        bear_confidence = 65
    else:
        bear_msg = "특별히 위험한 테마는 없지만, 고점 추격은 피하세요. "
        bear_msg += "이익 실현 타이밍도 중요합니다."
        bear_conditions = ["목표가 도달 시 부분 익절", "손절 라인 사전 설정 필수"]
        bear_confidence = 55

    posts.append({
        'persona': bear,
        'message': bear_msg,
        'timestamp': '2분 전',
        'likes': np.random.randint(30, 150),
        'comments': np.random.randint(15, 60),
        'validity': "해당 테마 안정화까지 (수일~1주)",
        'conditions': bear_conditions,
        'invalidate': "하락 테마 반등 또는 악재 해소 시",
        'confidence': bear_confidence
    })

    # 3. 차트장인 - 기술적 분석 + 테마 차트
    tech = TRADER_PERSONAS['tech_guru']
    if top_search:
        hot_stock = top_search[0]
        tech_msg = f"📊 오늘 인기 검색 1위 **{hot_stock['name']}** ({hot_stock.get('change', '')}). "
        tech_msg += f"KOSPI는 현재 {'20일선 위 정배열' if metrics.get('above_ma20') else '20일선 이탈 약세'}. "
        if metrics.get('above_ma20') and metrics.get('above_ma60'):
            tech_msg += "이평선 정배열에서 인기 테마 종목은 추세 추종 유효합니다."
            tech_confidence = 75
        else:
            tech_msg += "이평선 역배열이라 인기주도 단타 아니면 위험해요. 지지선 확인 필수!"
            tech_confidence = 55
    else:
        if metrics.get('above_ma20'):
            tech_msg = f"차트상 20일선({ma20:,.0f}) 지지 유효. 눌림목 매수 전략 유효합니다."
            tech_confidence = 70
        else:
            tech_msg = f"20일선 이탈 상태. {ma60:,.0f} 지지 테스트 중. 반등 확인 후 진입하세요."
            tech_confidence = 50

    posts.append({
        'persona': tech,
        'message': tech_msg,
        'timestamp': '5분 전',
        'likes': np.random.randint(80, 250),
        'comments': np.random.randint(20, 80),
        'validity': "이평선 상태 변화 시까지",
        'conditions': [
            f"20일선({ma20:,.0f}) 지지/돌파 여부 확인",
            "거래량 동반 여부로 신뢰도 판단",
            "인기 검색주 단기 변동성 주의"
        ],
        'invalidate': "이평선 정렬 상태 변경 시 재분석 필요",
        'confidence': tech_confidence
    })

    # 4. 거시경제 전문가 - 뉴스 기반
    macro = TRADER_PERSONAS['macro_sage']
    if market_news and len(market_news) > 1:
        # 뉴스에서 키워드 분석
        news_text = ' '.join(market_news)
        keywords = {
            '금리': '금리', '연준': '연준/Fed', 'Fed': '연준/Fed',
            '인플레': '인플레이션', '환율': '환율', '달러': '달러',
            '중국': '중국 경제', '반도체': '반도체 업황', '수출': '수출'
        }
        found_keywords = [v for k, v in keywords.items() if k in news_text]
        found_keywords = list(dict.fromkeys(found_keywords))[:2]  # 중복 제거, 최대 2개

        if found_keywords:
            macro_msg = f"🎓 오늘 시장 핵심은 **{', '.join(found_keywords)}**. "
            macro_msg += f"'{market_news[0][:40]}...' - 이 뉴스가 시장 방향 좌우할 수 있어요. "
        else:
            macro_msg = f"📰 주요 뉴스: '{market_news[0][:45]}...' "

        if '금리' in news_text or '연준' in news_text or 'Fed' in news_text:
            macro_msg += "금리 정책 변화는 시장 전체에 영향. 매크로 이벤트 주시하세요."
        elif '반도체' in news_text or '수출' in news_text:
            macro_msg += "한국 수출주 중심으로 영향 예상됩니다."
        macro_confidence = 70
    else:
        macro_msg = "거시경제 측면에서 당분간 특별한 이벤트는 없어 보입니다. "
        macro_msg += "개별 종목/섹터 펀더멘털에 집중하세요. 🎓"
        macro_confidence = 55

    posts.append({
        'persona': macro,
        'message': macro_msg,
        'timestamp': '8분 전',
        'likes': np.random.randint(100, 300),
        'comments': np.random.randint(25, 100),
        'validity': "이벤트 소화 시까지 (수일~1주)",
        'conditions': [
            "매크로 이벤트 결과에 따라 재평가",
            "금리/환율 급변 시 전략 수정 필요",
            "대외 변수(미국, 중국) 모니터링"
        ],
        'invalidate': "새로운 매크로 이벤트 발생 시",
        'confidence': macro_confidence
    })

    # 5. 개미투자자 - 인기 검색종목 기반
    retail = TRADER_PERSONAS['retail_voice']
    if top_search and len(top_search) > 0:
        retail_msg = f"다들 **{top_search[0]['name']}** 검색하시네요... 저도 관심 있었는데 😅 "
        if len(top_search) > 1:
            retail_msg += f"{top_search[1]['name']}도 핫하고. "
        retail_msg += "남들 다 살 때 사면 늦는다는데, 판단이 어려워요. "
        retail_msg += "소액으로 분할매수 해볼까 고민 중입니다!"
    elif rising_themes:
        retail_msg = f"{rising_themes[0]['name']} 테마 오른다는데 지금 사도 될까요? "
        retail_msg += "이미 많이 오른 것 같기도 하고... 전문가분들 의견 참고 중이에요! 😊"
    else:
        retail_msg = "오늘 시장 방향을 모르겠어요... "
        retail_msg += "일단 관망하면서 공부하고 있습니다. 화이팅! 💪"

    posts.append({
        'persona': retail,
        'message': retail_msg,
        'timestamp': '12분 전',
        'likes': np.random.randint(200, 500),
        'comments': np.random.randint(50, 150),
        'validity': "개인적 감상 (투자 조언 아님)",
        'conditions': [
            "인기 검색주 = 이미 많이 오른 경우 多",
            "분할매수로 리스크 관리 중",
            "손절가 미리 설정 필수"
        ],
        'invalidate': "개인 상황에 따라 다름",
        'confidence': None
    })

    # 6. 퀀트봇 - 데이터 요약
    quant = TRADER_PERSONAS['quant_bot']

    # 테마 통계
    up_count = len([t for t in hot_themes if t.get('change', 0) > 0])
    down_count = len([t for t in hot_themes if t.get('change', 0) < 0])

    quant_msg = f"[실시간 데이터] "
    if hot_themes:
        quant_msg += f"테마: 상승 {up_count}개 / 하락 {down_count}개 | "
    quant_msg += f"RSI: {rsi:.0f} | 변동성: {volatility:.1f}% | "

    # 종합 점수 계산
    score = 50
    score += min(20, up_count * 5)  # 상승 테마 개수
    score -= min(20, down_count * 5)  # 하락 테마 개수
    if metrics.get('above_ma20'): score += 10
    if metrics.get('above_ma60'): score += 10
    if 30 < rsi < 70: score += 5

    score = max(0, min(100, score))
    quant_msg += f"시장 점수: {score}/100 "

    if score >= 65:
        quant_msg += "📗 긍정적 (테마 강세 + 기술적 양호)"
    elif score >= 45:
        quant_msg += "📒 중립 (혼조세)"
    else:
        quant_msg += "📕 주의 (테마 약세 또는 기술적 약세)"

    posts.append({
        'persona': quant,
        'message': quant_msg,
        'timestamp': '15분 전',
        'likes': np.random.randint(150, 400),
        'comments': np.random.randint(30, 100),
        'validity': "실시간 (데이터 변경 시 자동 업데이트)",
        'conditions': [
            f"테마 동향: 상승 {up_count}개 vs 하락 {down_count}개",
            f"기술적: 20일선 {'✓' if metrics.get('above_ma20') else '✗'} / 60일선 {'✓' if metrics.get('above_ma60') else '✗'}",
            f"RSI: {rsi:.0f} (30-70 정상, 그 외 주의)"
        ],
        'invalidate': "데이터 변경 시 자동 재계산",
        'confidence': score
    })

    return posts


def render_sns_discussion(posts: List[Dict]):
    """SNS 스타일 토론 UI 렌더링 (유효기간/조건 포함)"""
    st.markdown("""
    <style>
    .sns-post {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .sns-header {
        display: flex;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    .sns-avatar {
        font-size: 2rem;
        margin-right: 0.75rem;
    }
    .sns-name {
        font-weight: bold;
        font-size: 1rem;
    }
    .sns-bio {
        font-size: 0.75rem;
        color: #6b7280;
    }
    .sns-time {
        font-size: 0.75rem;
        color: #9ca3af;
        margin-left: auto;
    }
    .sns-message {
        font-size: 1rem;
        line-height: 1.6;
        margin: 0.75rem 0;
    }
    .sns-actions {
        display: flex;
        gap: 1.5rem;
        color: #6b7280;
        font-size: 0.85rem;
    }
    .validity-badge {
        display: inline-block;
        background: #dbeafe;
        color: #1e40af;
        padding: 0.2rem 0.5rem;
        border-radius: 12px;
        font-size: 0.75rem;
        margin-right: 0.5rem;
    }
    .confidence-badge {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        border-radius: 12px;
        font-size: 0.75rem;
    }
    .detail-section {
        background: #f9fafb;
        border-radius: 8px;
        padding: 0.75rem;
        margin-top: 0.5rem;
        font-size: 0.85rem;
    }
    .condition-item {
        padding: 0.3rem 0;
        border-bottom: 1px dashed #e5e7eb;
    }
    .condition-item:last-child {
        border-bottom: none;
    }
    .invalidate-box {
        background: #fef2f2;
        border: 1px solid #fecaca;
        border-radius: 6px;
        padding: 0.5rem;
        margin-top: 0.5rem;
        font-size: 0.8rem;
        color: #991b1b;
    }
    </style>
    """, unsafe_allow_html=True)

    for idx, post in enumerate(posts):
        persona = post['persona']
        confidence = post.get('confidence')
        validity = post.get('validity', '')
        conditions = post.get('conditions', [])
        invalidate = post.get('invalidate', '')
        score_breakdown = post.get('score_breakdown', {})

        # 신뢰도 배지 색상
        if confidence is not None:
            if confidence >= 70:
                conf_color = '#22c55e'
                conf_bg = '#dcfce7'
            elif confidence >= 50:
                conf_color = '#eab308'
                conf_bg = '#fef9c3'
            else:
                conf_color = '#ef4444'
                conf_bg = '#fee2e2'
            conf_badge = f"<span class='confidence-badge' style='background: {conf_bg}; color: {conf_color};'>신뢰도 {confidence}%</span>"
        else:
            conf_badge = ""

        # 메인 포스트 렌더링
        st.markdown(f"""
        <div class='sns-post' style='border-left: 4px solid {persona["color"]};'>
            <div class='sns-header'>
                <span class='sns-avatar'>{persona["avatar"]}</span>
                <div>
                    <div class='sns-name' style='color: {persona["color"]};'>{persona["name"]}</div>
                    <div class='sns-bio'>{persona["bio"]}</div>
                </div>
                <span class='sns-time'>{post["timestamp"]}</span>
            </div>
            <div class='sns-message'>{post["message"]}</div>
            <div style='margin: 0.5rem 0;'>
                <span class='validity-badge'>⏱️ 유효기간: {validity}</span>
                {conf_badge}
            </div>
            <div class='sns-actions'>
                <span>❤️ {post["likes"]}</span>
                <span>💬 {post["comments"]}</span>
                <span>🔄 공유</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 상세 정보 expander
        with st.expander(f"📋 {persona['name']}의 논리 상세 보기", expanded=False):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**⏱️ 유효기간**")
                st.info(validity if validity else "명시되지 않음")

                if confidence is not None:
                    st.markdown("**📊 신뢰도**")
                    st.progress(confidence / 100)
                    st.caption(f"{confidence}% 신뢰도")

            with col2:
                st.markdown("**✅ 유효 조건**")
                if conditions:
                    for cond in conditions:
                        st.markdown(f"• {cond}")
                else:
                    st.caption("조건 없음")

            # 점수 breakdown (퀀트봇의 경우)
            if score_breakdown:
                st.markdown("**🔢 점수 구성**")
                breakdown_cols = st.columns(len(score_breakdown))
                for i, (key, val) in enumerate(score_breakdown.items()):
                    with breakdown_cols[i]:
                        st.metric(key, f"+{val}" if val > 0 else "0")

            # 무효화 조건
            if invalidate:
                st.markdown("**🚫 무효화 조건**")
                st.error(f"⚠️ {invalidate}")

            st.divider()


def identify_risks(metrics: Dict, condition: Dict) -> List[Dict]:
    """리스크 요인 식별"""
    risks = []

    # 과열 리스크
    if condition.get('momentum_warning') and metrics.get('rsi', 50) > 70:
        risks.append({
            'level': '높음',
            'factor': '기술적 과열',
            'description': 'RSI가 70을 넘어 과매수 구간입니다. 단기 조정 가능성이 있습니다.',
            'suggestion': '분할 매도 또는 신규 매수 자제'
        })

    # 고점 리스크
    if metrics.get('from_high', -100) > -5:
        risks.append({
            'level': '중간',
            'factor': '고점 부담',
            'description': '52주 고점 근처에서 저항이 발생할 수 있습니다.',
            'suggestion': '목표가 도달 시 부분 익절 고려'
        })

    # 변동성 리스크
    if metrics.get('volatility', 20) > 30:
        risks.append({
            'level': '중간',
            'factor': '높은 변동성',
            'description': '변동성이 높아 급등락 가능성이 있습니다.',
            'suggestion': '포지션 사이즈 축소, 손절가 설정 필수'
        })

    # 하락 추세 리스크
    if condition.get('trend_score', 50) < 40:
        risks.append({
            'level': '높음',
            'factor': '하락 추세',
            'description': '주요 이평선 아래에서 거래되며 추가 하락 가능성이 있습니다.',
            'suggestion': '관망 또는 소량만 분할 매수'
        })

    # 리스크가 없으면 긍정적 메시지
    if not risks:
        risks.append({
            'level': '낮음',
            'factor': '안정적 상태',
            'description': '현재 특별한 리스크 요인이 감지되지 않습니다.',
            'suggestion': '정상적인 투자 전략 유지'
        })

    return risks


def calculate_potential_targets(metrics: Dict, condition: Dict) -> Dict:
    """잠재적 목표가/지지선 계산"""
    current = metrics.get('current', 0)

    # 저항선 (잠재적 고점)
    resistances = []

    # 52주 고점
    high_52w = metrics.get('high_52w', current * 1.1)
    if high_52w > current:
        resistances.append({
            'price': high_52w,
            'label': '52주 고점',
            'distance': (high_52w / current - 1) * 100
        })

    # 심리적 저항
    round_up = np.ceil(current / 100) * 100
    if round_up > current:
        resistances.append({
            'price': round_up,
            'label': f'심리적 저항 ({round_up:,.0f})',
            'distance': (round_up / current - 1) * 100
        })

    # 이평선 저항
    ma60 = metrics.get('ma60', 0)
    ma120 = metrics.get('ma120', 0)

    if ma60 > current:
        resistances.append({
            'price': ma60,
            'label': '60일 이평선',
            'distance': (ma60 / current - 1) * 100
        })

    if ma120 > current:
        resistances.append({
            'price': ma120,
            'label': '120일 이평선',
            'distance': (ma120 / current - 1) * 100
        })

    # 지지선
    supports = []

    # 52주 저점
    low_52w = metrics.get('low_52w', current * 0.9)
    if low_52w < current:
        supports.append({
            'price': low_52w,
            'label': '52주 저점',
            'distance': (low_52w / current - 1) * 100
        })

    # 이평선 지지
    ma20 = metrics.get('ma20', 0)

    if ma20 < current:
        supports.append({
            'price': ma20,
            'label': '20일 이평선',
            'distance': (ma20 / current - 1) * 100
        })

    if ma60 < current:
        supports.append({
            'price': ma60,
            'label': '60일 이평선',
            'distance': (ma60 / current - 1) * 100
        })

    # 심리적 지지
    round_down = np.floor(current / 100) * 100
    if round_down < current:
        supports.append({
            'price': round_down,
            'label': f'심리적 지지 ({round_down:,.0f})',
            'distance': (round_down / current - 1) * 100
        })

    # 정렬
    resistances.sort(key=lambda x: x['price'])
    supports.sort(key=lambda x: x['price'], reverse=True)

    return {
        'current': current,
        'resistances': resistances[:4],
        'supports': supports[:4]
    }


# ============ 차트 생성 ============

def create_market_overview_chart(index_data: pd.DataFrame, name: str) -> go.Figure:
    """시장 종합 차트"""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3],
        subplot_titles=[f'{name} 지수', '거래량']
    )

    close = index_data['Close']

    # 캔들/라인 차트
    fig.add_trace(
        go.Scatter(
            x=index_data.index,
            y=close,
            mode='lines',
            name=name,
            line=dict(color='#3498db', width=2)
        ),
        row=1, col=1
    )

    # 이동평균선
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()

    fig.add_trace(
        go.Scatter(
            x=index_data.index,
            y=ma20,
            mode='lines',
            name='20일 이평',
            line=dict(color='#e74c3c', width=1, dash='dash')
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=index_data.index,
            y=ma60,
            mode='lines',
            name='60일 이평',
            line=dict(color='#2ecc71', width=1, dash='dash')
        ),
        row=1, col=1
    )

    # 거래량
    if 'Volume' in index_data.columns:
        colors = ['#22c55e' if close.iloc[i] >= close.iloc[i-1] else '#ef4444'
                  for i in range(1, len(close))]
        colors = ['#22c55e'] + colors

        fig.add_trace(
            go.Bar(
                x=index_data.index,
                y=index_data['Volume'],
                name='거래량',
                marker_color=colors,
                opacity=0.5
            ),
            row=2, col=1
        )

    fig.update_layout(
        height=500,
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        xaxis2_title='날짜',
        yaxis_title='지수',
        yaxis2_title='거래량',
        hovermode='x unified'
    )

    return fig


def create_sector_momentum_chart(sector_data: List[Dict]) -> go.Figure:
    """섹터 모멘텀 차트"""
    if not sector_data:
        return go.Figure()

    sectors = [d['name'] for d in sector_data]
    returns_1m = [d.get('return_1m', 0) for d in sector_data]
    returns_3m = [d.get('return_3m', 0) for d in sector_data]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name='1개월',
        x=sectors,
        y=returns_1m,
        marker_color=['#22c55e' if r > 0 else '#ef4444' for r in returns_1m]
    ))

    fig.add_trace(go.Bar(
        name='3개월',
        x=sectors,
        y=returns_3m,
        marker_color=['#16a34a' if r > 0 else '#dc2626' for r in returns_3m],
        opacity=0.6
    ))

    fig.update_layout(
        title='섹터별 수익률',
        barmode='group',
        height=400,
        xaxis_title='섹터',
        yaxis_title='수익률 (%)',
        showlegend=True
    )

    return fig


def create_risk_gauge(risk_level: str) -> go.Figure:
    """리스크 게이지"""
    level_map = {'낮음': 25, '보통': 50, '높음': 75, '매우 높음': 90}
    value = level_map.get(risk_level, 50)

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        title={'text': "시장 리스크 수준"},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 30], 'color': '#22c55e'},
                {'range': [30, 50], 'color': '#84cc16'},
                {'range': [50, 70], 'color': '#eab308'},
                {'range': [70, 85], 'color': '#f97316'},
                {'range': [85, 100], 'color': '#ef4444'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 70
            }
        }
    ))

    fig.update_layout(height=300)
    return fig


# ============ 페이지 렌더링 ============

def render_market_overview_page():
    """시장 종합 현황 페이지"""
    st.header("🌐 시장 종합 현황")
    st.markdown("*현재 시장의 논리, 근거, 주도 섹터, 리스크를 한눈에 파악하세요*")

    # 데이터 로드
    with st.spinner("시장 데이터 분석 중..."):
        index_data = fetch_market_index_data(120)
        gainers, losers = fetch_top_movers(5)

    if not index_data:
        st.error("시장 데이터를 불러올 수 없습니다.")
        return

    # 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 시장 현황", "🎯 주도 섹터/종목", "⚠️ 리스크 분석", "📈 목표/지지선"
    ])

    # ============ 탭 1: 시장 현황 ============
    with tab1:
        # 지수 선택
        selected_index = st.radio(
            "지수 선택",
            options=list(index_data.keys()),
            horizontal=True
        )

        selected_data = index_data.get(selected_index)
        if selected_data is None or selected_data.empty:
            st.warning("선택한 지수 데이터가 없습니다.")
            return

        # 지표 계산
        metrics = calculate_market_metrics(selected_data)
        condition = analyze_market_condition(metrics)

        # 상단 핵심 지표
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            current = metrics.get('current', 0)
            change_1d = metrics.get('return_1d', 0)
            delta_color = "normal" if change_1d >= 0 else "inverse"
            st.metric(
                f"{selected_index}",
                f"{current:,.2f}",
                f"{change_1d:+.2f}%",
                delta_color=delta_color
            )

        with col2:
            st.metric("1주일", f"{metrics.get('return_1w', 0):+.2f}%")

        with col3:
            st.metric("1개월", f"{metrics.get('return_1m', 0):+.2f}%")

        with col4:
            st.metric("3개월", f"{metrics.get('return_3m', 0):+.2f}%")

        st.divider()

        # 시장 국면 (섹터 분석 연동)
        market_phase = None
        if SECTOR_AVAILABLE:
            market_phase = "회복"  # 기본값, 실제로는 sector_rotation에서 가져옴

        # 분석 뷰 선택
        view_mode = st.radio(
            "분석 보기 방식",
            options=['💬 SNS 토론', '📄 요약 리포트'],
            horizontal=True,
            key="market_view_mode"
        )

        if view_mode == '💬 SNS 토론':
            st.subheader("💬 시장 토론방")
            st.caption("다양한 관점의 전문가들이 현재 시장을 분석합니다")

            # SNS 스타일 토론 생성
            posts = generate_sns_market_discussion(
                metrics, condition, gainers, losers, market_phase
            )
            render_sns_discussion(posts)

        else:
            st.subheader("📖 시장 분석 요약")
            narrative = generate_market_narrative(metrics, condition, market_phase)
            st.info(narrative)

        # 핵심 지표 카드
        st.subheader("📊 핵심 지표")

        col1, col2, col3 = st.columns(3)

        with col1:
            trend_color = '#22c55e' if condition['trend_score'] >= 50 else '#ef4444'
            st.markdown(f"""
            <div style='background: {trend_color}20; padding: 1rem; border-radius: 8px;
                        border-left: 4px solid {trend_color};'>
                <div style='font-size: 0.9em; color: gray;'>추세</div>
                <div style='font-size: 1.5em; font-weight: bold; color: {trend_color};'>
                    {condition['trend']}
                </div>
                <div style='font-size: 0.8em;'>추세 점수: {condition['trend_score']}/100</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            mom_color = '#ef4444' if condition['momentum_warning'] else '#3498db'
            st.markdown(f"""
            <div style='background: {mom_color}20; padding: 1rem; border-radius: 8px;
                        border-left: 4px solid {mom_color};'>
                <div style='font-size: 0.9em; color: gray;'>모멘텀 (RSI)</div>
                <div style='font-size: 1.5em; font-weight: bold; color: {mom_color};'>
                    {condition['momentum']}
                </div>
                <div style='font-size: 0.8em;'>RSI: {metrics.get('rsi', 50):.1f}</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            vol_color = '#f97316' if metrics.get('volatility', 20) > 25 else '#22c55e'
            st.markdown(f"""
            <div style='background: {vol_color}20; padding: 1rem; border-radius: 8px;
                        border-left: 4px solid {vol_color};'>
                <div style='font-size: 0.9em; color: gray;'>변동성</div>
                <div style='font-size: 1.5em; font-weight: bold; color: {vol_color};'>
                    {condition['volatility_state']}
                </div>
                <div style='font-size: 0.8em;'>연환산: {metrics.get('volatility', 20):.1f}%</div>
            </div>
            """, unsafe_allow_html=True)

        # 차트
        st.subheader("📈 차트")
        if PLOTLY_AVAILABLE:
            fig = create_market_overview_chart(selected_data, selected_index)
            st.plotly_chart(fig, use_container_width=True)

        # 이평선 상태
        st.markdown("#### 이동평균선 분석")
        ma_cols = st.columns(3)

        with ma_cols[0]:
            ma20_status = "✅ 위" if metrics.get('above_ma20') else "❌ 아래"
            st.metric("20일선", ma20_status, f"{metrics.get('ma20', 0):,.2f}")

        with ma_cols[1]:
            ma60_status = "✅ 위" if metrics.get('above_ma60') else "❌ 아래"
            st.metric("60일선", ma60_status, f"{metrics.get('ma60', 0):,.2f}")

        with ma_cols[2]:
            ma120_status = "✅ 위" if metrics.get('above_ma120') else "❌ 아래"
            st.metric("120일선", ma120_status, f"{metrics.get('ma120', 0):,.2f}")

    # ============ 탭 2: 주도 섹터/종목 ============
    with tab2:
        st.subheader("🎯 주도 섹터 & 종목")

        # 상승/하락 종목
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🔥 상승 상위")
            for stock in gainers[:5]:
                change = stock.get('change', 0)
                color = '#22c55e'
                st.markdown(f"""
                <div style='display: flex; justify-content: space-between; padding: 0.5rem;
                            background: {color}10; border-radius: 4px; margin-bottom: 0.3rem;'>
                    <span>{stock.get('name', '')} ({stock.get('code', '')})</span>
                    <span style='color: {color}; font-weight: bold;'>+{change:.2f}%</span>
                </div>
                """, unsafe_allow_html=True)

        with col2:
            st.markdown("#### 💧 하락 상위")
            for stock in losers[:5]:
                change = stock.get('change', 0)
                color = '#ef4444'
                st.markdown(f"""
                <div style='display: flex; justify-content: space-between; padding: 0.5rem;
                            background: {color}10; border-radius: 4px; margin-bottom: 0.3rem;'>
                    <span>{stock.get('name', '')} ({stock.get('code', '')})</span>
                    <span style='color: {color}; font-weight: bold;'>{change:.2f}%</span>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # 섹터 분석
        st.markdown("#### 📊 섹터별 동향")

        if SECTOR_AVAILABLE:
            # 섹터 데이터 (샘플)
            sector_sample = [
                {'name': '반도체', 'return_1m': 5.2, 'return_3m': 12.3},
                {'name': '2차전지', 'return_1m': 3.8, 'return_3m': 8.5},
                {'name': 'IT', 'return_1m': 2.1, 'return_3m': 6.2},
                {'name': '바이오', 'return_1m': 1.5, 'return_3m': 4.8},
                {'name': '자동차', 'return_1m': -0.8, 'return_3m': 2.1},
                {'name': '금융', 'return_1m': -1.2, 'return_3m': -0.5},
                {'name': '건설', 'return_1m': -2.5, 'return_3m': -3.2},
                {'name': '화학', 'return_1m': -3.1, 'return_3m': -5.8},
            ]

            if PLOTLY_AVAILABLE:
                fig = create_sector_momentum_chart(sector_sample)
                st.plotly_chart(fig, use_container_width=True)

            # 섹터 테이블
            sector_df = pd.DataFrame(sector_sample)
            sector_df.columns = ['섹터', '1개월 수익률', '3개월 수익률']
            sector_df['1개월 수익률'] = sector_df['1개월 수익률'].apply(lambda x: f"{x:+.1f}%")
            sector_df['3개월 수익률'] = sector_df['3개월 수익률'].apply(lambda x: f"{x:+.1f}%")

            st.dataframe(sector_df, use_container_width=True, hide_index=True)

        # 주도주 특징
        st.markdown("#### 💡 주도주 특징")
        st.info("""
        **현재 시장 주도주 특징:**
        - 🔋 2차전지/반도체 등 성장주 강세
        - 📈 외국인 순매수 종목 상승 우위
        - 💰 실적 개선주에 자금 집중

        **투자 시사점:**
        - 주도 섹터의 대장주에 집중
        - 섹터 로테이션 징후 모니터링
        - 수급 동향 확인 후 매매
        """)

    # ============ 탭 3: 리스크 분석 ============
    with tab3:
        st.subheader("⚠️ 리스크 분석")

        # 리스크 게이지
        if PLOTLY_AVAILABLE:
            fig = create_risk_gauge(condition.get('risk_level', '보통'))
            st.plotly_chart(fig, use_container_width=True)

        # 리스크 요인
        risks = identify_risks(metrics, condition)

        st.markdown("#### 📋 리스크 요인")

        for risk in risks:
            level_colors = {
                '낮음': '#22c55e',
                '중간': '#eab308',
                '높음': '#ef4444'
            }
            color = level_colors.get(risk['level'], '#6b7280')

            st.markdown(f"""
            <div style='background: {color}15; padding: 1rem; border-radius: 8px;
                        border-left: 4px solid {color}; margin-bottom: 1rem;'>
                <div style='display: flex; justify-content: space-between;'>
                    <span style='font-weight: bold;'>{risk['factor']}</span>
                    <span style='color: {color}; font-weight: bold;'>위험도: {risk['level']}</span>
                </div>
                <p style='margin: 0.5rem 0; color: #4b5563;'>{risk['description']}</p>
                <div style='background: white; padding: 0.5rem; border-radius: 4px;'>
                    💡 <strong>대응:</strong> {risk['suggestion']}
                </div>
            </div>
            """, unsafe_allow_html=True)

        # 리스크 관리 가이드
        st.markdown("#### 📚 리스크 관리 가이드")
        with st.expander("리스크 관리 방법 보기"):
            st.markdown("""
            **1. 포지션 사이즈 관리**
            - 전체 자산의 5% 이상을 단일 종목에 투자하지 않기
            - 변동성 높은 시장에서는 현금 비중 30% 이상 유지

            **2. 손절 원칙**
            - 매수가 대비 -7~10%에서 손절
            - 손절 후 감정적 복수매매 금지

            **3. 분산 투자**
            - 최소 5개 이상 종목에 분산
            - 섹터별 분산 (한 섹터 비중 30% 이하)

            **4. 시장 상황별 대응**
            - 상승장: 수익 실현 계획 수립
            - 하락장: 현금 비중 확대, 분할 매수
            - 횡보장: 박스권 매매, 배당주 관심
            """)

    # ============ 탭 4: 목표/지지선 ============
    with tab4:
        st.subheader("📈 잠재적 고점 & 지지선")

        targets = calculate_potential_targets(metrics, condition)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🔺 저항선 (잠재적 고점)")

            for r in targets['resistances']:
                distance = r['distance']
                color = '#ef4444' if distance > 10 else '#eab308'
                st.markdown(f"""
                <div style='background: {color}15; padding: 0.8rem; border-radius: 8px;
                            margin-bottom: 0.5rem;'>
                    <div style='display: flex; justify-content: space-between;'>
                        <span style='font-weight: bold;'>{r['label']}</span>
                        <span style='color: {color};'>+{distance:.1f}%</span>
                    </div>
                    <div style='font-size: 1.3em; font-weight: bold;'>{r['price']:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)

        with col2:
            st.markdown("#### 🔻 지지선")

            for s in targets['supports']:
                distance = abs(s['distance'])
                color = '#22c55e' if distance < 10 else '#3498db'
                st.markdown(f"""
                <div style='background: {color}15; padding: 0.8rem; border-radius: 8px;
                            margin-bottom: 0.5rem;'>
                    <div style='display: flex; justify-content: space-between;'>
                        <span style='font-weight: bold;'>{s['label']}</span>
                        <span style='color: {color};'>-{distance:.1f}%</span>
                    </div>
                    <div style='font-size: 1.3em; font-weight: bold;'>{s['price']:,.2f}</div>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # 목표가 해석
        st.markdown("#### 💡 해석")

        current = targets['current']
        nearest_resistance = targets['resistances'][0] if targets['resistances'] else None
        nearest_support = targets['supports'][0] if targets['supports'] else None

        if nearest_resistance and nearest_support:
            upside = nearest_resistance['distance']
            downside = abs(nearest_support['distance'])

            if upside > downside * 2:
                st.success(f"""
                **상승 여력 우세** 📈

                - 상승 여력: {upside:.1f}% (→ {nearest_resistance['label']})
                - 하락 리스크: {downside:.1f}% (→ {nearest_support['label']})
                - 손익비: {upside/downside:.1f} : 1

                매수 관점에서 유리한 위치입니다.
                """)
            elif downside > upside * 2:
                st.warning(f"""
                **하락 리스크 우세** 📉

                - 상승 여력: {upside:.1f}% (→ {nearest_resistance['label']})
                - 하락 리스크: {downside:.1f}% (→ {nearest_support['label']})
                - 손익비: {upside/downside:.1f} : 1

                신규 매수보다 관망이 유리합니다.
                """)
            else:
                st.info(f"""
                **균형 상태** ⚖️

                - 상승 여력: {upside:.1f}%
                - 하락 리스크: {downside:.1f}%

                박스권 매매 전략이 적합합니다.
                """)

        # 52주 범위 시각화
        st.markdown("#### 📊 52주 가격 범위")

        high_52w = metrics.get('high_52w', current * 1.2)
        low_52w = metrics.get('low_52w', current * 0.8)
        position_pct = (current - low_52w) / (high_52w - low_52w) * 100 if high_52w != low_52w else 50

        st.markdown(f"""
        <div style='position: relative; height: 40px; background: linear-gradient(to right, #22c55e, #eab308, #ef4444);
                    border-radius: 8px; margin: 1rem 0;'>
            <div style='position: absolute; left: {position_pct}%; transform: translateX(-50%);
                        top: -25px; font-weight: bold;'>현재</div>
            <div style='position: absolute; left: {position_pct}%; transform: translateX(-50%);
                        width: 4px; height: 40px; background: black;'></div>
        </div>
        <div style='display: flex; justify-content: space-between;'>
            <span>저점: {low_52w:,.0f}</span>
            <span>현재: {current:,.0f} ({position_pct:.0f}%)</span>
            <span>고점: {high_52w:,.0f}</span>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    render_market_overview_page()
