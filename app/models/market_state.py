from __future__ import annotations

import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MarketState(Base):
    """Snapshot of overall market conditions (BTC dominance, breadth, etc.)."""

    __tablename__ = "market_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    btc_dominance: Mapped[float] = mapped_column(Float, nullable=False)
    total_market_cap: Mapped[float] = mapped_column(Float, nullable=False)
    btc_price: Mapped[float] = mapped_column(Float, nullable=False)
    eth_price: Mapped[float] = mapped_column(Float, nullable=False)
    fear_greed_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    market_trend: Mapped[str] = mapped_column(String(20), nullable=False)  # bullish/bearish/neutral
    breadth_bullish_pct: Mapped[float] = mapped_column(Float, nullable=False)
    captured_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.now(datetime.UTC)
    )

    __table_args__ = (Index("ix_market_state_ts", "captured_at"),)


class FuturesMetric(Base):
    """Futures-specific metrics per symbol."""

    __tablename__ = "futures_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    funding_rate: Mapped[float] = mapped_column(Float, nullable=False)
    open_interest: Mapped[float] = mapped_column(Float, nullable=False)
    oi_change_pct: Mapped[float] = mapped_column(Float, nullable=False)
    long_short_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    liquidation_24h_long: Mapped[float] = mapped_column(Float, default=0.0)
    liquidation_24h_short: Mapped[float] = mapped_column(Float, default=0.0)
    captured_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.now(datetime.UTC)
    )

    __table_args__ = (Index("ix_futures_lookup", "exchange", "symbol", "captured_at"),)


class SentimentSnapshot(Base):
    """News & social sentiment snapshot."""

    __tablename__ = "sentiment_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str | None] = mapped_column(String(30), nullable=True)  # null = market-wide
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    sentiment_score: Mapped[float] = mapped_column(Float, nullable=False)  # -1.0 to 1.0
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    narratives: Mapped[str | None] = mapped_column(Text, nullable=True)
    captured_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.now(datetime.UTC)
    )
