"""Technical Analysis Engine — deterministic TA computations."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class SupportResistance:
    level: float
    strength: int  # number of touches
    type: str  # "support" or "resistance"


@dataclass
class TrendInfo:
    direction: str  # "bullish", "bearish", "neutral"
    ema_aligned: bool
    strength: float  # 0-1


@dataclass
class TAResult:
    """Complete TA analysis for a single symbol/timeframe."""

    symbol: str
    timeframe: str
    current_price: float
    trend: TrendInfo
    support_levels: list[SupportResistance]
    resistance_levels: list[SupportResistance]
    rsi: float
    rsi_divergence: str | None  # "bullish", "bearish", or None
    atr: float
    atr_pct: float
    vwap: float | None
    volume_sma_ratio: float  # current vol / 20-SMA vol
    breakout_detected: bool
    breakout_retest: bool
    ema_20: float
    ema_50: float
    ema_200: float


class TechnicalAnalysisEngine:
    """Runs deterministic technical analysis on OHLCV data."""

    @staticmethod
    def analyze(df: pd.DataFrame, symbol: str, timeframe: str) -> TAResult | None:
        if df is None or len(df) < 50:
            return None

        close = df["close"]
        high = df["high"]
        low = df["low"]
        volume = df["volume"]
        current_price = float(close.iloc[-1])

        # EMAs
        ema_20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
        ema_50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
        ema_200 = (
            float(close.ewm(span=200, adjust=False).mean().iloc[-1]) if len(df) >= 200 else 0.0
        )

        # Trend detection via EMA alignment
        if ema_200 > 0:
            ema_aligned = current_price > ema_20 > ema_50 > ema_200
            bearish_aligned = current_price < ema_20 < ema_50 < ema_200
        else:
            ema_aligned = current_price > ema_20 > ema_50
            bearish_aligned = current_price < ema_20 < ema_50

        if ema_aligned:
            trend_dir = "bullish"
        elif bearish_aligned:
            trend_dir = "bearish"
        else:
            trend_dir = "neutral"

        trend_strength = _compute_trend_strength(close, ema_20, ema_50)
        trend = TrendInfo(direction=trend_dir, ema_aligned=ema_aligned, strength=trend_strength)

        # RSI (14)
        rsi = _compute_rsi(close, 14)

        # RSI divergence
        rsi_div = _detect_rsi_divergence(close, rsi_series=_compute_rsi_series(close, 14))

        # ATR (14)
        atr = _compute_atr(high, low, close, 14)
        atr_pct = (atr / current_price) * 100 if current_price > 0 else 0.0

        # VWAP (intraday approximation)
        vwap = _compute_vwap(high, low, close, volume)

        # Volume analysis
        vol_sma = (
            float(volume.rolling(20).mean().iloc[-1]) if len(volume) >= 20 else float(volume.mean())
        )
        volume_ratio = float(volume.iloc[-1]) / vol_sma if vol_sma > 0 else 1.0

        # Support / Resistance
        supports, resistances = _find_support_resistance(high, low, close, current_price)

        # Breakout detection
        recent_high = float(high.iloc[-21:-1].max()) if len(high) >= 21 else float(high.max())
        breakout_detected = current_price > recent_high and volume_ratio > 1.5

        # Breakout retest
        breakout_retest = False
        if len(close) >= 5:
            prev_highs = high.iloc[-10:-3]
            if len(prev_highs) > 0:
                prev_high_val = float(prev_highs.max())
                recently_broke = float(close.iloc[-3]) > prev_high_val
                pulled_back = current_price <= prev_high_val * 1.02
                breakout_retest = recently_broke and pulled_back

        return TAResult(
            symbol=symbol,
            timeframe=timeframe,
            current_price=current_price,
            trend=trend,
            support_levels=supports,
            resistance_levels=resistances,
            rsi=rsi,
            rsi_divergence=rsi_div,
            atr=atr,
            atr_pct=atr_pct,
            vwap=vwap,
            volume_sma_ratio=volume_ratio,
            breakout_detected=breakout_detected,
            breakout_retest=breakout_retest,
            ema_20=ema_20,
            ema_50=ema_50,
            ema_200=ema_200,
        )


def _compute_rsi(close: pd.Series, period: int = 14) -> float:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1]) if not rsi.empty else 50.0


def _compute_rsi_series(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _detect_rsi_divergence(
    close: pd.Series, rsi_series: pd.Series, lookback: int = 14
) -> str | None:
    if len(close) < lookback + 5 or len(rsi_series) < lookback + 5:
        return None
    recent_close = close.iloc[-lookback:]
    recent_rsi = rsi_series.iloc[-lookback:]

    price_low1 = float(recent_close.iloc[: lookback // 2].min())
    price_low2 = float(recent_close.iloc[lookback // 2 :].min())
    rsi_low1 = float(recent_rsi.iloc[: lookback // 2].min())
    rsi_low2 = float(recent_rsi.iloc[lookback // 2 :].min())

    if price_low2 < price_low1 and rsi_low2 > rsi_low1:
        return "bullish"

    price_high1 = float(recent_close.iloc[: lookback // 2].max())
    price_high2 = float(recent_close.iloc[lookback // 2 :].max())
    rsi_high1 = float(recent_rsi.iloc[: lookback // 2].max())
    rsi_high2 = float(recent_rsi.iloc[lookback // 2 :].max())

    if price_high2 > price_high1 and rsi_high2 < rsi_high1:
        return "bearish"

    return None


def _compute_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
    tr = pd.concat(
        [high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1
    ).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return float(atr.iloc[-1]) if not atr.empty else 0.0


def _compute_vwap(
    high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series
) -> float | None:
    if volume.sum() == 0:
        return None
    tp = (high + low + close) / 3
    vwap = (tp * volume).cumsum() / volume.cumsum()
    return float(vwap.iloc[-1])


def _compute_trend_strength(close: pd.Series, ema20: float, ema50: float) -> float:
    current = float(close.iloc[-1])
    if ema20 == 0 or ema50 == 0:
        return 0.0
    spread = abs(ema20 - ema50) / ema50
    price_vs_ema = abs(current - ema20) / ema20
    return min(1.0, (spread + price_vs_ema) * 10)


def _find_support_resistance(
    high: pd.Series, low: pd.Series, close: pd.Series, current_price: float, window: int = 5
) -> tuple[list[SupportResistance], list[SupportResistance]]:
    supports: list[SupportResistance] = []
    resistances: list[SupportResistance] = []

    # Pivot-based S/R detection
    for i in range(window, len(close) - window):
        is_pivot_low = all(low.iloc[i] <= low.iloc[i - j] for j in range(1, window + 1)) and all(
            low.iloc[i] <= low.iloc[i + j] for j in range(1, window + 1)
        )
        is_pivot_high = all(high.iloc[i] >= high.iloc[i - j] for j in range(1, window + 1)) and all(
            high.iloc[i] >= high.iloc[i + j] for j in range(1, window + 1)
        )

        if is_pivot_low:
            level = float(low.iloc[i])
            _add_or_merge_level(supports, level, "support", current_price)

        if is_pivot_high:
            level = float(high.iloc[i])
            _add_or_merge_level(resistances, level, "resistance", current_price)

    supports.sort(key=lambda s: s.level, reverse=True)
    resistances.sort(key=lambda r: r.level)

    # Keep only nearby levels
    supports = [s for s in supports if s.level < current_price][:5]
    resistances = [r for r in resistances if r.level > current_price][:5]

    return supports, resistances


def _add_or_merge_level(
    levels: list[SupportResistance],
    new_level: float,
    level_type: str,
    current_price: float,
    tolerance: float = 0.015,
) -> None:
    for existing in levels:
        if abs(existing.level - new_level) / current_price < tolerance:
            existing.strength += 1
            existing.level = (existing.level + new_level) / 2
            return
    levels.append(SupportResistance(level=new_level, strength=1, type=level_type))
