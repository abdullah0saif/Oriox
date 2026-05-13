"""Pydantic schemas for API request/response models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SignalResponse(BaseModel):
    symbol: str
    exchange: str
    market_type: str
    direction: str
    setup_type: str
    timeframe: str

    entry_low: float
    entry_high: float
    stop_loss: float
    tp1: float
    tp2: float | None = None
    tp3: float | None = None
    rr_ratio: float

    confidence: int
    quality_score: float
    confluence_score: float
    risk_score: float
    market_condition_score: float
    final_score: float

    confluence_factors: list[str]
    risk_factors: list[str]
    invalidation: str

    explanation: str
    risk_summary: str
    market_context: str

    # Risk management
    position_size_pct: float | None = None
    suggested_leverage: int | None = None
    max_loss_pct: float | None = None
    risk_approved: bool = True
    risk_rejection_reason: str | None = None
    risk_warnings: list[str] = Field(default_factory=list)


class ScanResponse(BaseModel):
    signals: list[SignalResponse]
    market_trend: str
    btc_price: float
    btc_dominance: float
    fear_greed_index: int | None
    breadth_bullish_pct: float
    symbols_scanned: int
    setups_found: int
    setups_approved: int
    scan_duration_seconds: float


class MarketOverview(BaseModel):
    btc_price: float
    eth_price: float
    btc_dominance: float
    total_market_cap: float
    fear_greed_index: int | None
    market_trend: str
    breadth_bullish_pct: float


class BacktestRequest(BaseModel):
    symbol: str = "BTC/USDT"
    exchange: str = "binance"
    timeframe: str = "4h"
    market_type: str = "spot"
    limit: int = Field(default=500, ge=200, le=2000)


class BacktestResponse(BaseModel):
    total_trades: int
    wins: int
    losses: int
    expired: int
    win_rate: float
    avg_rr: float
    avg_pnl_pct: float
    total_pnl_pct: float
    by_setup_type: dict
    best_trade: dict | None
    worst_trade: dict | None


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
