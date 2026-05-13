from __future__ import annotations

import datetime
import enum

from sqlalchemy import DateTime, Enum, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SetupType(str, enum.Enum):
    ACCUMULATION_BREAKOUT = "accumulation_breakout"
    TREND_CONTINUATION = "trend_continuation"
    VOLUME_EXPANSION = "volume_expansion"
    NARRATIVE_ROTATION = "narrative_rotation"
    BREAKOUT_VOLUME = "breakout_volume"
    LIQUIDITY_SWEEP = "liquidity_sweep"
    FUNDING_RESET = "funding_reset"
    SHORT_SQUEEZE = "short_squeeze"
    PULLBACK_ENTRY = "pullback_entry"


class MarketType(str, enum.Enum):
    SPOT = "spot"
    FUTURES = "futures"


class SignalDirection(str, enum.Enum):
    LONG = "long"
    SHORT = "short"


class SignalStatus(str, enum.Enum):
    ACTIVE = "active"
    INVALIDATED = "invalidated"
    TP1_HIT = "tp1_hit"
    TP2_HIT = "tp2_hit"
    TP3_HIT = "tp3_hit"
    STOPPED_OUT = "stopped_out"
    EXPIRED = "expired"


class Signal(Base):
    __tablename__ = "signals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False)
    symbol: Mapped[str] = mapped_column(String(30), nullable=False)
    market_type: Mapped[MarketType] = mapped_column(Enum(MarketType), nullable=False)
    direction: Mapped[SignalDirection] = mapped_column(Enum(SignalDirection), nullable=False)
    setup_type: Mapped[SetupType] = mapped_column(Enum(SetupType), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(5), nullable=False)

    entry_low: Mapped[float] = mapped_column(Float, nullable=False)
    entry_high: Mapped[float] = mapped_column(Float, nullable=False)
    stop_loss: Mapped[float] = mapped_column(Float, nullable=False)
    tp1: Mapped[float] = mapped_column(Float, nullable=False)
    tp2: Mapped[float | None] = mapped_column(Float, nullable=True)
    tp3: Mapped[float | None] = mapped_column(Float, nullable=True)

    rr_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-100
    quality_score: Mapped[float] = mapped_column(Float, nullable=False)
    confluence_score: Mapped[float] = mapped_column(Float, nullable=False)

    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    risks: Mapped[str] = mapped_column(Text, nullable=False)
    invalidation: Mapped[str] = mapped_column(Text, nullable=False)
    market_context: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[SignalStatus] = mapped_column(
        Enum(SignalStatus), default=SignalStatus.ACTIVE, nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.now(datetime.UTC)
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.datetime.now(datetime.UTC),
        onupdate=datetime.datetime.now(datetime.UTC),
    )

    __table_args__ = (
        Index("ix_signal_active", "status", "created_at"),
        Index("ix_signal_symbol", "symbol", "status"),
    )


class SignalPerformance(Base):
    __tablename__ = "signal_performance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    signal_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    pnl_percent: Mapped[float] = mapped_column(Float, nullable=False)
    max_favorable: Mapped[float] = mapped_column(Float, nullable=False)
    max_adverse: Mapped[float] = mapped_column(Float, nullable=False)
    duration_hours: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    closed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.now(datetime.UTC)
    )
