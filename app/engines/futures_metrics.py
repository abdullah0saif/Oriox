"""Futures Metrics Engine — funding, OI, liquidations, squeeze detection."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import ccxt.async_support as ccxt

logger = logging.getLogger(__name__)


@dataclass
class FuturesAnalysis:
    exchange: str
    symbol: str
    funding_rate: float
    open_interest: float
    oi_change_pct: float
    long_short_ratio: float | None
    liquidation_24h_long: float
    liquidation_24h_short: float
    overcrowded_longs: bool
    overcrowded_shorts: bool
    squeeze_probability: float  # 0-100
    squeeze_direction: str | None  # "long_squeeze", "short_squeeze", or None
    funding_extreme: bool
    summary: str


class FuturesMetricsEngine:
    """Analyzes futures-specific data to detect crowding and squeeze setups."""

    FUNDING_EXTREME_THRESHOLD = 0.0005  # ±0.05%
    OI_SURGE_THRESHOLD = 10.0  # 10% OI change
    SQUEEZE_MIN_PROBABILITY = 40

    def __init__(self) -> None:
        self._prev_oi: dict[str, float] = {}

    async def analyze(
        self,
        exchange: ccxt.Exchange,
        exchange_name: str,
        symbol: str,
    ) -> FuturesAnalysis | None:
        try:
            funding_rate = await self._fetch_funding_rate(exchange, symbol)
            open_interest = await self._fetch_open_interest(exchange, symbol)
            long_short_ratio = await self._fetch_long_short_ratio(exchange, exchange_name, symbol)

            # OI change tracking
            cache_key = f"{exchange_name}:{symbol}"
            prev_oi = self._prev_oi.get(cache_key, open_interest)
            oi_change_pct = ((open_interest - prev_oi) / prev_oi * 100) if prev_oi > 0 else 0.0
            self._prev_oi[cache_key] = open_interest

            # Crowding detection
            overcrowded_longs = funding_rate > self.FUNDING_EXTREME_THRESHOLD and (
                long_short_ratio is not None and long_short_ratio > 2.0
            )
            overcrowded_shorts = funding_rate < -self.FUNDING_EXTREME_THRESHOLD and (
                long_short_ratio is not None and long_short_ratio < 0.5
            )

            funding_extreme = abs(funding_rate) > self.FUNDING_EXTREME_THRESHOLD

            # Squeeze probability
            squeeze_prob, squeeze_dir = self._calculate_squeeze(
                funding_rate, oi_change_pct, long_short_ratio, overcrowded_longs, overcrowded_shorts
            )

            summary = self._build_summary(
                funding_rate,
                open_interest,
                oi_change_pct,
                overcrowded_longs,
                overcrowded_shorts,
                squeeze_prob,
                squeeze_dir,
            )

            return FuturesAnalysis(
                exchange=exchange_name,
                symbol=symbol,
                funding_rate=funding_rate,
                open_interest=open_interest,
                oi_change_pct=oi_change_pct,
                long_short_ratio=long_short_ratio,
                liquidation_24h_long=0.0,  # requires dedicated API
                liquidation_24h_short=0.0,
                overcrowded_longs=overcrowded_longs,
                overcrowded_shorts=overcrowded_shorts,
                squeeze_probability=squeeze_prob,
                squeeze_direction=squeeze_dir,
                funding_extreme=funding_extreme,
                summary=summary,
            )
        except Exception:
            logger.exception("Futures analysis failed for %s %s", exchange_name, symbol)
            return None

    async def analyze_batch(
        self,
        exchange: ccxt.Exchange,
        exchange_name: str,
        symbols: list[str],
    ) -> list[FuturesAnalysis]:
        tasks = [self.analyze(exchange, exchange_name, sym) for sym in symbols]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

    def _calculate_squeeze(
        self,
        funding_rate: float,
        oi_change_pct: float,
        long_short_ratio: float | None,
        overcrowded_longs: bool,
        overcrowded_shorts: bool,
    ) -> tuple[float, str | None]:
        score = 0.0
        direction = None

        if overcrowded_longs:
            score += 30
            direction = "long_squeeze"
        elif overcrowded_shorts:
            score += 30
            direction = "short_squeeze"

        if abs(funding_rate) > self.FUNDING_EXTREME_THRESHOLD * 2:
            score += 20

        if oi_change_pct > self.OI_SURGE_THRESHOLD:
            score += 20

        if long_short_ratio is not None:
            if long_short_ratio > 3.0 or long_short_ratio < 0.33:
                score += 15

        # Extreme funding + rising OI = potential liquidation cascade
        if abs(funding_rate) > self.FUNDING_EXTREME_THRESHOLD and oi_change_pct > 5:
            score += 15

        score = min(100.0, score)
        if score < self.SQUEEZE_MIN_PROBABILITY:
            direction = None

        return score, direction

    @staticmethod
    async def _fetch_funding_rate(exchange: ccxt.Exchange, symbol: str) -> float:
        try:
            result = await exchange.fetch_funding_rate(symbol)
            return float(result.get("fundingRate", 0.0) or 0.0)
        except Exception:
            return 0.0

    @staticmethod
    async def _fetch_open_interest(exchange: ccxt.Exchange, symbol: str) -> float:
        try:
            result = await exchange.fetch_open_interest(symbol)
            return float(result.get("openInterestValue", 0.0) or 0.0)
        except Exception:
            return 0.0

    @staticmethod
    async def _fetch_long_short_ratio(
        exchange: ccxt.Exchange, exchange_name: str, symbol: str
    ) -> float | None:
        # Long/short ratio is exchange-specific and not standardized in CCXT
        try:
            if exchange_name == "binance":
                raw_symbol = symbol.replace("/", "")
                resp = await exchange.publicGetFuturesDataGlobalLongShortAccountRatio(
                    {"symbol": raw_symbol, "period": "1h", "limit": 1}
                )
                if resp:
                    return float(resp[0].get("longShortRatio", 1.0))
        except Exception:
            pass
        return None

    @staticmethod
    def _build_summary(
        funding_rate: float,
        open_interest: float,
        oi_change_pct: float,
        overcrowded_longs: bool,
        overcrowded_shorts: bool,
        squeeze_prob: float,
        squeeze_dir: str | None,
    ) -> str:
        parts: list[str] = []
        parts.append(f"Funding: {funding_rate:.4%}")
        parts.append(f"OI: ${open_interest:,.0f} ({oi_change_pct:+.1f}%)")

        if overcrowded_longs:
            parts.append("⚠ Overcrowded longs")
        elif overcrowded_shorts:
            parts.append("⚠ Overcrowded shorts")

        if squeeze_dir:
            parts.append(f"Squeeze probability: {squeeze_prob:.0f}% ({squeeze_dir})")

        return " | ".join(parts)
