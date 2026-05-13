"""Setup Detection Engine — deterministic rule-based setup identification.

This is the CORE of the system. All setup logic is deterministic.
AI is used ONLY for reasoning/explanation, never for detection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from app.engines.futures_metrics import FuturesAnalysis
from app.engines.technical_analysis import TAResult
from app.models.signal import MarketType, SetupType, SignalDirection

logger = logging.getLogger(__name__)


@dataclass
class SetupCandidate:
    """A detected trade setup before scoring and AI reasoning."""

    symbol: str
    exchange: str
    market_type: MarketType
    direction: SignalDirection
    setup_type: SetupType
    timeframe: str

    entry_low: float
    entry_high: float
    stop_loss: float
    tp1: float
    tp2: float | None = None
    tp3: float | None = None

    rr_ratio: float = 0.0

    # Raw confluence factors
    confluence_factors: list[str] = field(default_factory=list)
    risk_factors: list[str] = field(default_factory=list)
    invalidation: str = ""


class SetupDetectionEngine:
    """Scans TA + futures data and detects high-quality setups using deterministic rules."""

    MIN_RR = 2.0
    MIN_CONFLUENCE = 2

    def detect_setups(
        self,
        ta: TAResult,
        futures: FuturesAnalysis | None,
        exchange: str,
        market_type: MarketType,
    ) -> list[SetupCandidate]:
        setups: list[SetupCandidate] = []

        if market_type == MarketType.SPOT:
            setups.extend(self._detect_spot_setups(ta, exchange))
        else:
            setups.extend(self._detect_futures_setups(ta, futures, exchange))

        # Filter by minimum confluence and RR
        return [
            s
            for s in setups
            if len(s.confluence_factors) >= self.MIN_CONFLUENCE and s.rr_ratio >= self.MIN_RR
        ]

    # ──────────────────── SPOT SETUPS ────────────────────

    def _detect_spot_setups(self, ta: TAResult, exchange: str) -> list[SetupCandidate]:
        setups: list[SetupCandidate] = []

        acc_breakout = self._check_accumulation_breakout(ta, exchange)
        if acc_breakout:
            setups.append(acc_breakout)

        trend_cont = self._check_trend_continuation(ta, exchange, MarketType.SPOT)
        if trend_cont:
            setups.append(trend_cont)

        vol_exp = self._check_volume_expansion(ta, exchange)
        if vol_exp:
            setups.append(vol_exp)

        return setups

    def _check_accumulation_breakout(self, ta: TAResult, exchange: str) -> SetupCandidate | None:
        if not ta.breakout_detected:
            return None

        confluence: list[str] = []
        risks: list[str] = []

        confluence.append("Price broke above recent range high")

        if ta.volume_sma_ratio > 1.5:
            confluence.append(f"Volume {ta.volume_sma_ratio:.1f}x above average")
        else:
            return None  # No volume confirmation = no setup

        if ta.trend.direction == "bullish":
            confluence.append("Bullish trend structure")
        if ta.rsi > 50 and ta.rsi < 75:
            confluence.append(f"RSI momentum healthy ({ta.rsi:.0f})")
        if ta.rsi > 75:
            risks.append(f"RSI overbought ({ta.rsi:.0f})")

        if ta.trend.ema_aligned:
            confluence.append("EMA alignment confirmed")

        if len(confluence) < self.MIN_CONFLUENCE:
            return None

        # Calculate levels
        nearest_support = (
            ta.support_levels[0].level if ta.support_levels else ta.current_price * 0.97
        )
        stop_loss = nearest_support * 0.995
        risk = ta.current_price - stop_loss
        if risk <= 0:
            return None

        tp1 = ta.current_price + risk * 2
        tp2 = ta.current_price + risk * 3
        tp3 = ta.current_price + risk * 4.5

        rr = (tp1 - ta.current_price) / risk

        return SetupCandidate(
            symbol=ta.symbol,
            exchange=exchange,
            market_type=MarketType.SPOT,
            direction=SignalDirection.LONG,
            setup_type=SetupType.ACCUMULATION_BREAKOUT,
            timeframe=ta.timeframe,
            entry_low=ta.current_price * 0.998,
            entry_high=ta.current_price * 1.005,
            stop_loss=stop_loss,
            tp1=tp1,
            tp2=tp2,
            tp3=tp3,
            rr_ratio=round(rr, 2),
            confluence_factors=confluence,
            risk_factors=risks,
            invalidation=f"Close below {stop_loss:.4f}",
        )

    def _check_trend_continuation(
        self, ta: TAResult, exchange: str, market_type: MarketType
    ) -> SetupCandidate | None:
        if ta.trend.direction == "neutral":
            return None

        is_long = ta.trend.direction == "bullish"

        # Price should be pulling back to EMA
        ema_distance_pct = abs(ta.current_price - ta.ema_20) / ta.ema_20 * 100
        if ema_distance_pct > 3.0:
            return None  # Too far from EMA — not a pullback

        near_ema = ema_distance_pct < 1.5

        confluence: list[str] = []
        risks: list[str] = []

        if ta.trend.ema_aligned:
            confluence.append(
                "EMA alignment confirmed (20 > 50 > 200)" if is_long else "Bearish EMA alignment"
            )

        if near_ema:
            confluence.append(f"Price near 20 EMA ({ema_distance_pct:.1f}% away)")

        if is_long and ta.rsi > 40 and ta.rsi < 65:
            confluence.append(f"RSI in healthy pullback zone ({ta.rsi:.0f})")
        elif not is_long and ta.rsi > 40 and ta.rsi < 60:
            confluence.append(f"RSI supports bearish continuation ({ta.rsi:.0f})")

        if ta.trend.strength > 0.3:
            confluence.append(f"Trend strength: {ta.trend.strength:.1%}")

        if ta.breakout_retest:
            confluence.append("Breakout retest in progress")

        if len(confluence) < self.MIN_CONFLUENCE:
            return None

        if is_long:
            stop_loss = ta.ema_50 * 0.99
            risk = ta.current_price - stop_loss
        else:
            stop_loss = ta.ema_50 * 1.01
            risk = stop_loss - ta.current_price

        if risk <= 0:
            return None

        direction = SignalDirection.LONG if is_long else SignalDirection.SHORT

        if is_long:
            tp1 = ta.current_price + risk * 2
            tp2 = ta.current_price + risk * 3
        else:
            tp1 = ta.current_price - risk * 2
            tp2 = ta.current_price - risk * 3

        rr = abs(tp1 - ta.current_price) / risk

        return SetupCandidate(
            symbol=ta.symbol,
            exchange=exchange,
            market_type=market_type,
            direction=direction,
            setup_type=SetupType.TREND_CONTINUATION,
            timeframe=ta.timeframe,
            entry_low=ta.current_price * (0.998 if is_long else 0.995),
            entry_high=ta.current_price * (1.005 if is_long else 1.002),
            stop_loss=stop_loss,
            tp1=tp1,
            tp2=tp2,
            tp3=None,
            rr_ratio=round(rr, 2),
            confluence_factors=confluence,
            risk_factors=risks,
            invalidation=f"Close {'below' if is_long else 'above'} 50 EMA ({ta.ema_50:.4f})",
        )

    def _check_volume_expansion(self, ta: TAResult, exchange: str) -> SetupCandidate | None:
        if ta.volume_sma_ratio < 2.0:
            return None

        if ta.trend.direction != "bullish":
            return None

        confluence: list[str] = [
            f"Volume spike {ta.volume_sma_ratio:.1f}x above average",
            "Bullish trend structure",
        ]
        risks: list[str] = []

        if ta.trend.ema_aligned:
            confluence.append("EMA alignment confirmed")
        if ta.rsi > 55:
            confluence.append(f"RSI momentum strong ({ta.rsi:.0f})")
        if ta.rsi > 80:
            risks.append("RSI heavily overbought — potential pullback")

        if len(confluence) < self.MIN_CONFLUENCE:
            return None

        nearest_support = (
            ta.support_levels[0].level if ta.support_levels else ta.current_price * 0.96
        )
        stop_loss = nearest_support * 0.995
        risk = ta.current_price - stop_loss
        if risk <= 0:
            return None

        tp1 = ta.current_price + risk * 2.5
        rr = (tp1 - ta.current_price) / risk

        return SetupCandidate(
            symbol=ta.symbol,
            exchange=exchange,
            market_type=MarketType.SPOT,
            direction=SignalDirection.LONG,
            setup_type=SetupType.VOLUME_EXPANSION,
            timeframe=ta.timeframe,
            entry_low=ta.current_price * 0.997,
            entry_high=ta.current_price * 1.003,
            stop_loss=stop_loss,
            tp1=tp1,
            tp2=ta.current_price + risk * 3.5,
            tp3=None,
            rr_ratio=round(rr, 2),
            confluence_factors=confluence,
            risk_factors=risks,
            invalidation=f"Close below {stop_loss:.4f}",
        )

    # ──────────────────── FUTURES SETUPS ────────────────────

    def _detect_futures_setups(
        self, ta: TAResult, futures: FuturesAnalysis | None, exchange: str
    ) -> list[SetupCandidate]:
        setups: list[SetupCandidate] = []

        trend_cont = self._check_trend_continuation(ta, exchange, MarketType.FUTURES)
        if trend_cont:
            if futures:
                self._enrich_with_futures(trend_cont, futures)
            setups.append(trend_cont)

        if futures:
            squeeze = self._check_squeeze_setup(ta, futures, exchange)
            if squeeze:
                setups.append(squeeze)

            funding_reset = self._check_funding_reset(ta, futures, exchange)
            if funding_reset:
                setups.append(funding_reset)

        liquidity_sweep = self._check_liquidity_sweep(ta, exchange)
        if liquidity_sweep:
            setups.append(liquidity_sweep)

        pullback = self._check_pullback_entry(ta, futures, exchange)
        if pullback:
            setups.append(pullback)

        return setups

    def _check_squeeze_setup(
        self, ta: TAResult, futures: FuturesAnalysis, exchange: str
    ) -> SetupCandidate | None:
        if futures.squeeze_probability < 50:
            return None

        if futures.squeeze_direction == "short_squeeze":
            direction = SignalDirection.LONG
            is_long = True
        elif futures.squeeze_direction == "long_squeeze":
            direction = SignalDirection.SHORT
            is_long = False
        else:
            return None

        confluence: list[str] = [
            f"Squeeze probability {futures.squeeze_probability:.0f}%",
            f"Direction: {futures.squeeze_direction}",
        ]
        risks: list[str] = []

        if futures.funding_extreme:
            confluence.append(f"Extreme funding rate ({futures.funding_rate:.4%})")
        if futures.overcrowded_longs:
            confluence.append("Overcrowded longs detected")
        if futures.overcrowded_shorts:
            confluence.append("Overcrowded shorts detected")
        if abs(futures.oi_change_pct) > 10:
            confluence.append(f"OI surge {futures.oi_change_pct:+.1f}%")

        if ta.trend.direction == "bullish" and not is_long:
            risks.append("Counter-trend: overall trend is bullish")
        if ta.trend.direction == "bearish" and is_long:
            risks.append("Counter-trend: overall trend is bearish")

        if len(confluence) < 3:
            return None

        atr = ta.atr if ta.atr > 0 else ta.current_price * 0.02
        if is_long:
            stop_loss = ta.current_price - atr * 1.5
            tp1 = ta.current_price + atr * 3
            tp2 = ta.current_price + atr * 5
        else:
            stop_loss = ta.current_price + atr * 1.5
            tp1 = ta.current_price - atr * 3
            tp2 = ta.current_price - atr * 5

        risk = abs(ta.current_price - stop_loss)
        rr = abs(tp1 - ta.current_price) / risk if risk > 0 else 0

        setup_type = SetupType.SHORT_SQUEEZE if is_long else SetupType.SHORT_SQUEEZE

        return SetupCandidate(
            symbol=ta.symbol,
            exchange=exchange,
            market_type=MarketType.FUTURES,
            direction=direction,
            setup_type=setup_type,
            timeframe=ta.timeframe,
            entry_low=ta.current_price * (0.998 if is_long else 0.995),
            entry_high=ta.current_price * (1.005 if is_long else 1.002),
            stop_loss=stop_loss,
            tp1=tp1,
            tp2=tp2,
            tp3=None,
            rr_ratio=round(rr, 2),
            confluence_factors=confluence,
            risk_factors=risks,
            invalidation=f"Close {'below' if is_long else 'above'} {stop_loss:.4f}",
        )

    def _check_funding_reset(
        self, ta: TAResult, futures: FuturesAnalysis, exchange: str
    ) -> SetupCandidate | None:
        # Funding rate was extreme and is now resetting
        if abs(futures.funding_rate) > 0.0001:
            return None  # Still elevated

        if ta.trend.direction == "neutral":
            return None

        is_long = ta.trend.direction == "bullish"
        confluence: list[str] = [
            "Funding rate has reset to neutral",
            f"Trend: {ta.trend.direction}",
        ]
        risks: list[str] = []

        if ta.trend.ema_aligned:
            confluence.append("EMA alignment supports direction")
        if ta.rsi > 40 and ta.rsi < 65 and is_long:
            confluence.append(f"RSI healthy ({ta.rsi:.0f})")

        if len(confluence) < self.MIN_CONFLUENCE:
            return None

        atr = ta.atr if ta.atr > 0 else ta.current_price * 0.02
        if is_long:
            stop_loss = ta.current_price - atr * 1.5
            tp1 = ta.current_price + atr * 2.5
            tp2 = ta.current_price + atr * 4
        else:
            stop_loss = ta.current_price + atr * 1.5
            tp1 = ta.current_price - atr * 2.5
            tp2 = ta.current_price - atr * 4

        risk = abs(ta.current_price - stop_loss)
        rr = abs(tp1 - ta.current_price) / risk if risk > 0 else 0

        return SetupCandidate(
            symbol=ta.symbol,
            exchange=exchange,
            market_type=MarketType.FUTURES,
            direction=SignalDirection.LONG if is_long else SignalDirection.SHORT,
            setup_type=SetupType.FUNDING_RESET,
            timeframe=ta.timeframe,
            entry_low=ta.current_price * (0.998 if is_long else 0.995),
            entry_high=ta.current_price * (1.005 if is_long else 1.002),
            stop_loss=stop_loss,
            tp1=tp1,
            tp2=tp2,
            tp3=None,
            rr_ratio=round(rr, 2),
            confluence_factors=confluence,
            risk_factors=risks,
            invalidation=f"Close {'below' if is_long else 'above'} {stop_loss:.4f}",
        )

    def _check_liquidity_sweep(self, ta: TAResult, exchange: str) -> SetupCandidate | None:
        if not ta.support_levels or not ta.resistance_levels:
            return None

        # Check if price swept below support and reclaimed
        nearest_support = ta.support_levels[0]
        if ta.current_price < nearest_support.level:
            return None  # Still below — not reclaimed

        # Price should have recently dipped below and come back
        sweep_distance = (ta.current_price - nearest_support.level) / ta.current_price
        if sweep_distance > 0.03:
            return None  # Too far from the sweep level

        confluence: list[str] = [
            f"Price reclaimed support at {nearest_support.level:.4f}",
            f"Support strength: {nearest_support.strength} touches",
        ]
        risks: list[str] = []

        if ta.rsi_divergence == "bullish":
            confluence.append("Bullish RSI divergence")
        if ta.volume_sma_ratio > 1.3:
            confluence.append(f"Volume confirmation ({ta.volume_sma_ratio:.1f}x)")

        if len(confluence) < self.MIN_CONFLUENCE:
            return None

        stop_loss = nearest_support.level * 0.985
        risk = ta.current_price - stop_loss
        if risk <= 0:
            return None

        tp1 = ta.current_price + risk * 2.5
        tp2 = ta.current_price + risk * 4
        rr = (tp1 - ta.current_price) / risk

        return SetupCandidate(
            symbol=ta.symbol,
            exchange=exchange,
            market_type=MarketType.FUTURES,
            direction=SignalDirection.LONG,
            setup_type=SetupType.LIQUIDITY_SWEEP,
            timeframe=ta.timeframe,
            entry_low=ta.current_price * 0.998,
            entry_high=ta.current_price * 1.003,
            stop_loss=stop_loss,
            tp1=tp1,
            tp2=tp2,
            tp3=None,
            rr_ratio=round(rr, 2),
            confluence_factors=confluence,
            risk_factors=risks,
            invalidation=f"Close below {stop_loss:.4f}",
        )

    def _check_pullback_entry(
        self, ta: TAResult, futures: FuturesAnalysis | None, exchange: str
    ) -> SetupCandidate | None:
        if ta.trend.direction != "bullish" or not ta.trend.ema_aligned:
            return None

        # Price must be near 20 EMA (pullback)
        distance = abs(ta.current_price - ta.ema_20) / ta.ema_20
        if distance > 0.01:
            return None

        confluence: list[str] = [
            "Bullish trend with EMA alignment",
            f"Price pulling back to 20 EMA ({distance:.2%} away)",
        ]
        risks: list[str] = []

        if ta.rsi > 40 and ta.rsi < 60:
            confluence.append(f"RSI cooled off ({ta.rsi:.0f})")
        if ta.volume_sma_ratio < 0.8:
            confluence.append("Volume declining on pullback (healthy)")
        if futures and not futures.overcrowded_longs:
            confluence.append("Funding not overcrowded")

        if len(confluence) < 3:
            return None

        stop_loss = ta.ema_50 * 0.99
        risk = ta.current_price - stop_loss
        if risk <= 0:
            return None

        tp1 = ta.current_price + risk * 2.5
        tp2 = ta.current_price + risk * 4
        rr = (tp1 - ta.current_price) / risk

        return SetupCandidate(
            symbol=ta.symbol,
            exchange=exchange,
            market_type=MarketType.FUTURES,
            direction=SignalDirection.LONG,
            setup_type=SetupType.PULLBACK_ENTRY,
            timeframe=ta.timeframe,
            entry_low=ta.ema_20 * 0.998,
            entry_high=ta.current_price * 1.003,
            stop_loss=stop_loss,
            tp1=tp1,
            tp2=tp2,
            tp3=None,
            rr_ratio=round(rr, 2),
            confluence_factors=confluence,
            risk_factors=risks,
            invalidation=f"Close below 50 EMA ({ta.ema_50:.4f})",
        )

    @staticmethod
    def _enrich_with_futures(setup: SetupCandidate, futures: FuturesAnalysis) -> None:
        if futures.funding_extreme:
            if (setup.direction == SignalDirection.LONG and futures.funding_rate > 0) or (
                setup.direction == SignalDirection.SHORT and futures.funding_rate < 0
            ):
                setup.risk_factors.append(
                    f"Funding rate extreme ({futures.funding_rate:.4%}) — crowded side"
                )
            else:
                setup.confluence_factors.append("Funding supports direction")

        if futures.squeeze_probability > 40:
            setup.confluence_factors.append(
                f"Squeeze probability {futures.squeeze_probability:.0f}%"
            )
