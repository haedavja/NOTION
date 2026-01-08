"""
확률 예측 모델 모듈
거시경제, 자금흐름, 센티먼트를 종합하여 시장 방향 확률을 예측합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import cross_val_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class MarketDirection(Enum):
    """시장 방향"""
    STRONG_BULL = "강세장"
    BULL = "상승"
    NEUTRAL = "횡보"
    BEAR = "하락"
    STRONG_BEAR = "약세장"


@dataclass
class PredictionResult:
    """예측 결과"""
    direction: MarketDirection
    probability: float
    confidence: float
    factors: Dict[str, float]
    description: str


class ProbabilityModel:
    """확률 예측 모델 클래스"""

    # 요소별 가중치
    DEFAULT_WEIGHTS = {
        'macro': 0.30,          # 거시경제
        'flow': 0.25,           # 자금흐름
        'sentiment': 0.20,      # 센티먼트
        'technical': 0.25,      # 기술적 분석
    }

    # 지표별 신호 가중치
    SIGNAL_WEIGHTS = {
        # 거시경제
        'yield_curve': 0.15,
        'inflation': 0.10,
        'employment': 0.10,
        'economic_cycle': 0.15,

        # 자금흐름
        'risk_appetite': 0.15,
        'sector_rotation': 0.10,
        'market_breadth': 0.10,

        # 센티먼트
        'news_sentiment': 0.15,
        'sentiment_trend': 0.10,

        # 기술적
        'trend': 0.15,
        'momentum': 0.10,
        'volatility': 0.10,
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        초기화

        Args:
            weights: 커스텀 가중치 (없으면 기본값 사용)
        """
        self.weights = weights or self.DEFAULT_WEIGHTS
        self.ml_model = None
        self.scaler = None

        if SKLEARN_AVAILABLE:
            self.ml_model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                random_state=42
            )
            self.scaler = StandardScaler()

    def calculate_macro_score(self, macro_analysis: Dict) -> Tuple[float, Dict]:
        """
        거시경제 분석 점수 계산

        Args:
            macro_analysis: 거시경제 분석 결과

        Returns:
            (점수, 세부 요소)
        """
        scores = {}
        total_weight = 0
        weighted_score = 0

        # 경기 사이클
        cycle = macro_analysis.get('economic_cycle', '')
        if '확장' in cycle:
            scores['economic_cycle'] = 0.8
        elif '정점' in cycle:
            scores['economic_cycle'] = 0.5
        elif '수축' in cycle:
            scores['economic_cycle'] = 0.2
        elif '저점' in cycle:
            scores['economic_cycle'] = 0.6
        else:
            scores['economic_cycle'] = 0.5

        # 신호들
        signals = macro_analysis.get('signals', [])
        bullish_count = sum(1 for s in signals if s.get('signal') == 'bullish')
        bearish_count = sum(1 for s in signals if s.get('signal') == 'bearish')
        total = len(signals) or 1

        scores['signals'] = 0.5 + (bullish_count - bearish_count) / total * 0.5

        # 종합 점수
        for key, value in scores.items():
            weight = self.SIGNAL_WEIGHTS.get(key, 0.1)
            weighted_score += value * weight
            total_weight += weight

        final_score = weighted_score / total_weight if total_weight > 0 else 0.5

        return final_score, scores

    def calculate_flow_score(self, flow_analysis: Dict) -> Tuple[float, Dict]:
        """
        자금흐름 분석 점수 계산

        Args:
            flow_analysis: 자금흐름 분석 결과

        Returns:
            (점수, 세부 요소)
        """
        scores = {}

        # 위험 선호도
        risk_score = flow_analysis.get('risk_score', 0.5)
        scores['risk_appetite'] = risk_score

        # 시장 폭
        breadth = flow_analysis.get('market_breadth', {})
        health_score = breadth.get('health_score', 0.5)
        scores['market_breadth'] = health_score

        # 유입/유출
        inflows = len(flow_analysis.get('inflows', []))
        outflows = len(flow_analysis.get('outflows', []))
        total = inflows + outflows or 1
        scores['flow_direction'] = 0.5 + (inflows - outflows) / total * 0.3

        # 종합
        final_score = np.mean(list(scores.values()))

        return final_score, scores

    def calculate_sentiment_score(self, sentiment_analysis: Dict) -> Tuple[float, Dict]:
        """
        센티먼트 분석 점수 계산

        Args:
            sentiment_analysis: 센티먼트 분석 결과

        Returns:
            (점수, 세부 요소)
        """
        scores = {}

        # 종합 센티먼트
        overall = sentiment_analysis.get('overall_analysis', {})
        composite = overall.get('composite_score', 0)
        scores['news_sentiment'] = 0.5 + composite * 0.5  # -1~1을 0~1로 변환

        # 센티먼트 변화
        shift = sentiment_analysis.get('sentiment_shift', {})
        shift_value = shift.get('shift', 0)
        scores['sentiment_trend'] = 0.5 + min(max(shift_value, -0.5), 0.5)

        final_score = np.mean(list(scores.values()))

        return final_score, scores

    def calculate_technical_score(self, technical_analysis: Dict) -> Tuple[float, Dict]:
        """
        기술적 분석 점수 계산

        Args:
            technical_analysis: 기술적 분석 결과

        Returns:
            (점수, 세부 요소)
        """
        scores = {}

        # 종합 점수
        composite = technical_analysis.get('composite_score', 0)
        scores['overall'] = 0.5 + composite * 0.5

        # 트렌드
        trend = technical_analysis.get('trend_analysis', {})
        trend_str = trend.get('trend', '')
        if 'Strong Up' in trend_str:
            scores['trend'] = 0.9
        elif 'Up' in trend_str:
            scores['trend'] = 0.7
        elif 'Strong Down' in trend_str:
            scores['trend'] = 0.1
        elif 'Down' in trend_str:
            scores['trend'] = 0.3
        else:
            scores['trend'] = 0.5

        # 모멘텀
        momentum = technical_analysis.get('momentum_analysis', {})
        rsi = momentum.get('rsi', 50)
        if rsi > 70:
            scores['momentum'] = 0.3  # 과매수는 하락 리스크
        elif rsi < 30:
            scores['momentum'] = 0.7  # 과매도는 반등 기대
        else:
            scores['momentum'] = 0.5 + (rsi - 50) / 100

        final_score = np.mean(list(scores.values()))

        return final_score, scores

    def predict_probability(self,
                           macro_analysis: Optional[Dict] = None,
                           flow_analysis: Optional[Dict] = None,
                           sentiment_analysis: Optional[Dict] = None,
                           technical_analysis: Optional[Dict] = None) -> PredictionResult:
        """
        종합 확률 예측

        Args:
            macro_analysis: 거시경제 분석 결과
            flow_analysis: 자금흐름 분석 결과
            sentiment_analysis: 센티먼트 분석 결과
            technical_analysis: 기술적 분석 결과

        Returns:
            예측 결과
        """
        scores = {}
        factors = {}
        total_weight = 0

        # 각 요소별 점수 계산
        if macro_analysis:
            macro_score, macro_factors = self.calculate_macro_score(macro_analysis)
            scores['macro'] = macro_score
            factors['macro'] = macro_factors
            total_weight += self.weights['macro']

        if flow_analysis:
            flow_score, flow_factors = self.calculate_flow_score(flow_analysis)
            scores['flow'] = flow_score
            factors['flow'] = flow_factors
            total_weight += self.weights['flow']

        if sentiment_analysis:
            sent_score, sent_factors = self.calculate_sentiment_score(sentiment_analysis)
            scores['sentiment'] = sent_score
            factors['sentiment'] = sent_factors
            total_weight += self.weights['sentiment']

        if technical_analysis:
            tech_score, tech_factors = self.calculate_technical_score(technical_analysis)
            scores['technical'] = tech_score
            factors['technical'] = tech_factors
            total_weight += self.weights['technical']

        # 가중 평균
        if total_weight > 0:
            weighted_sum = sum(
                scores.get(k, 0.5) * self.weights.get(k, 0)
                for k in ['macro', 'flow', 'sentiment', 'technical']
            )
            probability = weighted_sum / total_weight
        else:
            probability = 0.5

        # 방향 결정
        if probability > 0.7:
            direction = MarketDirection.STRONG_BULL
        elif probability > 0.55:
            direction = MarketDirection.BULL
        elif probability < 0.3:
            direction = MarketDirection.STRONG_BEAR
        elif probability < 0.45:
            direction = MarketDirection.BEAR
        else:
            direction = MarketDirection.NEUTRAL

        # 신뢰도 (요소 간 일관성)
        if scores:
            score_values = list(scores.values())
            consistency = 1 - np.std(score_values)  # 편차가 작을수록 일관성 높음
            confidence = min(max(consistency, 0.3), 0.95)
        else:
            confidence = 0.5

        # 설명 생성
        description = self._generate_description(direction, scores, probability)

        return PredictionResult(
            direction=direction,
            probability=probability,
            confidence=confidence,
            factors=factors,
            description=description
        )

    def _generate_description(self, direction: MarketDirection,
                             scores: Dict, probability: float) -> str:
        """예측 설명 생성"""
        parts = []

        # 방향
        parts.append(f"예상 방향: {direction.value} (확률: {probability*100:.1f}%)")

        # 주요 요소
        if scores:
            strongest = max(scores.items(), key=lambda x: abs(x[1] - 0.5))
            weakest = min(scores.items(), key=lambda x: abs(x[1] - 0.5))

            parts.append(f"주요 신호: {strongest[0]} ({strongest[1]*100:.0f}%)")
            parts.append(f"중립 신호: {weakest[0]} ({weakest[1]*100:.0f}%)")

        return " | ".join(parts)

    def get_factor_breakdown(self, prediction: PredictionResult) -> Dict:
        """
        예측 요소 상세 분석

        Args:
            prediction: 예측 결과

        Returns:
            요소별 상세 분석
        """
        breakdown = {
            'direction': prediction.direction.value,
            'probability': prediction.probability,
            'confidence': prediction.confidence,
            'factors': {},
        }

        for category, factors in prediction.factors.items():
            category_data = {
                'score': np.mean(list(factors.values())),
                'weight': self.weights.get(category, 0),
                'details': factors,
            }
            breakdown['factors'][category] = category_data

        return breakdown

    def calculate_risk_adjusted_outlook(self, prediction: PredictionResult,
                                        volatility: float = 0.15) -> Dict:
        """
        위험 조정 전망 계산

        Args:
            prediction: 예측 결과
            volatility: 시장 변동성 (연율화)

        Returns:
            위험 조정 전망
        """
        # 기대 수익률 추정
        if prediction.probability > 0.5:
            expected_return = (prediction.probability - 0.5) * 2 * 0.10  # 최대 10%
        else:
            expected_return = (prediction.probability - 0.5) * 2 * 0.10

        # 샤프 비율 (간단화)
        risk_free_rate = 0.04
        if volatility > 0:
            sharpe_ratio = (expected_return - risk_free_rate) / volatility
        else:
            sharpe_ratio = 0

        # 위험 조정 점수
        risk_adjusted_score = expected_return / (1 + volatility)

        # 포지션 사이징 제안
        kelly_fraction = (prediction.probability - 0.5) * 2  # 켈리 기준 간략화
        suggested_exposure = min(max(kelly_fraction * prediction.confidence, 0), 1)

        return {
            'expected_return': expected_return * 100,  # %
            'volatility': volatility * 100,
            'sharpe_ratio': sharpe_ratio,
            'risk_adjusted_score': risk_adjusted_score,
            'suggested_exposure': suggested_exposure * 100,  # %
            'risk_level': 'High' if volatility > 0.25 else ('Medium' if volatility > 0.15 else 'Low'),
        }

    def backtest_signals(self, historical_signals: pd.DataFrame,
                        returns: pd.Series,
                        threshold: float = 0.55) -> Dict:
        """
        신호 백테스트

        Args:
            historical_signals: 과거 신호 데이터 (probability 컬럼 포함)
            returns: 실제 수익률
            threshold: 매수 신호 임계값

        Returns:
            백테스트 결과
        """
        if 'probability' not in historical_signals.columns:
            return {'error': 'probability column required'}

        # 신호 생성
        signals = (historical_signals['probability'] > threshold).astype(int)
        signals = signals.shift(1).fillna(0)  # 다음 기간에 적용

        # 전략 수익률
        strategy_returns = signals * returns

        # 성과 지표
        total_return = (1 + strategy_returns).prod() - 1
        buy_hold_return = (1 + returns).prod() - 1

        win_rate = (strategy_returns > 0).sum() / (signals > 0).sum() if (signals > 0).sum() > 0 else 0

        # 최대 낙폭
        cumulative = (1 + strategy_returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()

        return {
            'total_return': total_return * 100,
            'buy_hold_return': buy_hold_return * 100,
            'excess_return': (total_return - buy_hold_return) * 100,
            'win_rate': win_rate * 100,
            'max_drawdown': max_drawdown * 100,
            'total_signals': int((signals > 0).sum()),
            'sharpe_ratio': strategy_returns.mean() / strategy_returns.std() * np.sqrt(252) if strategy_returns.std() > 0 else 0,
        }


# ML 기반 확장 모델
class MLProbabilityModel(ProbabilityModel):
    """ML 기반 확률 예측 모델"""

    def __init__(self):
        super().__init__()
        self.is_trained = False

    def prepare_features(self, data: Dict) -> np.ndarray:
        """
        특성 벡터 생성

        Args:
            data: 각 분석 결과를 포함한 딕셔너리

        Returns:
            특성 벡터
        """
        features = []

        # 거시경제 특성
        macro = data.get('macro', {})
        features.extend([
            macro.get('yield_spread', 0),
            macro.get('cpi_yoy', 2.5),
            macro.get('unemployment_rate', 4.0),
        ])

        # 자금흐름 특성
        flow = data.get('flow', {})
        features.extend([
            flow.get('risk_score', 0.5),
            flow.get('market_breadth', {}).get('health_score', 0.5),
        ])

        # 센티먼트 특성
        sentiment = data.get('sentiment', {})
        features.extend([
            sentiment.get('composite_score', 0),
        ])

        # 기술적 특성
        technical = data.get('technical', {})
        features.extend([
            technical.get('rsi', 50) / 100,
            1 if technical.get('above_ma_200', False) else 0,
        ])

        return np.array(features).reshape(1, -1)

    def train(self, X: np.ndarray, y: np.ndarray):
        """
        모델 학습

        Args:
            X: 특성 행렬
            y: 타겟 (0: 하락, 1: 상승)
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn이 필요합니다.")

        X_scaled = self.scaler.fit_transform(X)
        self.ml_model.fit(X_scaled, y)
        self.is_trained = True

        # 교차 검증
        cv_scores = cross_val_score(self.ml_model, X_scaled, y, cv=5)
        return {
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std(),
        }

    def predict_ml(self, data: Dict) -> Dict:
        """
        ML 기반 예측

        Args:
            data: 분석 데이터

        Returns:
            예측 결과
        """
        if not self.is_trained:
            raise ValueError("모델이 학습되지 않았습니다.")

        features = self.prepare_features(data)
        features_scaled = self.scaler.transform(features)

        # 예측
        prediction = self.ml_model.predict(features_scaled)[0]
        probabilities = self.ml_model.predict_proba(features_scaled)[0]

        return {
            'prediction': 'Up' if prediction == 1 else 'Down',
            'probability_up': probabilities[1],
            'probability_down': probabilities[0],
            'confidence': max(probabilities),
        }
