#!/bin/bash
# ===========================================
# NOTION 시장 예측 시스템 실행 스크립트 (Linux/Mac)
# ===========================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  NOTION 시장 예측 시스템${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 명령어 확인
COMMAND=${1:-dashboard}

case $COMMAND in
    dashboard|d)
        echo -e "${YELLOW}대시보드 시작 중...${NC}"
        echo "브라우저에서 http://localhost:8501 접속"
        echo ""
        streamlit run dashboard/app.py --server.port=8501
        ;;

    analyze|a)
        echo -e "${YELLOW}분석 실행 중...${NC}"
        python main.py
        ;;

    install|i)
        echo -e "${YELLOW}의존성 설치 중...${NC}"
        pip install -e .
        echo -e "${GREEN}설치 완료!${NC}"
        ;;

    install-full|if)
        echo -e "${YELLOW}전체 의존성 설치 중 (ML + AI 포함)...${NC}"
        pip install -e ".[full]"
        echo -e "${GREEN}설치 완료!${NC}"
        ;;

    docker|dk)
        echo -e "${YELLOW}Docker 컨테이너 빌드 및 실행...${NC}"
        docker-compose up --build -d
        echo -e "${GREEN}컨테이너 시작됨! http://localhost:8501${NC}"
        ;;

    docker-stop|dks)
        echo -e "${YELLOW}Docker 컨테이너 중지...${NC}"
        docker-compose down
        echo -e "${GREEN}중지됨${NC}"
        ;;

    test|t)
        echo -e "${YELLOW}테스트 실행 중...${NC}"
        pytest tests/ -v
        ;;

    help|h|*)
        echo "사용법: ./scripts/run.sh [명령어]"
        echo ""
        echo "명령어:"
        echo "  dashboard, d     대시보드 실행 (기본값)"
        echo "  analyze, a       콘솔 분석 실행"
        echo "  install, i       기본 의존성 설치"
        echo "  install-full, if 전체 의존성 설치 (ML+AI)"
        echo "  docker, dk       Docker 컨테이너 실행"
        echo "  docker-stop, dks Docker 컨테이너 중지"
        echo "  test, t          테스트 실행"
        echo "  help, h          도움말"
        ;;
esac
