"""
Snowflake 시각화 모듈 테스트 - 중앙화된 설정 통합 포함
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from analysis.snowflake_viz import (
        SnowflakeScores, SnowflakeAnalyzer,
        get_score_interpretation, get_overall_rating,
        snowflake_analyzer, _USE_CENTRAL_CONFIG
    )
    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SNOWFLAKE_AVAILABLE = False

try:
    from config.constants import SNOWFLAKE as SNOWFLAKE_CONFIG
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False


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
        # total은 가중 평균 (value*0.25 + future*0.20 + past*0.20 + dividend*0.10 + health*0.25)
        expected_total = 4.0 * 0.25 + 3.5 * 0.20 + 4.2 * 0.20 + 3.0 * 0.10 + 4.5 * 0.25
        assert abs(scores.total - expected_total) < 0.01

    def test_scores_total_calculation(self):
        """총점 계산 (가중 평균)"""
        scores = SnowflakeScores(
            value=5.0,
            future=5.0,
            past=5.0,
            dividend=5.0,
            health=5.0
        )
        # 모든 점수가 5.0이면 가중평균도 5.0
        assert abs(scores.total - 5.0) < 0.01

        scores_low = SnowflakeScores(
            value=1.0,
            future=1.0,
            past=1.0,
            dividend=1.0,
            health=1.0
        )
        # 모든 점수가 1.0이면 가중평균도 1.0
        assert abs(scores_low.total - 1.0) < 0.01

    def test_scores_boundary_values(self):
        """경계값 테스트"""
        # 최소값
        scores_min = SnowflakeScores(
            value=0.0, future=0.0, past=0.0, dividend=0.0, health=0.0
        )
        assert abs(scores_min.total - 0.0) < 0.01

        # 최대값
        scores_max = SnowflakeScores(
            value=6.0, future=6.0, past=6.0, dividend=6.0, health=6.0
        )
        assert abs(scores_max.total - 6.0) < 0.01

    def test_scores_min_score(self):
        """최소 점수 반환"""
        scores = SnowflakeScores(
            value=4.0, future=2.0, past=3.0, dividend=1.5, health=5.0
        )
        assert scores.min_score == 1.5

    def test_scores_to_dict(self):
        """딕셔너리 변환"""
        scores = SnowflakeScores(
            value=4.0, future=3.0, past=3.5, dividend=2.0, health=4.5
        )
        d = scores.to_dict()
        assert d['가치'] == 4.0
        assert d['미래'] == 3.0
        assert d['과거'] == 3.5
        assert d['배당'] == 2.0
        assert d['건전성'] == 4.5


@pytest.mark.skipif(not SNOWFLAKE_AVAILABLE, reason="Snowflake module not available")
class TestSnowflakeAnalyzer:
    """Snowflake 분석기 테스트"""

    @pytest.fixture
    def analyzer(self):
        """SnowflakeAnalyzer 인스턴스"""
        return SnowflakeAnalyzer()

    def test_analyzer_sector_data(self, analyzer):
        """섹터 데이터 존재 확인 (property 형태)"""
        sector_per = analyzer.SECTOR_AVG_PER
        assert len(sector_per) > 0
        assert '반도체' in sector_per
        assert 'default' in sector_per

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


@pytest.mark.skipif(not SNOWFLAKE_AVAILABLE or not CONFIG_AVAILABLE,
                    reason="Snowflake or config module not available")
class TestCentralConfigIntegration:
    """중앙화된 설정 통합 테스트"""

    def test_central_config_flag(self):
        """중앙 설정 플래그 확인"""
        assert _USE_CENTRAL_CONFIG is True

    def test_weights_from_config(self):
        """가중치가 중앙 설정에서 로드되는지 확인"""
        weights = SNOWFLAKE_CONFIG.weights
        assert 'value' in weights
        assert 'future' in weights
        assert 'past' in weights
        assert 'dividend' in weights
        assert 'health' in weights
        # 가중치 합계는 1.0
        total_weight = sum(weights.values())
        assert abs(total_weight - 1.0) < 0.01

    def test_grade_thresholds_from_config(self):
        """등급 기준이 중앙 설정에서 로드되는지 확인"""
        assert SNOWFLAKE_CONFIG.grade_a_plus >= SNOWFLAKE_CONFIG.grade_a
        assert SNOWFLAKE_CONFIG.grade_a >= SNOWFLAKE_CONFIG.grade_b
        assert SNOWFLAKE_CONFIG.grade_b >= SNOWFLAKE_CONFIG.grade_c
        assert SNOWFLAKE_CONFIG.grade_c >= SNOWFLAKE_CONFIG.grade_d

    def test_sector_per_from_config(self):
        """섹터별 PER이 중앙 설정에서 로드되는지 확인"""
        sector_per = SNOWFLAKE_CONFIG.sector_per
        assert '반도체' in sector_per
        assert 'default' in sector_per
        assert sector_per['반도체'] == 20
        assert sector_per['바이오'] == 50

    def test_get_overall_rating_uses_config(self):
        """get_overall_rating이 중앙 설정 등급 기준을 사용하는지 확인"""
        # A+ 등급 (grade_a_plus = 5.0 이상)
        scores_a_plus = SnowflakeScores(
            value=5.5, future=5.5, past=5.5, dividend=5.5, health=5.5
        )
        grade, emoji, desc = get_overall_rating(scores_a_plus)
        assert grade == "A+"

        # B 등급 (grade_b = 3.5)
        scores_b = SnowflakeScores(
            value=3.6, future=3.6, past=3.6, dividend=3.6, health=3.6
        )
        grade_b, _, _ = get_overall_rating(scores_b)
        assert grade_b in ["B", "B+"]

        # C 등급 (grade_c = 3.0)
        scores_c = SnowflakeScores(
            value=3.1, future=3.1, past=3.1, dividend=3.1, health=3.1
        )
        grade_c, _, _ = get_overall_rating(scores_c)
        assert grade_c == "C+"


@pytest.mark.skipif(not SNOWFLAKE_AVAILABLE, reason="Snowflake module not available")
class TestScoreInterpretationExtended:
    """점수 해석 확장 테스트"""

    def test_interpretation_high_scores(self):
        """높은 점수 해석"""
        scores = SnowflakeScores(
            value=5.0, future=5.0, past=5.0, dividend=5.0, health=5.0
        )
        interpretations = get_score_interpretation(scores)

        # 모든 축에 대해 긍정적 해석 (🟢 포함)
        for key, value in interpretations.items():
            assert '🟢' in value

    def test_interpretation_low_scores(self):
        """낮은 점수 해석"""
        scores = SnowflakeScores(
            value=1.0, future=1.0, past=1.0, dividend=1.0, health=1.0
        )
        interpretations = get_score_interpretation(scores)

        # 모든 축에 대해 부정적 해석 (🔴 포함)
        for key, value in interpretations.items():
            assert '🔴' in value

    def test_grade_rating_range(self):
        """모든 등급 범위 테스트"""
        test_cases = [
            (5.5, "A+"),
            (4.6, "A"),
            (4.1, "B+"),
            (3.6, "B"),
            (3.1, "C+"),
            (2.6, "C"),
            (2.1, "D"),
            (1.5, "F"),
        ]

        for score_val, expected_prefix in test_cases:
            scores = SnowflakeScores(
                value=score_val, future=score_val, past=score_val,
                dividend=score_val, health=score_val
            )
            grade, _, _ = get_overall_rating(scores)
            assert grade.startswith(expected_prefix[0]), f"Score {score_val} expected {expected_prefix}, got {grade}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
