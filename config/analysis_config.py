"""
분석 설정 파일
하드코딩된 임계값을 중앙 관리
"""

# ==================== 급등/급락 분석 설정 ====================

RALLY_CONFIG = {
    # 최소 상승률 기준
    'min_rally_1d': 3.0,      # 1일 최소 상승률 (%)
    'min_rally_5d': 5.0,      # 5일 최소 상승률 (%)
    'min_rally_1m': 10.0,     # 1개월 최소 상승률 (%)

    # 분석 대상 수
    'max_stocks_to_analyze': 100,   # 분석할 최대 종목 수
    'top_n_results': 15,            # 결과로 반환할 상위 N개

    # 거래량 기준
    'min_volume_ratio': 1.0,        # 최소 거래량 비율 (평균 대비)
}

DECLINE_CONFIG = {
    # 최소 하락률 기준 (음수)
    'min_decline_1d': -3.0,    # 1일 최소 하락률 (%)
    'min_decline_5d': -5.0,    # 5일 최소 하락률 (%)
    'min_decline_1m': -10.0,   # 1개월 최소 하락률 (%)

    # 분석 대상 수
    'max_stocks_to_analyze': 100,
    'top_n_results': 15,
}


# ==================== 밸류에이션 임계값 ====================

VALUATION_THRESHOLDS = {
    # PER 기준
    'per_undervalued': 10,      # 저평가 기준
    'per_fair': 20,             # 적정 평가 상한
    'per_overvalued': 50,       # 고평가 기준

    # PBR 기준
    'pbr_undervalued': 1.0,
    'pbr_overvalued': 3.0,

    # 부채비율 기준
    'debt_ratio_safe': 100,     # 안전 수준 (%)
    'debt_ratio_warning': 200,  # 경고 수준 (%)
    'debt_ratio_danger': 400,   # 위험 수준 (%)

    # 공매도 비율
    'short_interest_normal': 5,   # 정상 (%)
    'short_interest_high': 15,    # 높음 (%)
    'short_interest_extreme': 25, # 극단적 (%)
}


# ==================== 기술적 지표 임계값 ====================

TECHNICAL_THRESHOLDS = {
    # RSI 기준
    'rsi_oversold': 30,         # 과매도
    'rsi_overbought': 70,       # 과매수
    'rsi_extreme_oversold': 20,
    'rsi_extreme_overbought': 80,

    # 이격도 기준 (%)
    'ma_deviation_oversold': -20,   # 이평선 대비 과매도
    'ma_deviation_overbought': 20,  # 이평선 대비 과매수

    # 거래량 급증 기준
    'volume_spike_ratio': 3.0,      # 평균 대비 3배 이상
}


# ==================== 수급 임계값 ====================

INVESTOR_THRESHOLDS = {
    # 순매수 금액 기준 (억원)
    'foreign_significant': 100,     # 외국인 유의미한 순매수
    'inst_significant': 50,         # 기관 유의미한 순매수

    # 연속 매수/매도 일수
    'consecutive_days_strong': 5,   # 강한 수급 신호
}


# ==================== 점수 가중치 ====================

SCORE_WEIGHTS = {
    # 급등 분석 가중치
    'rally': {
        'supply_demand': 0.30,      # 수급
        'technical': 0.25,          # 기술적 지표
        'narrative': 0.25,          # 테마/뉴스
        'valuation': 0.20,          # 밸류에이션
    },

    # 하락 분석 가중치
    'decline': {
        'supply_demand': 0.30,
        'technical': 0.25,
        'fundamental': 0.25,
        'sentiment': 0.20,
    },
}


# ==================== 섹터 ETF 코드 ====================

SECTOR_ETFS = {
    '반도체': '091160',
    '2차전지': '305720',
    '바이오': '244580',
    '은행': '091170',
    '자동차': '091180',
    '철강': '139260',
    '건설': '139220',
    '화학': '139250',
    '미디어': '228790',
    '에너지': '117460',
}


def get_config(category: str, key: str, default=None):
    """설정값 조회 헬퍼 함수"""
    configs = {
        'rally': RALLY_CONFIG,
        'decline': DECLINE_CONFIG,
        'valuation': VALUATION_THRESHOLDS,
        'technical': TECHNICAL_THRESHOLDS,
        'investor': INVESTOR_THRESHOLDS,
        'weights': SCORE_WEIGHTS,
        'etf': SECTOR_ETFS,
    }
    config = configs.get(category, {})
    return config.get(key, default)
