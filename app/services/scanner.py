"""Scanner Service — orchestrates the full scan pipeline."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.core.config import settings
from app.engines.ai_reasoning import AIReasoning, AIReasoningEngine
from app.engines.futures_metrics import FuturesAnalysis, FuturesMetricsEngine
from app.engines.market_data import GlobalMarketData, MarketDataEngine
from app.engines.risk_management import RiskAssessment, RiskManagementEngine
from app.engines.sentiment import SentimentEngine
from app.engines.setup_detection import SetupCandidate, SetupDetectionEngine
from app.engines.signal_ranking import RankedSignal, SignalRankingEngine
from app.engines.technical_analysis import TAResult, TechnicalAnalysisEngine
from app.models.signal import MarketType

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    signals: list[RankedSignal]
    risk_assessments: dict[str, RiskAssessment]  # keyed by symbol
    market_data: GlobalMarketData
    scan_duration_seconds: float = 0.0
    symbols_scanned: int = 0
    setups_found: int = 0
    setups_approved: int = 0


class ScannerService:
    """Runs the full scan pipeline: data → TA → futures → detection → AI → rank → risk."""

    def __init__(self) -> None:
        api_keys: dict[str, dict[str, str]] = {}
        if settings.binance_api_key:
            api_keys["binance"] = {
                "api_key": settings.binance_api_key,
                "api_secret": settings.binance_api_secret,
            }
        if settings.bybit_api_key:
            api_keys["bybit"] = {
                "api_key": settings.bybit_api_key,
                "api_secret": settings.bybit_api_secret,
            }
        if settings.mexc_api_key:
            api_keys["mexc"] = {
                "api_key": settings.mexc_api_key,
                "api_secret": settings.mexc_api_secret,
            }

        self.market_data = MarketDataEngine(api_keys=api_keys)
        self.ta = TechnicalAnalysisEngine()
        self.futures = FuturesMetricsEngine()
        self.detection = SetupDetectionEngine()
        self.ai = AIReasoningEngine()
        self.ranking = SignalRankingEngine()
        self.risk = RiskManagementEngine()
        self.sentiment = SentimentEngine(settings.cryptopanic_api_key)

    async def initialize(self) -> None:
        await self.market_data.init_exchanges()

    async def shutdown(self) -> None:
        await self.market_data.close()

    async def run_full_scan(
        self,
        exchange_name: str = "binance",
        timeframe: str = "4h",
        include_futures: bool = True,
    ) -> ScanResult:
        import time

        start = time.monotonic()

        # 1. Fetch global market data + candles in parallel
        global_data_task = self.market_data.fetch_global_market_data()
        candles_task = self.market_data.fetch_all_candles(exchange_name, timeframe)
        global_data, candles = await asyncio.gather(global_data_task, candles_task)

        # Compute market breadth
        breadth = await self.market_data.compute_market_breadth(candles)
        global_data.breadth_bullish_pct = breadth

        # Determine market trend from BTC
        btc_candles = [c for c in candles if c.symbol == "BTC/USDT"]
        if btc_candles:
            btc_ta = self.ta.analyze(btc_candles[0].df, "BTC/USDT", timeframe)
            if btc_ta:
                global_data.market_trend = btc_ta.trend.direction

        # 2. Run TA on all symbols
        ta_results: list[TAResult] = []
        for candle in candles:
            result = self.ta.analyze(candle.df, candle.symbol, timeframe)
            if result:
                ta_results.append(result)

        # 3. Fetch futures metrics (if enabled)
        futures_map: dict[str, FuturesAnalysis] = {}
        if include_futures and exchange_name in self.market_data.exchanges:
            exchange = self.market_data.exchanges[exchange_name]
            try:
                # Switch to futures mode
                exchange.options["defaultType"] = "swap"
                for ta_r in ta_results:
                    fm = await self.futures.analyze(exchange, exchange_name, ta_r.symbol)
                    if fm:
                        futures_map[ta_r.symbol] = fm
            except Exception:
                logger.exception("Futures metrics fetch failed")
            finally:
                exchange.options["defaultType"] = "spot"

        # 4. Detect setups
        all_setups: list[SetupCandidate] = []
        for ta_r in ta_results:
            # Spot setups
            spot_setups = self.detection.detect_setups(
                ta_r, futures_map.get(ta_r.symbol), exchange_name, MarketType.SPOT
            )
            all_setups.extend(spot_setups)

            # Futures setups
            if include_futures:
                futures_setups = self.detection.detect_setups(
                    ta_r, futures_map.get(ta_r.symbol), exchange_name, MarketType.FUTURES
                )
                all_setups.extend(futures_setups)

        # 4b. Deduplicate: same symbol + same setup type across spot/futures — keep best market type
        all_setups = self._deduplicate_setups(all_setups)

        # 5. AI reasoning for each setup
        setups_with_reasoning: list[tuple[SetupCandidate, AIReasoning]] = []
        for setup in all_setups:
            reasoning = await self.ai.explain_setup(setup, global_data)
            setups_with_reasoning.append((setup, reasoning))

        # 6. Rank signals
        ranked = self.ranking.rank_batch(setups_with_reasoning, global_data)

        # 7. Filter by minimum confidence
        ranked = [r for r in ranked if r.confidence >= settings.min_setup_confidence]

        # 7b. Diversity cap: max 2 signals per setup type to avoid monotony
        ranked = self._apply_diversity_cap(ranked, max_per_type=2)

        # 8. Risk assessment
        risk_map: dict[str, RiskAssessment] = {}
        for signal in ranked:
            ta_match = next((t for t in ta_results if t.symbol == signal.setup.symbol), None)
            atr_pct = ta_match.atr_pct if ta_match else 2.0
            assessment = self.risk.assess(signal, atr_pct=atr_pct)
            risk_map[signal.setup.symbol] = assessment

        # Filter to only approved signals
        approved = [
            r
            for r in ranked
            if risk_map.get(
                r.setup.symbol,
                RiskAssessment(
                    approved=False,
                    reason="",
                    position_size_pct=0,
                    suggested_leverage=0,
                    max_loss_pct=0,
                    volatility_adjusted_sl=0,
                    warnings=[],
                ),
            ).approved
        ]

        elapsed = time.monotonic() - start

        return ScanResult(
            signals=approved,
            risk_assessments=risk_map,
            market_data=global_data,
            scan_duration_seconds=round(elapsed, 2),
            symbols_scanned=len(candles),
            setups_found=len(all_setups),
            setups_approved=len(approved),
        )

    @staticmethod
    def _deduplicate_setups(setups: list[SetupCandidate]) -> list[SetupCandidate]:
        """If the same symbol has the same setup type in both spot and futures, keep futures only."""
        seen: dict[tuple[str, str], SetupCandidate] = {}
        for s in setups:
            key = (s.symbol, s.setup_type.value)
            existing = seen.get(key)
            if existing is None:
                seen[key] = s
            elif s.market_type == MarketType.FUTURES and existing.market_type == MarketType.SPOT:
                seen[key] = s  # Prefer futures (more data: funding, OI)
            elif len(s.confluence_factors) > len(existing.confluence_factors):
                seen[key] = s  # Keep the one with more confluence
        return list(seen.values())

    @staticmethod
    def _apply_diversity_cap(
        ranked: list[RankedSignal], max_per_type: int = 2
    ) -> list[RankedSignal]:
        """Cap signals per setup type to ensure variety. Keep highest-scored."""
        type_counts: dict[str, int] = {}
        result: list[RankedSignal] = []
        for signal in ranked:  # already sorted by score descending
            st = signal.setup.setup_type.value
            count = type_counts.get(st, 0)
            if count < max_per_type:
                result.append(signal)
                type_counts[st] = count + 1
        return result
