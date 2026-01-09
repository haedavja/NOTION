"""
REST API 서버
외부 연동용 API 엔드포인트 제공
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, Any
from functools import wraps

try:
    from flask import Flask, jsonify, request, abort
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

try:
    from fastapi import FastAPI, HTTPException, Depends, Query
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


# API 키 인증
API_KEY = os.getenv("NOTION_API_KEY", "")


def require_api_key(f):
    """API 키 인증 데코레이터 (Flask)"""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if API_KEY and api_key != API_KEY:
            abort(401, description="Invalid API key")
        return f(*args, **kwargs)
    return decorated


class APIServer:
    """API 서버 (Flask 기반)"""

    def __init__(self, host: str = "0.0.0.0", port: int = 5000):
        if not FLASK_AVAILABLE:
            raise ImportError("Flask가 필요합니다: pip install flask flask-cors")

        self.host = host
        self.port = port
        self.app = Flask(__name__)
        CORS(self.app)

        self._setup_routes()

    def _setup_routes(self):
        """라우트 설정"""

        @self.app.route('/api/health', methods=['GET'])
        def health():
            """헬스 체크"""
            return jsonify({
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0"
            })

        @self.app.route('/api/portfolio', methods=['GET'])
        @require_api_key
        def get_portfolio():
            """포트폴리오 조회"""
            try:
                from portfolio.portfolio import Portfolio
                portfolio = Portfolio()
                portfolio.load()

                return jsonify({
                    "success": True,
                    "data": {
                        "positions": [
                            {
                                "symbol": p.symbol,
                                "name": p.name,
                                "quantity": p.quantity,
                                "avg_price": p.avg_price,
                                "current_price": p.current_price,
                                "market_value": p.market_value,
                                "unrealized_pnl": p.unrealized_pnl,
                                "return_pct": p.return_pct
                            }
                            for p in portfolio.positions.values()
                        ],
                        "total_value": portfolio.total_value,
                        "total_cost": portfolio.total_cost,
                        "total_return": portfolio.total_return
                    }
                })
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route('/api/portfolio/position', methods=['POST'])
        @require_api_key
        def add_position():
            """포지션 추가"""
            try:
                data = request.get_json()
                from portfolio.portfolio import Portfolio
                portfolio = Portfolio()
                portfolio.load()

                portfolio.add_position(
                    symbol=data['symbol'],
                    name=data.get('name', data['symbol']),
                    quantity=data['quantity'],
                    price=data['price']
                )

                return jsonify({"success": True, "message": "Position added"})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 400

        @self.app.route('/api/watchlist', methods=['GET'])
        @require_api_key
        def get_watchlist():
            """워치리스트 조회"""
            try:
                from portfolio.watchlist import watchlist_manager
                items = watchlist_manager.get_items()

                return jsonify({
                    "success": True,
                    "data": [
                        {
                            "symbol": item.symbol,
                            "name": item.name,
                            "group": item.group,
                            "current_price": item.current_price,
                            "change_pct": item.change_pct
                        }
                        for item in items
                    ]
                })
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route('/api/watchlist', methods=['POST'])
        @require_api_key
        def add_to_watchlist():
            """워치리스트 추가"""
            try:
                data = request.get_json()
                from portfolio.watchlist import watchlist_manager

                item = watchlist_manager.add_item(
                    symbol=data['symbol'],
                    name=data.get('name', data['symbol']),
                    group=data.get('group', 'favorites')
                )

                return jsonify({"success": True, "data": {"symbol": item.symbol}})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 400

        @self.app.route('/api/alerts', methods=['GET'])
        @require_api_key
        def get_alerts():
            """알림 히스토리"""
            try:
                from alerts.notification import notification_manager
                history = notification_manager.get_history(limit=50)

                return jsonify({
                    "success": True,
                    "data": history
                })
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route('/api/alerts/send', methods=['POST'])
        @require_api_key
        def send_alert():
            """알림 전송"""
            try:
                data = request.get_json()
                from alerts.notification import send_notification

                result = send_notification(
                    title=data['title'],
                    body=data['body'],
                    msg_type=data.get('type', 'info')
                )

                return jsonify({"success": True, "results": result})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 400

        @self.app.route('/api/calendar', methods=['GET'])
        @require_api_key
        def get_calendar():
            """경제 캘린더"""
            try:
                from data.economic_calendar import economic_calendar
                days = request.args.get('days', 30, type=int)

                events = economic_calendar.get_upcoming_events(days)

                return jsonify({
                    "success": True,
                    "data": [
                        {
                            "date": e.date,
                            "time": e.time,
                            "event": e.event,
                            "country": e.country,
                            "importance": e.importance
                        }
                        for e in events
                    ]
                })
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route('/api/stock/<symbol>', methods=['GET'])
        @require_api_key
        def get_stock(symbol: str):
            """주식 정보"""
            try:
                import yfinance as yf
                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="1mo")

                return jsonify({
                    "success": True,
                    "data": {
                        "symbol": symbol,
                        "name": info.get('longName', symbol),
                        "current_price": info.get('currentPrice'),
                        "previous_close": info.get('previousClose'),
                        "market_cap": info.get('marketCap'),
                        "pe_ratio": info.get('forwardPE'),
                        "dividend_yield": info.get('dividendYield'),
                        "52w_high": info.get('fiftyTwoWeekHigh'),
                        "52w_low": info.get('fiftyTwoWeekLow'),
                        "history": {
                            "dates": [d.strftime("%Y-%m-%d") for d in hist.index],
                            "prices": hist['Close'].tolist()
                        }
                    }
                })
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route('/api/stock/<symbol>/patterns', methods=['GET'])
        @require_api_key
        def get_patterns(symbol: str):
            """차트 패턴 분석"""
            try:
                import yfinance as yf
                from analysis.chart_patterns import chart_analyzer

                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="6mo")

                result = chart_analyzer.analyze(hist)

                return jsonify({
                    "success": True,
                    "data": {
                        "symbol": symbol,
                        "patterns": [
                            {
                                "type": p.pattern_type.value,
                                "signal": p.signal.value,
                                "confidence": p.confidence,
                                "description": p.description
                            }
                            for p in result.get('patterns', [])
                        ],
                        "support_resistance": [
                            {
                                "level": sr.level,
                                "type": sr.type,
                                "strength": sr.strength
                            }
                            for sr in result.get('support_resistance', [])
                        ],
                        "trend": result.get('trend')
                    }
                })
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route('/api/backup', methods=['POST'])
        @require_api_key
        def create_backup():
            """백업 생성"""
            try:
                from utils.backup import backup_manager
                data = request.get_json() or {}

                backup = backup_manager.create_backup(
                    description=data.get('description', 'API backup')
                )

                return jsonify({
                    "success": True,
                    "data": {
                        "id": backup.id,
                        "filename": backup.filename,
                        "size": backup.size
                    }
                })
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        @self.app.route('/api/backups', methods=['GET'])
        @require_api_key
        def list_backups():
            """백업 목록"""
            try:
                from utils.backup import backup_manager
                backups = backup_manager.list_backups()

                return jsonify({
                    "success": True,
                    "data": [
                        {
                            "id": b.id,
                            "filename": b.filename,
                            "created_at": b.created_at,
                            "size": b.size,
                            "description": b.description
                        }
                        for b in backups
                    ]
                })
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

    def run(self, debug: bool = False):
        """서버 실행"""
        self.app.run(host=self.host, port=self.port, debug=debug)


# FastAPI 버전 (선택적)
if FASTAPI_AVAILABLE:
    from pydantic import BaseModel

    class PositionCreate(BaseModel):
        symbol: str
        name: str = None
        quantity: int
        price: float

    class WatchlistCreate(BaseModel):
        symbol: str
        name: str = None
        group: str = "favorites"

    class AlertCreate(BaseModel):
        title: str
        body: str
        type: str = "info"

    def create_fastapi_app() -> FastAPI:
        """FastAPI 앱 생성"""
        app = FastAPI(
            title="NOTION Portfolio API",
            description="포트폴리오 관리 시스템 API",
            version="1.0.0"
        )

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        async def verify_api_key(x_api_key: str = None):
            if API_KEY and x_api_key != API_KEY:
                raise HTTPException(status_code=401, detail="Invalid API key")
            return True

        @app.get("/api/health")
        async def health():
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0"
            }

        @app.get("/api/portfolio")
        async def get_portfolio(authenticated: bool = Depends(verify_api_key)):
            try:
                from portfolio.portfolio import Portfolio
                portfolio = Portfolio()
                portfolio.load()

                return {
                    "success": True,
                    "data": {
                        "positions": [
                            {
                                "symbol": p.symbol,
                                "name": p.name,
                                "quantity": p.quantity,
                                "avg_price": p.avg_price
                            }
                            for p in portfolio.positions.values()
                        ]
                    }
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        return app


def run_api_server(host: str = "0.0.0.0", port: int = 5000,
                   use_fastapi: bool = False):
    """API 서버 실행"""
    if use_fastapi and FASTAPI_AVAILABLE:
        app = create_fastapi_app()
        uvicorn.run(app, host=host, port=port)
    elif FLASK_AVAILABLE:
        server = APIServer(host, port)
        server.run()
    else:
        raise ImportError("Flask 또는 FastAPI가 필요합니다")


if __name__ == "__main__":
    run_api_server()
