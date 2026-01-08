# 📊 거시경제 기반 시장 예측 시스템

거시경제 지표, 자금 흐름, 뉴스 센티먼트, 기술적 분석을 종합하여 시장 방향을 확률적으로 예측하는 시스템입니다.

## 🌟 주요 기능

### 1. 데이터 수집
- **거시경제 지표**: FRED API를 통한 금리, 인플레이션, 고용, GDP 등 핵심 지표 수집
- **시장 데이터**: Yahoo Finance를 통한 주가, ETF, 채권, 환율 데이터
- **자금 흐름**: 섹터별 자금 유출입 추적
- **뉴스 분석**: RSS 피드 및 News API를 통한 경제 뉴스 수집

### 2. 분석
- **거시경제 분석**: 경기 사이클 판단, 수익률 곡선 분석
- **자금흐름 분석**: 위험 선호도, 섹터 로테이션 감지
- **센티먼트 분석**: 뉴스 감성 분석, 키워드 트렌드
- **기술적 분석**: 이동평균, RSI, MACD, 볼린저 밴드

### 3. 예측
- **확률 모델**: 다중 요소를 가중 결합한 시장 방향 확률
- **시나리오 분석**: 연착륙, 경착륙, 스태그플레이션 등 시나리오별 전망
- **자산 배분**: 시나리오 확률 기반 최적 포트폴리오 추천

### 4. 대시보드
- **Streamlit 기반**: 인터랙티브 웹 대시보드
- **실시간 시각화**: 차트, 게이지, 히트맵 등
- **커스터마이징**: 분석 가중치 조절 가능

## 📁 프로젝트 구조

```
├── data/                    # 데이터 수집 모듈
│   ├── macro_indicators.py  # 거시경제 지표
│   ├── market_data.py       # 시장 데이터
│   ├── fund_flow.py         # 자금 흐름
│   └── news_collector.py    # 뉴스 수집
│
├── analysis/                # 분석 모듈
│   ├── macro_analysis.py    # 거시경제 분석
│   ├── flow_analysis.py     # 자금흐름 분석
│   ├── sentiment.py         # 센티먼트 분석
│   └── technical.py         # 기술적 분석
│
├── prediction/              # 예측 모듈
│   ├── probability_model.py # 확률 예측
│   └── scenarios.py         # 시나리오 분석
│
├── dashboard/               # 대시보드
│   └── app.py               # Streamlit 앱
│
├── main.py                  # 메인 실행 파일
├── config.py                # 설정
├── requirements.txt         # 의존성
└── README.md
```

## 🚀 시작하기

### 설치

```bash
# 저장소 클론
git clone <repository-url>
cd macro-market-predictor

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### API 키 설정 (선택사항)

실시간 데이터를 사용하려면 API 키가 필요합니다:

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집하여 API 키 입력
```

- **FRED API**: https://fred.stlouisfed.org/docs/api/api_key.html
- **News API**: https://newsapi.org/

### 실행

#### 콘솔 분석

```bash
# 샘플 데이터로 분석
python main.py

# 실시간 데이터로 분석 (API 키 필요)
python main.py --live

# 결과를 JSON으로 저장
python main.py --output result.json
```

#### 대시보드

```bash
# 대시보드 실행
python main.py --mode dashboard

# 또는 직접 실행
streamlit run dashboard/app.py
```

브라우저에서 http://localhost:8501 접속

## 📊 출력 예시

```
============================================================
📊 거시경제 기반 시장 예측 시스템
   분석 시간: 2024-12-15 10:30:00
============================================================

🎯 예측 방향: 상승
   확률: 62.5%
   신뢰도: 71.3%

📝 예상 방향: 상승 (확률: 62.5%) | 주요 신호: macro (68%) | 중립 신호: sentiment (52%)

📊 시나리오 분석
가장 가능성 높은 시나리오: 연착륙
확률: 42.3%
설명: 인플레이션 완화, 경기 침체 없이 성장 둔화

💰 권장 자산 배분
   • 주식: 55.2%
   • 채권: 28.4%
   • 금: 8.7%
   • 현금: 7.7%
```

## ⚙️ 설정

### 분석 가중치 조절

`config.py` 또는 환경 변수에서 가중치 조절:

```python
# config.py
macro_weight: float = 0.30      # 거시경제 가중치
flow_weight: float = 0.25       # 자금흐름 가중치
sentiment_weight: float = 0.20  # 센티먼트 가중치
technical_weight: float = 0.25  # 기술적 가중치
```

### 대시보드에서 가중치 조절

사이드바의 슬라이더를 통해 실시간으로 가중치 조절 가능

## 📈 분석 방법론

### 경기 사이클 판단
- GDP 성장률 및 가속도
- 인플레이션 추세
- 실업률 변화
- 수익률 곡선 형태

### 확률 계산
1. 각 분석 모듈에서 0-1 범위의 점수 산출
2. 가중 평균으로 종합 점수 계산
3. 시나리오별 확률 분배
4. 베이지안 업데이트로 최종 확률 산출

### 시나리오
- **연착륙 (Soft Landing)**: 인플레이션 완화, 성장 둔화
- **경착륙 (Hard Landing)**: 경기 침체, 고용 악화
- **스태그플레이션**: 높은 인플레이션 + 경기 침체
- **강세장**: 강한 성장, 기업 실적 호조
- **회복**: 저점 통과 후 회복 국면

## ⚠️ 면책 조항

- 본 시스템의 예측은 **참고용**이며, 투자 결정의 유일한 근거가 되어서는 안 됩니다.
- 과거 성과는 미래 수익을 보장하지 않습니다.
- 투자에 따른 모든 책임은 투자자 본인에게 있습니다.
- 금융 전문가와 상담 후 투자 결정을 내리시기 바랍니다.

## 🔧 기술 스택

- **Python 3.9+**
- **데이터 수집**: yfinance, fredapi, newsapi-python, feedparser
- **데이터 처리**: pandas, numpy
- **ML/NLP**: scikit-learn, transformers (선택적)
- **시각화**: streamlit, plotly
- **기타**: python-dotenv

## 📝 라이선스

MIT License

## 🤝 기여

이슈와 PR을 환영합니다!
