"""
Snowflake 시각화 모듈 테스트
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from analysis.snowflake_viz import (
        SnowflakeScores, SnowflakeAnalyzer,
        get_score_interpretation, get_overall_rating,
        snowflake_analyzer
    )
    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SNOWFLAKE_AVAILABLE = False


@pytest.mark.skipif(not SNOWFLAKE_AVAILABLE, reason="Snowflake module not available")
class TestSnowflakeScores:
    """Snowflake 점수 데이터클래스 테스트"""

    def test_scores_creation(self):
        """SnowflakeScores 생성"""
        scores = SnowflakeScores(
            value=4.0,
            future=3.5,
            past=4.2,
            dividend=3.0,
            health=4.5
        )

        assert scores.value == 4.0
        assert scores.future == 3.5
        assert scores.past == 4.2
        assert scores.dividend == 3.0
        assert scores.health == 4.5
        assert scores.total == 4.0 + 3.5 + 4.2 + 3.0 + 4.5

    def test_scores_total_calculation(self):
        """총점 계산"""
        scores = SnowflakeScores(
            value=5.0,
            future=5.0,
            past=5.0,
            dividend=5.0,
            health=5.0
        )
        assert scores.total == 25.0

        scores_low = SnowflakeScores(
            value=1.0,
            future=1.0,
            past=1.0,
            dividend=1.0,
            health=1.0
        )
        assert scores_low.total == 5.0

    def test_scores_boundary_values(self):
        """경계값 테스트"""
        # 최소값
        scores_min = SnowflakeScores(
            value=0.0, future=0.0, past=0.0, dividend=0.0, health=0.0
        )
        assert scores_min.total == 0.0

        # 최대값
        scores_max = SnowflakeScores(
            value=6.0, future=6.0, past=6.0, dividend=6.0, health=6.0
        )
        assert scores_max.total == 30.0


@pytest.mark.skipif(not SNOWFLAKE_AVAILABLE, reason="Snowflake module not available")
class TestSnowflakeAnalyzer:
    """Snowflake 분석기 테스트"""

    @pytest.fixture
    def analyzer(self):
        """SnowflakeAnalyzer 인스턴스"""
        return SnowflakeAnalyzer()

    def test_analyzer_sector_data(self, analyzer):
        """섹터 데이터 존재 확인"""
        assert hasattr(analyzer, 'sector_per_avg')
        assert len(analyzer.sector_per_avg) > 0
        assert '반도체' in analyzer.sector_per_avg
        assert 'default' in analyzer.sector_per_avg

    def test_calculate_scores_basic(self, analyzer):
        """기본 점수 계산"""
        fundamentals = {
            'per': 15,
            'pbr': 1.5,
            'roe': 15,
            'dividend_yield': 2.0,
            'debt_ratio': 50,
            'current_ratio': 1.5,
            'revenue_growth': 10,
            'operating_margin': 15
        }

        scores = analyzer.calculate_scores(fundamentals)

        assert isinstance(scores, SnowflakeScores)
        assert 0 <= scores.value <= 6
        assert 0 <= scores.future <= 6
        assert 0 <= scores.past <= 6
        assert 0 <= scores.dividend <= 6
        assert 0 <= scores.health <= 6

    def test_calculate_scores_with_sector(self, analyzer):
        """섹터별 점수 계산"""
        fundamentals = {
            'per': 20,
            'pbr': 2.0,
            'roe': 12,
            'dividend_yield': 1.5,
            'debt_ratio': 60,
        }

        scores_default = analyzer.calculate_scores(fundamentals, sector='default')
        scores_semi = analyzer.calculate_scores(fundamentals, sector='반도체')

        # 섹터에 따라 value 점수가 다를 수 있음
        assert scores_default is not None
        assert scores_semi is not None

    def test_calculate_scores_missing_data(self, analyzer):
        """데이터 누락 시 처리"""
        # 최소 데이터
        fundamentals = {'per': 15}
        scores = analyzer.calculate_scores(fundamentals)
        assert scores is not None

        # 빈 데이터
        scores_empty = analyzer.calculate_scores({})
        assert scores_empty is not None

    def test_value_score_calculation(self, analyzer):
        """가치 점수 계산"""
        # 저평가
        low_valuation = {'per': 8, 'pbr': 0.8}
        scores_low = analyzer.calculate_scores(low_valuation)

        # 고평가
        high_valuation = {'per': 50, 'pbr': 5.0}
        scores_high = analyzer.calculate_scores(high_valuation)

        # 저평가가 더 높은 가치 점수
        assert scores_low.value >= scores_high.value

    def test_health_score_calculation(self, analyzer):
        """재무 건전성 점수 계산"""
        # 건전한 재무
        healthy = {'debt_ratio': 30, 'current_ratio': 2.5}
        scores_healthy = analyzer.calculate_scores(healthy)

        # 취약한 재무
        weak = {'debt_ratio': 200, 'current_ratio': 0.5}
        scores_weak = analyzer.calculate_scores(weak)

        # 건전한 쪽이 더 높은 점수
        assert scores_healthy.health >= scores_weak.health


@pytest.mark.skipif(not SNOWFLAKE_AVAILABLE, reason="Snowflake module not available")
class TestScoreInterpretation:
    """점수 해석 테스트"""

    def test_get_score_interpretation(self):
        """점수 해석 생성"""
        scores = SnowflakeScores(
            value=4.5,
            future=3.0,
            past=4.0,
            dividend=2.5,
            health=5.0
        )

        interpretations = get_score_interpretation(scores)

        assert isinstance(interpretations, dict)
        assert len(interpretations) > 0

    def test_get_overall_rating(self):
        """종합 등급 생성"""
        # 우수
        scores_excellent = SnowflakeScores(
            value=5.0, future=5.0, past=5.0, dividend=5.0, health=5.0
        )
        grade, emoji, desc = get_overall_rating(scores_excellent)
        assert grade in ["A+", "A", "B+", "B", "C", "D", "F"]
        assert emoji is not None
        assert desc is not None

        # 저조
        scores_poor = SnowflakeScores(
            value=1.0, future=1.0, past=1.0, dividend=1.0, health=1.0
        )
        grade_poor, _, _ = get_overall_rating(scores_poor)
        assert grade_poor in ["A+", "A", "B+", "B", "C", "D", "F"]


@pytest.mark.skipif(not SNOWFLAKE_AVAILABLE, reason="Snowflake module not available")
class TestSnowflakeSingleton:
    """싱글톤 인스턴스 테스트"""

    def test_singleton_exists(self):
        """싱글톤 인스턴스 존재"""
        assert snowflake_analyzer is not None
        assert isinstance(snowflake_analyzer, SnowflakeAnalyzer)

    def test_singleton_methods(self):
        """싱글톤 메서드 접근"""
        scores = snowflake_analyzer.calculate_scores({'per': 15, 'roe': 10})
        assert scores is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
