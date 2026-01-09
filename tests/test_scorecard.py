"""
종합 스코어카드 모듈 테스트
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.scorecard import (
    ScoreCategory, CategoryScore, ComprehensiveScorecard,
    ScorecardGenerator, render_comprehensive_scorecard
)


class TestScoreCategory:
    """점수 카테고리 테스트"""

    def test_score_categories_exist(self):
        """모든 필수 카테고리 존재 확인"""
        assert ScoreCategory.SNOWFLAKE.value == "펀더멘털"
        assert ScoreCategory.TECHNICAL.value == "기술적"
        assert ScoreCategory.SUPPLY_DEMAND.value == "수급"
        assert ScoreCategory.POTENTIAL.value == "잠재 요인"
        assert ScoreCategory.RALLY_CREDIBILITY.value == "상승 신뢰도"


class TestCategoryScore:
    """카테고리별 점수 테스트"""

    def test_category_score_creation(self):
        """CategoryScore 생성"""
        cat_score = CategoryScore(
            category=ScoreCategory.SNOWFLAKE,
            score=75.0,
            grade="B+",
            summary="양호한 펀더멘털",
            details={'value': 4.0, 'future': 3.5}
        )

        assert cat_score.category == ScoreCategory.SNOWFLAKE
        assert cat_score.score == 75.0
        assert cat_score.grade == "B+"
        assert cat_score.summary == "양호한 펀더멘털"
        assert 'value' in cat_score.details


class TestScorecardGenerator:
    """스코어카드 생성기 테스트"""

    @pytest.fixture
    def generator(self):
        """ScorecardGenerator 인스턴스"""
        return ScorecardGenerator()

    def test_generator_weights(self, generator):
        """가중치 합계 검증"""
        total_weight = sum(generator.weights.values())
        assert abs(total_weight - 1.0) < 0.001

    def test_get_grade_boundaries(self, generator):
        """등급 경계값 테스트"""
        assert generator._get_grade(95) == "A+"
        assert generator._get_grade(90) == "A+"
        assert generator._get_grade(85) == "A"
        assert generator._get_grade(80) == "A"
        assert generator._get_grade(75) == "B+"
        assert generator._get_grade(70) == "B+"
        assert generator._get_grade(65) == "B"
        assert generator._get_grade(60) == "B"
        assert generator._get_grade(55) == "C"
        assert generator._get_grade(50) == "C"
        assert generator._get_grade(45) == "D"
        assert generator._get_grade(40) == "D"
        assert generator._get_grade(35) == "F"
        assert generator._get_grade(0) == "F"

    def test_get_star_rating(self, generator):
        """별점 계산 테스트"""
        assert generator._get_star_rating(85) == 5
        assert generator._get_star_rating(80) == 5
        assert generator._get_star_rating(70) == 4
        assert generator._get_star_rating(65) == 4
        assert generator._get_star_rating(55) == 3
        assert generator._get_star_rating(50) == 3
        assert generator._get_star_rating(40) == 2
        assert generator._get_star_rating(35) == 2
        assert generator._get_star_rating(30) == 1
        assert generator._get_star_rating(0) == 1

    def test_get_recommendation(self, generator):
        """투자 권고 테스트"""
        assert generator._get_recommendation(75, []) == "적극 매수"
        assert generator._get_recommendation(70, []) == "적극 매수"
        assert generator._get_recommendation(65, []) == "매수"
        assert generator._get_recommendation(60, []) == "매수"
        assert generator._get_recommendation(55, []) == "보유"
        assert generator._get_recommendation(50, []) == "보유"
        assert generator._get_recommendation(45, []) == "비중 축소"
        assert generator._get_recommendation(40, []) == "비중 축소"
        assert generator._get_recommendation(35, []) == "매도 검토"
        assert generator._get_recommendation(0, []) == "매도 검토"

    def test_calculate_technical_score(self, generator):
        """기술적 점수 계산"""
        # 중립 상태
        score_neutral = generator._calculate_technical_score({
            'rsi': 50, 'trend': '중립', 'ma_signal': ''
        })
        assert 40 <= score_neutral <= 70

        # 상승 신호
        score_bullish = generator._calculate_technical_score({
            'rsi': 45, 'trend': '상승', 'ma_signal': '골든크로스'
        })
        assert score_bullish > score_neutral

        # 과매도
        score_oversold = generator._calculate_technical_score({
            'rsi': 25, 'trend': '하락', 'ma_signal': ''
        })
        assert score_oversold > 50  # 과매도는 매수 기회

        # 과매수
        score_overbought = generator._calculate_technical_score({
            'rsi': 75, 'trend': '상승', 'ma_signal': ''
        })
        assert score_overbought < 80

    def test_calculate_supply_demand_score(self, generator):
        """수급 점수 계산"""
        # 수급 양호
        score_good = generator._calculate_supply_demand_score({
            'foreign_net': 100, 'inst_net': 50, 'trend': '매집'
        })
        assert score_good >= 70

        # 수급 불량
        score_bad = generator._calculate_supply_demand_score({
            'foreign_net': -100, 'inst_net': -50, 'trend': '이탈'
        })
        assert score_bad <= 40

        # 중립
        score_neutral = generator._calculate_supply_demand_score({
            'foreign_net': 0, 'inst_net': 0, 'trend': '중립'
        })
        assert 40 <= score_neutral <= 60

    def test_generate_minimal(self, generator):
        """최소 데이터로 스코어카드 생성"""
        scorecard = generator.generate(
            symbol="TEST",
            name="테스트 종목"
        )

        assert scorecard.symbol == "TEST"
        assert scorecard.name == "테스트 종목"
        assert scorecard.overall_score == 50  # 기본값
        assert scorecard.overall_grade is not None
        assert 1 <= scorecard.overall_rating <= 5

    def test_generate_with_technical(self, generator):
        """기술적 데이터로 스코어카드 생성"""
        scorecard = generator.generate(
            symbol="TEST",
            name="테스트 종목",
            technical_data={'rsi': 45, 'trend': '상승', 'ma_signal': '골든크로스'}
        )

        assert len(scorecard.categories) >= 1
        assert any(c.category == ScoreCategory.TECHNICAL for c in scorecard.categories)

    def test_generate_with_supply_demand(self, generator):
        """수급 데이터로 스코어카드 생성"""
        scorecard = generator.generate(
            symbol="TEST",
            name="테스트 종목",
            supply_demand_data={'foreign_net': 100, 'inst_net': 50, 'trend': '매집'}
        )

        assert any(c.category == ScoreCategory.SUPPLY_DEMAND for c in scorecard.categories)

    def test_generate_full(self, generator):
        """전체 데이터로 스코어카드 생성"""
        # Mock snowflake scores
        class MockSnowflakeScores:
            def __init__(self):
                self.value = 4.0
                self.future = 3.5
                self.past = 4.0
                self.dividend = 3.0
                self.health = 4.5
                self.total = 19.0

        # Mock potential analysis
        class MockPotential:
            bullish_score = 70
            bearish_score = 30

        # Mock rally credibility
        class MockRally:
            overall = 65
            level = type('Level', (), {'value': '보통'})()

        scorecard = generator.generate(
            symbol="005930",
            name="삼성전자",
            snowflake_scores=MockSnowflakeScores(),
            technical_data={'rsi': 55, 'trend': '상승', 'ma_signal': '골든크로스'},
            supply_demand_data={'foreign_net': 80, 'inst_net': 40, 'trend': '매집'},
            potential_analysis=MockPotential(),
            rally_credibility=MockRally()
        )

        # 5개 카테고리 모두 포함
        assert len(scorecard.categories) == 5

        # 점수 범위 확인
        assert 0 <= scorecard.overall_score <= 100

        # 등급/권고 확인
        assert scorecard.overall_grade in ["A+", "A", "B+", "B", "C", "D", "F"]
        assert scorecard.recommendation in ["적극 매수", "매수", "보유", "비중 축소", "매도 검토"]

    def test_strengths_weaknesses_analysis(self, generator):
        """강점/약점 분석"""
        categories = [
            CategoryScore(ScoreCategory.SNOWFLAKE, 80, "A", "우수한 펀더멘털"),
            CategoryScore(ScoreCategory.TECHNICAL, 35, "F", "과매수 주의"),
            CategoryScore(ScoreCategory.SUPPLY_DEMAND, 60, "B", "수급 중립"),
        ]

        strengths, weaknesses = generator._analyze_strengths_weaknesses(categories)

        assert len(strengths) >= 1  # Snowflake는 강점
        assert len(weaknesses) >= 1  # Technical은 약점

    def test_key_insight_generation(self, generator):
        """핵심 인사이트 생성"""
        # 높은 점수
        insight_high = generator._generate_key_insight(
            75, [], ["강점1", "강점2", "강점3"], []
        )
        assert "우수한" in insight_high or "양호" in insight_high

        # 중간 점수
        insight_mid = generator._generate_key_insight(
            55, [], [], ["약점1"]
        )
        assert "개선" in insight_mid or "평균" in insight_mid

        # 낮은 점수
        insight_low = generator._generate_key_insight(
            35, [], [], ["약점1", "약점2"]
        )
        assert "주의" in insight_low or "낮" in insight_low


class TestComprehensiveScorecard:
    """종합 스코어카드 데이터클래스 테스트"""

    def test_scorecard_creation(self):
        """스코어카드 생성"""
        scorecard = ComprehensiveScorecard(
            symbol="005930",
            name="삼성전자",
            overall_score=72.5,
            overall_grade="B+",
            overall_rating=4,
            recommendation="적극 매수",
            categories=[],
            strengths=["펀더멘털 우수"],
            weaknesses=[],
            key_insight="양호한 투자 후보"
        )

        assert scorecard.symbol == "005930"
        assert scorecard.overall_score == 72.5
        assert scorecard.overall_rating == 4
        assert len(scorecard.strengths) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
