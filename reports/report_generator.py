"""
성과 리포트 생성기
PDF/HTML 리포트 자동 생성
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image, PageBreak, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics.charts.lineplots import LinePlot
    from reportlab.graphics.charts.piecharts import Pie
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


@dataclass
class ReportConfig:
    """리포트 설정"""
    report_type: str = "daily"  # daily, weekly, monthly
    include_charts: bool = True
    include_transactions: bool = True
    include_analysis: bool = True
    page_size: str = "A4"
    language: str = "ko"


@dataclass
class PortfolioSnapshot:
    """포트폴리오 스냅샷"""
    date: str
    total_value: float
    total_cost: float
    total_return: float
    return_pct: float
    positions: List[Dict]
    allocation: Dict[str, float]


@dataclass
class ReportData:
    """리포트 데이터"""
    period_start: str
    period_end: str
    current_snapshot: PortfolioSnapshot
    previous_snapshot: Optional[PortfolioSnapshot]
    transactions: List[Dict]
    performance_history: List[Dict]
    market_summary: Dict
    analysis: Dict


class ReportGenerator:
    """리포트 생성기"""

    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir or Path.home() / ".notion_portfolio" / "reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 스타일 초기화
        if REPORTLAB_AVAILABLE:
            self.styles = getSampleStyleSheet()
            self._setup_korean_font()
            self._setup_custom_styles()

    def _setup_korean_font(self):
        """한글 폰트 설정"""
        # 시스템 폰트 경로들
        font_paths = [
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
            "/usr/share/fonts/nanum/NanumGothic.ttf",
            "C:/Windows/Fonts/malgun.ttf",
            "/System/Library/Fonts/AppleGothic.ttf"
        ]

        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('Korean', font_path))
                    self.korean_font = 'Korean'
                    return
                except Exception:
                    pass

        self.korean_font = 'Helvetica'

    def _setup_custom_styles(self):
        """커스텀 스타일 설정"""
        self.styles.add(ParagraphStyle(
            name='KoreanTitle',
            fontName=self.korean_font,
            fontSize=24,
            leading=30,
            alignment=TA_CENTER,
            spaceAfter=20
        ))

        self.styles.add(ParagraphStyle(
            name='KoreanHeading',
            fontName=self.korean_font,
            fontSize=14,
            leading=18,
            spaceBefore=15,
            spaceAfter=10,
            textColor=colors.HexColor('#1f77b4')
        ))

        self.styles.add(ParagraphStyle(
            name='KoreanBody',
            fontName=self.korean_font,
            fontSize=10,
            leading=14
        ))

        self.styles.add(ParagraphStyle(
            name='KoreanSmall',
            fontName=self.korean_font,
            fontSize=8,
            leading=10,
            textColor=colors.grey
        ))

    def generate_pdf(self, data: ReportData, config: ReportConfig = None) -> str:
        """PDF 리포트 생성"""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab 패키지가 필요합니다: pip install reportlab")

        config = config or ReportConfig()

        # 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"portfolio_report_{config.report_type}_{timestamp}.pdf"
        filepath = self.output_dir / filename

        # PDF 생성
        page_size = A4 if config.page_size == "A4" else letter
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=page_size,
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1.5*cm,
            bottomMargin=1.5*cm
        )

        # 컨텐츠 생성
        story = []

        # 타이틀
        story.append(Paragraph("포트폴리오 성과 리포트", self.styles['KoreanTitle']))
        story.append(Paragraph(
            f"기간: {data.period_start} ~ {data.period_end}",
            self.styles['KoreanSmall']
        ))
        story.append(Spacer(1, 20))

        # 요약 섹션
        story.extend(self._create_summary_section(data))

        # 포지션 섹션
        story.extend(self._create_positions_section(data))

        # 성과 분석
        if config.include_analysis:
            story.extend(self._create_analysis_section(data))

        # 거래 내역
        if config.include_transactions and data.transactions:
            story.append(PageBreak())
            story.extend(self._create_transactions_section(data))

        # 시장 요약
        story.extend(self._create_market_section(data))

        # 푸터
        story.append(Spacer(1, 30))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
        story.append(Paragraph(
            f"생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | NOTION 포트폴리오 관리 시스템",
            self.styles['KoreanSmall']
        ))

        # PDF 빌드
        doc.build(story)

        return str(filepath)

    def _create_summary_section(self, data: ReportData) -> List:
        """요약 섹션 생성"""
        elements = []
        snapshot = data.current_snapshot

        elements.append(Paragraph("포트폴리오 요약", self.styles['KoreanHeading']))

        # 요약 테이블
        summary_data = [
            ["항목", "값"],
            ["총 자산", f"₩{snapshot.total_value:,.0f}"],
            ["총 투자금", f"₩{snapshot.total_cost:,.0f}"],
            ["총 수익", f"₩{snapshot.total_return:,.0f}"],
            ["수익률", f"{snapshot.return_pct:+.2f}%"],
        ]

        # 전일 대비 변화
        if data.previous_snapshot:
            change = snapshot.total_value - data.previous_snapshot.total_value
            change_pct = (change / data.previous_snapshot.total_value) * 100
            summary_data.append(["전일 대비", f"₩{change:+,.0f} ({change_pct:+.2f}%)"])

        table = Table(summary_data, colWidths=[3*cm, 5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), self.korean_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#dee2e6'))
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))

        return elements

    def _create_positions_section(self, data: ReportData) -> List:
        """포지션 섹션 생성"""
        elements = []

        elements.append(Paragraph("보유 종목", self.styles['KoreanHeading']))

        if not data.current_snapshot.positions:
            elements.append(Paragraph("보유 종목이 없습니다.", self.styles['KoreanBody']))
            return elements

        # 포지션 테이블
        headers = ["종목", "수량", "평균단가", "현재가", "평가금액", "손익", "수익률"]
        table_data = [headers]

        for pos in data.current_snapshot.positions[:15]:  # 최대 15개
            row = [
                pos.get('name', pos.get('symbol', '')),
                f"{pos.get('quantity', 0):,}",
                f"₩{pos.get('avg_price', 0):,.0f}",
                f"₩{pos.get('current_price', 0):,.0f}",
                f"₩{pos.get('market_value', 0):,.0f}",
                f"₩{pos.get('unrealized_pnl', 0):+,.0f}",
                f"{pos.get('return_pct', 0):+.2f}%"
            ]
            table_data.append(row)

        col_widths = [3*cm, 1.5*cm, 2*cm, 2*cm, 2.5*cm, 2*cm, 1.5*cm]
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), self.korean_font),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6'))
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))

        return elements

    def _create_analysis_section(self, data: ReportData) -> List:
        """분석 섹션 생성"""
        elements = []

        elements.append(Paragraph("성과 분석", self.styles['KoreanHeading']))

        analysis = data.analysis

        # 성과 지표
        metrics = [
            ["지표", "값", "설명"],
            ["샤프 비율", f"{analysis.get('sharpe_ratio', 0):.2f}", "위험 대비 수익"],
            ["최대 낙폭", f"{analysis.get('max_drawdown', 0):.2f}%", "최고점 대비 최대 하락"],
            ["변동성", f"{analysis.get('volatility', 0):.2f}%", "일간 수익률 표준편차"],
            ["베타", f"{analysis.get('beta', 0):.2f}", "시장 대비 민감도"],
            ["승률", f"{analysis.get('win_rate', 0):.1f}%", "수익 거래 비율"]
        ]

        table = Table(metrics, colWidths=[3*cm, 2.5*cm, 6*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#28a745')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), self.korean_font),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6'))
        ]))

        elements.append(table)
        elements.append(Spacer(1, 15))

        # AI 분석 코멘트
        if analysis.get('ai_comment'):
            elements.append(Paragraph("AI 분석:", self.styles['KoreanBody']))
            elements.append(Paragraph(analysis['ai_comment'], self.styles['KoreanBody']))

        elements.append(Spacer(1, 20))

        return elements

    def _create_transactions_section(self, data: ReportData) -> List:
        """거래 내역 섹션 생성"""
        elements = []

        elements.append(Paragraph("거래 내역", self.styles['KoreanHeading']))

        # 거래 테이블
        headers = ["일시", "종목", "유형", "수량", "단가", "금액"]
        table_data = [headers]

        for tx in data.transactions[:20]:  # 최대 20개
            row = [
                tx.get('date', ''),
                tx.get('name', tx.get('symbol', '')),
                tx.get('type', ''),
                f"{tx.get('quantity', 0):,}",
                f"₩{tx.get('price', 0):,.0f}",
                f"₩{tx.get('amount', 0):,.0f}"
            ]
            table_data.append(row)

        table = Table(table_data, colWidths=[2.5*cm, 3*cm, 1.5*cm, 1.5*cm, 2.5*cm, 2.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6c757d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), self.korean_font),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6'))
        ]))

        elements.append(table)
        elements.append(Spacer(1, 20))

        return elements

    def _create_market_section(self, data: ReportData) -> List:
        """시장 요약 섹션 생성"""
        elements = []

        elements.append(Paragraph("시장 요약", self.styles['KoreanHeading']))

        market = data.market_summary

        # 시장 지수
        indices = [
            ["지수", "현재", "변동"],
            ["KOSPI", f"{market.get('kospi', 0):,.2f}", f"{market.get('kospi_change', 0):+.2f}%"],
            ["KOSDAQ", f"{market.get('kosdaq', 0):,.2f}", f"{market.get('kosdaq_change', 0):+.2f}%"],
            ["S&P 500", f"{market.get('sp500', 0):,.2f}", f"{market.get('sp500_change', 0):+.2f}%"],
            ["NASDAQ", f"{market.get('nasdaq', 0):,.2f}", f"{market.get('nasdaq_change', 0):+.2f}%"],
        ]

        table = Table(indices, colWidths=[3*cm, 3*cm, 2.5*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#17a2b8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), self.korean_font),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6'))
        ]))

        elements.append(table)

        return elements

    def generate_html(self, data: ReportData, config: ReportConfig = None) -> str:
        """HTML 리포트 생성"""
        config = config or ReportConfig()

        # 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"portfolio_report_{config.report_type}_{timestamp}.html"
        filepath = self.output_dir / filename

        snapshot = data.current_snapshot

        html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>포트폴리오 성과 리포트</title>
    <style>
        body {{ font-family: 'Nanum Gothic', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #1f77b4; text-align: center; }}
        h2 {{ color: #333; border-bottom: 2px solid #1f77b4; padding-bottom: 10px; }}
        .period {{ text-align: center; color: #666; margin-bottom: 30px; }}
        .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .summary-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; text-align: center; }}
        .summary-card .value {{ font-size: 24px; font-weight: bold; color: #1f77b4; }}
        .summary-card .label {{ color: #666; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: #1f77b4; color: white; padding: 12px; text-align: center; }}
        td {{ padding: 10px; border-bottom: 1px solid #ddd; text-align: center; }}
        tr:hover {{ background: #f5f5f5; }}
        .positive {{ color: #28a745; }}
        .negative {{ color: #dc3545; }}
        .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 포트폴리오 성과 리포트</h1>
        <p class="period">기간: {data.period_start} ~ {data.period_end}</p>

        <h2>💰 포트폴리오 요약</h2>
        <div class="summary-grid">
            <div class="summary-card">
                <div class="value">₩{snapshot.total_value:,.0f}</div>
                <div class="label">총 자산</div>
            </div>
            <div class="summary-card">
                <div class="value">₩{snapshot.total_cost:,.0f}</div>
                <div class="label">총 투자금</div>
            </div>
            <div class="summary-card">
                <div class="value {'positive' if snapshot.total_return >= 0 else 'negative'}">₩{snapshot.total_return:+,.0f}</div>
                <div class="label">총 수익</div>
            </div>
            <div class="summary-card">
                <div class="value {'positive' if snapshot.return_pct >= 0 else 'negative'}">{snapshot.return_pct:+.2f}%</div>
                <div class="label">수익률</div>
            </div>
        </div>

        <h2>📈 보유 종목</h2>
        <table>
            <tr>
                <th>종목</th>
                <th>수량</th>
                <th>평균단가</th>
                <th>현재가</th>
                <th>평가금액</th>
                <th>손익</th>
                <th>수익률</th>
            </tr>
"""

        for pos in snapshot.positions:
            pnl = pos.get('unrealized_pnl', 0)
            ret = pos.get('return_pct', 0)
            pnl_class = 'positive' if pnl >= 0 else 'negative'

            html += f"""
            <tr>
                <td>{pos.get('name', pos.get('symbol', ''))}</td>
                <td>{pos.get('quantity', 0):,}</td>
                <td>₩{pos.get('avg_price', 0):,.0f}</td>
                <td>₩{pos.get('current_price', 0):,.0f}</td>
                <td>₩{pos.get('market_value', 0):,.0f}</td>
                <td class="{pnl_class}">₩{pnl:+,.0f}</td>
                <td class="{pnl_class}">{ret:+.2f}%</td>
            </tr>
"""

        html += f"""
        </table>

        <div class="footer">
            <p>생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>NOTION 포트폴리오 관리 시스템</p>
        </div>
    </div>
</body>
</html>
"""

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        return str(filepath)


# 싱글톤 인스턴스
report_generator = ReportGenerator()


def generate_daily_report(portfolio_data: Dict) -> str:
    """일일 리포트 생성"""
    # 데이터 변환
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    current_snapshot = PortfolioSnapshot(
        date=today,
        total_value=portfolio_data.get('total_value', 0),
        total_cost=portfolio_data.get('total_cost', 0),
        total_return=portfolio_data.get('total_return', 0),
        return_pct=portfolio_data.get('return_pct', 0),
        positions=portfolio_data.get('positions', []),
        allocation=portfolio_data.get('allocation', {})
    )

    data = ReportData(
        period_start=today,
        period_end=today,
        current_snapshot=current_snapshot,
        previous_snapshot=None,
        transactions=portfolio_data.get('transactions', []),
        performance_history=[],
        market_summary=portfolio_data.get('market', {}),
        analysis=portfolio_data.get('analysis', {})
    )

    config = ReportConfig(report_type="daily")

    return report_generator.generate_html(data, config)
