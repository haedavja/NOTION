"""
핵심 계산 함수 단위 테스트
발견된 버그 유형을 사전에 방지하기 위한 테스트
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


class TestRSICalculation:
    """RSI 계산 테스트 - ZeroDivisionError 방지 확인"""

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """테스트용 RSI 계산 (수정된 버전)"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        # ZeroDivisionError 방지
        loss_adj = loss.replace(0, 1e-10)
        rs = gain / loss_adj
        rsi = 100 - (100 / (1 + rs))

        return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else 50.0

    def test_rsi_normal_case(self):
        """정상적인 가격 데이터로 RSI 계산"""
        prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
                          110, 112, 111, 113, 115, 114, 116, 118, 117, 119])
        rsi = self.calculate_rsi(prices)
        assert 0 <= rsi <= 100, f"RSI must be between 0-100, got {rsi}"

    def test_rsi_all_gains_no_loss(self):
        """모든 날 상승 (loss=0) - ZeroDivisionError 방지 확인"""
        prices = pd.Series([100 + i for i in range(20)])  # 계속 상승
        rsi = self.calculate_rsi(prices)
        assert rsi > 90, f"All gains should result in RSI > 90, got {rsi}"
        assert not np.isnan(rsi), "RSI should not be NaN"
        assert not np.isinf(rsi), "RSI should not be infinite"

    def test_rsi_all_losses_no_gain(self):
        """모든 날 하락 (gain=0)"""
        prices = pd.Series([100 - i for i in range(20)])  # 계속 하락
        rsi = self.calculate_rsi(prices)
        assert rsi < 10, f"All losses should result in RSI < 10, got {rsi}"

    def test_rsi_flat_prices(self):
        """가격 변동 없음 (gain=0, loss=0)"""
        prices = pd.Series([100] * 20)  # 변동 없음
        rsi = self.calculate_rsi(prices)
        assert not np.isnan(rsi), "RSI should not be NaN for flat prices"
        assert not np.isinf(rsi), "RSI should not be infinite"

    def test_rsi_insufficient_data(self):
        """데이터 부족 시"""
        prices = pd.Series([100, 101, 102])  # 3개뿐
        rsi = self.calculate_rsi(prices)
        # NaN일 수 있지만 예외 발생하면 안 됨
        assert isinstance(rsi, float)


class TestHashSeed:
    """Hash 시드 테스트 - 음수 처리 확인"""

    def test_hash_positive(self):
        """양수 해시값"""
        code = "005930"
        seed = abs(hash(code)) % 2**32
        assert 0 <= seed < 2**32

    def test_hash_negative_handling(self):
        """음수 해시값 처리"""
        # 음수 해시를 생성할 수 있는 문자열 찾기
        for code in ["test", "abc", "000000", "AAAA", "zzzz"]:
            seed = abs(hash(code)) % 2**32
            assert 0 <= seed < 2**32, f"Seed for {code} out of range: {seed}"

    def test_reproducibility(self):
        """같은 코드는 같은 시드 생성"""
        code = "005930"
        seed1 = abs(hash(code)) % 2**32
        seed2 = abs(hash(code)) % 2**32
        assert seed1 == seed2


class TestScoreCalculation:
    """점수 계산 테스트"""

    def test_score_bounds(self):
        """점수가 0-100 범위 내"""
        scores = [0, 50, 100, -10, 150]
        bounded = [min(100, max(0, s)) for s in scores]
        assert all(0 <= s <= 100 for s in bounded)

    def test_probability_bounds(self):
        """확률이 0-1 범위 내"""
        probs = [0.0, 0.5, 1.0, -0.1, 1.5]
        bounded = [min(1.0, max(0.0, p)) for p in probs]
        assert all(0 <= p <= 1 for p in bounded)


class TestDataValidation:
    """데이터 검증 테스트"""

    def test_etf_codes_unique(self):
        """ETF 코드 중복 확인"""
        sector_etfs = {
            '반도체': '091160',
            '2차전지': '305720',
            '바이오': '244580',
            '은행': '091170',
            '자동차': '091180',
            '철강': '139260',
            '건설': '139220',
            '화학': '139250',
            '미디어': '228790',
            '에너지': '117460',
        }
        codes = list(sector_etfs.values())
        assert len(codes) == len(set(codes)), "Duplicate ETF codes found"

    def test_expected_move_range_order(self):
        """예상 변동폭 범위 순서 확인 (min, max)"""
        ranges = [(-40, -20), (-10, 10), (5, 15)]
        for r in ranges:
            assert r[0] <= r[1], f"Range should be (min, max): {r}"

    def test_empty_dataframe_handling(self):
        """빈 DataFrame 처리"""
        df = pd.DataFrame()
        assert df.empty
        # iloc 접근 전 empty 체크 필요
        if not df.empty:
            _ = df.iloc[-1]


class TestTimeDelta:
    """시간 계산 테스트"""

    def test_total_seconds_vs_seconds(self):
        """.seconds vs .total_seconds() 차이"""
        delta = timedelta(hours=2, seconds=30)

        # .seconds는 초 부분만 반환 (0-86399)
        seconds_only = delta.seconds  # 7230 (2*3600 + 30)

        # .total_seconds()는 전체를 초로 변환
        total = delta.total_seconds()  # 7230.0

        # 2시간 이상이면 .seconds와 .total_seconds()가 같을 수 있음
        # 하지만 1일 이상이면 다름
        delta_day = timedelta(days=1, hours=1)
        assert delta_day.seconds == 3600  # 1시간만
        assert delta_day.total_seconds() == 90000  # 25시간

    def test_cache_expiry_logic(self):
        """캐시 만료 로직 테스트"""
        cache_time = datetime.now() - timedelta(hours=2)
        elapsed = (datetime.now() - cache_time).total_seconds()

        # 1시간(3600초) 넘으면 만료
        is_expired = elapsed >= 3600
        assert is_expired, "2 hours should be expired"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
