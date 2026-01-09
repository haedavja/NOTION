# NOTION 시장 예측 시스템 - 유지보수 가이드

> **최종 수정**: 2026-01
> **버전**: v2.5 (한국 주식 중심 대시보드)

## 🔥 핵심 기능 (메인 대시보드)

### 1. SNS 스타일 시장 토론
**위치**: `dashboard/market_overview_page.py`

6명의 트레이더 페르소나가 현재 시장을 분석하고 토론합니다.

**페르소나 목록**:
| 이름 | 역할 | 색상 | 아바타 |
|:---:|:---:|:---:|:---:|
| 강세론자 김프로 | 낙관적 전망 | `#22c55e` | 📈 |
| 신중파 이차장 | 보수적 분석 | `#ef4444` | 📉 |
| 차트장인 박대리 | 기술적 분석 | `#3b82f6` | 📊 |
| 거시경제 최박사 | 매크로 분석 | `#8b5cf6` | 🎓 |
| 개미투자자 정씨 | 개인 관점 | `#f59e0b` | 🐜 |
| 퀀트봇 Q-1 | 데이터 기반 | `#06b6d4` | 🤖 |

**핵심 함수**:
```python
# 토론 생성
generate_sns_market_discussion(metrics, condition, gainers, losers, selected_stock)

# 메인 대시보드용 컴팩트 버전 (app.py)
render_sns_discussion_compact(metrics, condition, gainers, losers)
```

**새 페르소나 추가 방법**:
1. `TRADER_PERSONAS` 딕셔너리에 추가
2. `generate_sns_market_discussion()`에 해당 로직 추가

---

### 2. Snowflake 분석 (6축 레이더 차트)
**위치**: `analysis/snowflake_viz.py`, `dashboard/snowflake_page.py`

Simply Wall St 스타일 5축 레이더 차트로 종목 특성을 시각화합니다.

**5가지 평가 축**:
| 축 | 설명 | 평가 기준 |
|:---:|:---:|:---|
| 가치 (Value) | 밸류에이션 | PER, PBR |
| 미래 (Future) | 성장성 | 매출/이익 성장률 |
| 과거 (Past) | 과거 수익 | ROE, 영업이익률 |
| 배당 (Dividend) | 배당 매력 | 배당수익률 |
| 건전성 (Health) | 재무 안정성 | 부채비율, 유동비율 |

**핵심 함수**:
```python
# 점수 계산
scores = snowflake_analyzer.calculate_scores(fundamentals=stock_data, sector='default')

# 차트 생성
fig = create_snowflake_chart(scores, stock_name)

# 등급 판정
grade, emoji, description = get_overall_rating(scores)
```

**메인 대시보드에서 전체 종목 검색 지원**:
- `_get_stock_fundamentals_for_snowflake(code)` - 실제 데이터 조회
- `KoreanStockAnalyzer.get_fundamentals(code)` - pykrx에서 PER/PBR/배당 조회

---

### 3. 잠재적 요인(Catalyst) 분석
**위치**: `analysis/potential_analyzer.py`, `dashboard/potential_page.py`

아직 발생하지 않았지만 주가에 큰 영향을 줄 수 있는 잠재적 요인을 분석합니다.

**촉매 유형 (CatalystType)**:
- 상승: 실적 서프라이즈, 신제품, 시장 확대, 규제 승인, 파트너십, 저평가 해소
- 하락: 실적 미스, 경쟁 심화, 규제 리스크, 부채/유동성, 고평가 부담

**핵심 클래스**:
```python
class PotentialAnalyzer:
    def analyze(self, symbol, name, news, financial_data, technical_data) -> PotentialAnalysis

class PotentialAnalysis:
    bullish_catalysts: List[PotentialCatalyst]  # 상승 촉매
    bearish_catalysts: List[PotentialCatalyst]  # 하락 촉매
    bullish_score: float  # 상승 점수 (0-100)
    bearish_score: float  # 하락 점수 (0-100)
```

**Probability enum (Python 3.13+ 호환)**:
```python
class Probability(Enum):
    def __init__(self, korean: str, prob_value: float, color: str):
        self.korean = korean
        self.prob_value = prob_value  # 'value' 대신 'prob_value' 사용
        self.color = color
```

---

## 프로젝트 구조

```
NOTION/
├── dashboard/              # Streamlit 대시보드 페이지
│   ├── app.py             # 메인 앱 (라우팅)
│   ├── navigation.py      # 사이드바 네비게이션
│   ├── market_overview_page.py  # 시장 종합 현황 (SNS 토론)
│   └── ...
├── components/            # 재사용 UI 컴포넌트
│   ├── stock_search.py    # 종목 검색
│   ├── watchlist.py       # 관심 종목
│   ├── price_alert.py     # 가격 알림
│   └── easy_explanation.py # 쉬운 설명
├── analysis/              # 분석 모듈
│   ├── scorecard.py       # 종합 스코어카드
│   ├── snowflake_viz.py   # Snowflake 시각화
│   ├── sector_rotation.py # 섹터 회전 분석
│   └── ...
├── korea/                 # 한국 주식 데이터
│   └── krx_data.py        # KRX 데이터 수집
├── utils/                 # 유틸리티
│   ├── offline_cache.py   # 오프라인 캐시
│   └── ...
└── data/                  # 데이터 저장
    ├── watchlists/        # 워치리스트 JSON
    ├── alerts.json        # 알림 설정
    └── cache/             # 캐시 데이터
```

## 주요 파일별 가이드

### 1. dashboard/app.py (메인 앱)

**역할**: 페이지 라우팅, 데이터 로드, 전체 레이아웃

**수정 시 주의사항**:
- 새 페이지 추가 시:
  1. import 문 추가 (try-except로 감싸기)
  2. `availability` 딕셔너리에 추가
  3. 페이지 라우팅 섹션에 elif 추가
  4. `navigation.py`의 MENU_STRUCTURE에 메뉴 추가

```python
# 새 페이지 추가 예시
try:
    from dashboard.new_page import render_new_page
    NEW_PAGE_AVAILABLE = True
except ImportError:
    NEW_PAGE_AVAILABLE = False

# availability에 추가
availability = {
    ...
    'new_page': NEW_PAGE_AVAILABLE,
}

# 라우팅에 추가
elif current_page == 'new_page':
    if NEW_PAGE_AVAILABLE:
        render_new_page()
    else:
        render_unavailable_page("새 기능")
```

### 2. dashboard/market_overview_page.py (시장 종합)

**역할**: SNS 스타일 시장 토론, 리스크 분석

**핵심 상수**:
- `TRADER_PERSONAS`: 6개 트레이더 페르소나 정의

**새 페르소나 추가 방법**:
1. `TRADER_PERSONAS`에 새 항목 추가
2. `generate_sns_market_discussion()`에 해당 로직 추가
3. 색상은 기존 색상 규칙 참조

**페르소나 색상 규칙**:
- 강세: `#22c55e` (초록)
- 약세: `#ef4444` (빨강)
- 기술적: `#3b82f6` (파랑)
- 거시경제: `#8b5cf6` (보라)
- 개인투자자: `#f59e0b` (주황)
- 퀀트: `#06b6d4` (시안)

### 3. components/ (UI 컴포넌트)

**파일별 역할**:
- `stock_search.py`: 종목 검색 자동완성
- `watchlist.py`: 관심 종목 저장/관리 (JSON 저장)
- `price_alert.py`: 가격 알림 설정
- `easy_explanation.py`: 초보자용 설명

**데이터 저장 위치**:
- 워치리스트: `data/watchlists/{name}.json`
- 알림: `data/alerts.json`

**새 컴포넌트 추가 시**:
1. `components/` 폴더에 파일 생성
2. `components/__init__.py`에 import 추가
3. `__all__` 리스트 업데이트

### 4. analysis/ (분석 모듈)

**핵심 모듈**:
- `scorecard.py`: `ScorecardGenerator`, `ComprehensiveScorecard`
- `snowflake_viz.py`: 5축 레이더 차트
- `sector_rotation.py`: 섹터 회전 분석
- `benchmark.py`: 벤치마크 비교
- `correlation.py`: 상관관계 분석

**분석 결과 데이터 구조**:
```python
# Snowflake 점수 (각 0-100)
{
    'value': 75,      # 가치
    'future': 80,     # 미래성장
    'past': 65,       # 과거수익
    'health': 90,     # 재무건전
    'dividend': 50    # 배당
}

# 스코어카드 결과
ComprehensiveScorecard(
    stock_code='005930',
    stock_name='삼성전자',
    overall_score=75.5,
    overall_grade='B+',
    category_scores=[...],
    summary='...',
    generated_at=datetime.now()
)
```

## 의존성 관리

### 필수 패키지
```
streamlit>=1.28.0
pandas>=1.5.0
numpy>=1.23.0
```

### 선택적 패키지
```
pykrx          # 한국 주식 데이터
plotly         # 차트 시각화
yfinance       # 해외 주식 데이터
openai         # AI 분석
```

### 패키지 미설치 시 동작
- 각 모듈은 try-except로 import를 감싸 미설치 시에도 앱 실행 가능
- `XXX_AVAILABLE = False` 플래그로 기능 비활성화
- 비활성화된 기능은 `render_unavailable_page()` 표시

## 데이터 흐름

```
[KRX/yfinance] → [분석 모듈] → [대시보드 페이지] → [Streamlit UI]
       ↓              ↓
   [캐시 저장]   [세션 상태]
```

### 캐시 관리
- TTL 기반 캐시: `utils/offline_cache.py`
- 캐시 위치: `data/cache/`
- 캐시 정리: `clear_cache(older_than_hours=24)`

## 에러 처리 가이드

### 로깅
```python
import logging
logger = logging.getLogger(__name__)

try:
    # 작업
except Exception as e:
    logger.warning(f"작업 실패: {e}")
    # 폴백 처리
```

### 데이터 조회 실패 시
- KRX 미설치/오류: 샘플 데이터 반환
- 네트워크 오류: 만료된 캐시 사용
- 완전 실패: 기본값 또는 빈 데이터

## 테스트

### 구문 검사
```bash
python -m py_compile dashboard/*.py components/*.py analysis/*.py
```

### 모듈 import 검사
```bash
python -c "from dashboard.app import main; print('OK')"
```

## 배포 체크리스트

1. [ ] 모든 파일 구문 검사 통과
2. [ ] 필수 패키지 requirements.txt에 명시
3. [ ] 환경 변수 설정 확인 (API 키 등)
4. [ ] 데이터 디렉토리 존재 확인
5. [ ] 캐시 디렉토리 쓰기 권한 확인

## 버전 히스토리

- **v2.0** (2024-01): SNS 스타일 토론, 논리 상세 기능 추가
- **v1.5**: 워치리스트, 가격 알림 기능 추가
- **v1.0**: 초기 버전

---
*최종 수정: 2024-01*
