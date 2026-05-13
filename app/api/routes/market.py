"""Market data API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query

from app.api.schemas import MarketOverview
from app.engines.market_data import MarketDataEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/market", tags=["market"])

_engine: MarketDataEngine | None = None


async def get_engine() -> MarketDataEngine:
    global _engine
    if _engine is None:
        _engine = MarketDataEngine()
        await _engine.init_exchanges()
    return _engine


@router.get("/overview", response_model=MarketOverview)
async def market_overview() -> MarketOverview:
    """Get current global market overview."""
    engine = await get_engine()
    data = await engine.fetch_global_market_data()

    candles = await engine.fetch_all_candles("binance", "4h")
    breadth = await engine.compute_market_breadth(candles)

    return MarketOverview(
        btc_price=data.btc_price,
        eth_price=data.eth_price,
        btc_dominance=data.btc_dominance,
        total_market_cap=data.total_market_cap,
        fear_greed_index=data.fear_greed_index,
        market_trend=data.market_trend,
        breadth_bullish_pct=breadth,
    )


@router.get("/candles")
async def get_candles(
    symbol: str = Query("BTC/USDT"),
    exchange: str = Query("binance"),
    timeframe: str = Query("4h"),
    limit: int = Query(200, ge=10, le=1000),
) -> dict:
    """Fetch OHLCV candles for charting."""
    engine = await get_engine()
    candle = await engine.fetch_ohlcv(exchange, symbol, timeframe, limit)
    if not candle:
        return {"error": "Failed to fetch candles", "data": []}

    records = candle.df.reset_index().to_dict(orient="records")
    # Convert timestamps
    for r in records:
        if hasattr(r["timestamp"], "isoformat"):
            r["timestamp"] = r["timestamp"].isoformat()
        r["time"] = (
            int(candle.df.index[records.index(r)].timestamp())
            if hasattr(candle.df.index[0], "timestamp")
            else 0
        )

    return {"symbol": symbol, "timeframe": timeframe, "data": records}


@router.get("/tickers")
async def get_tickers(
    exchange: str = Query("binance"),
) -> dict:
    """Get current tickers for tracked symbols."""
    engine = await get_engine()
    tickers = {}
    for symbol in engine.symbols[:20]:
        ticker = await engine.fetch_ticker(exchange, symbol)
        if ticker:
            tickers[symbol] = {
                "last": ticker.get("last"),
                "change_pct": ticker.get("percentage"),
                "volume": ticker.get("baseVolume"),
                "high": ticker.get("high"),
                "low": ticker.get("low"),
            }
    return {"exchange": exchange, "tickers": tickers}
