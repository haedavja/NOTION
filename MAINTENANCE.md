# NOTION 시장 예측 시스템 - 유지보수 가이드

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
