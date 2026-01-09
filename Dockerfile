# ===========================================
# NOTION 시장 예측 시스템 Docker 이미지
# ===========================================
#
# 빌드: docker build -t notion-market .
# 실행: docker run -p 8501:8501 notion-market
# 환경변수 포함: docker run -p 8501:8501 --env-file .env notion-market
#

FROM python:3.11-slim

# 메타데이터
LABEL maintainer="NOTION Team"
LABEL description="거시경제 기반 시장 예측 시스템"
LABEL version="1.0.0"

# 환경 변수 설정
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# 작업 디렉토리
WORKDIR /app

# 시스템 의존성 (최소화)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# pip 업그레이드
RUN pip install --upgrade pip

# 의존성 먼저 설치 (캐시 활용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# bcrypt 추가 설치 (보안)
RUN pip install --no-cache-dir bcrypt>=4.0.0

# 애플리케이션 코드 복사
COPY . .

# 비루트 사용자 생성 (보안)
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app
USER appuser

# 데이터 디렉토리 생성
RUN mkdir -p /home/appuser/.notion_portfolio

# 포트 노출
EXPOSE 8501

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# 실행
CMD ["streamlit", "run", "dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
