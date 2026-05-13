"""Backtesting & Evaluation — replay historical data through the detection engine."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pandas as pd

from app.engines.setup_detection import SetupCandidate, SetupDetectionEngine
from app.engines.signal_ranking import SignalRankingEngine
from app.engines.technical_analysis import TechnicalAnalysisEngine
from app.models.signal import MarketType

logger = logging.getLogger(__name__)


@dataclass
class BacktestTrade:
    symbol: str
    setup_type: str
    direction: str
    entry: float
    stop_loss: float
    tp1: float
    rr_ratio: float
    outcome: str  # "tp1_hit", "stopped_out", "expired"
    pnl_pct: float
    bars_held: int


@dataclass
class BacktestResult:
    total_trades: int
    wins: int
    losses: int
    expired: int
    win_rate: float
    avg_rr: float
    avg_pnl_pct: float
    total_pnl_pct: float
    best_trade: BacktestTrade | None
    worst_trade: BacktestTrade | None
    trades: list[BacktestTrade] = field(default_factory=list)
    by_setup_type: dict[str, dict[str, float]] = field(default_factory=dict)


class BacktestEngine:
    """Replays historical candle data through the setup detection engine."""

    MAX_BARS_HOLD = 50  # max bars to hold a position

    def __init__(self) -> None:
        self.ta_engine = TechnicalAnalysisEngine()
        self.detection = SetupDetectionEngine()
        self.ranking = SignalRankingEngine()

    def run(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        exchange: str = "binance",
        market_type: MarketType = MarketType.SPOT,
        window: int = 200,
    ) -> BacktestResult:
        trades: list[BacktestTrade] = []

        if len(df) < window + self.MAX_BARS_HOLD:
            return BacktestResult(
                total_trades=0,
                wins=0,
                losses=0,
                expired=0,
                win_rate=0,
                avg_rr=0,
                avg_pnl_pct=0,
                total_pnl_pct=0,
                best_trade=None,
                worst_trade=None,
            )

        for i in range(window, len(df) - self.MAX_BARS_HOLD):
            slice_df = df.iloc[i - window : i].copy()
            ta_result = self.ta_engine.analyze(slice_df, symbol, timeframe)
            if not ta_result:
                continue

            setups = self.detection.detect_setups(ta_result, None, exchange, market_type)
            if not setups:
                continue

            # Take the first (best) setup
            setup = setups[0]
            trade = self._simulate_trade(setup, df, i)
            if trade:
                trades.append(trade)

        return self._compile_results(trades)

    def _simulate_trade(
        self, setup: SetupCandidate, df: pd.DataFrame, entry_idx: int
    ) -> BacktestTrade | None:
        entry = (setup.entry_low + setup.entry_high) / 2
        is_long = setup.direction.value == "long"

        for bar in range(1, self.MAX_BARS_HOLD + 1):
            idx = entry_idx + bar
            if idx >= len(df):
                break

            bar_high = float(df.iloc[idx]["high"])
            bar_low = float(df.iloc[idx]["low"])

            # Check stop loss
            if is_long and bar_low <= setup.stop_loss:
                pnl = ((setup.stop_loss - entry) / entry) * 100
                return BacktestTrade(
                    symbol=setup.symbol,
                    setup_type=setup.setup_type.value,
                    direction=setup.direction.value,
                    entry=entry,
                    stop_loss=setup.stop_loss,
                    tp1=setup.tp1,
                    rr_ratio=setup.rr_ratio,
                    outcome="stopped_out",
                    pnl_pct=round(pnl, 2),
                    bars_held=bar,
                )
            if not is_long and bar_high >= setup.stop_loss:
                pnl = ((entry - setup.stop_loss) / entry) * 100
                return BacktestTrade(
                    symbol=setup.symbol,
                    setup_type=setup.setup_type.value,
                    direction=setup.direction.value,
                    entry=entry,
                    stop_loss=setup.stop_loss,
                    tp1=setup.tp1,
                    rr_ratio=setup.rr_ratio,
                    outcome="stopped_out",
                    pnl_pct=round(pnl, 2),
                    bars_held=bar,
                )

            # Check TP1
            if is_long and bar_high >= setup.tp1:
                pnl = ((setup.tp1 - entry) / entry) * 100
                return BacktestTrade(
                    symbol=setup.symbol,
                    setup_type=setup.setup_type.value,
                    direction=setup.direction.value,
                    entry=entry,
                    stop_loss=setup.stop_loss,
                    tp1=setup.tp1,
                    rr_ratio=setup.rr_ratio,
                    outcome="tp1_hit",
                    pnl_pct=round(pnl, 2),
                    bars_held=bar,
                )
            if not is_long and bar_low <= setup.tp1:
                pnl = ((entry - setup.tp1) / entry) * 100
                return BacktestTrade(
                    symbol=setup.symbol,
                    setup_type=setup.setup_type.value,
                    direction=setup.direction.value,
                    entry=entry,
                    stop_loss=setup.stop_loss,
                    tp1=setup.tp1,
                    rr_ratio=setup.rr_ratio,
                    outcome="tp1_hit",
                    pnl_pct=round(pnl, 2),
                    bars_held=bar,
                )

        # Expired — exit at last close
        exit_price = float(df.iloc[min(entry_idx + self.MAX_BARS_HOLD, len(df) - 1)]["close"])
        pnl = (
            ((exit_price - entry) / entry * 100)
            if is_long
            else ((entry - exit_price) / entry * 100)
        )
        return BacktestTrade(
            symbol=setup.symbol,
            setup_type=setup.setup_type.value,
            direction=setup.direction.value,
            entry=entry,
            stop_loss=setup.stop_loss,
            tp1=setup.tp1,
            rr_ratio=setup.rr_ratio,
            outcome="expired",
            pnl_pct=round(pnl, 2),
            bars_held=self.MAX_BARS_HOLD,
        )

    @staticmethod
    def _compile_results(trades: list[BacktestTrade]) -> BacktestResult:
        if not trades:
            return BacktestResult(
                total_trades=0,
                wins=0,
                losses=0,
                expired=0,
                win_rate=0,
                avg_rr=0,
                avg_pnl_pct=0,
                total_pnl_pct=0,
                best_trade=None,
                worst_trade=None,
            )

        wins = [t for t in trades if t.outcome == "tp1_hit"]
        losses = [t for t in trades if t.outcome == "stopped_out"]
        expired = [t for t in trades if t.outcome == "expired"]

        total_pnl = sum(t.pnl_pct for t in trades)
        avg_pnl = total_pnl / len(trades)
        avg_rr = sum(t.rr_ratio for t in trades) / len(trades)

        best = max(trades, key=lambda t: t.pnl_pct)
        worst = min(trades, key=lambda t: t.pnl_pct)

        # By setup type
        by_type: dict[str, dict[str, float]] = {}
        for t in trades:
            if t.setup_type not in by_type:
                by_type[t.setup_type] = {"trades": 0, "wins": 0, "pnl": 0.0}
            by_type[t.setup_type]["trades"] += 1
            if t.outcome == "tp1_hit":
                by_type[t.setup_type]["wins"] += 1
            by_type[t.setup_type]["pnl"] += t.pnl_pct

        for st in by_type:
            total = by_type[st]["trades"]
            by_type[st]["win_rate"] = (by_type[st]["wins"] / total * 100) if total > 0 else 0

        return BacktestResult(
            total_trades=len(trades),
            wins=len(wins),
            losses=len(losses),
            expired=len(expired),
            win_rate=round(len(wins) / len(trades) * 100, 1) if trades else 0,
            avg_rr=round(avg_rr, 2),
            avg_pnl_pct=round(avg_pnl, 2),
            total_pnl_pct=round(total_pnl, 2),
            best_trade=best,
            worst_trade=worst,
            trades=trades,
            by_setup_type=by_type,
        )
