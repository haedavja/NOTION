"""
GPT API 분석 모듈
OpenAI GPT를 활용한 시장 분석
"""

import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class GPTAnalyzer:
    """GPT 기반 분석기"""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        초기화

        Args:
            api_key: OpenAI API 키 (없으면 환경변수 사용)
            model: 사용할 모델 (gpt-4o-mini, gpt-4o, gpt-3.5-turbo 등)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        self.enabled = OPENAI_AVAILABLE and bool(self.api_key)

        if self.enabled:
            openai.api_key = self.api_key

        # 시스템 프롬프트
        self.system_prompts = {
            'market_analyst': """당신은 전문 시장 분석가입니다.
거시경제 데이터, 시장 동향, 기술적 분석을 종합하여 객관적인 분석을 제공합니다.
항상 데이터에 기반하여 분석하고, 불확실성이 있으면 명시합니다.
한국어로 응답합니다.""",

            'news_analyst': """당신은 금융 뉴스 분석 전문가입니다.
뉴스 기사를 분석하여 시장에 미치는 영향을 평가합니다.
감정적 편향을 배제하고 객관적으로 분석합니다.
한국어로 응답합니다.""",

            'portfolio_advisor': """당신은 전문 포트폴리오 자문가입니다.
투자자의 포트폴리오를 분석하고 리스크와 기회를 객관적으로 평가합니다.
투자 결정은 투자자 본인의 책임임을 항상 명시합니다.
한국어로 응답합니다.""",

            'thesis_evaluator': """당신은 투자 논리 평가 전문가입니다.
투자자의 투자 이유를 듣고 객관적인 데이터와 비교하여 평가합니다.
논리의 강점과 약점을 명확히 지적하고,
편향적 사고나 위험 요소가 있으면 솔직하게 알려줍니다.
한국어로 응답합니다.""",
        }

    def _call_api(self, messages: List[Dict], temperature: float = 0.7,
                  max_tokens: int = 2000) -> Optional[str]:
        """API 호출"""
        if not self.enabled:
            return None

        try:
            response = openai.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"GPT API 오류: {e}")
            return None

    def analyze_market(self, market_data: Dict) -> Optional[str]:
        """
        시장 상황 분석

        Args:
            market_data: 시장 데이터 (지수, 섹터, 거시경제 등)

        Returns:
            분석 결과 텍스트
        """
        prompt = f"""다음 시장 데이터를 분석해주세요:

{json.dumps(market_data, indent=2, ensure_ascii=False, default=str)}

다음 항목에 대해 분석해주세요:
1. 현재 시장 상황 요약
2. 주요 리스크 요인
3. 주목할 기회 요인
4. 단기(1-2주) 전망
5. 중기(1-3개월) 전망
6. 권장 포지셔닝"""

        messages = [
            {"role": "system", "content": self.system_prompts['market_analyst']},
            {"role": "user", "content": prompt}
        ]

        return self._call_api(messages, temperature=0.5)

    def analyze_news(self, news_items: List[Dict]) -> Optional[str]:
        """
        뉴스 분석 및 요약

        Args:
            news_items: 뉴스 목록 [{title, summary, source, date}, ...]

        Returns:
            분석 결과
        """
        news_text = "\n".join([
            f"- [{item.get('source', 'Unknown')}] {item.get('title', '')}: {item.get('summary', '')[:200]}"
            for item in news_items[:20]  # 최대 20개
        ])

        prompt = f"""다음 금융 뉴스들을 분석해주세요:

{news_text}

다음 형식으로 분석해주세요:
1. 핵심 뉴스 요약 (3-5개)
2. 시장 심리 평가 (긍정/중립/부정)
3. 섹터별 영향
4. 투자자 주의사항"""

        messages = [
            {"role": "system", "content": self.system_prompts['news_analyst']},
            {"role": "user", "content": prompt}
        ]

        return self._call_api(messages, temperature=0.5)

    def analyze_portfolio(self, portfolio: Dict, market_context: Optional[Dict] = None) -> Optional[str]:
        """
        포트폴리오 분석

        Args:
            portfolio: 포트폴리오 정보
            market_context: 현재 시장 상황

        Returns:
            분석 결과
        """
        context = ""
        if market_context:
            context = f"\n현재 시장 상황:\n{json.dumps(market_context, indent=2, ensure_ascii=False, default=str)}"

        prompt = f"""다음 포트폴리오를 분석해주세요:

{json.dumps(portfolio, indent=2, ensure_ascii=False, default=str)}
{context}

다음 항목에 대해 분석해주세요:
1. 포트폴리오 구성 평가
2. 분산투자 적절성
3. 리스크 요인
4. 현재 시장 상황에서의 적합성
5. 개선 제안"""

        messages = [
            {"role": "system", "content": self.system_prompts['portfolio_advisor']},
            {"role": "user", "content": prompt}
        ]

        return self._call_api(messages, temperature=0.6)

    def evaluate_investment_thesis(self, symbol: str, thesis: str,
                                   fundamental_data: Dict,
                                   technical_data: Dict,
                                   news_data: Optional[List[Dict]] = None) -> Optional[str]:
        """
        투자 논리 평가

        Args:
            symbol: 종목 코드
            thesis: 투자자의 투자 이유
            fundamental_data: 펀더멘털 데이터
            technical_data: 기술적 분석 데이터
            news_data: 관련 뉴스

        Returns:
            평가 결과
        """
        news_summary = ""
        if news_data:
            news_summary = "\n최근 뉴스:\n" + "\n".join([
                f"- {item.get('title', '')}" for item in news_data[:5]
            ])

        prompt = f"""투자자가 {symbol}에 대해 다음과 같은 이유로 투자했습니다:

"{thesis}"

객관적 데이터:

펀더멘털:
{json.dumps(fundamental_data, indent=2, ensure_ascii=False, default=str)}

기술적 분석:
{json.dumps(technical_data, indent=2, ensure_ascii=False, default=str)}
{news_summary}

투자자의 투자 논리를 평가해주세요:

1. 논리의 타당성 점수 (1-10)
2. 논리의 강점
3. 논리의 약점 또는 위험 요소
4. 데이터와의 일치 여부
5. 투자자가 놓친 점
6. 종합 의견 및 제안

솔직하고 객관적으로 평가해주세요. 투자자의 편향이 있다면 지적해주세요."""

        messages = [
            {"role": "system", "content": self.system_prompts['thesis_evaluator']},
            {"role": "user", "content": prompt}
        ]

        return self._call_api(messages, temperature=0.4)

    def generate_scenario_analysis(self, scenarios: List[Dict], portfolio: Dict) -> Optional[str]:
        """
        시나리오별 포트폴리오 영향 분석

        Args:
            scenarios: 시나리오 목록
            portfolio: 포트폴리오

        Returns:
            시나리오 분석 결과
        """
        prompt = f"""다음 경제 시나리오들에 대해 포트폴리오 영향을 분석해주세요:

시나리오:
{json.dumps(scenarios, indent=2, ensure_ascii=False, default=str)}

포트폴리오:
{json.dumps(portfolio, indent=2, ensure_ascii=False, default=str)}

각 시나리오별로:
1. 예상 영향
2. 유리한 자산
3. 불리한 자산
4. 대응 전략

을 분석해주세요."""

        messages = [
            {"role": "system", "content": self.system_prompts['portfolio_advisor']},
            {"role": "user", "content": prompt}
        ]

        return self._call_api(messages, temperature=0.5)

    def get_investment_ideas(self, market_data: Dict, preferences: Optional[Dict] = None) -> Optional[str]:
        """
        투자 아이디어 생성

        Args:
            market_data: 현재 시장 데이터
            preferences: 투자자 선호도

        Returns:
            투자 아이디어
        """
        pref_text = ""
        if preferences:
            pref_text = f"\n투자자 선호:\n{json.dumps(preferences, indent=2, ensure_ascii=False, default=str)}"

        prompt = f"""현재 시장 상황을 기반으로 투자 아이디어를 제안해주세요:

시장 데이터:
{json.dumps(market_data, indent=2, ensure_ascii=False, default=str)}
{pref_text}

다음 형식으로 3-5개의 투자 아이디어를 제안해주세요:
1. 아이디어 명
2. 투자 근거
3. 예상 수익 시나리오
4. 리스크 요인
5. 적합한 투자 기간

모든 투자에는 위험이 따르며, 최종 결정은 투자자 본인의 책임임을 명시하세요."""

        messages = [
            {"role": "system", "content": self.system_prompts['market_analyst']},
            {"role": "user", "content": prompt}
        ]

        return self._call_api(messages, temperature=0.7)

    def chat(self, message: str, context: Optional[str] = None,
             role: str = 'market_analyst') -> Optional[str]:
        """
        자유 대화형 분석

        Args:
            message: 사용자 메시지
            context: 추가 컨텍스트
            role: 역할 (market_analyst, news_analyst, portfolio_advisor, thesis_evaluator)

        Returns:
            응답
        """
        system_prompt = self.system_prompts.get(role, self.system_prompts['market_analyst'])

        user_content = message
        if context:
            user_content = f"컨텍스트:\n{context}\n\n질문: {message}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        return self._call_api(messages, temperature=0.7)

    def get_status(self) -> Dict:
        """상태 확인"""
        return {
            'enabled': self.enabled,
            'model': self.model,
            'openai_installed': OPENAI_AVAILABLE,
            'api_key_set': bool(self.api_key),
        }


# 사용 예시
def example_usage():
    """사용 예시"""
    analyzer = GPTAnalyzer()

    if not analyzer.enabled:
        print("GPT 분석기가 비활성화되어 있습니다.")
        print("OPENAI_API_KEY 환경변수를 설정하세요.")
        return

    # 시장 분석
    market_data = {
        'SPY': {'price': 450, 'change_1d': -1.2, 'change_1m': 3.5},
        'VIX': 18.5,
        'DXY': 104.2,
        '10Y_yield': 4.3,
    }
    analysis = analyzer.analyze_market(market_data)
    print(analysis)
