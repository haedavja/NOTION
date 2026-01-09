# 시스템 아키텍처

이 문서는 시스템의 전체 구조와 각 모듈의 역할, 의존성을 설명합니다.

## 목차

1. [전체 구조](#전체-구조)
2. [모듈별 상세](#모듈별-상세)
3. [데이터 흐름](#데이터-흐름)
4. [핵심 유틸리티](#핵심-유틸리티)
5. [설정 관리](#설정-관리)
6. [확장 가이드](#확장-가이드)

---

## 전체 구조

```
┌──────────────────────────────────────────────────────────────────┐
│                         Dashboard (Streamlit)                      │
│  ┌─────────────┬─────────────┬─────────────┬─────────────────┐   │
│  │   app.py    │ korea_page  │ ai_chat     │     auth.py     │   │
│  └──────┬──────┴──────┬──────┴──────┬──────┴────────┬────────┘   │
└─────────┼─────────────┼─────────────┼───────────────┼────────────┘
          │             │             │               │
          ▼             ▼             ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Analysis Layer                             │
│  ┌────────────┬──────────────┬────────────┬─────────────────┐   │
│  │   macro    │  sentiment   │  technical │ social_sentiment│   │
│  └─────┬──────┴───────┬──────┴─────┬──────┴────────┬────────┘   │
└────────┼──────────────┼────────────┼───────────────┼────────────┘
         │              │            │               │
         ▼              ▼            ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Data Layer                                │
│  ┌────────────┬──────────────┬────────────┬─────────────────┐   │
│  │   macro    │    market    │  fund_flow │  news_collector │   │
│  │ indicators │    data      │            │                 │   │
│  └─────┬──────┴───────┬──────┴─────┬──────┴────────┬────────┘   │
└────────┼──────────────┼────────────┼───────────────┼────────────┘
         │              │            │               │
         ▼              ▼            ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                       External APIs                               │
│  ┌────────────┬──────────────┬────────────┬─────────────────┐   │
│  │    FRED    │    Yahoo     │    News    │      RSS        │   │
│  │    API     │   Finance    │    API     │     Feeds       │   │
│  └────────────┴──────────────┴────────────┴─────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      Supporting Modules                          │
│  ┌─────────┬───────────┬─────────┬──────────┬───────────────┐  │
│  │  utils  │  alerts   │portfolio│  korea   │   prediction  │  │
│  └─────────┴───────────┴─────────┴──────────┴───────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 모듈별 상세

### 1. Dashboard (`dashboard/`)

| 파일 | 역할 | 주요 의존성 |
|------|------|-------------|
| `app.py` | 메인 대시보드 | streamlit, analysis/* |
| `korea_page.py` | 한국 시장 페이지 | korea/*, analysis/* |
| `ai_chat_page.py` | AI 채팅 인터페이스 | OpenAI API |
| `auth.py` | 사용자 인증 | bcrypt/hashlib, secrets |

**auth.py 인증 흐름:**
```
사용자 입력 → _verify_password() → 해시 비교 → 세션 생성
                    │
                    ├── bcrypt 해시 ($2b$...)
                    ├── PBKDF2 해시 (pbkdf2:...)
                    └── 레거시 SHA256 (64자 hex)
```

### 2. Analysis (`analysis/`)

| 파일 | 역할 | 입력 | 출력 |
|------|------|------|------|
| `macro_analysis.py` | 거시경제 분석 | 경제 지표 | 경기 사이클, 점수 |
| `sentiment.py` | 뉴스 감성 분석 | 뉴스 텍스트 | 감성 점수 |
| `technical.py` | 기술적 분석 | 가격 데이터 | RSI, MACD 등 |
| `social_sentiment.py` | 소셜 감성 | SNS 데이터 | 감성 지표 |
| `flow_analysis.py` | 자금 흐름 | ETF 데이터 | 섹터별 흐름 |

### 3. Data (`data/`)

| 파일 | 역할 | 외부 API |
|------|------|----------|
| `macro_indicators.py` | 거시 지표 수집 | FRED API |
| `market_data.py` | 시장 데이터 | Yahoo Finance |
| `fund_flow.py` | 자금 흐름 | Yahoo Finance |
| `news_collector.py` | 뉴스 수집 | News API, RSS |

### 4. Portfolio (`portfolio/`)

| 파일 | 역할 | 특이사항 |
|------|------|----------|
| `portfolio.py` | 포트폴리오 모델 | Position, Portfolio 클래스 |
| `data_store.py` | 데이터 영속성 | **스레드 안전 (RLock)** |
| `watchlist.py` | 관심 종목 | 로깅 적용 |
| `multi_portfolio.py` | 다중 포트폴리오 | 로깅 적용 |
| `thesis_evaluator.py` | 투자 논리 평가 | - |

**data_store.py 구조:**
```python
DataStore
├── save_portfolio()    # 스레드 안전
├── load_portfolio()    # 스레드 안전
├── save_reports()      # 스레드 안전
├── load_reports()      # 스레드 안전
├── save_settings()     # 스레드 안전
├── load_settings()     # 스레드 안전
├── save_alerts()       # 스레드 안전
├── load_alerts()       # 스레드 안전
├── export_all()        # 경로 검증 + 스레드 안전
├── import_all()        # 경로 검증 + 스레드 안전
└── clear_all()         # 스레드 안전
```

### 5. Alerts (`alerts/`)

| 파일 | 역할 | 채널 |
|------|------|------|
| `telegram_bot.py` | 텔레그램 알림 | Telegram API |
| `discord_bot.py` | 디스코드 알림 | Discord Webhook |
| `news_alert.py` | 뉴스 알림 시스템 | telegram, discord |
| `price_alert.py` | 가격 알림 | telegram, discord |
| `price_monitor.py` | 가격 모니터링 | - |
| `alert_scheduler.py` | 알림 스케줄러 | schedule 라이브러리 |

### 6. Korea (`korea/`)

| 파일 | 역할 |
|------|------|
| `market_keywords.py` | 한국 시장 키워드 분석 |
| `dividend_calendar.py` | 배당 캘린더 |
| `dart_monitor.py` | DART 공시 모니터링 |

### 7. Utils (`utils/`)

| 파일 | 역할 | 보안 기능 |
|------|------|----------|
| `cache.py` | 캐싱 시스템 | JSON 직렬화, SHA256, **Lock** |
| `validators.py` | 입력 검증 | XSS 방지, 경로 검증 |
| `api_utils.py` | API 유틸리티 | SHA256 캐시 키 |
| `backup.py` | 백업 유틸리티 | SHA256 체크섬 |
| `circuit_breaker.py` | 회로 차단기 | 장애 격리 |

### 8. Prediction (`prediction/`)

| 파일 | 역할 |
|------|------|
| `probability_model.py` | 확률 예측 모델 |
| `scenarios.py` | 시나리오 분석 |

### 9. Config (`config/`)

| 파일 | 역할 |
|------|------|
| `settings.py` | 중앙 설정 관리 (싱글톤) |

---

## 데이터 흐름

### 1. 시장 예측 흐름

```
External APIs
     │
     ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Data     │────▶│   Analysis  │────▶│ Prediction  │
│  Collectors │     │   Modules   │     │   Model     │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
                                        ┌───────────┐
                                        │ Dashboard │
                                        └───────────┘
```

### 2. 알림 흐름

```
┌───────────────┐     ┌───────────────┐     ┌────────────────┐
│ News/Price    │────▶│ Alert System  │────▶│ Telegram/      │
│ Collectors    │     │ (Scheduler)   │     │ Discord        │
└───────────────┘     └───────────────┘     └────────────────┘
        │                    │
        ▼                    ▼
  ┌──────────┐         ┌──────────┐
  │  Cache   │         │ DataStore│
  └──────────┘         └──────────┘
```

### 3. 포트폴리오 데이터 흐름

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User      │────▶│  DataStore  │────▶│   JSON      │
│   Input     │     │  (RLock)    │     │   Files     │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                          ▼
                    ~/.notion_portfolio/
                    ├── portfolio.json
                    ├── reports.json
                    ├── settings.json
                    └── alerts.json
```

---

## 핵심 유틸리티

### 캐싱 시스템 (`utils/cache.py`)

```
┌────────────────────────────────────────────────────┐
│                  Cache System                       │
├────────────────────┬───────────────────────────────┤
│    MemoryCache     │        FileCache              │
├────────────────────┼───────────────────────────────┤
│ - LRU 방식         │ - 디스크 저장                 │
│ - OrderedDict      │ - JSON 직렬화                 │
│ - max_size 제한    │ - .cache.json 파일            │
│ - TTL 지원         │ - TTL 지원                    │
│ - Lock 적용        │ - Lock 적용                   │
└────────────────────┴───────────────────────────────┘
                          │
                          ▼
                 @cached(ttl=300) 데코레이터
```

### 검증 시스템 (`utils/validators.py`)

```
┌─────────────────────────────────────────────────────┐
│                  Validator                          │
├─────────────────────────────────────────────────────┤
│ .required()  .string()  .number()  .email()        │
│ .stock_symbol()  .date()  .url()  .currency()      │
└─────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────┐
│                  Sanitizer                          │
├─────────────────────────────────────────────────────┤
│ .html_escape()      - XSS 방지                      │
│ .strip_html_tags()  - HTML 태그 제거               │
│ .sanitize_filename() - 파일명 안전화               │
│ .sanitize_path()    - 경로 탐색 방지               │
│ .sanitize_sql_identifier() - SQL 인젝션 방지       │
└─────────────────────────────────────────────────────┘
                          │
┌─────────────────────────────────────────────────────┐
│               PathValidator                         │
├─────────────────────────────────────────────────────┤
│ .validate_file_path()  - 파일 경로 검증            │
│ .validate_directory()  - 디렉토리 검증             │
└─────────────────────────────────────────────────────┘
```

### Circuit Breaker (`utils/circuit_breaker.py`)

```
    ┌────────┐         ┌────────┐         ┌────────┐
    │ CLOSED │────────▶│  OPEN  │────────▶│  HALF  │
    │        │ 실패 N회│        │ 타임아웃│  OPEN  │
    └────────┘         └────────┘         └────────┘
         ▲                                     │
         │                                     │
         └──────────── 성공 ───────────────────┘
```

---

## 설정 관리

### 환경 변수

```bash
# API Keys
FRED_API_KEY=your_key
NEWS_API_KEY=your_key
OPENAI_API_KEY=your_key

# 알림
TELEGRAM_BOT_TOKEN=your_token
TELEGRAM_CHAT_ID=your_id
DISCORD_WEBHOOK_URL=your_url

# 대시보드
DASHBOARD_PASSWORD=your_password
```

### 설정 우선순위

```
환경 변수 > config/settings.py > 기본값
```

### 싱글톤 설정 (`config/settings.py`)

```python
from config.settings import get_settings

settings = get_settings()  # 항상 같은 인스턴스 반환
```

---

## 확장 가이드

### 새 데이터 소스 추가

1. `data/` 디렉토리에 새 모듈 생성
2. 기존 패턴 따르기:
   ```python
   class NewDataCollector:
       def __init__(self):
           self.cache = get_memory_cache()

       @cached(ttl=300)
       def fetch_data(self):
           # API 호출
           pass
   ```

### 새 분석 모듈 추가

1. `analysis/` 디렉토리에 모듈 생성
2. 입력 검증 적용:
   ```python
   from utils.validators import Validator

   def analyze(data):
       result = Validator.required(data)
       if not result.is_valid:
           raise ValueError(result.error_message)
   ```

### 새 알림 채널 추가

1. `alerts/` 디렉토리에 알림 클래스 생성
2. 기존 인터페이스 따르기:
   ```python
   class NewNotifier:
       def __init__(self):
           self.enabled = True

       def send_alert(self, title, message):
           pass
   ```

---

## 테스트 가이드

### 단위 테스트 위치
```
tests/
├── test_validators.py
├── test_cache.py
├── test_data_store.py
└── ...
```

### 테스트 실행
```bash
pytest tests/
pytest tests/test_validators.py -v
```

---

## 의존성 다이어그램

```
dashboard/
    └── analysis/, portfolio/, alerts/, korea/
        └── data/, utils/
            └── External APIs
                └── config/
```

---

## 버전 정보

| 모듈 | 최종 수정 | 주요 변경 |
|------|----------|----------|
| auth.py | 2026-01 | bcrypt 해싱 |
| cache.py | 2026-01 | JSON, Lock |
| data_store.py | 2026-01 | RLock, 경로 검증 |
| validators.py | 2026-01 | Sanitizer 추가 |
