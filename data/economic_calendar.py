"""
경제 캘린더
주요 경제 지표 발표 일정 및 실적 발표 캘린더
"""

import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from bs4 import BeautifulSoup
import json
from pathlib import Path


@dataclass
class EconomicEvent:
    """경제 이벤트"""
    date: str
    time: str
    country: str  # US, KR, etc.
    event: str
    importance: str  # high, medium, low
    previous: Optional[str] = None
    forecast: Optional[str] = None
    actual: Optional[str] = None

    @property
    def is_high_importance(self) -> bool:
        return self.importance == "high"

    @property
    def datetime_str(self) -> str:
        return f"{self.date} {self.time}"


@dataclass
class EarningsEvent:
    """실적 발표 이벤트"""
    date: str
    symbol: str
    name: str
    market: str  # US, KR
    eps_estimate: Optional[float] = None
    eps_actual: Optional[float] = None
    revenue_estimate: Optional[float] = None
    revenue_actual: Optional[float] = None
    time: str = "BMO"  # BMO (Before Market Open), AMC (After Market Close)


class EconomicCalendar:
    """경제 캘린더"""

    # 주요 경제 지표 (고정 일정)
    RECURRING_EVENTS = {
        "US": [
            {"event": "FOMC 금리 결정", "frequency": "6주", "importance": "high"},
            {"event": "비농업 고용지표", "frequency": "월초 금요일", "importance": "high"},
            {"event": "CPI (소비자물가)", "frequency": "매월 중순", "importance": "high"},
            {"event": "PPI (생산자물가)", "frequency": "매월 중순", "importance": "medium"},
            {"event": "소매판매", "frequency": "매월", "importance": "medium"},
            {"event": "GDP 성장률", "frequency": "분기", "importance": "high"},
            {"event": "ISM 제조업", "frequency": "매월 초", "importance": "medium"},
            {"event": "ISM 서비스업", "frequency": "매월 초", "importance": "medium"},
            {"event": "신규 실업수당 청구", "frequency": "매주 목요일", "importance": "low"},
        ],
        "KR": [
            {"event": "한국은행 금통위", "frequency": "월 1회", "importance": "high"},
            {"event": "수출입 동향", "frequency": "매월 초", "importance": "medium"},
            {"event": "CPI (소비자물가)", "frequency": "매월 초", "importance": "medium"},
            {"event": "GDP 성장률", "frequency": "분기", "importance": "high"},
            {"event": "기업경기실사지수(BSI)", "frequency": "매월", "importance": "low"},
            {"event": "산업생산지수", "frequency": "매월", "importance": "medium"},
        ]
    }

    # 2024-2025 FOMC 일정 (예시)
    FOMC_DATES = [
        "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12",
        "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
        "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18",
        "2025-07-30", "2025-09-17", "2025-11-05", "2025-12-17"
    ]

    def __init__(self):
        self.cache_dir = Path.home() / ".notion_portfolio" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.events: List[EconomicEvent] = []
        self.earnings: List[EarningsEvent] = []

    def get_upcoming_events(self, days: int = 30,
                            country: str = None,
                            importance: str = None) -> List[EconomicEvent]:
        """예정된 경제 이벤트 조회"""
        # 캐시 로드 또는 새로 가져오기
        self._load_or_fetch_events()

        today = datetime.now().date()
        end_date = today + timedelta(days=days)

        filtered = []
        for event in self.events:
            try:
                event_date = datetime.strptime(event.date, "%Y-%m-%d").date()
                if today <= event_date <= end_date:
                    if country and event.country != country:
                        continue
                    if importance and event.importance != importance:
                        continue
                    filtered.append(event)
            except ValueError:
                continue

        return sorted(filtered, key=lambda x: x.date)

    def get_fomc_schedule(self) -> List[EconomicEvent]:
        """FOMC 일정 조회"""
        events = []
        today = datetime.now().date()

        for date_str in self.FOMC_DATES:
            fomc_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if fomc_date >= today:
                events.append(EconomicEvent(
                    date=date_str,
                    time="19:00",  # 한국 시간
                    country="US",
                    event="FOMC 금리 결정",
                    importance="high"
                ))

        return events[:8]  # 다음 8개

    def get_this_week_events(self) -> List[EconomicEvent]:
        """이번 주 이벤트"""
        today = datetime.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        self._load_or_fetch_events()

        weekly = []
        for event in self.events:
            try:
                event_date = datetime.strptime(event.date, "%Y-%m-%d").date()
                if start_of_week <= event_date <= end_of_week:
                    weekly.append(event)
            except ValueError:
                continue

        return sorted(weekly, key=lambda x: (x.date, x.time))

    def _load_or_fetch_events(self):
        """이벤트 로드 또는 가져오기"""
        cache_file = self.cache_dir / "economic_calendar.json"

        # 캐시 확인
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                    cache_date = datetime.fromisoformat(cache.get('date', '2000-01-01'))

                    # 24시간 이내 캐시 사용
                    if datetime.now() - cache_date < timedelta(hours=24):
                        self.events = [EconomicEvent(**e) for e in cache.get('events', [])]
                        return
            except Exception:
                pass

        # 새로 가져오기
        self._fetch_events()

        # 캐시 저장
        try:
            cache = {
                'date': datetime.now().isoformat(),
                'events': [
                    {
                        'date': e.date,
                        'time': e.time,
                        'country': e.country,
                        'event': e.event,
                        'importance': e.importance,
                        'previous': e.previous,
                        'forecast': e.forecast,
                        'actual': e.actual
                    }
                    for e in self.events
                ]
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _fetch_events(self):
        """경제 이벤트 가져오기"""
        self.events = []

        # FOMC 일정 추가
        for fomc in self.get_fomc_schedule():
            self.events.append(fomc)

        # 기본 이벤트 생성 (실제로는 API나 웹 스크래핑으로 가져옴)
        today = datetime.now()

        # 이번 달 CPI 추정일 (보통 10~15일)
        cpi_date = today.replace(day=12)
        if cpi_date.date() >= today.date():
            self.events.append(EconomicEvent(
                date=cpi_date.strftime("%Y-%m-%d"),
                time="21:30",
                country="US",
                event="CPI (소비자물가지수)",
                importance="high"
            ))

        # 다음 달 고용지표 (첫째 주 금요일)
        next_month = today.replace(day=1) + timedelta(days=32)
        next_month = next_month.replace(day=1)
        first_friday = next_month + timedelta(days=(4 - next_month.weekday() + 7) % 7)

        self.events.append(EconomicEvent(
            date=first_friday.strftime("%Y-%m-%d"),
            time="21:30",
            country="US",
            event="비농업 고용지표 (NFP)",
            importance="high"
        ))

        # 한국 금통위 (보통 매월 넷째 주 목요일)
        kr_date = today.replace(day=22)
        while kr_date.weekday() != 3:  # 목요일
            kr_date += timedelta(days=1)

        if kr_date.date() >= today.date():
            self.events.append(EconomicEvent(
                date=kr_date.strftime("%Y-%m-%d"),
                time="10:00",
                country="KR",
                event="한국은행 금융통화위원회",
                importance="high"
            ))

        # 주간 실업수당 (매주 목요일)
        this_thursday = today + timedelta(days=(3 - today.weekday() + 7) % 7)
        for i in range(4):
            thursday = this_thursday + timedelta(weeks=i)
            self.events.append(EconomicEvent(
                date=thursday.strftime("%Y-%m-%d"),
                time="21:30",
                country="US",
                event="주간 신규실업수당 청구",
                importance="low"
            ))

    def get_earnings_calendar(self, days: int = 14,
                               symbol: str = None) -> List[EarningsEvent]:
        """실적 발표 캘린더"""
        # 실제로는 API로 가져옴 (예: finnhub, yahoo finance)
        # 여기서는 예시 데이터
        earnings = [
            EarningsEvent(
                date=(datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
                symbol="AAPL",
                name="Apple Inc.",
                market="US",
                time="AMC"
            ),
            EarningsEvent(
                date=(datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d"),
                symbol="MSFT",
                name="Microsoft Corporation",
                market="US",
                time="AMC"
            ),
            EarningsEvent(
                date=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
                symbol="005930.KS",
                name="삼성전자",
                market="KR",
                time="BMO"
            ),
        ]

        if symbol:
            earnings = [e for e in earnings if e.symbol == symbol]

        return earnings

    def get_calendar_summary(self) -> Dict[str, Any]:
        """캘린더 요약"""
        this_week = self.get_this_week_events()
        upcoming_fomc = self.get_fomc_schedule()[:3]

        high_importance = [e for e in this_week if e.is_high_importance]

        return {
            "this_week_count": len(this_week),
            "high_importance_count": len(high_importance),
            "this_week_events": this_week,
            "upcoming_fomc": upcoming_fomc,
            "next_fomc": upcoming_fomc[0] if upcoming_fomc else None
        }

    def get_market_hours(self, market: str = "US") -> Dict[str, str]:
        """시장 운영 시간"""
        hours = {
            "US": {
                "pre_market": "16:00 - 22:30 (KST)",
                "regular": "22:30 - 05:00 (KST)",
                "after_hours": "05:00 - 09:00 (KST)"
            },
            "KR": {
                "regular": "09:00 - 15:30 (KST)",
                "after_hours": "15:40 - 18:00 (KST)"
            }
        }
        return hours.get(market, hours["US"])


# 싱글톤 인스턴스
economic_calendar = EconomicCalendar()


def get_this_week_events() -> List[EconomicEvent]:
    """이번 주 경제 이벤트"""
    return economic_calendar.get_this_week_events()


def get_upcoming_events(days: int = 30) -> List[EconomicEvent]:
    """예정된 경제 이벤트"""
    return economic_calendar.get_upcoming_events(days)


def get_next_fomc() -> Optional[EconomicEvent]:
    """다음 FOMC"""
    schedule = economic_calendar.get_fomc_schedule()
    return schedule[0] if schedule else None
