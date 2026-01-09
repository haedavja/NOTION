# 보안 가이드

이 문서는 시스템에 적용된 보안 조치와 개발자가 알아야 할 보안 관련 사항을 설명합니다.

## 목차

1. [인증 및 패스워드](#인증-및-패스워드)
2. [데이터 직렬화](#데이터-직렬화)
3. [해시 알고리즘](#해시-알고리즘)
4. [입력 검증](#입력-검증)
5. [스레드 안전성](#스레드-안전성)
6. [로깅](#로깅)
7. [체크리스트](#보안-체크리스트)

---

## 인증 및 패스워드

### 구현 위치
- `dashboard/auth.py`

### 패스워드 해싱

```python
# bcrypt 사용 (권장, rounds=12)
# 없을 경우 PBKDF2 폴백 (iterations=100000)
```

**주요 사항:**
- bcrypt가 설치되어 있으면 자동으로 사용
- bcrypt 미설치 시 PBKDF2-SHA256으로 폴백
- 레거시 SHA256 해시도 검증 가능 (마이그레이션 지원)
- 타이밍 공격 방지를 위해 `hmac.compare_digest()` 사용

### 레거시 마이그레이션
기존 SHA256 해시 사용자가 로그인 시 자동으로 새 해시로 업그레이드됩니다:
```python
# 레거시 해시 형식: 64자 hex (SHA256)
# 새 bcrypt 형식: $2b$12$... 또는 pbkdf2:salt:key
```

### 권장 사항
- [ ] bcrypt 패키지 설치: `pip install bcrypt`
- [ ] 기존 사용자 로그인 시 해시 자동 업그레이드 확인
- [ ] 환경 변수로 비밀번호 관리 (`DASHBOARD_PASSWORD`)

---

## 데이터 직렬화

### 구현 위치
- `utils/cache.py`

### Pickle 제거
**위험:** Pickle은 역직렬화 시 임의 코드 실행 가능 (RCE 취약점)

**변경 사항:**
```python
# Before (취약)
import pickle
data = pickle.load(f)

# After (안전)
import json
data = json.load(f)
```

### 레거시 캐시 처리
- `.cache` 파일 (pickle) → 자동 삭제
- `.cache.json` 파일 (JSON) → 새 형식

### JSON 직렬화 주의사항
```python
# datetime, Decimal 등은 default=str 사용
json.dump(data, f, ensure_ascii=False, default=str)
```

---

## 해시 알고리즘

### MD5 → SHA256 교체

| 파일 | 용도 | 변경 전 | 변경 후 |
|------|------|---------|---------|
| `utils/cache.py` | 캐시 키 | MD5 | SHA256[:32] |
| `utils/backup.py` | 체크섬 | MD5 | SHA256 |
| `utils/api_utils.py` | API 캐시 키 | MD5 | SHA256[:32] |
| `alerts/news_alert.py` | 뉴스 해시 | MD5 | SHA256[:32] |

**참고:** MD5는 충돌 공격에 취약하므로 보안 관련 용도에 사용하지 말 것

---

## 입력 검증

### 구현 위치
- `utils/validators.py`

### 제공되는 검증기

```python
from utils.validators import Validator, Sanitizer, PathValidator

# 기본 검증
Validator.string(value, min_length=1, max_length=100)
Validator.number(value, min_value=0, max_value=1000000)
Validator.email(value)
Validator.stock_symbol(value)
Validator.url(value)
Validator.date(value)

# 새니타이저 (보안)
Sanitizer.html_escape(text)      # XSS 방지
Sanitizer.strip_html_tags(text)  # HTML 태그 제거
Sanitizer.sanitize_filename(name) # 파일명 안전화
Sanitizer.sanitize_path(path)    # 경로 탐색 방지
Sanitizer.sanitize_sql_identifier(id)  # SQL 인젝션 방지

# 경로 검증
PathValidator.validate_file_path(path, allowed_extensions={'.json'})
PathValidator.validate_directory(path, must_exist=True)
```

### 경로 탐색 공격 방지
```python
# 위험한 패턴 차단
if '..' in path:  # 상위 디렉토리 접근 시도
    return False
if '\x00' in path:  # Null 바이트 인젝션
    return False
```

### 적용된 파일
- `portfolio/data_store.py`: `export_all()`, `import_all()`에 경로 검증 추가

---

## 스레드 안전성

### 구현 위치
- `utils/cache.py` → `FileCache` 클래스
- `portfolio/data_store.py` → `DataStore` 클래스

### 락 사용 패턴

```python
from threading import Lock, RLock

class FileCache:
    def __init__(self):
        self._lock = Lock()  # 단순 락

    def get(self, key):
        with self._lock:  # 임계 영역
            # 파일 읽기
            pass

class DataStore:
    def __init__(self):
        self._lock = RLock()  # 재귀적 락 (중첩 호출 허용)

    def save_portfolio(self, portfolio):
        with self._lock:
            # 파일 쓰기
            pass
```

### Lock vs RLock
- **Lock**: 같은 스레드도 두 번 획득 불가 (단순한 경우)
- **RLock**: 같은 스레드에서 중첩 획득 가능 (메서드 간 호출 시)

### 주의사항
- 락 범위는 최소화 (성능)
- 데드락 방지: 락 획득 순서 일관성 유지
- 파일 I/O는 반드시 락 내부에서 수행

---

## 로깅

### 구현
모든 `print()` 문을 `logging` 모듈로 교체했습니다.

```python
import logging
logger = logging.getLogger(__name__)

# 사용
logger.debug("디버그 정보")
logger.info("일반 정보")
logger.warning("경고")
logger.error(f"오류 발생: {e}")
```

### 로깅 레벨 가이드
| 레벨 | 용도 |
|------|------|
| DEBUG | 개발/디버깅용 상세 정보 |
| INFO | 정상 작동 확인용 |
| WARNING | 잠재적 문제 |
| ERROR | 오류 발생 (복구 가능) |
| CRITICAL | 심각한 오류 (복구 불가) |

### 민감 정보 로깅 금지
```python
# 절대 로깅하지 말 것
logger.info(f"Password: {password}")  # ❌
logger.info(f"API Key: {api_key}")    # ❌
logger.info(f"Token: {token}")        # ❌

# 대신
logger.info("사용자 인증 성공")        # ✅
logger.debug(f"사용자 ID: {user_id}")  # ✅
```

---

## 예외 처리

### Bare Except 금지

```python
# Before (잘못된 방식)
try:
    something()
except:  # 모든 예외 포착 - SystemExit, KeyboardInterrupt 포함
    pass

# After (올바른 방식)
try:
    something()
except (ValueError, TypeError) as e:  # 구체적 예외 지정
    logger.error(f"오류: {e}")
except Exception as e:  # 일반 예외 (최소한 이것 사용)
    logger.error(f"예상치 못한 오류: {e}")
```

### 수정된 파일
- `portfolio/data_store.py`
- `korea/market_keywords.py`
- `dashboard/korea_page.py`
- `korea/dividend_calendar.py`
- `analysis/social_sentiment.py`
- `dashboard/ai_chat_page.py`
- `korea/dart_monitor.py`

---

## 보안 체크리스트

### 새 기능 개발 시
- [ ] 사용자 입력은 `Validator` 또는 `Sanitizer`로 검증
- [ ] 파일 경로는 `PathValidator`로 검증
- [ ] HTML 출력 시 `Sanitizer.html_escape()` 적용
- [ ] 파일 직렬화는 JSON만 사용 (Pickle 금지)
- [ ] 공유 자원 접근 시 락 사용
- [ ] `print()` 대신 `logger` 사용
- [ ] 구체적 예외 타입 지정

### 코드 리뷰 시
- [ ] 하드코딩된 비밀번호/API 키 없음
- [ ] SQL 쿼리에 파라미터 바인딩 사용
- [ ] 외부 입력 검증 여부
- [ ] 에러 메시지에 민감 정보 노출 없음

### 배포 전
- [ ] DEBUG 로그 비활성화
- [ ] 환경 변수로 설정 관리
- [ ] bcrypt 패키지 설치 확인
- [ ] 레거시 pickle 캐시 파일 삭제

---

## 관련 파일 목록

| 카테고리 | 파일 |
|----------|------|
| 인증 | `dashboard/auth.py` |
| 캐싱 | `utils/cache.py` |
| 검증 | `utils/validators.py` |
| 데이터 저장 | `portfolio/data_store.py` |
| 백업 | `utils/backup.py` |
| API | `utils/api_utils.py` |
| 알림 | `alerts/news_alert.py` |

---

## 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|----------|
| 2026-01 | 1.0 | 초기 보안 가이드 작성 |
| - | - | bcrypt 패스워드 해싱 적용 |
| - | - | Pickle → JSON 마이그레이션 |
| - | - | MD5 → SHA256 교체 |
| - | - | 입력 검증 모듈 확장 |
| - | - | 스레드 안전성 추가 |
