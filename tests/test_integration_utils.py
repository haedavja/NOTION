"""
통합 유틸리티 모듈 테스트
"""

import pytest
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from analysis.integration_utils import (
        convert_fundamentals_to_snowflake_data,
        get_snowflake_scores_for_stock,
        clear_snowflake_cache,
        get_investment_insight,
        normalize_sector,
        SECTOR_MAPPING,
        _make_cache_key,
        _snowflake_cache,
        _cache_ttl
    )
    INTEGRATION_AVAILABLE = True
except ImportError:
    INTEGRATION_AVAILABLE = False

try:
    from analysis.snowflake_viz import SnowflakeScores
    SNOWFLAKE_AVAILABLE = True
except ImportError:
    SNOWFLAKE_AVAILABLE = False


@pytest.mark.skipif(not INTEGRATION_AVAILABLE, reason="Integration module not available")
class TestConvertFundamentals:
    """펀더멘털 변환 테스트"""

    def test_convert_dict(self):
        """dict 변환"""
        data = {'per': 15, 'pbr': 1.5, 'roe': 10}
        result = convert_fundamentals_to_snowflake_data(data)

        assert result == data

    def test_convert_dataclass(self):
        """dataclass 변환"""
        from dataclasses import dataclass

        @dataclass
        class MockFundamentals:
            per: float = 15.0
            pbr: float = 1.5
            roe: float = 10.0
            dividend_yield: float = 2.0
            debt_ratio: float = 50.0

        fundamentals = MockFundamentals()
        result = convert_fundamentals_to_snowflake_data(fundamentals)

        assert result['per'] == 15.0
        assert result['pbr'] == 1.5
        assert result['roe'] == 10.0
        assert result['dividend_yield'] == 2.0
        assert result['debt_ratio'] == 50.0

    def test_convert_empty(self):
        """빈 데이터 처리"""
        result = convert_fundamentals_to_snowflake_data(None)
        assert result == {}

        result = convert_fundamentals_to_snowflake_data([])
        assert result == {}


@pytest.mark.skipif(not INTEGRATION_AVAILABLE or not SNOWFLAKE_AVAILABLE,
                    reason="Required modules not available")
class TestSnowflakeCache:
    """Snowflake 캐싱 테스트"""

    def setup_method(self):
        """테스트 전 캐시 초기화"""
        clear_snowflake_cache()

    def test_cache_key_generation(self):
        """캐시 키 생성"""
        data1 = {'per': 15, 'pbr': 1.5}
        data2 = {'per': 15, 'pbr': 1.5}
        data3 = {'per': 20, 'pbr': 2.0}

        key1 = _make_cache_key(data1, 'default')
        key2 = _make_cache_key(data2, 'default')
        key3 = _make_cache_key(data3, 'default')

        # 같은 데이터는 같은 키
        assert key1 == key2
        # 다른 데이터는 다른 키
        assert key1 != key3

    def test_cache_different_sectors(self):
        """섹터별 캐시 분리"""
        data = {'per': 15}

        key_default = _make_cache_key(data, 'default')
        key_semi = _make_cache_key(data, '반도체')

        # 같은 데이터여도 섹터가 다르면 다른 키
        assert key_default != key_semi

    def test_get_scores_caching(self):
        """점수 캐싱 동작"""
        fundamentals = {'per': 15, 'pbr': 1.5, 'roe': 10}

        # 첫 번째 호출
        scores1 = get_snowflake_scores_for_stock(fundamentals)

        # 캐시에 저장되었는지 확인
        assert len(_snowflake_cache) > 0

        # 두 번째 호출 (캐시에서)
        scores2 = get_snowflake_scores_for_stock(fundamentals)

        # 동일한 결과
        assert scores1.total == scores2.total

    def test_clear_cache(self):
        """캐시 초기화"""
        fundamentals = {'per': 15}
        get_snowflake_scores_for_stock(fundamentals)

        assert len(_snowflake_cache) > 0

        clear_snowflake_cache()

        assert len(_snowflake_cache) == 0

    def test_cache_returns_scores(self):
        """캐시된 값 반환 검증"""
        fundamentals = {'per': 15, 'pbr': 1.5}
        scores = get_snowflake_scores_for_stock(fundamentals)

        assert scores is not None
        assert isinstance(scores, SnowflakeScores)
        assert hasattr(scores, 'total')


@pytest.mark.skipif(not INTEGRATION_AVAILABLE or not SNOWFLAKE_AVAILABLE,
                    reason="Required modules not available")
class TestInvestmentInsight:
    """투자 인사이트 테스트"""

    def test_insight_excellent(self):
        """우수 종목 인사이트"""
        scores = SnowflakeScores(
            value=5.0, future=4.5, past=4.0, dividend=4.0, health=5.0
        )
        insight = get_investment_insight(scores)

        assert "강점" in insight
        assert "저평가" in insight or "성장" in insight or "실적" in insight

    def test_insight_poor(self):
        """저조 종목 인사이트"""
        scores = SnowflakeScores(
            value=1.0, future=1.5, past=2.0, dividend=1.0, health=1.5
        )
        insight = get_investment_insight(scores)

        assert "약점" in insight or "신중한" in insight

    def test_insight_mixed(self):
        """혼합 종목 인사이트"""
        scores = SnowflakeScores(
            value=5.0, future=4.0, past=2.0, dividend=2.0, health=4.0
        )
        insight = get_investment_insight(scores)

        assert "강점" in insight
        assert "약점" in insight or "→" in insight

    def test_insight_categories(self):
        """카테고리별 인사이트"""
        # 저평가 매력
        scores_value = SnowflakeScores(
            value=5.0, future=3.0, past=3.0, dividend=3.0, health=3.0
        )
        assert "저평가" in get_investment_insight(scores_value)

        # 성장 기대
        scores_growth = SnowflakeScores(
            value=3.0, future=5.0, past=3.0, dividend=3.0, health=3.0
        )
        assert "성장" in get_investment_insight(scores_growth)

        # 배당 매력
        scores_dividend = SnowflakeScores(
            value=3.0, future=3.0, past=3.0, dividend=5.0, health=3.0
        )
        assert "배당" in get_investment_insight(scores_dividend)


@pytest.mark.skipif(not INTEGRATION_AVAILABLE, reason="Integration module not available")
class TestSectorMapping:
    """섹터 매핑 테스트"""

    def test_sector_mapping_exists(self):
        """섹터 매핑 존재"""
        assert len(SECTOR_MAPPING) > 0
        assert '반도체' in SECTOR_MAPPING
        assert 'IT' in SECTOR_MAPPING
        assert '바이오' in SECTOR_MAPPING

    def test_normalize_sector(self):
        """섹터 정규화"""
        assert normalize_sector('반도체') == '반도체'
        assert normalize_sector('소프트웨어') == 'IT'
        assert normalize_sector('인터넷') == 'IT'
        assert normalize_sector('배터리') == '2차전지'

    def test_normalize_sector_empty(self):
        """빈 섹터 처리"""
        assert normalize_sector('') == 'default'
        assert normalize_sector(None) == 'default'

    def test_normalize_sector_unknown(self):
        """알 수 없는 섹터"""
        assert normalize_sector('새로운섹터') == '새로운섹터'


@pytest.mark.skipif(not INTEGRATION_AVAILABLE, reason="Integration module not available")
class TestGetSnowflakeScores:
    """Snowflake 점수 조회 테스트"""

    def setup_method(self):
        """테스트 전 캐시 초기화"""
        clear_snowflake_cache()

    def test_get_scores_none_data(self):
        """None 데이터 처리"""
        result = get_snowflake_scores_for_stock(None)
        assert result is None

    def test_get_scores_empty_data(self):
        """빈 데이터 처리"""
        result = get_snowflake_scores_for_stock({})
        # 빈 데이터도 기본값으로 처리될 수 있음
        # 구현에 따라 None 또는 기본값 반환

    @pytest.mark.skipif(not SNOWFLAKE_AVAILABLE, reason="Snowflake not available")
    def test_get_scores_valid_data(self):
        """유효한 데이터 처리"""
        fundamentals = {
            'per': 15,
            'pbr': 1.5,
            'roe': 12,
            'dividend_yield': 2.0,
            'debt_ratio': 50
        }

        scores = get_snowflake_scores_for_stock(fundamentals)

        assert scores is not None
        assert 0 <= scores.value <= 6
        assert 0 <= scores.total <= 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
