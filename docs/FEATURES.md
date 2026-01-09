# NOTION 주요 기능 상세 가이드

> **버전**: v2.5 | **최종 수정**: 2026-01

이 문서는 NOTION 시스템의 핵심 기능을 상세히 설명합니다. 다른 AI나 개발자가 유지보수할 때 참고하세요.

---

## 목차

1. [SNS 스타일 시장 토론](#1-sns-스타일-시장-토론)
2. [Snowflake 분석](#2-snowflake-분석)
3. [잠재적 요인(Catalyst) 분석](#3-잠재적-요인catalyst-분석)
4. [한국 시장 데이터](#4-한국-시장-데이터)
5. [데이터 흐름 및 폴백 패턴](#5-데이터-흐름-및-폴백-패턴)

---

## 1. SNS 스타일 시장 토론

### 개요
트위터/X 스타일의 UI로 6명의 가상 트레이더가 현재 시장 상황을 분석합니다.

### 파일 위치
- **메인**: `dashboard/market_overview_page.py`
- **메인 대시보드용**: `dashboard/app.py` → `render_sns_discussion_compact()`

### 6명의 페르소나

```python
TRADER_PERSONAS = {
    'bullish': {
        'name': '강세론자 김프로',
        'avatar': '📈',
        'color': '#22c55e',
        'style': '낙관적, 상승 요인 강조',
        'personality': '항상 기회를 찾는 긍정적인 베테랑'
    },
    'bearish': {
        'name': '신중파 이차장',
        'avatar': '📉',
        'color': '#ef4444',
        'style': '보수적, 리스크 경고',
        'personality': '신중하고 방어적인 분석가'
    },
    'technical': {
        'name': '차트장인 박대리',
        'avatar': '📊',
        'color': '#3b82f6',
        'style': '기술적 분석, 차트 패턴',
        'personality': '숫자와 패턴에 집중'
    },
    'macro': {
        'name': '거시경제 최박사',
        'avatar': '🎓',
        'color': '#8b5cf6',
        'style': '거시경제, 정책 영향',
        'personality': '큰 그림을 보는 이코노미스트'
    },
    'retail': {
        'name': '개미투자자 정씨',
        'avatar': '🐜',
        'color': '#f59e0b',
        'style': '개인 투자자 관점',
        'personality': '현실적이고 공감되는 의견'
    },
    'quant': {
        'name': '퀀트봇 Q-1',
        'avatar': '🤖',
        'color': '#06b6d4',
        'style': '데이터 기반, 통계적',
        'personality': '감정 없는 데이터 분석'
    }
}
```

### 의견 생성 로직

```python
def generate_sns_market_discussion(metrics, condition, gainers, losers, selected_stock):
    """
    Args:
        metrics: 시장 지표 (return_1d, return_5d, volatility, rsi, volume_ratio 등)
        condition: 시장 상태 (trend, strength, signal, risk_level)
        gainers: 상승 상위 종목 리스트
        losers: 하락 상위 종목 리스트
        selected_stock: 특정 종목 분석용 (선택)

    Returns:
        List[Dict]: 각 페르소나의 의견 (message, confidence, likes, comments 등)
    """
```

### 신뢰도/유효기간 시스템
각 의견에는 신뢰도와 유효기간이 부여됩니다:
- **신뢰도**: 70%+ (높음/초록), 50-69% (중간/노랑), 50% 미만 (낮음/빨강)
- **유효기간**: 단기(1-3일), 중기(1-2주), 장기(1개월+)

---

## 2. Snowflake 분석

### 개요
Simply Wall St 스타일의 5축 레이더 차트로 종목의 투자 매력도를 시각화합니다.

### 파일 위치
- **분석 엔진**: `analysis/snowflake_viz.py`
- **대시보드 페이지**: `dashboard/snowflake_page.py`
- **메인 대시보드용**: `dashboard/app.py` → `render_snowflake_compact()`

### 5가지 평가 축

| 축 | 변수명 | 평가 기준 | 점수 범위 |
|:---:|:---:|:---|:---:|
| 가치 | `value` | PER, PBR (낮을수록 좋음) | 0-6 |
| 미래 | `future` | 매출/이익 성장률 | 0-6 |
| 과거 | `past` | ROE, 영업이익률 | 0-6 |
| 배당 | `dividend` | 배당수익률 | 0-6 |
| 건전성 | `health` | 부채비율, 유동비율 | 0-6 |

### 핵심 클래스

```python
@dataclass
class SnowflakeScores:
    value: float      # 가치 점수
    future: float     # 미래 점수
    past: float       # 과거 점수
    dividend: float   # 배당 점수
    health: float     # 건전성 점수
    total: float      # 종합 점수 (5축 평균)
```

### 등급 판정

```python
def get_overall_rating(scores: SnowflakeScores) -> Tuple[str, str, str]:
    """
    Returns:
        (등급, 이모지, 설명)
        예: ('A', '🌟', '투자 매력도가 높습니다')
    """
    total = scores.total
    if total >= 5.0: return ('S', '👑', '최상위 투자 매력')
    elif total >= 4.0: return ('A', '🌟', '높은 투자 매력')
    elif total >= 3.0: return ('B', '👍', '양호한 투자 매력')
    elif total >= 2.0: return ('C', '😐', '보통')
    else: return ('D', '⚠️', '투자 주의')
```

### 메인 대시보드 전체 종목 검색

```python
def _get_stock_fundamentals_for_snowflake(code: str) -> Optional[Dict]:
    """
    KoreanStockAnalyzer를 통해 실제 펀더멘털 데이터 조회

    데이터 소스: pykrx → stock.get_market_fundamental_by_date()
    폴백: 기본값 딕셔너리 반환
    """
```

---

## 3. 잠재적 요인(Catalyst) 분석

### 개요
아직 발생하지 않았지만 주가에 큰 영향을 줄 수 있는 잠재적 요인을 분석합니다.

### 파일 위치
- **분석 엔진**: `analysis/potential_analyzer.py`
- **대시보드 페이지**: `dashboard/potential_page.py`
- **메인 대시보드용**: `dashboard/app.py` → `render_catalyst_compact()`

### 촉매 유형 (CatalystType Enum)

**상승 촉매:**
- `EARNINGS_SURPRISE`: 실적 서프라이즈
- `NEW_PRODUCT`: 신제품/서비스 출시
- `MARKET_EXPANSION`: 시장 확대/진출
- `REGULATORY_APPROVAL`: 규제 승인/인허가
- `PARTNERSHIP`: 파트너십/M&A
- `UNDERVALUATION`: 저평가 해소
- `SHORT_SQUEEZE`: 숏스퀴즈
- `DIVIDEND_INCREASE`: 배당 확대
- `BUYBACK`: 자사주 매입
- `TURNAROUND`: 턴어라운드

**하락 촉매:**
- `EARNINGS_MISS`: 실적 미스
- `COMPETITION`: 경쟁 심화
- `REGULATORY_RISK`: 규제 리스크
- `DEBT_LIQUIDITY`: 부채/유동성
- `DEMAND_SLOWDOWN`: 수요 둔화
- `MARGIN_PRESSURE`: 마진 압박
- `OVERVALUATION`: 고평가 부담
- `DILUTION_RISK`: 희석 리스크

### 핵심 데이터 구조

```python
@dataclass
class PotentialCatalyst:
    catalyst_type: CatalystType
    description: str
    impact: ImpactLevel      # 상/중/하
    probability: Probability  # 매우높음/높음/중간/낮음
    timeframe: Timeframe      # 단기/중기/장기
    expected_move_pct: Tuple[float, float]  # 예상 변동폭
    evidence: List[str]       # 근거
    triggers: List[str]       # 트리거 조건
    risks: List[str]          # 관련 리스크

@dataclass
class PotentialAnalysis:
    symbol: str
    name: str
    bullish_catalysts: List[PotentialCatalyst]
    bearish_catalysts: List[PotentialCatalyst]
    bullish_score: float      # 0-100
    bearish_score: float      # 0-100
    overall_bias: str         # '상승', '중립', '하락'
    conviction_level: str     # '높음', '중간', '낮음'
    key_thesis: str           # 핵심 투자 논리
    action_recommendation: str
    risk_reward_ratio: float
    watch_points: List[str]
```

### Python 3.13+ 호환성

```python
class Probability(Enum):
    """Python 3.13에서 Enum.value 설정 불가 → prob_value 사용"""
    VERY_HIGH = ('매우높음', 0.85, '#22c55e')
    HIGH = ('높음', 0.70, '#84cc16')
    MEDIUM = ('중간', 0.50, '#eab308')
    LOW = ('낮음', 0.30, '#f97316')

    def __init__(self, korean: str, prob_value: float, color: str):
        self.korean = korean
        self.prob_value = prob_value  # 'value' 대신!
        self.color = color
```

---

## 4. 한국 시장 데이터

### 데이터 소스

| 데이터 | 소스 | 파일 |
|:---:|:---:|:---:|
| 주식 목록/가격 | pykrx | `korea/krx_data.py` |
| KOSPI/KOSDAQ 지수 | pykrx | `korea/krx_data.py` |
| 펀더멘털 (PER/PBR) | pykrx | `korea/korean_stocks.py` |
| 환율 | exchangerate-api.com | `korea/bok_indicators.py` |
| 배당 캘린더 | 자체 계산 | `korea/dividend_calendar.py` |

### KRXDataCollector 핵심 메서드

```python
class KRXDataCollector:
    def get_stock_list(self, market='ALL') -> pd.DataFrame
    def get_stock_price(self, code, start_date, end_date) -> pd.DataFrame
    def get_market_summary(self) -> Dict
    def get_index_data(self, index_code, start_date, end_date) -> pd.DataFrame
    def get_investor_trading_by_stock(self, code, days) -> Dict
```

### KoreanStockAnalyzer 핵심 메서드

```python
class KoreanStockAnalyzer:
    def get_fundamentals(self, code) -> StockFundamentals
    def analyze_technical(self, code, days) -> Dict
    def get_foreign_trend(self, code, days) -> Dict
```

---

## 5. 데이터 흐름 및 폴백 패턴

### 다중 소스 폴백 패턴

모든 데이터 조회는 다음 패턴을 따릅니다:

```
실시간 API → 캐시 → 네이버 스크래핑 → 샘플 데이터
```

### 예시: 환율 조회

```python
def get_exchange_rates(self) -> Dict:
    # 1. exchangerate-api.com (무료)
    rates = self._fetch_realtime_exchange_rates()
    if rates:
        return rates

    # 2. 네이버 금융 스크래핑
    rates = self._scrape_naver_exchange()
    if rates:
        return rates

    # 3. 샘플 데이터
    return self._get_sample_rates()
```

### 예시: KOSPI/KOSDAQ 지수

```python
def fetch_market_index_data(days: int) -> Dict[str, pd.DataFrame]:
    # 1. pykrx API
    try:
        indices = krx.get_index_data(...)
        if indices:
            return indices
    except:
        pass

    # 2. 샘플 데이터 생성
    return _generate_sample_data()
```

### 세션 상태 관리

Streamlit 세션 상태를 활용한 데이터 캐싱:

```python
# 종목 선택 저장
st.session_state.snowflake_selected_code = code
st.session_state.snowflake_selected_name = name

# 페이지 이동
st.session_state.current_page = 'snowflake'
st.rerun()
```

---

## 트러블슈팅

### 자주 발생하는 문제

| 증상 | 원인 | 해결 |
|:---|:---|:---|
| "데이터 로딩 중..." 멈춤 | API 실패 + 샘플 폴백 누락 | `if not data: return _generate_sample()` 추가 |
| Python 3.13 Enum 오류 | `self.value` 사용 | `self.prob_value`로 변경 |
| HTML 텍스트로 표시 | `st.markdown` 렌더링 실패 | `components.html()` 사용 |
| 환율 오래된 값 | 샘플 데이터 사용 중 | 실시간 API 연결 확인 |

---

## 문서 업데이트 이력

| 날짜 | 변경 내용 |
|:---:|:---|
| 2026-01 | 초기 작성 - 핵심 기능 3가지 문서화 |
