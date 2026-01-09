"""
투자 일지/노트
매매 사유 기록 및 복기
"""

import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import uuid


class EmotionTag(Enum):
    """감정 태그"""
    CONFIDENT = "confident"  # 확신
    FOMO = "fomo"  # 놓칠까 두려움
    FEAR = "fear"  # 공포
    GREED = "greed"  # 탐욕
    PATIENT = "patient"  # 인내
    IMPULSIVE = "impulsive"  # 충동적
    CALM = "calm"  # 침착
    ANXIOUS = "anxious"  # 불안


class TradeType(Enum):
    """거래 유형"""
    BUY = "buy"
    SELL = "sell"
    ADD = "add"  # 추가 매수
    REDUCE = "reduce"  # 일부 매도


class JournalCategory(Enum):
    """일지 카테고리"""
    TRADE = "trade"  # 매매 일지
    ANALYSIS = "analysis"  # 분석 노트
    STRATEGY = "strategy"  # 전략 메모
    REVIEW = "review"  # 복기
    LEARNING = "learning"  # 학습 내용
    IDEA = "idea"  # 아이디어


@dataclass
class TradeJournalEntry:
    """매매 일지 항목"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    time: str = field(default_factory=lambda: datetime.now().strftime("%H:%M"))
    symbol: str = ""
    name: str = ""
    trade_type: str = TradeType.BUY.value
    quantity: int = 0
    price: float = 0.0

    # 매매 이유
    reason: str = ""
    thesis: str = ""  # 투자 논거

    # 감정 상태
    emotion: str = EmotionTag.CALM.value
    confidence_level: int = 5  # 1-10

    # 목표/계획
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    holding_period: str = ""  # 예상 보유 기간

    # 시장 상황
    market_condition: str = ""  # 시장 상황 메모

    # 결과 (나중에 기록)
    actual_result: Optional[float] = None
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    lessons_learned: str = ""

    # 태그
    tags: List[str] = field(default_factory=list)


@dataclass
class GeneralNote:
    """일반 노트"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    time: str = field(default_factory=lambda: datetime.now().strftime("%H:%M"))
    category: str = JournalCategory.ANALYSIS.value
    title: str = ""
    content: str = ""
    symbols: List[str] = field(default_factory=list)  # 관련 종목
    tags: List[str] = field(default_factory=list)
    importance: int = 3  # 1-5


@dataclass
class ReviewEntry:
    """복기 항목"""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    date: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))
    period: str = ""  # 복기 기간 (예: 2024-01)

    # 실적
    total_trades: int = 0
    winning_trades: int = 0
    total_return: float = 0.0

    # 분석
    best_trade: str = ""
    worst_trade: str = ""
    patterns_noticed: str = ""  # 발견한 패턴
    mistakes: str = ""  # 실수
    improvements: str = ""  # 개선점

    # 감정 분석
    emotional_triggers: str = ""  # 감정적 트리거
    discipline_score: int = 5  # 1-10, 원칙 준수도


class InvestmentJournal:
    """투자 일지 관리자"""

    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir or Path.home() / ".notion_portfolio" / "journal")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.trades_file = self.data_dir / "trades.json"
        self.notes_file = self.data_dir / "notes.json"
        self.reviews_file = self.data_dir / "reviews.json"

        self.trades: List[TradeJournalEntry] = []
        self.notes: List[GeneralNote] = []
        self.reviews: List[ReviewEntry] = []

        self._load()

    def _load(self):
        """데이터 로드"""
        # 매매 일지
        if self.trades_file.exists():
            try:
                with open(self.trades_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.trades = [TradeJournalEntry(**t) for t in data]
            except Exception:
                self.trades = []

        # 노트
        if self.notes_file.exists():
            try:
                with open(self.notes_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.notes = [GeneralNote(**n) for n in data]
            except Exception:
                self.notes = []

        # 복기
        if self.reviews_file.exists():
            try:
                with open(self.reviews_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.reviews = [ReviewEntry(**r) for r in data]
            except Exception:
                self.reviews = []

    def _save(self):
        """데이터 저장"""
        try:
            with open(self.trades_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(t) for t in self.trades], f, ensure_ascii=False, indent=2)

            with open(self.notes_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(n) for n in self.notes], f, ensure_ascii=False, indent=2)

            with open(self.reviews_file, 'w', encoding='utf-8') as f:
                json.dump([asdict(r) for r in self.reviews], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"저장 실패: {e}")

    def add_trade(self, **kwargs) -> TradeJournalEntry:
        """매매 일지 추가"""
        entry = TradeJournalEntry(**kwargs)
        self.trades.insert(0, entry)  # 최신순
        self._save()
        return entry

    def update_trade_result(self, trade_id: str, exit_price: float,
                            exit_date: str = None, lessons: str = "") -> bool:
        """매매 결과 업데이트"""
        for trade in self.trades:
            if trade.id == trade_id:
                trade.exit_price = exit_price
                trade.exit_date = exit_date or datetime.now().strftime("%Y-%m-%d")
                trade.lessons_learned = lessons

                # 수익률 계산
                if trade.trade_type in [TradeType.BUY.value, TradeType.ADD.value]:
                    trade.actual_result = ((exit_price - trade.price) / trade.price) * 100
                else:
                    trade.actual_result = ((trade.price - exit_price) / exit_price) * 100

                self._save()
                return True
        return False

    def add_note(self, **kwargs) -> GeneralNote:
        """노트 추가"""
        note = GeneralNote(**kwargs)
        self.notes.insert(0, note)
        self._save()
        return note

    def add_review(self, **kwargs) -> ReviewEntry:
        """복기 추가"""
        review = ReviewEntry(**kwargs)
        self.reviews.insert(0, review)
        self._save()
        return review

    def get_trades(self, symbol: str = None, start_date: str = None,
                   end_date: str = None, limit: int = None) -> List[TradeJournalEntry]:
        """매매 일지 조회"""
        filtered = self.trades

        if symbol:
            filtered = [t for t in filtered if t.symbol == symbol]

        if start_date:
            filtered = [t for t in filtered if t.date >= start_date]

        if end_date:
            filtered = [t for t in filtered if t.date <= end_date]

        if limit:
            filtered = filtered[:limit]

        return filtered

    def get_notes(self, category: str = None, tag: str = None,
                  limit: int = None) -> List[GeneralNote]:
        """노트 조회"""
        filtered = self.notes

        if category:
            filtered = [n for n in filtered if n.category == category]

        if tag:
            filtered = [n for n in filtered if tag in n.tags]

        if limit:
            filtered = filtered[:limit]

        return filtered

    def delete_trade(self, trade_id: str) -> bool:
        """매매 일지 삭제"""
        original_len = len(self.trades)
        self.trades = [t for t in self.trades if t.id != trade_id]
        if len(self.trades) < original_len:
            self._save()
            return True
        return False

    def delete_note(self, note_id: str) -> bool:
        """노트 삭제"""
        original_len = len(self.notes)
        self.notes = [n for n in self.notes if n.id != note_id]
        if len(self.notes) < original_len:
            self._save()
            return True
        return False

    def get_emotion_analysis(self, months: int = 3) -> Dict[str, Any]:
        """감정 분석"""
        cutoff = datetime.now() - timedelta(days=months * 30)
        cutoff_str = cutoff.strftime("%Y-%m-%d")

        recent_trades = [t for t in self.trades if t.date >= cutoff_str]

        if not recent_trades:
            return {}

        # 감정별 분포
        emotion_counts = {}
        for trade in recent_trades:
            emotion = trade.emotion
            if emotion not in emotion_counts:
                emotion_counts[emotion] = {'count': 0, 'profitable': 0}
            emotion_counts[emotion]['count'] += 1
            if trade.actual_result and trade.actual_result > 0:
                emotion_counts[emotion]['profitable'] += 1

        # 감정별 승률
        emotion_win_rates = {}
        for emotion, data in emotion_counts.items():
            if data['count'] > 0:
                emotion_win_rates[emotion] = data['profitable'] / data['count'] * 100

        # 평균 확신도와 수익률 상관
        confidence_results = [(t.confidence_level, t.actual_result or 0)
                              for t in recent_trades if t.actual_result is not None]

        return {
            'total_trades': len(recent_trades),
            'emotion_distribution': emotion_counts,
            'emotion_win_rates': emotion_win_rates,
            'avg_confidence': sum(t.confidence_level for t in recent_trades) / len(recent_trades),
            'confidence_results': confidence_results
        }

    def get_performance_by_tag(self) -> Dict[str, Dict]:
        """태그별 성과"""
        tag_performance = {}

        for trade in self.trades:
            if trade.actual_result is None:
                continue

            for tag in trade.tags:
                if tag not in tag_performance:
                    tag_performance[tag] = {'trades': 0, 'total_return': 0, 'wins': 0}

                tag_performance[tag]['trades'] += 1
                tag_performance[tag]['total_return'] += trade.actual_result
                if trade.actual_result > 0:
                    tag_performance[tag]['wins'] += 1

        # 평균 수익률 및 승률 계산
        for tag, data in tag_performance.items():
            if data['trades'] > 0:
                data['avg_return'] = data['total_return'] / data['trades']
                data['win_rate'] = data['wins'] / data['trades'] * 100

        return tag_performance

    def search(self, query: str) -> Dict[str, List]:
        """검색"""
        query_lower = query.lower()

        matching_trades = [
            t for t in self.trades
            if query_lower in t.reason.lower() or
               query_lower in t.thesis.lower() or
               query_lower in t.symbol.lower() or
               query_lower in t.name.lower()
        ]

        matching_notes = [
            n for n in self.notes
            if query_lower in n.title.lower() or
               query_lower in n.content.lower()
        ]

        return {
            'trades': matching_trades,
            'notes': matching_notes
        }

    def export_to_markdown(self, filepath: str = None) -> str:
        """마크다운 내보내기"""
        filepath = filepath or str(self.data_dir / "journal_export.md")

        lines = ["# 투자 일지\n"]

        # 매매 일지
        lines.append("## 매매 기록\n")
        for trade in self.trades[:50]:  # 최근 50개
            lines.append(f"### {trade.date} - {trade.name} ({trade.symbol})")
            lines.append(f"- **유형**: {trade.trade_type}")
            lines.append(f"- **수량/가격**: {trade.quantity}주 @ ₩{trade.price:,.0f}")
            lines.append(f"- **이유**: {trade.reason}")
            if trade.actual_result is not None:
                lines.append(f"- **결과**: {trade.actual_result:+.2f}%")
            if trade.lessons_learned:
                lines.append(f"- **교훈**: {trade.lessons_learned}")
            lines.append("")

        # 노트
        lines.append("\n## 노트\n")
        for note in self.notes[:30]:
            lines.append(f"### {note.date} - {note.title}")
            lines.append(f"*카테고리: {note.category}*\n")
            lines.append(note.content)
            lines.append("")

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return filepath


# 싱글톤 인스턴스
investment_journal = InvestmentJournal()


def add_trade_entry(**kwargs) -> TradeJournalEntry:
    """매매 일지 추가"""
    return investment_journal.add_trade(**kwargs)


def add_note(**kwargs) -> GeneralNote:
    """노트 추가"""
    return investment_journal.add_note(**kwargs)


def get_recent_trades(limit: int = 20) -> List[TradeJournalEntry]:
    """최근 매매 조회"""
    return investment_journal.get_trades(limit=limit)
