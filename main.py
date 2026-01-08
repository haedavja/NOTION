"""
거시경제 기반 시장 예측 시스템
메인 실행 파일
"""

import argparse
import json
from datetime import datetime

from data.macro_indicators import MacroIndicators, get_sample_macro_data
from data.market_data import MarketData, get_sample_market_data
from data.fund_flow import FundFlowTracker, get_sample_fund_flow
from data.news_collector import NewsCollector, get_sample_news

from analysis.macro_analysis import MacroAnalyzer
from analysis.flow_analysis import FlowAnalyzer
from analysis.sentiment import SentimentAnalyzer
from analysis.technical import TechnicalAnalyzer

from prediction.probability_model import ProbabilityModel
from prediction.scenarios import ScenarioAnalyzer


def run_analysis(use_sample: bool = True, verbose: bool = True):
    """
    전체 분석 실행

    Args:
        use_sample: 샘플 데이터 사용 여부
        verbose: 상세 출력 여부

    Returns:
        분석 결과 딕셔너리
    """
    print("=" * 60)
    print("📊 거시경제 기반 시장 예측 시스템")
    print(f"   분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 데이터 로드
    print("\n[1/5] 데이터 로드 중...")

    if use_sample:
        macro_data = get_sample_macro_data()
        market_data = get_sample_market_data()
        fund_flow_data = get_sample_fund_flow()
        news_data = get_sample_news()
        print("   ✓ 샘플 데이터 로드 완료")
    else:
        # 실시간 데이터 로드 (API 키 필요)
        try:
            macro_collector = MacroIndicators()
            market_collector = MarketData()
            news_collector = NewsCollector()

            macro_data = macro_collector.get_all_indicators()
            market_data = market_collector.get_sector_data()
            news_data = news_collector.get_all_rss_news()
            fund_flow_data = get_sample_fund_flow()  # 자금흐름은 샘플 사용
            print("   ✓ 실시간 데이터 로드 완료")
        except Exception as e:
            print(f"   ⚠ 실시간 데이터 로드 실패: {e}")
            print("   ✓ 샘플 데이터로 대체")
            macro_data = get_sample_macro_data()
            market_data = get_sample_market_data()
            fund_flow_data = get_sample_fund_flow()
            news_data = get_sample_news()

    # 2. 거시경제 분석
    print("\n[2/5] 거시경제 분석 중...")
    macro_analyzer = MacroAnalyzer()
    macro_analysis = macro_analyzer.get_summary(macro_data)

    if verbose:
        print(f"   • 경기 사이클: {macro_analysis['economic_cycle']}")
        print(f"   • 전망: {macro_analysis['overall_outlook']}")

    # 3. 자금흐름 분석
    print("\n[3/5] 자금흐름 분석 중...")
    flow_analyzer = FlowAnalyzer()
    flow_analysis = flow_analyzer.get_flow_summary(market_data)

    if verbose:
        print(f"   • 위험 선호도: {flow_analysis['risk_regime']}")
        print(f"   • 위험 점수: {flow_analysis['risk_score']*100:.1f}")

    # 4. 센티먼트 분석
    print("\n[4/5] 센티먼트 분석 중...")
    sentiment_analyzer = SentimentAnalyzer(use_ml=False)
    sentiment_analysis = sentiment_analyzer.get_summary(news_data)

    if verbose:
        overall = sentiment_analysis.get('overall_analysis', {})
        print(f"   • 종합 센티먼트: {overall.get('overall_sentiment', 'N/A')}")
        print(f"   • 센티먼트 점수: {overall.get('composite_score', 0):.2f}")

    # 5. 기술적 분석
    print("\n[5/5] 기술적 분석 중...")
    technical_analyzer = TechnicalAnalyzer()

    if 'sp500' in market_data.columns:
        technical_analysis = technical_analyzer.get_technical_summary(market_data['sp500'])
    else:
        first_col = market_data.columns[0]
        technical_analysis = technical_analyzer.get_technical_summary(market_data[first_col])

    if verbose:
        print(f"   • 추세: {technical_analysis.get('trend_analysis', {}).get('trend', 'N/A')}")
        print(f"   • 기술적 점수: {technical_analysis.get('composite_score', 0):.2f}")

    # 종합 예측
    print("\n" + "=" * 60)
    print("📈 종합 예측")
    print("=" * 60)

    prob_model = ProbabilityModel()
    prediction = prob_model.predict_probability(
        macro_analysis=macro_analysis,
        flow_analysis=flow_analysis,
        sentiment_analysis=sentiment_analysis,
        technical_analysis=technical_analysis
    )

    print(f"\n🎯 예측 방향: {prediction.direction.value}")
    print(f"   확률: {prediction.probability*100:.1f}%")
    print(f"   신뢰도: {prediction.confidence*100:.1f}%")
    print(f"\n📝 {prediction.description}")

    # 시나리오 분석
    print("\n" + "-" * 60)
    print("📊 시나리오 분석")
    print("-" * 60)

    scenario_analyzer = ScenarioAnalyzer()
    scenario_summary = scenario_analyzer.get_summary(
        macro_analysis, flow_analysis, sentiment_analysis
    )

    most_likely = scenario_summary.get('most_likely_scenario', {})
    print(f"\n가장 가능성 높은 시나리오: {most_likely.get('name', 'N/A')}")
    print(f"확률: {most_likely.get('probability', 0):.1f}%")
    print(f"설명: {most_likely.get('description', '')}")

    # 자산 배분 추천
    print("\n" + "-" * 60)
    print("💰 권장 자산 배분")
    print("-" * 60)

    allocation = scenario_summary.get('recommended_allocation', {})
    for asset, weight in allocation.items():
        asset_kr = {'equities': '주식', 'bonds': '채권', 'gold': '금', 'cash': '현금'}
        print(f"   • {asset_kr.get(asset, asset)}: {weight:.1f}%")

    # 섹터 추천
    print("\n" + "-" * 60)
    print("🏭 섹터 추천")
    print("-" * 60)

    sector_recs = scenario_summary.get('sector_recommendations', {})
    print(f"   비중 확대: {', '.join(sector_recs.get('overweight', []))}")
    print(f"   비중 축소: {', '.join(sector_recs.get('underweight', []))}")

    # 리스크 요인
    print("\n" + "-" * 60)
    print("⚠️ 주요 리스크 요인")
    print("-" * 60)

    for risk in scenario_summary.get('risk_factors', []):
        print(f"   • {risk}")

    print("\n" + "=" * 60)
    print("✅ 분석 완료")
    print("=" * 60)

    # 결과 반환
    return {
        'timestamp': datetime.now().isoformat(),
        'prediction': {
            'direction': prediction.direction.value,
            'probability': prediction.probability,
            'confidence': prediction.confidence,
        },
        'macro_analysis': macro_analysis,
        'flow_analysis': flow_analysis,
        'sentiment_analysis': sentiment_analysis,
        'technical_analysis': technical_analysis,
        'scenario_summary': scenario_summary,
    }


def run_dashboard():
    """Streamlit 대시보드 실행"""
    import subprocess
    import sys

    print("대시보드를 시작합니다...")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "dashboard/app.py",
        "--server.port", "8501"
    ])


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description='거시경제 기반 시장 예측 시스템'
    )

    parser.add_argument(
        '--mode',
        choices=['analysis', 'dashboard'],
        default='analysis',
        help='실행 모드: analysis(분석), dashboard(대시보드)'
    )

    parser.add_argument(
        '--sample',
        action='store_true',
        default=True,
        help='샘플 데이터 사용 (기본값: True)'
    )

    parser.add_argument(
        '--live',
        action='store_true',
        help='실시간 데이터 사용 (API 키 필요)'
    )

    parser.add_argument(
        '--output',
        type=str,
        help='결과 저장 파일 (JSON)'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='간략한 출력'
    )

    args = parser.parse_args()

    if args.mode == 'dashboard':
        run_dashboard()
    else:
        use_sample = not args.live
        result = run_analysis(use_sample=use_sample, verbose=not args.quiet)

        if args.output:
            # JSON으로 저장
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2, default=str)
            print(f"\n결과가 {args.output}에 저장되었습니다.")


if __name__ == "__main__":
    main()
