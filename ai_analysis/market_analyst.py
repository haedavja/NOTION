"""
AI 기반 시장 분석가
GPT를 활용한 종합 시장 분석
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from .gpt_analyzer import GPTAnalyzer

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


@dataclass
class MarketAnalysisResult:
    """시장 분석 결과"""
    timestamp: datetime
    market_summary: str
    risk_assessment: str
    opportunities: List[str]
    sector_analysis: Dict[str, str]
    recommendations: List[str]
    raw_analysis: Optional[str] = None


class AIMarketAnalyst:
    """AI 기반 시장 분석가"""

    def __init__(self, api_key: Optional[str] = None):
        """
        초기화

        Args:
            api_key: OpenAI API 키
        """
        self.gpt = GPTAnalyzer(api_key=api_key)

        # 주요 지수 및 지표
        self.market_indices = {
            'SPY': 'S&P 500',
            'QQQ': 'NASDAQ 100',
            'IWM': 'Russell 2000',
            'DIA': 'Dow Jones',
        }

        self.sector_etfs = {
            'XLK': '기술',
            'XLF': '금융',
            'XLE': '에너지',
            'XLV': '헬스케어',
            'XLY': '소비재',
            'XLP': '필수소비재',
            'XLI': '산업',
            'XLU': '유틸리티',
            'XLRE': '부동산',
            'XLB': '소재',
            'XLC': '통신',
        }

        self.macro_indicators = {
            '^VIX': 'VIX',
            '^TNX': '10년물 국채',
            'GLD': '금',
            'UUP': '달러',
        }

    def _fetch_market_data(self) -> Dict:
        """시장 데이터 수집"""
        if not YFINANCE_AVAILABLE:
            return self._get_sample_data()

        data = {
            'indices': {},
            'sectors': {},
            'macro': {},
            'timestamp': datetime.now().isoformat(),
        }

        try:
            # 지수 데이터
            for symbol, name in self.market_indices.items():
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='1mo')
                if not hist.empty:
                    current = hist['Close'].iloc[-1]
                    prev_day = hist['Close'].iloc[-2] if len(hist) > 1 else current
                    month_ago = hist['Close'].iloc[0]

                    data['indices'][name] = {
                        'price': round(current, 2),
                        'change_1d': round((current / prev_day - 1) * 100, 2),
                        'change_1m': round((current / month_ago - 1) * 100, 2),
                    }

            # 섹터 데이터
            for symbol, name in self.sector_etfs.items():
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='1mo')
                if not hist.empty:
                    current = hist['Close'].iloc[-1]
                    month_ago = hist['Close'].iloc[0]

                    data['sectors'][name] = {
                        'change_1m': round((current / month_ago - 1) * 100, 2),
                    }

            # 거시 지표
            for symbol, name in self.macro_indicators.items():
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period='5d')
                if not hist.empty:
                    current = hist['Close'].iloc[-1]
                    data['macro'][name] = round(current, 2)

        except Exception as e:
            print(f"데이터 수집 오류: {e}")
            return self._get_sample_data()

        return data

    def _get_sample_data(self) -> Dict:
        """샘플 데이터"""
        return {
            'indices': {
                'S&P 500': {'price': 4500, 'change_1d': -0.5, 'change_1m': 2.3},
                'NASDAQ 100': {'price': 15800, 'change_1d': -0.8, 'change_1m': 3.1},
                'Russell 2000': {'price': 2050, 'change_1d': -0.3, 'change_1m': 1.5},
                'Dow Jones': {'price': 35200, 'change_1d': -0.2, 'change_1m': 1.8},
            },
            'sectors': {
                '기술': {'change_1m': 4.2},
                '금융': {'change_1m': 1.8},
                '에너지': {'change_1m': -2.3},
                '헬스케어': {'change_1m': 0.9},
                '소비재': {'change_1m': 2.1},
            },
            'macro': {
                'VIX': 18.5,
                '10년물 국채': 4.35,
                '금': 2050,
                '달러': 104.2,
            },
            'timestamp': datetime.now().isoformat(),
        }

    def analyze_market(self, include_sectors: bool = True) -> Optional[MarketAnalysisResult]:
        """
        시장 종합 분석

        Args:
            include_sectors: 섹터 분석 포함 여부

        Returns:
            분석 결과
        """
        # 데이터 수집
        market_data = self._fetch_market_data()

        if not include_sectors:
            market_data.pop('sectors', None)

        # GPT 분석
        raw_analysis = self.gpt.analyze_market(market_data)

        if raw_analysis is None:
            return self._generate_rule_based_analysis(market_data)

        # 결과 파싱 (간단한 구조화)
        return MarketAnalysisResult(
            timestamp=datetime.now(),
            market_summary=self._extract_section(raw_analysis, "시장 상황"),
            risk_assessment=self._extract_section(raw_analysis, "리스크"),
            opportunities=self._extract_list(raw_analysis, "기회"),
            sector_analysis=self._extract_sector_analysis(raw_analysis),
            recommendations=self._extract_list(raw_analysis, "권장"),
            raw_analysis=raw_analysis,
        )

    def _extract_section(self, text: str, keyword: str) -> str:
        """텍스트에서 섹션 추출"""
        lines = text.split('\n')
        result = []
        in_section = False

        for line in lines:
            if keyword in line:
                in_section = True
                continue
            if in_section:
                if line.startswith('#') or (line.strip() and line[0].isdigit() and '.' in line[:3]):
                    break
                result.append(line)

        return '\n'.join(result).strip()[:500] or "분석 데이터 없음"

    def _extract_list(self, text: str, keyword: str) -> List[str]:
        """리스트 항목 추출"""
        lines = text.split('\n')
        result = []
        in_section = False

        for line in lines:
            if keyword in line:
                in_section = True
                continue
            if in_section:
                if line.strip().startswith('-') or line.strip().startswith('•'):
                    result.append(line.strip().lstrip('-•').strip())
                elif line.startswith('#') or (line.strip() and line[0].isdigit() and '.' in line[:3]):
                    break

        return result[:5] or ["분석 결과 없음"]

    def _extract_sector_analysis(self, text: str) -> Dict[str, str]:
        """섹터 분석 추출"""
        sectors = {}
        for sector in self.sector_etfs.values():
            if sector in text:
                # 간단한 추출 - 섹터 이름 주변 텍스트
                idx = text.find(sector)
                snippet = text[idx:idx+200]
                end = snippet.find('\n\n')
                if end > 0:
                    snippet = snippet[:end]
                sectors[sector] = snippet.strip()
        return sectors

    def _generate_rule_based_analysis(self, market_data: Dict) -> MarketAnalysisResult:
        """규칙 기반 분석 (GPT 사용 불가시)"""
        indices = market_data.get('indices', {})
        sectors = market_data.get('sectors', {})
        macro = market_data.get('macro', {})

        # 시장 요약
        sp500 = indices.get('S&P 500', {})
        change_1d = sp500.get('change_1d', 0)
        change_1m = sp500.get('change_1m', 0)

        if change_1d > 1:
            daily_status = "강세"
        elif change_1d < -1:
            daily_status = "약세"
        else:
            daily_status = "보합"

        if change_1m > 5:
            monthly_trend = "상승 추세"
        elif change_1m < -5:
            monthly_trend = "하락 추세"
        else:
            monthly_trend = "횡보 추세"

        market_summary = f"S&P 500 기준 일간 {daily_status} ({change_1d:+.2f}%), 월간 {monthly_trend} ({change_1m:+.2f}%)"

        # 리스크 평가
        vix = macro.get('VIX', 20)
        if vix > 30:
            risk = "높은 변동성 경고 (VIX: {:.1f})".format(vix)
        elif vix > 20:
            risk = "보통 변동성 (VIX: {:.1f})".format(vix)
        else:
            risk = "낮은 변동성 (VIX: {:.1f})".format(vix)

        # 섹터 분석
        sector_analysis = {}
        for sector, data in sectors.items():
            change = data.get('change_1m', 0)
            if change > 3:
                sector_analysis[sector] = f"강세 ({change:+.1f}%)"
            elif change < -3:
                sector_analysis[sector] = f"약세 ({change:+.1f}%)"
            else:
                sector_analysis[sector] = f"보합 ({change:+.1f}%)"

        # 기회 요인
        opportunities = []
        strong_sectors = [s for s, d in sectors.items() if d.get('change_1m', 0) > 3]
        if strong_sectors:
            opportunities.append(f"강세 섹터: {', '.join(strong_sectors)}")
        if vix < 15:
            opportunities.append("낮은 변동성으로 안정적 투자 환경")

        # 권장사항
        recommendations = []
        if change_1m > 5 and vix < 20:
            recommendations.append("추세 추종 전략 유효")
        if vix > 25:
            recommendations.append("방어적 포지션 고려")
        if not recommendations:
            recommendations.append("분산투자 유지")

        return MarketAnalysisResult(
            timestamp=datetime.now(),
            market_summary=market_summary,
            risk_assessment=risk,
            opportunities=opportunities or ["특별한 기회 요인 없음"],
            sector_analysis=sector_analysis,
            recommendations=recommendations,
            raw_analysis=None,
        )

    def get_daily_briefing(self) -> str:
        """일일 브리핑 생성"""
        result = self.analyze_market()

        if result is None:
            return "분석을 수행할 수 없습니다."

        if result.raw_analysis:
            return result.raw_analysis

        # 규칙 기반 결과 포맷팅
        briefing = f"""
📊 일일 시장 브리핑
{'-'*40}
📈 시장 요약
{result.market_summary}

⚠️ 리스크 평가
{result.risk_assessment}

💡 기회 요인
{chr(10).join('• ' + o for o in result.opportunities)}

📌 권장사항
{chr(10).join('• ' + r for r in result.recommendations)}

🕐 분석 시각: {result.timestamp.strftime('%Y-%m-%d %H:%M')}
"""
        return briefing

    def analyze_specific_stock(self, symbol: str) -> Optional[str]:
        """
        특정 종목 AI 분석

        Args:
            symbol: 종목 코드

        Returns:
            분석 결과
        """
        if not YFINANCE_AVAILABLE:
            return "yfinance가 필요합니다."

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period='3mo')

            if hist.empty:
                return f"{symbol} 데이터를 가져올 수 없습니다."

            # 기본 정보
            stock_data = {
                'symbol': symbol,
                'name': info.get('longName', symbol),
                'price': round(hist['Close'].iloc[-1], 2),
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'dividend_yield': info.get('dividendYield'),
                'beta': info.get('beta'),
                '52w_high': info.get('fiftyTwoWeekHigh'),
                '52w_low': info.get('fiftyTwoWeekLow'),
                'avg_volume': info.get('averageVolume'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
            }

            # 기술적 지표
            closes = hist['Close']
            stock_data['technical'] = {
                'ma_20': round(closes.rolling(20).mean().iloc[-1], 2) if len(closes) >= 20 else None,
                'ma_50': round(closes.rolling(50).mean().iloc[-1], 2) if len(closes) >= 50 else None,
                'change_1w': round((closes.iloc[-1] / closes.iloc[-5] - 1) * 100, 2) if len(closes) >= 5 else None,
                'change_1m': round((closes.iloc[-1] / closes.iloc[-22] - 1) * 100, 2) if len(closes) >= 22 else None,
                'change_3m': round((closes.iloc[-1] / closes.iloc[0] - 1) * 100, 2),
            }

            return self.gpt.chat(
                message=f"{symbol} 종목을 분석해주세요. 투자 매력도와 리스크를 평가해주세요.",
                context=str(stock_data),
                role='market_analyst'
            )

        except Exception as e:
            return f"분석 오류: {e}"

    def get_status(self) -> Dict:
        """상태 확인"""
        return {
            'gpt_enabled': self.gpt.enabled,
            'yfinance_available': YFINANCE_AVAILABLE,
        }
