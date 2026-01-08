"""
AI 투자 어시스턴트
GPT 기반 종목 분석, 투자 질문 응답, 뉴스 요약
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Generator
from dataclasses import dataclass, field

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


@dataclass
class ChatMessage:
    """채팅 메시지"""
    role: str  # system, user, assistant
    content: str
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class AnalysisResult:
    """분석 결과"""
    symbol: str
    summary: str
    strengths: List[str]
    weaknesses: List[str]
    recommendation: str
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'summary': self.summary,
            'strengths': self.strengths,
            'weaknesses': self.weaknesses,
            'recommendation': self.recommendation,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat()
        }


class AIAssistant:
    """AI 투자 어시스턴트"""

    SYSTEM_PROMPT = """당신은 전문 투자 분석가입니다. 다음 원칙을 따릅니다:

1. 객관적이고 균형 잡힌 분석 제공
2. 투자 위험을 항상 명시
3. 구체적인 수치와 근거 제시
4. 한국어로 명확하게 설명
5. 투자 권유가 아닌 정보 제공임을 명시

분석 시 고려 사항:
- 재무제표 (PER, PBR, ROE, 부채비율)
- 기술적 지표 (이동평균, RSI, MACD)
- 시장 환경 및 섹터 동향
- 리스크 요인"""

    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        self.conversation_history: List[ChatMessage] = []
        self.max_history = 20

        if OPENAI_AVAILABLE and self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
        else:
            self.client = None

    def is_available(self) -> bool:
        """AI 사용 가능 여부"""
        return self.client is not None

    def _call_api(self, messages: List[Dict], stream: bool = False) -> str:
        """OpenAI API 호출"""
        if not self.client:
            return "OpenAI API 키가 설정되지 않았습니다. 환경변수 OPENAI_API_KEY를 설정하세요."

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
                stream=stream
            )

            if stream:
                return response  # Generator 반환
            else:
                return response.choices[0].message.content

        except Exception as e:
            return f"API 오류: {str(e)}"

    def chat(self, user_message: str, context: Dict = None) -> str:
        """채팅 응답"""
        # 시스템 프롬프트
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]

        # 컨텍스트 추가
        if context:
            context_str = self._format_context(context)
            messages.append({
                "role": "system",
                "content": f"현재 포트폴리오/시장 정보:\n{context_str}"
            })

        # 대화 이력
        for msg in self.conversation_history[-self.max_history:]:
            messages.append({"role": msg.role, "content": msg.content})

        # 사용자 메시지
        messages.append({"role": "user", "content": user_message})

        # API 호출
        response = self._call_api(messages)

        # 이력 저장
        self.conversation_history.append(ChatMessage(role="user", content=user_message))
        self.conversation_history.append(ChatMessage(role="assistant", content=response))

        return response

    def chat_stream(self, user_message: str, context: Dict = None) -> Generator:
        """스트리밍 채팅 응답"""
        messages = [{"role": "system", "content": self.SYSTEM_PROMPT}]

        if context:
            context_str = self._format_context(context)
            messages.append({
                "role": "system",
                "content": f"현재 포트폴리오/시장 정보:\n{context_str}"
            })

        for msg in self.conversation_history[-self.max_history:]:
            messages.append({"role": msg.role, "content": msg.content})

        messages.append({"role": "user", "content": user_message})

        if not self.client:
            yield "OpenAI API 키가 설정되지 않았습니다."
            return

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
                stream=True
            )

            full_response = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content

            # 이력 저장
            self.conversation_history.append(ChatMessage(role="user", content=user_message))
            self.conversation_history.append(ChatMessage(role="assistant", content=full_response))

        except Exception as e:
            yield f"API 오류: {str(e)}"

    def analyze_stock(self, symbol: str, stock_data: Dict) -> AnalysisResult:
        """종목 분석"""
        prompt = f"""다음 종목을 분석해주세요:

종목: {symbol}
종목명: {stock_data.get('name', 'N/A')}

재무 지표:
- 현재가: {stock_data.get('price', 'N/A'):,}원
- PER: {stock_data.get('per', 'N/A')}
- PBR: {stock_data.get('pbr', 'N/A')}
- ROE: {stock_data.get('roe', 'N/A')}%
- 영업이익률: {stock_data.get('operating_margin', 'N/A')}%
- 부채비율: {stock_data.get('debt_ratio', 'N/A')}%

기술적 지표:
- RSI: {stock_data.get('rsi', 'N/A')}
- MACD 신호: {stock_data.get('macd_signal', 'N/A')}
- 20일 이평선 대비: {stock_data.get('vs_ma20', 'N/A')}%

최근 동향:
- 1개월 수익률: {stock_data.get('return_1m', 'N/A')}%
- 3개월 수익률: {stock_data.get('return_3m', 'N/A')}%

다음 형식으로 응답해주세요:
1. 요약 (2-3문장)
2. 강점 (3개)
3. 약점/리스크 (3개)
4. 투자 의견 (매수/중립/매도)
5. 신뢰도 (0-100)"""

        response = self._call_api([
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ])

        # 응답 파싱
        return self._parse_analysis(symbol, response)

    def summarize_news(self, news_items: List[Dict]) -> str:
        """뉴스 요약"""
        if not news_items:
            return "요약할 뉴스가 없습니다."

        news_text = "\n".join([
            f"- {item.get('title', '')} ({item.get('source', '')})"
            for item in news_items[:10]
        ])

        prompt = f"""다음 뉴스를 요약하고 시장에 미칠 영향을 분석해주세요:

{news_text}

다음을 포함해주세요:
1. 핵심 내용 요약 (3-5줄)
2. 시장 영향 (긍정/부정/중립)
3. 주목할 섹터/종목
4. 투자자 유의사항"""

        return self._call_api([
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ])

    def explain_indicator(self, indicator: str, value: float, context: str = "") -> str:
        """지표 설명"""
        prompt = f"""투자 지표를 쉽게 설명해주세요:

지표: {indicator}
현재값: {value}
{f'컨텍스트: {context}' if context else ''}

다음을 포함해주세요:
1. 지표의 의미
2. 현재 값의 해석
3. 투자 시 활용 방법
4. 주의사항"""

        return self._call_api([
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ])

    def get_investment_advice(self, portfolio_summary: Dict,
                             market_outlook: str = "") -> str:
        """투자 조언"""
        prompt = f"""현재 포트폴리오에 대한 조언을 해주세요:

포트폴리오 현황:
- 총 평가액: {portfolio_summary.get('total_value', 0):,}원
- 총 손익: {portfolio_summary.get('total_pnl', 0):,}원 ({portfolio_summary.get('total_return', 0):.2f}%)
- 종목 수: {portfolio_summary.get('position_count', 0)}개

보유 종목:
{self._format_positions(portfolio_summary.get('positions', []))}

{f'시장 전망: {market_outlook}' if market_outlook else ''}

다음을 제안해주세요:
1. 현재 포트폴리오 평가
2. 리스크 요인
3. 개선 제안 (리밸런싱, 분산투자 등)
4. 주의사항

※ 이 조언은 참고용이며 투자 결정의 책임은 본인에게 있습니다."""

        return self._call_api([
            {"role": "system", "content": self.SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ])

    def clear_history(self):
        """대화 이력 초기화"""
        self.conversation_history.clear()

    def _format_context(self, context: Dict) -> str:
        """컨텍스트 포맷팅"""
        lines = []
        if 'portfolio_value' in context:
            lines.append(f"포트폴리오 평가액: {context['portfolio_value']:,}원")
        if 'positions' in context:
            lines.append(f"보유 종목: {len(context['positions'])}개")
        if 'market_status' in context:
            lines.append(f"시장 상태: {context['market_status']}")
        return "\n".join(lines)

    def _format_positions(self, positions: List[Dict]) -> str:
        """포지션 포맷팅"""
        if not positions:
            return "보유 종목 없음"

        lines = []
        for pos in positions[:10]:
            pnl = pos.get('pnl', 0)
            pnl_pct = pos.get('pnl_pct', 0)
            sign = '+' if pnl >= 0 else ''
            lines.append(f"- {pos.get('name', 'N/A')}: {sign}{pnl:,.0f}원 ({sign}{pnl_pct:.1f}%)")
        return "\n".join(lines)

    def _parse_analysis(self, symbol: str, response: str) -> AnalysisResult:
        """분석 응답 파싱"""
        # 기본값
        result = AnalysisResult(
            symbol=symbol,
            summary=response[:500] if len(response) > 500 else response,
            strengths=[],
            weaknesses=[],
            recommendation="중립",
            confidence=50.0
        )

        try:
            lines = response.split('\n')

            # 강점 추출
            in_strengths = False
            in_weaknesses = False

            for line in lines:
                line = line.strip()

                if '강점' in line or 'Strength' in line.lower():
                    in_strengths = True
                    in_weaknesses = False
                    continue
                elif '약점' in line or '리스크' in line or 'Weakness' in line.lower():
                    in_strengths = False
                    in_weaknesses = True
                    continue
                elif '투자 의견' in line or '의견' in line:
                    in_strengths = False
                    in_weaknesses = False
                    if '매수' in line:
                        result.recommendation = "매수"
                    elif '매도' in line:
                        result.recommendation = "매도"
                    else:
                        result.recommendation = "중립"
                elif '신뢰도' in line:
                    import re
                    match = re.search(r'(\d+)', line)
                    if match:
                        result.confidence = float(match.group(1))

                if in_strengths and line.startswith(('-', '•', '*', '1', '2', '3')):
                    result.strengths.append(line.lstrip('-•* 0123456789.'))
                elif in_weaknesses and line.startswith(('-', '•', '*', '1', '2', '3')):
                    result.weaknesses.append(line.lstrip('-•* 0123456789.'))

        except Exception:
            pass

        return result


# 전역 인스턴스
ai_assistant = AIAssistant()
