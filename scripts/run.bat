@echo off
REM ===========================================
REM NOTION 시장 예측 시스템 실행 스크립트 (Windows)
REM ===========================================

setlocal enabledelayedexpansion

cd /d "%~dp0\.."

echo ========================================
echo   NOTION 시장 예측 시스템
echo ========================================
echo.

set COMMAND=%1
if "%COMMAND%"=="" set COMMAND=dashboard

if /i "%COMMAND%"=="dashboard" goto :dashboard
if /i "%COMMAND%"=="d" goto :dashboard
if /i "%COMMAND%"=="analyze" goto :analyze
if /i "%COMMAND%"=="a" goto :analyze
if /i "%COMMAND%"=="install" goto :install
if /i "%COMMAND%"=="i" goto :install
if /i "%COMMAND%"=="install-full" goto :install_full
if /i "%COMMAND%"=="if" goto :install_full
if /i "%COMMAND%"=="docker" goto :docker
if /i "%COMMAND%"=="dk" goto :docker
if /i "%COMMAND%"=="docker-stop" goto :docker_stop
if /i "%COMMAND%"=="dks" goto :docker_stop
if /i "%COMMAND%"=="test" goto :test
if /i "%COMMAND%"=="t" goto :test
goto :help

:dashboard
echo 대시보드 시작 중...
echo 브라우저에서 http://localhost:8501 접속
echo.
streamlit run dashboard/app.py --server.port=8501
goto :end

:analyze
echo 분석 실행 중...
python main.py
goto :end

:install
echo 의존성 설치 중...
pip install -e .
echo 설치 완료!
goto :end

:install_full
echo 전체 의존성 설치 중 (ML + AI 포함)...
pip install -e ".[full]"
echo 설치 완료!
goto :end

:docker
echo Docker 컨테이너 빌드 및 실행...
docker-compose up --build -d
echo 컨테이너 시작됨! http://localhost:8501
goto :end

:docker_stop
echo Docker 컨테이너 중지...
docker-compose down
echo 중지됨
goto :end

:test
echo 테스트 실행 중...
pytest tests/ -v
goto :end

:help
echo 사용법: run.bat [명령어]
echo.
echo 명령어:
echo   dashboard, d     대시보드 실행 (기본값)
echo   analyze, a       콘솔 분석 실행
echo   install, i       기본 의존성 설치
echo   install-full, if 전체 의존성 설치 (ML+AI)
echo   docker, dk       Docker 컨테이너 실행
echo   docker-stop, dks Docker 컨테이너 중지
echo   test, t          테스트 실행
echo   help, h          도움말
goto :end

:end
endlocal
