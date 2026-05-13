"""Backtesting API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.api.schemas import BacktestRequest, BacktestResponse
from app.engines.market_data import MarketDataEngine
from app.models.signal import MarketType
from app.services.backtesting import BacktestEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/backtest", tags=["backtest"])

_market_data: MarketDataEngine | None = None


async def get_market_data() -> MarketDataEngine:
    global _market_data
    if _market_data is None:
        _market_data = MarketDataEngine()
        await _market_data.init_exchanges()
    return _market_data


@router.post("/run", response_model=BacktestResponse)
async def run_backtest(req: BacktestRequest) -> BacktestResponse:
    """Run a backtest on historical data for a given symbol."""
    md = await get_market_data()
    candle = await md.fetch_ohlcv(req.exchange, req.symbol, req.timeframe, req.limit)

    if not candle or len(candle.df) < 200:
        return BacktestResponse(
            total_trades=0,
            wins=0,
            losses=0,
            expired=0,
            win_rate=0,
            avg_rr=0,
            avg_pnl_pct=0,
            total_pnl_pct=0,
            by_setup_type={},
            best_trade=None,
            worst_trade=None,
        )

    market_type = MarketType.FUTURES if req.market_type == "futures" else MarketType.SPOT
    engine = BacktestEngine()
    result = engine.run(candle.df, req.symbol, req.timeframe, req.exchange, market_type)

    return BacktestResponse(
        total_trades=result.total_trades,
        wins=result.wins,
        losses=result.losses,
        expired=result.expired,
        win_rate=result.win_rate,
        avg_rr=result.avg_rr,
        avg_pnl_pct=result.avg_pnl_pct,
        total_pnl_pct=result.total_pnl_pct,
        by_setup_type=result.by_setup_type,
        best_trade=vars(result.best_trade) if result.best_trade else None,
        worst_trade=vars(result.worst_trade) if result.worst_trade else None,
    )
