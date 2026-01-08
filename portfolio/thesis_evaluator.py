"""
투자 논리 평가 모듈
사용자의 매수 이유를 객관적으로 분석하고 평가합니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

from .portfolio import Position, InvestmentThesis


class ThesisRating(Enum):
    """논리 평가 등급"""
    STRONG = "매우 긍정"      # 논리가 현재 데이터와 강하게 일치
    POSITIVE = "긍정"         # 논리가 현재 데이터와 일치
    NEUTRAL = "중립"          # 판단 보류
    NEGATIVE = "부정"         # 논리와 현재 상황 불일치
    WEAK = "매우 부정"        # 논리가 현재 데이터와 크게 불일치


@dataclass
class ThesisEvaluation:
    """논리 평가 결과"""
    position: Position
    rating: ThesisRating
    score: float                    # -1 ~ 1
    confidence: float               # 0 ~ 1

    # 분석 결과
    fundamental_check: Dict         # 펀더멘털 체크
    technical_check: Dict           # 기술적 체크
    macro_alignment: Dict           # 거시경제 정합성
    risk_assessment: Dict           # 리스크 평가

    # 종합 의견
    strengths: List[str]            # 강점
    weaknesses: List[str]           # 약점
    recommendations: List[str]       # 권고사항
    probability_assessment: Dict     # 확률적 평가


class ThesisEvaluator:
    """투자 논리 평가 클래스"""

    # 논리 유형별 체크 포인트
    THESIS_CHECKPOINTS = {
        InvestmentThesis.GROWTH: [
            'revenue_growth',      # 매출 성장률
            'earnings_growth',     # 이익 성장률
            'market_expansion',    # 시장 확대
            'competitive_moat',    # 경쟁 해자
            'price_momentum',      # 가격 모멘텀
        ],
        InvestmentThesis.VALUE: [
            'pe_ratio',            # PER
            'pb_ratio',            # PBR
            'dividend_yield',      # 배당 수익률
            'fcf_yield',           # FCF 수익률
            'margin_of_safety',    # 안전 마진
        ],
        InvestmentThesis.DIVIDEND: [
            'dividend_yield',
            'dividend_growth',     # 배당 성장
            'payout_ratio',        # 배당 성향
            'dividend_consistency', # 배당 지속성
        ],
        InvestmentThesis.MOMENTUM: [
            'price_trend',         # 가격 추세
            'relative_strength',   # 상대 강도
            'volume_trend',        # 거래량 추세
            'breakout_status',     # 돌파 여부
        ],
        InvestmentThesis.MACRO: [
            'interest_rate_sensitivity',  # 금리 민감도
            'inflation_hedge',            # 인플레 헷지
            'economic_cycle',             # 경기 사이클
            'sector_outlook',             # 섹터 전망
        ],
        InvestmentThesis.SECTOR_ROTATION: [
            'sector_momentum',     # 섹터 모멘텀
            'relative_performance', # 상대 성과
            'cycle_position',      # 사이클 위치
        ],
        InvestmentThesis.TECHNICAL: [
            'trend_direction',
            'support_resistance',
            'momentum_indicators',
            'volume_analysis',
        ],
    }

    # 키워드 분석용 (투자 논리 텍스트에서 추출)
    POSITIVE_KEYWORDS = {
        'growth': ['성장', '확대', '증가', '급증', 'growth', 'expansion', 'increase'],
        'value': ['저평가', '할인', '저렴', 'undervalued', 'cheap', 'discount'],
        'dividend': ['배당', '수익률', 'dividend', 'yield', 'income'],
        'moat': ['독점', '해자', '경쟁력', 'monopoly', 'moat', 'competitive'],
        'catalyst': ['촉매', '이벤트', '발표', 'catalyst', 'event', 'announcement'],
    }

    RISK_KEYWORDS = {
        'high_valuation': ['고평가', '버블', 'overvalued', 'expensive', 'bubble'],
        'competition': ['경쟁', '위협', 'competition', 'threat', 'disrupt'],
        'regulation': ['규제', '법률', 'regulation', 'legal', 'antitrust'],
        'macro_risk': ['금리', '인플레', '경기침체', 'interest', 'inflation', 'recession'],
    }

    # 기업별 핵심 투자 테마 정보 (출처 및 신뢰도 포함)
    COMPANY_KNOWLEDGE = {
        # 현대차 그룹
        '005380.KS': {  # 현대차
            'name': '현대자동차',
            'themes': {
                '로봇': {
                    'subsidiary': '보스턴 다이나믹스 (Boston Dynamics)',
                    'subsidiary_source': '현대차 공시 (2021.06)',
                    'subsidiary_confidence': 100,
                    'acquisition': '2021년 약 11억 달러(약 1.1조원)에 인수, 지분 80% 확보',
                    'acquisition_source': '현대차그룹 공식 발표 및 SEC 공시',
                    'acquisition_confidence': 100,
                    'products': ['Spot (4족 보행 로봇)', 'Atlas (휴머노이드)', 'Stretch (물류 로봇)'],
                    'products_source': '보스턴 다이나믹스 공식 홈페이지',
                    'products_confidence': 100,
                    'revenue_contribution': '전체 매출의 1% 미만 추정 (별도 공시 없음)',
                    'revenue_source': '애널리스트 추정치 종합, 사업보고서 미공개',
                    'revenue_confidence': 40,  # 추정치라서 낮음
                    'competitors': ['테슬라 옵티머스', '샤오미 CyberDog', '유니트리', 'Figure AI'],
                    'competitors_source': '산업 리서치 및 뉴스 종합',
                    'competitors_confidence': 85,
                    'risks': [
                        {'risk': '로봇 상용화 지연', 'confidence': 80, 'source': '산업 전문가 의견'},
                        {'risk': '연간 R&D 비용 약 3000억원 이상 추정', 'confidence': 50, 'source': '애널리스트 추정'},
                        {'risk': '수익화 시점 2027년 이후 전망', 'confidence': 60, 'source': '증권사 리포트 종합'},
                    ],
                    'catalysts': [
                        {'catalyst': '현대차 공장 Spot 로봇 도입 확대', 'confidence': 90, 'source': '현대차 뉴스룸'},
                        {'catalyst': '물류 로봇 Stretch 상용화', 'confidence': 70, 'source': '보스턴 다이나믹스 발표'},
                        {'catalyst': '휴머노이드 Atlas 양산', 'confidence': 40, 'source': '기술 개발 단계, 양산 일정 미정'},
                    ],
                    'investor_mindset': '전기차를 넘어 로봇/모빌리티 기업으로의 전환에 베팅',
                    'key_question': '보스턴 다이나믹스가 언제 흑자전환하고 현대차 실적에 의미있게 기여할 것인가?',
                },
                '전기차': {
                    'models': ['아이오닉5', '아이오닉6', 'EV9', '캐스퍼 일렉트릭'],
                    'platform': 'E-GMP 전용 플랫폼',
                    'market_share': '글로벌 전기차 판매 4위권',
                    'risks': ['테슬라/중국 업체와의 가격 경쟁', '배터리 원가'],
                    'investor_mindset': '전기차 전환 수혜, 현대차의 기술력 신뢰',
                },
            },
        },
        '000270.KS': {  # 기아
            'name': '기아',
            'themes': {
                '전기차': {
                    'models': ['EV6', 'EV9', 'EV3', 'EV5'],
                    'strength': 'EV6 - 유럽 올해의 차 수상',
                    'risks': ['전기차 성장 둔화', '중국 업체 경쟁'],
                    'investor_mindset': '현대차그룹 전기차 수혜주',
                },
                'PBV': {
                    'concept': 'Purpose Built Vehicle (목적 기반 차량)',
                    'examples': ['로보택시', '배송 차량', '이동식 사무실'],
                    'investor_mindset': '미래 모빌리티 신사업 기대',
                },
            },
        },
        # 삼성전자
        '005930.KS': {
            'name': '삼성전자',
            'themes': {
                'AI': {
                    'products': ['HBM3E 메모리', '갤럭시 AI', '엑시노스'],
                    'hbm_status': 'HBM3E 엔비디아 퀄 진행 중 (2024년 기준)',
                    'risks': ['SK하이닉스 대비 HBM 기술 격차', '파운드리 수율'],
                    'investor_mindset': 'AI 반도체 수요 급증 수혜 기대',
                },
                '반도체': {
                    'segments': ['메모리 (DRAM/NAND)', '파운드리', '시스템LSI'],
                    'market_position': '메모리 1위, 파운드리 2위',
                    'risks': ['중국 업체 추격', '사이클 변동성'],
                    'investor_mindset': '반도체 슈퍼사이클 수혜',
                },
            },
        },
        # SK하이닉스
        '000660.KS': {
            'name': 'SK하이닉스',
            'themes': {
                'AI': {
                    'products': ['HBM3E', 'HBM4 개발 중'],
                    'customer': '엔비디아 HBM 독점 공급 (2024년 기준)',
                    'market_share': 'HBM 시장 점유율 50% 이상',
                    'risks': ['삼성 추격', '공급 과잉 가능성'],
                    'investor_mindset': 'AI 반도체 최대 수혜주, 엔비디아 파트너',
                },
            },
        },
        # 네이버
        '035420.KS': {
            'name': '네이버',
            'themes': {
                'AI': {
                    'products': ['하이퍼클로바X', '서치GPT', 'CLOVA'],
                    'strategy': '검색/커머스에 AI 통합',
                    'risks': ['글로벌 빅테크 경쟁', 'AI 투자 비용'],
                    'investor_mindset': '한국 대표 AI 플랫폼 기업',
                },
            },
        },
        # 미국 주식
        'NVDA': {
            'name': '엔비디아',
            'themes': {
                'AI': {
                    'products': ['H100', 'H200', 'Blackwell B100/B200'],
                    'market_position': 'AI GPU 시장 점유율 80% 이상',
                    'customers': ['MS', 'Meta', 'Google', 'Amazon', '오픈AI'],
                    'risks': ['AMD/인텔 경쟁', '중국 수출 규제', '고객사 자체 칩 개발'],
                    'investor_mindset': 'AI 인프라 필수 기업, AI 골드러시의 곡괭이',
                },
            },
        },
        'TSLA': {
            'name': '테슬라',
            'themes': {
                '로봇': {
                    'product': '옵티머스 (Optimus) 휴머노이드 로봇',
                    'timeline': '2025년 한정 판매, 2026년 대량 생산 목표',
                    'use_case': '공장 자동화, 가정용 로봇',
                    'risks': ['기술 완성도', '상용화 지연', '보스턴 다이나믹스 등 경쟁'],
                    'investor_mindset': '테슬라를 자동차가 아닌 AI/로봇 기업으로 평가',
                },
                '전기차': {
                    'models': ['Model 3', 'Model Y', 'Cybertruck', 'Model 2 (저가형)'],
                    'risks': ['중국 업체 경쟁', '가격 인하 압박'],
                    'investor_mindset': '전기차 리더, 자율주행 기술력',
                },
                'FSD': {
                    'product': 'Full Self-Driving (완전자율주행)',
                    'status': 'FSD v12 - 순수 AI 기반',
                    'risks': ['규제', '사고 책임', '기술 완성도'],
                    'investor_mindset': '로보택시 사업 기대',
                },
            },
        },
        'AAPL': {
            'name': '애플',
            'themes': {
                'AI': {
                    'products': ['Apple Intelligence', 'Siri 강화', '온디바이스 AI'],
                    'strategy': '프라이버시 중심 온디바이스 AI',
                    'risks': ['AI 후발주자', '오픈AI 의존'],
                    'investor_mindset': 'AI 기능으로 아이폰 교체 사이클 기대',
                },
                'VR': {
                    'product': 'Vision Pro',
                    'risks': ['높은 가격', '킬러 앱 부재'],
                    'investor_mindset': '새로운 컴퓨팅 플랫폼 기대',
                },
            },
        },
        'MSFT': {
            'name': '마이크로소프트',
            'themes': {
                'AI': {
                    'products': ['Copilot', 'Azure OpenAI', 'GitHub Copilot'],
                    'partnership': '오픈AI 최대 투자자 (130억 달러+)',
                    'strategy': '전 제품에 AI 통합',
                    'investor_mindset': 'AI 시대 최대 수혜 기업, 오픈AI 파트너',
                },
            },
        },
        'GOOGL': {
            'name': '구글 (알파벳)',
            'themes': {
                'AI': {
                    'products': ['Gemini', 'Bard', 'TPU'],
                    'risks': ['검색 시장 잠식 우려', 'AI 경쟁 후발'],
                    'investor_mindset': 'AI 원천 기술력, 데이터 우위',
                },
            },
        },
    }

    def __init__(self):
        """초기화"""
        self.cache = {}

    def get_stock_data(self, symbol: str, period: str = '1y') -> Optional[pd.DataFrame]:
        """주가 데이터 조회"""
        if not YFINANCE_AVAILABLE:
            return None

        cache_key = f"{symbol}_{period}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            self.cache[cache_key] = data
            return data
        except Exception as e:
            print(f"데이터 조회 실패 ({symbol}): {e}")
            return None

    def get_fundamental_data(self, symbol: str) -> Dict:
        """펀더멘털 데이터 조회"""
        if not YFINANCE_AVAILABLE:
            return {}

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            return {
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'pb_ratio': info.get('priceToBook'),
                'ps_ratio': info.get('priceToSalesTrailing12Months'),
                'dividend_yield': info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
                'payout_ratio': info.get('payoutRatio', 0) * 100 if info.get('payoutRatio') else 0,
                'revenue_growth': info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else 0,
                'earnings_growth': info.get('earningsGrowth', 0) * 100 if info.get('earningsGrowth') else 0,
                'profit_margin': info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 0,
                'roe': info.get('returnOnEquity', 0) * 100 if info.get('returnOnEquity') else 0,
                'debt_to_equity': info.get('debtToEquity'),
                'current_ratio': info.get('currentRatio'),
                'market_cap': info.get('marketCap'),
                'beta': info.get('beta'),
                '52w_high': info.get('fiftyTwoWeekHigh'),
                '52w_low': info.get('fiftyTwoWeekLow'),
                'avg_volume': info.get('averageVolume'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
            }
        except Exception as e:
            print(f"펀더멘털 조회 실패 ({symbol}): {e}")
            return {}

    def analyze_thesis_keywords(self, thesis_description: str) -> Dict:
        """투자 논리 키워드 분석"""
        text_lower = thesis_description.lower()

        positive_found = []
        risk_found = []

        for category, keywords in self.POSITIVE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    positive_found.append({'category': category, 'keyword': keyword})

        for category, keywords in self.RISK_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    risk_found.append({'category': category, 'keyword': keyword})

        return {
            'positive_factors': positive_found,
            'risk_factors': risk_found,
            'positive_count': len(positive_found),
            'risk_count': len(risk_found),
        }

    def check_fundamental_alignment(self, position: Position, fundamentals: Dict) -> Dict:
        """펀더멘털 정합성 체크"""
        checks = {
            'passed': [],
            'failed': [],
            'warnings': [],
            'score': 0,
        }

        thesis_type = position.thesis_type

        # 성장주 체크
        if thesis_type == InvestmentThesis.GROWTH:
            revenue_growth = fundamentals.get('revenue_growth', 0)
            earnings_growth = fundamentals.get('earnings_growth', 0)

            if revenue_growth > 15:
                checks['passed'].append(f"매출 성장률 양호: {revenue_growth:.1f}%")
            elif revenue_growth > 0:
                checks['warnings'].append(f"매출 성장률 보통: {revenue_growth:.1f}%")
            else:
                checks['failed'].append(f"매출 역성장: {revenue_growth:.1f}%")

            if earnings_growth > 15:
                checks['passed'].append(f"이익 성장률 양호: {earnings_growth:.1f}%")
            elif earnings_growth > 0:
                checks['warnings'].append(f"이익 성장률 보통: {earnings_growth:.1f}%")
            else:
                checks['failed'].append(f"이익 역성장: {earnings_growth:.1f}%")

            # PEG 비율 체크
            pe = fundamentals.get('forward_pe', 0)
            if pe and earnings_growth > 0:
                peg = pe / earnings_growth
                if peg < 1:
                    checks['passed'].append(f"PEG 비율 양호: {peg:.2f}")
                elif peg < 2:
                    checks['warnings'].append(f"PEG 비율 보통: {peg:.2f}")
                else:
                    checks['failed'].append(f"PEG 비율 높음: {peg:.2f}")

        # 가치주 체크
        elif thesis_type == InvestmentThesis.VALUE:
            pe = fundamentals.get('pe_ratio')
            pb = fundamentals.get('pb_ratio')

            if pe:
                if pe < 15:
                    checks['passed'].append(f"PER 저평가: {pe:.1f}")
                elif pe < 25:
                    checks['warnings'].append(f"PER 적정: {pe:.1f}")
                else:
                    checks['failed'].append(f"PER 고평가: {pe:.1f}")

            if pb:
                if pb < 1.5:
                    checks['passed'].append(f"PBR 저평가: {pb:.2f}")
                elif pb < 3:
                    checks['warnings'].append(f"PBR 적정: {pb:.2f}")
                else:
                    checks['failed'].append(f"PBR 고평가: {pb:.2f}")

        # 배당주 체크
        elif thesis_type == InvestmentThesis.DIVIDEND:
            div_yield = fundamentals.get('dividend_yield', 0)
            payout = fundamentals.get('payout_ratio', 0)

            if div_yield > 3:
                checks['passed'].append(f"배당 수익률 양호: {div_yield:.2f}%")
            elif div_yield > 1.5:
                checks['warnings'].append(f"배당 수익률 보통: {div_yield:.2f}%")
            else:
                checks['failed'].append(f"배당 수익률 낮음: {div_yield:.2f}%")

            if 30 < payout < 70:
                checks['passed'].append(f"배당 성향 적정: {payout:.1f}%")
            elif payout > 90:
                checks['failed'].append(f"배당 성향 과다: {payout:.1f}%")

        # 점수 계산
        total_checks = len(checks['passed']) + len(checks['failed']) + len(checks['warnings'])
        if total_checks > 0:
            score = (len(checks['passed']) - len(checks['failed']) * 0.5) / total_checks
            checks['score'] = max(min(score, 1), -1)

        return checks

    def check_technical_alignment(self, position: Position, price_data: pd.DataFrame) -> Dict:
        """기술적 분석 정합성 체크"""
        checks = {
            'passed': [],
            'failed': [],
            'warnings': [],
            'indicators': {},
            'score': 0,
        }

        if price_data is None or price_data.empty:
            return checks

        close = price_data['Close']
        current_price = close.iloc[-1]

        # 이동평균
        ma_20 = close.rolling(20).mean().iloc[-1]
        ma_50 = close.rolling(50).mean().iloc[-1]
        ma_200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None

        checks['indicators']['ma_20'] = ma_20
        checks['indicators']['ma_50'] = ma_50
        checks['indicators']['ma_200'] = ma_200

        # 추세 체크
        if current_price > ma_20 > ma_50:
            checks['passed'].append("단기 상승 추세 (가격 > MA20 > MA50)")
        elif current_price < ma_20 < ma_50:
            checks['failed'].append("단기 하락 추세 (가격 < MA20 < MA50)")
        else:
            checks['warnings'].append("혼조세")

        if ma_200 and current_price > ma_200:
            checks['passed'].append("장기 상승 추세 (200일선 위)")
        elif ma_200:
            checks['failed'].append("장기 하락 추세 (200일선 아래)")

        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]

        checks['indicators']['rsi'] = current_rsi

        if 30 < current_rsi < 70:
            checks['passed'].append(f"RSI 중립 구간: {current_rsi:.1f}")
        elif current_rsi > 70:
            checks['warnings'].append(f"RSI 과매수: {current_rsi:.1f}")
        else:
            checks['warnings'].append(f"RSI 과매도: {current_rsi:.1f}")

        # 52주 고저점 대비
        high_52w = close.tail(252).max() if len(close) >= 252 else close.max()
        low_52w = close.tail(252).min() if len(close) >= 252 else close.min()

        from_high = (current_price / high_52w - 1) * 100
        from_low = (current_price / low_52w - 1) * 100

        checks['indicators']['from_52w_high'] = from_high
        checks['indicators']['from_52w_low'] = from_low

        if from_high > -10:
            checks['passed'].append(f"52주 고점 근처 ({from_high:.1f}%)")
        elif from_high < -30:
            checks['failed'].append(f"52주 고점 대비 크게 하락 ({from_high:.1f}%)")

        # 수익률 분석
        returns_1m = (current_price / close.iloc[-21] - 1) * 100 if len(close) >= 21 else 0
        returns_3m = (current_price / close.iloc[-63] - 1) * 100 if len(close) >= 63 else 0

        checks['indicators']['return_1m'] = returns_1m
        checks['indicators']['return_3m'] = returns_3m

        # 모멘텀 투자 논리일 경우
        if position.thesis_type == InvestmentThesis.MOMENTUM:
            if returns_1m > 5 and returns_3m > 10:
                checks['passed'].append("강한 모멘텀 확인")
            elif returns_1m < 0 and returns_3m < 0:
                checks['failed'].append("모멘텀 약화")

        # 점수 계산
        total = len(checks['passed']) + len(checks['failed']) + len(checks['warnings'])
        if total > 0:
            score = (len(checks['passed']) - len(checks['failed']) * 0.5) / total
            checks['score'] = max(min(score, 1), -1)

        return checks

    def assess_risk(self, position: Position, fundamentals: Dict, price_data: pd.DataFrame) -> Dict:
        """리스크 평가"""
        risk_assessment = {
            'overall_risk': 'medium',
            'risk_score': 0.5,  # 0 (낮음) ~ 1 (높음)
            'risks': [],
            'mitigants': [],
        }

        # 변동성 리스크
        if price_data is not None and not price_data.empty:
            returns = price_data['Close'].pct_change()
            volatility = returns.std() * np.sqrt(252) * 100

            if volatility > 40:
                risk_assessment['risks'].append(f"높은 변동성: {volatility:.1f}%")
                risk_assessment['risk_score'] += 0.2
            elif volatility < 20:
                risk_assessment['mitigants'].append(f"낮은 변동성: {volatility:.1f}%")

        # 밸류에이션 리스크
        pe = fundamentals.get('pe_ratio')
        if pe and pe > 40:
            risk_assessment['risks'].append(f"높은 밸류에이션 (PER: {pe:.1f})")
            risk_assessment['risk_score'] += 0.15

        # 부채 리스크
        debt_equity = fundamentals.get('debt_to_equity')
        if debt_equity and debt_equity > 2:
            risk_assessment['risks'].append(f"높은 부채 비율: {debt_equity:.2f}")
            risk_assessment['risk_score'] += 0.15

        # 베타 리스크
        beta = fundamentals.get('beta')
        if beta and beta > 1.5:
            risk_assessment['risks'].append(f"높은 시장 민감도 (Beta: {beta:.2f})")
            risk_assessment['risk_score'] += 0.1
        elif beta and beta < 0.8:
            risk_assessment['mitigants'].append(f"낮은 시장 민감도 (Beta: {beta:.2f})")

        # 손절가 대비 현재가
        if position.stop_loss and position.current_price:
            downside = (position.stop_loss / position.current_price - 1) * 100
            if downside > -5:
                risk_assessment['risks'].append(f"손절가 근접: {abs(downside):.1f}% 하락 시 손절")
                risk_assessment['risk_score'] += 0.2

        # 목표가 대비 현재가
        if position.target_price and position.current_price:
            upside = (position.target_price / position.current_price - 1) * 100
            if upside < 5:
                risk_assessment['warnings'] = ["목표가 근접 - 출구 전략 검토 필요"]

        # 전체 리스크 레벨
        if risk_assessment['risk_score'] > 0.7:
            risk_assessment['overall_risk'] = 'high'
        elif risk_assessment['risk_score'] < 0.3:
            risk_assessment['overall_risk'] = 'low'

        return risk_assessment

    def calculate_probability_assessment(self, position: Position,
                                         fundamental_check: Dict,
                                         technical_check: Dict,
                                         risk_assessment: Dict) -> Dict:
        """확률적 평가"""
        # 목표가 도달 확률 추정
        target_probability = 0.5
        stop_probability = 0.5

        # 펀더멘털 점수 반영
        fundamental_score = fundamental_check.get('score', 0)
        target_probability += fundamental_score * 0.15

        # 기술적 점수 반영
        technical_score = technical_check.get('score', 0)
        target_probability += technical_score * 0.15

        # 리스크 반영
        risk_score = risk_assessment.get('risk_score', 0.5)
        stop_probability = 0.2 + risk_score * 0.3

        # 기대값 계산
        if position.target_price and position.stop_loss and position.current_price:
            upside = (position.target_price / position.current_price - 1) * 100
            downside = (position.stop_loss / position.current_price - 1) * 100

            expected_return = (target_probability * upside) + (stop_probability * downside)
            risk_reward_ratio = abs(upside / downside) if downside != 0 else 0

            return {
                'target_probability': min(max(target_probability, 0.1), 0.9) * 100,
                'stop_probability': min(max(stop_probability, 0.1), 0.5) * 100,
                'upside_potential': upside,
                'downside_risk': downside,
                'expected_return': expected_return,
                'risk_reward_ratio': risk_reward_ratio,
                'kelly_fraction': (target_probability * risk_reward_ratio - (1 - target_probability)) / risk_reward_ratio if risk_reward_ratio > 0 else 0,
            }

        return {
            'target_probability': target_probability * 100,
            'stop_probability': stop_probability * 100,
        }

    def _generate_detailed_recommendations(
        self, position: Position, fundamentals: Dict, price_data: pd.DataFrame,
        fundamental_check: Dict, technical_check: Dict, risk_assessment: Dict,
        overall_score: float, keyword_analysis: Dict
    ) -> List[str]:
        """투자 논리 유형과 데이터 기반의 자연스러운 애널리스트 스타일 권고사항 생성"""
        recommendations = []
        thesis_type = position.thesis_type
        thesis_desc = position.thesis_description if position.thesis_description else ""
        thesis_lower = thesis_desc.lower()

        name = position.name or position.symbol
        sector = fundamentals.get('sector', '')
        industry = fundamentals.get('industry', '')

        # 기본 데이터 추출
        revenue_growth = fundamentals.get('revenue_growth', 0) or 0
        earnings_growth = fundamentals.get('earnings_growth', 0) or 0
        pe = fundamentals.get('pe_ratio') or fundamentals.get('forward_pe')
        pb = fundamentals.get('pb_ratio')
        roe = fundamentals.get('roe', 0) or 0
        debt_equity = fundamentals.get('debt_to_equity')
        div_yield = fundamentals.get('dividend_yield', 0) or 0

        indicators = technical_check.get('indicators', {})
        rsi = indicators.get('rsi', 50)
        return_1m = indicators.get('return_1m', 0)
        return_3m = indicators.get('return_3m', 0)
        from_high = indicators.get('from_52w_high', 0)

        # === 1. 자연스러운 종합 분석 ===
        intro = f"📋 **{name} 투자논리 분석**\n\n"

        if thesis_desc:
            intro += f"입력하신 투자 논리는 \"{thesis_desc}\"입니다. "

        # 섹터 정보 추가
        if sector:
            intro += f"{name}은(는) {sector} 섹터에 속해 있습니다. "

        recommendations.append(intro)

        # === 2. 기업별 맞춤 분석 (지식 베이스 활용) ===
        company_info = self.COMPANY_KNOWLEDGE.get(position.symbol, {})
        company_themes = company_info.get('themes', {})

        # 테마 매칭 (사용자 입력과 기업 지식 매칭)
        matched_theme = None
        matched_theme_key = None
        for theme_key, theme_info in company_themes.items():
            if theme_key.lower() in thesis_lower or any(kw in thesis_lower for kw in [theme_key, theme_key.lower()]):
                matched_theme = theme_info
                matched_theme_key = theme_key
                break

        # 신뢰도 표시 함수
        def confidence_badge(conf: int) -> str:
            if conf >= 90:
                return f"[신뢰도 {conf}% 🟢]"
            elif conf >= 70:
                return f"[신뢰도 {conf}% 🟡]"
            elif conf >= 50:
                return f"[신뢰도 {conf}% 🟠]"
            else:
                return f"[신뢰도 {conf}% 🔴 추정치]"

        # 로봇/신사업 관련
        if any(kw in thesis_lower for kw in ['로봇', 'robot', '신사업', '미래', '새로운', '대세']):
            # 기업별 맞춤 분석
            if matched_theme and matched_theme_key in ['로봇', 'robot']:
                analysis = f"🤖 **{name} 로봇 사업 심층 분석**\n\n"
                analysis += f"말씀하신 대로 '{thesis_desc}' - 이 관점을 이해합니다.\n\n"

                # 자회사/핵심 정보 (출처 포함)
                if 'subsidiary' in matched_theme:
                    conf = matched_theme.get('subsidiary_confidence', 0)
                    src = matched_theme.get('subsidiary_source', '')
                    analysis += f"**핵심 자회사**: {matched_theme['subsidiary']}\n"
                    analysis += f"  └ 출처: {src} {confidence_badge(conf)}\n\n"

                if 'acquisition' in matched_theme:
                    conf = matched_theme.get('acquisition_confidence', 0)
                    src = matched_theme.get('acquisition_source', '')
                    analysis += f"**인수 정보**: {matched_theme['acquisition']}\n"
                    analysis += f"  └ 출처: {src} {confidence_badge(conf)}\n\n"

                if 'products' in matched_theme:
                    conf = matched_theme.get('products_confidence', 0)
                    src = matched_theme.get('products_source', '')
                    analysis += f"**주요 제품**: {', '.join(matched_theme['products'])}\n"
                    analysis += f"  └ 출처: {src} {confidence_badge(conf)}\n\n"

                # 투자자 관점 이해
                if 'investor_mindset' in matched_theme:
                    analysis += f"💭 **투자자님의 관점 이해**: {matched_theme['investor_mindset']}\n\n"

                # 핵심 질문
                if 'key_question' in matched_theme:
                    analysis += f"❓ **핵심 질문**: {matched_theme['key_question']}\n\n"

                # 현실 체크 (출처/신뢰도 포함)
                if 'revenue_contribution' in matched_theme:
                    conf = matched_theme.get('revenue_confidence', 0)
                    src = matched_theme.get('revenue_source', '')
                    analysis += f"⚠️ **현실 체크**: {matched_theme['revenue_contribution']}\n"
                    analysis += f"  └ 출처: {src} {confidence_badge(conf)}\n"
                    analysis += f"  └ 즉, 로봇 테마가 현재 실적에 미치는 영향은 제한적입니다.\n"
                    analysis += f"  └ 이는 '미래 가치'에 대한 베팅임을 인지하셔야 합니다.\n\n"

                # 경쟁 구도
                if 'competitors' in matched_theme:
                    conf = matched_theme.get('competitors_confidence', 0)
                    src = matched_theme.get('competitors_source', '')
                    analysis += f"**경쟁사**: {', '.join(matched_theme['competitors'])}\n"
                    analysis += f"  └ 출처: {src} {confidence_badge(conf)}\n"
                    analysis += f"  └ 보스턴 다이나믹스의 기술력은 뛰어나지만, 상용화와 수익화는 별개입니다.\n\n"

                # 리스크 (개별 신뢰도 포함)
                risks = matched_theme.get('risks', [])
                if risks:
                    analysis += f"**핵심 리스크**:\n"
                    for r in risks:
                        if isinstance(r, dict):
                            conf = r.get('confidence', 0)
                            src = r.get('source', '')
                            analysis += f"  • {r['risk']} {confidence_badge(conf)}\n"
                            analysis += f"    └ 근거: {src}\n"
                        else:
                            analysis += f"  • {r}\n"
                    analysis += "\n"

                # 촉매 (개별 신뢰도 포함)
                catalysts = matched_theme.get('catalysts', [])
                if catalysts:
                    analysis += f"**주시할 촉매**:\n"
                    for c in catalysts:
                        if isinstance(c, dict):
                            conf = c.get('confidence', 0)
                            src = c.get('source', '')
                            analysis += f"  • {c['catalyst']} {confidence_badge(conf)}\n"
                            analysis += f"    └ 근거: {src}\n"
                        else:
                            analysis += f"  • {c}\n"

                recommendations.append(analysis)
            else:
                # 일반적인 로봇/신사업 분석 (지식 없는 경우)
                analysis = f"🤖 **신사업(로봇) 논리 분석**\n\n"
                analysis += f"말씀하신 '{thesis_desc}' 논리에 대해 검토해보겠습니다.\n\n"

                if revenue_growth < 15:
                    analysis += f"현재 {name}의 전체 매출 성장률은 {revenue_growth:.1f}%입니다. "
                    analysis += f"로봇/신사업이 아직 전체 매출에서 차지하는 비중이 미미할 가능성이 높습니다. "
                    analysis += f"신사업 테마로 투자하실 경우, 해당 사업부의 매출 비중과 성장률을 별도로 확인하셔야 합니다.\n\n"

                if earnings_growth < 0:
                    analysis += f"⚠️ 특히 전체 이익이 {earnings_growth:.1f}% 역성장 중인 점이 우려됩니다. "
                    analysis += f"신사업 투자로 인한 비용 증가가 수익성을 압박하고 있을 수 있습니다.\n\n"

                analysis += f"**체크포인트**: 해당 신사업부 매출 비중, 경쟁사 대비 기술력, 수주 현황을 분기별로 확인하시기 바랍니다."
                recommendations.append(analysis)

        # AI 관련
        elif any(kw in thesis_lower for kw in ['ai', '인공지능', 'artificial', '반도체', 'hbm']):
            # 기업별 AI 지식이 있는 경우
            ai_theme = company_themes.get('AI', {})
            if ai_theme:
                analysis = f"🧠 **{name} AI 사업 심층 분석**\n\n"
                analysis += f"말씀하신 '{thesis_desc}' 관점을 이해합니다.\n\n"

                if 'products' in ai_theme:
                    analysis += f"**AI 관련 제품/서비스**: {', '.join(ai_theme['products'])}\n"
                if 'market_position' in ai_theme:
                    analysis += f"**시장 지위**: {ai_theme['market_position']}\n"
                if 'customer' in ai_theme:
                    analysis += f"**핵심 고객**: {ai_theme['customer']}\n"
                if 'partnership' in ai_theme:
                    analysis += f"**파트너십**: {ai_theme['partnership']}\n"

                if 'investor_mindset' in ai_theme:
                    analysis += f"\n💭 **투자자님의 관점**: {ai_theme['investor_mindset']}\n\n"

                # 현실 체크
                if revenue_growth > 30:
                    analysis += f"✅ 매출이 {revenue_growth:.1f}% 성장 중으로, AI 수혜가 실적에 반영되고 있습니다.\n\n"
                else:
                    analysis += f"⚠️ 전체 매출 성장률은 {revenue_growth:.1f}%입니다. AI 사업이 전체에서 차지하는 비중을 확인해보세요.\n\n"

                if 'risks' in ai_theme:
                    analysis += f"**핵심 리스크**:\n"
                    for risk in ai_theme['risks']:
                        analysis += f"  • {risk}\n"

                recommendations.append(analysis)
            else:
                # 일반 AI 분석
                analysis = f"🧠 **AI 성장 논리 분석**\n\n"

                if revenue_growth > 30:
                    analysis += f"매출이 {revenue_growth:.1f}% 성장 중으로, AI 수혜가 실적에 반영되고 있는 것으로 보입니다. "
                else:
                    analysis += f"현재 매출 성장률은 {revenue_growth:.1f}%입니다. "
                    analysis += f"AI 테마에 대한 시장의 기대가 선반영되어 있을 가능성이 있습니다. "
                    analysis += f"실제 AI 관련 매출이 전체에서 차지하는 비중을 확인해보셔야 합니다.\n\n"

                if pe and pe > 30:
                    analysis += f"PER {pe:.1f}x로 고평가 구간입니다. AI 성장이 기대에 미치지 못할 경우 밸류에이션 조정 위험이 있습니다."

                recommendations.append(analysis)

        # 성장주 일반
        elif thesis_type == InvestmentThesis.GROWTH or any(kw in thesis_lower for kw in ['성장', 'growth', '확장']):
            analysis = f"📈 **성장주 논리 분석**\n\n"

            if revenue_growth > 20 and earnings_growth > 20:
                analysis += f"매출 {revenue_growth:.1f}%, 이익 {earnings_growth:.1f}% 성장으로 성장주 논리가 유효합니다. "
            elif revenue_growth > 0 and earnings_growth < 0:
                analysis += f"매출은 {revenue_growth:.1f}% 성장하고 있으나, 이익은 {earnings_growth:.1f}% 역성장 중입니다. "
                analysis += f"성장을 위한 투자 비용이 수익성을 압박하고 있습니다. 장기적 관점에서 이익 턴어라운드 시점을 주시해야 합니다.\n\n"
            elif revenue_growth < 10:
                analysis += f"매출 성장률이 {revenue_growth:.1f}%로 성장주 프리미엄을 정당화하기 어려운 수준입니다. "
                analysis += f"성장 논리를 재검토하시거나, 다른 투자 근거를 찾아보시기 바랍니다."

            recommendations.append(analysis)

        # 가치주
        elif thesis_type == InvestmentThesis.VALUE or any(kw in thesis_lower for kw in ['저평가', '가치', 'value', '싸다']):
            analysis = f"💎 **가치주 논리 분석**\n\n"

            if pe:
                if pe < 10:
                    analysis += f"PER {pe:.1f}x로 확실히 저평가 구간입니다. "
                elif pe < 15:
                    analysis += f"PER {pe:.1f}x로 저평가 논리가 어느 정도 유효합니다. "
                else:
                    analysis += f"PER {pe:.1f}x로 저평가라고 보기 어렵습니다. 저평가 논리를 재검토해주세요. "

            if roe:
                if roe > 15:
                    analysis += f"\n\nROE가 {roe:.1f}%로 우량합니다. 저평가 + 고수익성의 좋은 조합입니다."
                elif roe < 5:
                    analysis += f"\n\n⚠️ 다만 ROE가 {roe:.1f}%로 낮습니다. 저평가에는 이유가 있을 수 있습니다 (가치 함정 주의)."

            recommendations.append(analysis)

        # 배당주
        elif thesis_type == InvestmentThesis.DIVIDEND or any(kw in thesis_lower for kw in ['배당', 'dividend', '인컴']):
            analysis = f"💵 **배당주 논리 분석**\n\n"

            if div_yield > 4:
                analysis += f"배당 수익률 {div_yield:.2f}%로 양호합니다. "
            elif div_yield > 2:
                analysis += f"배당 수익률 {div_yield:.2f}%로 적정 수준입니다. "
            else:
                analysis += f"배당 수익률이 {div_yield:.2f}%로 배당주 논리가 약합니다. "

            if earnings_growth < 0:
                analysis += f"\n\n⚠️ 이익이 {earnings_growth:.1f}% 역성장 중입니다. 향후 배당 삭감 가능성을 염두에 두세요."

            recommendations.append(analysis)

        # === 3. 기술적 상황 ===
        tech_analysis = f"📊 **현재 기술적 상황**\n\n"

        if rsi > 70:
            tech_analysis += f"RSI가 {rsi:.1f}로 과매수 구간입니다. 단기적으로 조정이 올 수 있으니 "
            tech_analysis += f"신규 매수보다는 보유 관망이 적절해 보입니다.\n\n"
        elif rsi < 30:
            tech_analysis += f"RSI가 {rsi:.1f}로 과매도 구간입니다. 투자 논리가 유효하다면 추가 매수 기회일 수 있습니다.\n\n"

        if return_3m > 30:
            tech_analysis += f"최근 3개월간 {return_3m:.1f}% 급등했습니다. 단기 과열 신호이니 분할 매수/매도 전략을 권장합니다.\n\n"
        elif return_3m < -20:
            tech_analysis += f"최근 3개월간 {return_3m:.1f}% 하락했습니다. 투자 논리가 여전히 유효한지 점검이 필요합니다.\n\n"

        if from_high < -30:
            tech_analysis += f"52주 고점 대비 {from_high:.1f}% 하락한 상태입니다. 바닥 확인 후 접근하시는 것이 안전합니다."
        elif from_high > -5:
            tech_analysis += f"52주 고점 근처({from_high:.1f}%)에 있습니다. 신고가 돌파 시 추가 상승 모멘텀이 기대됩니다."

        recommendations.append(tech_analysis)

        # === 4. 리스크 요약 ===
        risks = []
        if debt_equity and debt_equity > 100:
            risks.append(f"부채비율 {debt_equity:.0f}% (재무 리스크)")
        if earnings_growth < -10:
            risks.append(f"이익 {earnings_growth:.1f}% 역성장 (수익성 리스크)")
        if rsi > 75:
            risks.append(f"RSI {rsi:.1f} 과매수 (단기 조정 리스크)")
        if pe and pe > 40:
            risks.append(f"PER {pe:.1f}x 고평가 (밸류에이션 리스크)")

        if risks:
            risk_text = f"⚠️ **주요 리스크 요인**\n\n"
            for r in risks:
                risk_text += f"• {r}\n"
            recommendations.append(risk_text)

        # === 5. 액션 아이템 ===
        actions = f"📌 **향후 모니터링 사항**\n\n"
        actions += f"1. 분기 실적 발표 시 '{thesis_desc}' 관련 매출/비중 변화 확인\n"
        actions += f"2. 경쟁사 동향 및 산업 뉴스 모니터링\n"
        actions += f"3. 목표가/손절가 도달 여부 주기적 체크\n\n"
        actions += f"해당 이슈들에 대해 정기적으로 평가하고 알림을 드리겠습니다."

        recommendations.append(actions)

        return recommendations

    def evaluate(self, position: Position, macro_data: Optional[Dict] = None) -> ThesisEvaluation:
        """종합 평가 실행"""
        # 데이터 수집
        price_data = self.get_stock_data(position.symbol)
        fundamentals = self.get_fundamental_data(position.symbol)

        # 키워드 분석
        keyword_analysis = self.analyze_thesis_keywords(position.thesis_description)

        # 펀더멘털 체크
        fundamental_check = self.check_fundamental_alignment(position, fundamentals)

        # 기술적 체크
        technical_check = self.check_technical_alignment(position, price_data)

        # 리스크 평가
        risk_assessment = self.assess_risk(position, fundamentals, price_data)

        # 확률 평가
        probability_assessment = self.calculate_probability_assessment(
            position, fundamental_check, technical_check, risk_assessment
        )

        # 종합 점수 계산
        scores = [
            fundamental_check.get('score', 0),
            technical_check.get('score', 0),
            -risk_assessment.get('risk_score', 0.5) + 0.5,  # 리스크 점수 반전
        ]
        overall_score = np.mean(scores)

        # 등급 결정
        if overall_score > 0.4:
            rating = ThesisRating.STRONG
        elif overall_score > 0.15:
            rating = ThesisRating.POSITIVE
        elif overall_score > -0.15:
            rating = ThesisRating.NEUTRAL
        elif overall_score > -0.4:
            rating = ThesisRating.NEGATIVE
        else:
            rating = ThesisRating.WEAK

        # 강점/약점/권고사항 정리
        strengths = fundamental_check['passed'] + technical_check['passed'] + risk_assessment.get('mitigants', [])
        weaknesses = fundamental_check['failed'] + technical_check['failed'] + risk_assessment['risks']
        warnings = fundamental_check['warnings'] + technical_check['warnings']

        # 구체적 권고사항 생성
        recommendations = self._generate_detailed_recommendations(
            position, fundamentals, price_data,
            fundamental_check, technical_check, risk_assessment,
            overall_score, keyword_analysis
        )

        if risk_assessment['overall_risk'] == 'high':
            recommendations.append("⚠️ 전체 리스크 높음: 손절가 준수 필수, 비중 축소 고려")

        if warnings:
            recommendations.extend([f"주의: {w}" for w in warnings[:2]])

        return ThesisEvaluation(
            position=position,
            rating=rating,
            score=overall_score,
            confidence=0.7,  # 데이터 가용성에 따라 조정

            fundamental_check=fundamental_check,
            technical_check=technical_check,
            macro_alignment={'status': 'not_checked'},  # 거시경제 정합성은 별도 분석
            risk_assessment=risk_assessment,

            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            probability_assessment=probability_assessment,
        )

    def evaluate_portfolio(self, positions: List[Position]) -> List[ThesisEvaluation]:
        """포트폴리오 전체 평가"""
        evaluations = []

        for position in positions:
            try:
                evaluation = self.evaluate(position)
                evaluations.append(evaluation)
            except Exception as e:
                print(f"평가 실패 ({position.symbol}): {e}")

        return evaluations

    def get_summary_report(self, evaluations: List[ThesisEvaluation]) -> Dict:
        """평가 요약 리포트"""
        if not evaluations:
            return {'error': 'No evaluations'}

        # 등급별 분포
        rating_dist = {}
        for e in evaluations:
            rating = e.rating.value
            rating_dist[rating] = rating_dist.get(rating, 0) + 1

        # 평균 점수
        avg_score = np.mean([e.score for e in evaluations])

        # 가장 강한/약한 포지션
        sorted_evals = sorted(evaluations, key=lambda x: x.score, reverse=True)
        strongest = sorted_evals[0] if sorted_evals else None
        weakest = sorted_evals[-1] if sorted_evals else None

        # 전체 권고사항
        all_recommendations = []
        for e in evaluations:
            all_recommendations.extend(e.recommendations)

        return {
            'total_positions': len(evaluations),
            'rating_distribution': rating_dist,
            'average_score': avg_score,
            'strongest_position': {
                'symbol': strongest.position.symbol,
                'score': strongest.score,
                'rating': strongest.rating.value,
            } if strongest else None,
            'weakest_position': {
                'symbol': weakest.position.symbol,
                'score': weakest.score,
                'rating': weakest.rating.value,
            } if weakest else None,
            'key_recommendations': list(set(all_recommendations))[:5],
        }
