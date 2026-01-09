"""
데이터 영속성 모듈
포트폴리오, 보고서, 설정을 JSON 파일로 저장/로드

=== 인수인계 메모 ===

[스레드 안전성]
- 모든 메서드는 RLock으로 보호됨
- RLock 사용 이유: 재귀적 호출 허용 (같은 스레드에서 중첩 락 가능)
- 파일 I/O가 있는 모든 작업은 락 내부에서 수행

[저장 위치]
기본 경로: ~/.notion_portfolio/
├── portfolio.json    # 포트폴리오 데이터
├── reports.json      # 보고서 히스토리
├── settings.json     # 사용자 설정
└── alerts.json       # 알림 히스토리

[보안: 경로 검증]
export_all(), import_all()에 경로 검증 적용:
- '..' 포함 여부 (경로 탐색 공격)
- 허용 확장자: .json, .csv, .xlsx만 허용
- 로그에 경로 탐색 시도 기록

[전역 인스턴스]
data_store = DataStore()  # 모듈 임포트 시 자동 생성
직접 생성하지 말고 이 인스턴스 사용 권장

[확장 시 주의]
- 새 저장 메서드 추가 시 반드시 with self._lock: 사용
- 새 파일 추가 시 __init__에 경로 추가
- clear_all() 수정 시 새 파일도 포함

[데이터 형식]
- 모든 데이터는 JSON으로 저장
- datetime은 ISO 형식 문자열로 변환
- Enum은 .value로 변환
"""

import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import asdict
from threading import RLock

from .portfolio import Portfolio, Position, AssetType
from .thesis_evaluator import ThesisReport, ThesisReportHistory

logger = logging.getLogger(__name__)


class DataStore:
    """JSON 기반 데이터 저장소 (스레드 안전)"""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # 기본 저장 경로: 사용자 홈 디렉토리
            data_dir = os.path.join(os.path.expanduser("~"), ".notion_portfolio")

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 파일 경로
        self.portfolio_file = self.data_dir / "portfolio.json"
        self.reports_file = self.data_dir / "reports.json"
        self.settings_file = self.data_dir / "settings.json"
        self.alerts_file = self.data_dir / "alerts.json"

        # 스레드 안전성을 위한 락 (RLock은 재귀적 락킹 허용)
        self._lock = RLock()

    # ===== 포트폴리오 저장/로드 =====

    def save_portfolio(self, portfolio: Portfolio) -> bool:
        """포트폴리오 저장 (스레드 안전)"""
        with self._lock:
            try:
                data = {
                    'name': portfolio.name,
                    'positions': [],
                    'saved_at': datetime.now().isoformat()
                }

                for pos in portfolio.positions:
                    pos_data = {
                        'symbol': pos.symbol,
                        'name': pos.name,
                        'quantity': pos.quantity,
                        'avg_cost': pos.avg_cost,
                        'current_price': pos.current_price,
                        'asset_type': pos.asset_type.value if pos.asset_type else 'STOCK',
                        'thesis_type': pos.thesis_type.value if pos.thesis_type else None,
                        'thesis_description': pos.thesis_description,
                        'target_price': pos.target_price,
                        'stop_loss': pos.stop_loss,
                        'time_horizon': pos.time_horizon,
                        'weight': pos.weight,
                        'purchase_date': pos.purchase_date.isoformat() if pos.purchase_date else None,
                    }
                    data['positions'].append(pos_data)

                with open(self.portfolio_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                return True
            except Exception as e:
                logger.error(f"포트폴리오 저장 실패: {e}")
                return False

    def load_portfolio(self) -> Optional[Portfolio]:
        """포트폴리오 로드 (스레드 안전)"""
        with self._lock:
            try:
                if not self.portfolio_file.exists():
                    return None

                with open(self.portfolio_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                from .portfolio import InvestmentThesis

                portfolio = Portfolio(name=data.get('name', 'My Portfolio'))

                for pos_data in data.get('positions', []):
                    # AssetType 변환
                    asset_type = AssetType.STOCK
                    if pos_data.get('asset_type'):
                        try:
                            asset_type = AssetType(pos_data['asset_type'])
                        except (ValueError, KeyError):
                            pass

                    # InvestmentThesis 변환
                    thesis_type = None
                    if pos_data.get('thesis_type'):
                        try:
                            thesis_type = next(
                                (t for t in InvestmentThesis if t.value == pos_data['thesis_type']),
                                None
                            )
                        except (ValueError, StopIteration):
                            pass

                    # 날짜 변환
                    purchase_date = None
                    if pos_data.get('purchase_date'):
                        try:
                            purchase_date = datetime.fromisoformat(pos_data['purchase_date'])
                        except (ValueError, TypeError):
                            pass

                    position = Position(
                        symbol=pos_data['symbol'],
                        name=pos_data.get('name', pos_data['symbol']),
                        quantity=pos_data['quantity'],
                        avg_cost=pos_data['avg_cost'],
                        current_price=pos_data.get('current_price', pos_data['avg_cost']),
                        asset_type=asset_type,
                        thesis_type=thesis_type,
                        thesis_description=pos_data.get('thesis_description', ''),
                        target_price=pos_data.get('target_price'),
                        stop_loss=pos_data.get('stop_loss'),
                        time_horizon=pos_data.get('time_horizon'),
                        weight=pos_data.get('weight'),
                        purchase_date=purchase_date,
                    )
                    portfolio.add_position(position)

                return portfolio
            except Exception as e:
                logger.error(f"포트폴리오 로드 실패: {e}")
                return None

    # ===== 보고서 저장/로드 =====

    def save_reports(self, reports: Dict[str, ThesisReportHistory]) -> bool:
        """보고서 히스토리 저장 (스레드 안전)"""
        with self._lock:
            try:
                data = {}
                for symbol, history in reports.items():
                    data[symbol] = {
                        'symbol': history.symbol,
                        'reports': [r.to_dict() for r in history.reports]
                    }

                with open(self.reports_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                return True
            except Exception as e:
                logger.error(f"보고서 저장 실패: {e}")
                return False

    def load_reports(self) -> Dict[str, ThesisReportHistory]:
        """보고서 히스토리 로드 (스레드 안전)"""
        with self._lock:
            try:
                if not self.reports_file.exists():
                    return {}

                with open(self.reports_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                reports = {}
                for symbol, history_data in data.items():
                    history = ThesisReportHistory(symbol=symbol)
                    for report_dict in history_data.get('reports', []):
                        report = ThesisReport.from_dict(report_dict)
                        history.reports.append(report)
                    reports[symbol] = history

                return reports
            except Exception as e:
                logger.error(f"보고서 로드 실패: {e}")
                return {}

    # ===== 설정 저장/로드 =====

    def save_settings(self, settings: Dict) -> bool:
        """사용자 설정 저장 (스레드 안전)"""
        with self._lock:
            try:
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, ensure_ascii=False, indent=2)
                return True
            except Exception as e:
                logger.error(f"설정 저장 실패: {e}")
                return False

    def load_settings(self) -> Dict:
        """사용자 설정 로드 (스레드 안전)"""
        with self._lock:
            try:
                if not self.settings_file.exists():
                    return {}

                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"설정 로드 실패: {e}")
                return {}

    # ===== 알림 저장/로드 =====

    def save_alerts(self, alerts: List[Dict]) -> bool:
        """알림 히스토리 저장 (스레드 안전)"""
        with self._lock:
            try:
                with open(self.alerts_file, 'w', encoding='utf-8') as f:
                    json.dump(alerts, f, ensure_ascii=False, indent=2)
                return True
            except Exception as e:
                logger.error(f"알림 저장 실패: {e}")
                return False

    def load_alerts(self) -> List[Dict]:
        """알림 히스토리 로드 (스레드 안전)"""
        with self._lock:
            try:
                if not self.alerts_file.exists():
                    return []

                with open(self.alerts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"알림 로드 실패: {e}")
                return []

    # ===== 유틸리티 =====

    def _validate_path(self, file_path: str) -> bool:
        """파일 경로 유효성 검증 (경로 탐색 공격 방지)"""
        try:
            # 절대 경로로 변환
            abs_path = Path(file_path).resolve()

            # .. 이나 특수 문자 포함 여부 확인
            if '..' in str(file_path):
                logger.warning(f"경로 탐색 시도 감지: {file_path}")
                return False

            # 허용된 확장자 확인
            allowed_extensions = {'.json', '.csv', '.xlsx'}
            if abs_path.suffix.lower() not in allowed_extensions:
                logger.warning(f"허용되지 않은 파일 확장자: {abs_path.suffix}")
                return False

            return True
        except Exception as e:
            logger.error(f"경로 검증 실패: {e}")
            return False

    def export_all(self, export_path: str) -> bool:
        """모든 데이터 내보내기 (스레드 안전)"""
        # 경로 유효성 검증
        if not self._validate_path(export_path):
            logger.error(f"유효하지 않은 내보내기 경로: {export_path}")
            return False

        with self._lock:
            try:
                export_data = {
                    'exported_at': datetime.now().isoformat(),
                    'portfolio': None,
                    'reports': None,
                    'settings': None,
                }

                if self.portfolio_file.exists():
                    with open(self.portfolio_file, 'r', encoding='utf-8') as f:
                        export_data['portfolio'] = json.load(f)

                if self.reports_file.exists():
                    with open(self.reports_file, 'r', encoding='utf-8') as f:
                        export_data['reports'] = json.load(f)

                if self.settings_file.exists():
                    with open(self.settings_file, 'r', encoding='utf-8') as f:
                        export_data['settings'] = json.load(f)

                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)

                return True
            except Exception as e:
                logger.error(f"내보내기 실패: {e}")
                return False

    def import_all(self, import_path: str) -> bool:
        """모든 데이터 가져오기 (스레드 안전)"""
        # 경로 유효성 검증
        if not self._validate_path(import_path):
            logger.error(f"유효하지 않은 가져오기 경로: {import_path}")
            return False

        with self._lock:
            try:
                with open(import_path, 'r', encoding='utf-8') as f:
                    import_data = json.load(f)

                if import_data.get('portfolio'):
                    with open(self.portfolio_file, 'w', encoding='utf-8') as f:
                        json.dump(import_data['portfolio'], f, ensure_ascii=False, indent=2)

                if import_data.get('reports'):
                    with open(self.reports_file, 'w', encoding='utf-8') as f:
                        json.dump(import_data['reports'], f, ensure_ascii=False, indent=2)

                if import_data.get('settings'):
                    with open(self.settings_file, 'w', encoding='utf-8') as f:
                        json.dump(import_data['settings'], f, ensure_ascii=False, indent=2)

                return True
            except Exception as e:
                logger.error(f"가져오기 실패: {e}")
                return False

    def clear_all(self) -> bool:
        """모든 데이터 삭제 (스레드 안전)"""
        with self._lock:
            try:
                for file in [self.portfolio_file, self.reports_file, self.settings_file, self.alerts_file]:
                    if file.exists():
                        file.unlink()
                return True
            except Exception as e:
                logger.error(f"삭제 실패: {e}")
                return False


# 전역 인스턴스
data_store = DataStore()
