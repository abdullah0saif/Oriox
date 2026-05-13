"""Risk Management Layer — position sizing, leverage safety, drawdown tracking."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.engines.setup_detection import SetupCandidate
from app.engines.signal_ranking import RankedSignal

logger = logging.getLogger(__name__)


@dataclass
class RiskAssessment:
    approved: bool
    reason: str | None  # None if approved
    position_size_pct: float  # % of portfolio
    suggested_leverage: int
    max_loss_pct: float  # max loss as % of portfolio
    volatility_adjusted_sl: float
    warnings: list[str]


class RiskManagementEngine:
    """Validates setups against risk rules and calculates position sizing."""

    DEFAULT_RISK_PER_TRADE = 1.0  # 1% of portfolio per trade
    MAX_RISK_PER_TRADE = 2.0
    MAX_LEVERAGE_SPOT = 1
    MAX_LEVERAGE_FUTURES = 10
    MIN_RR = 2.0
    MAX_CONCURRENT_RISK = 5.0  # max 5% of portfolio in active risk

    def assess(
        self,
        signal: RankedSignal,
        portfolio_value: float = 10000.0,
        current_exposure_pct: float = 0.0,
        atr_pct: float = 2.0,
    ) -> RiskAssessment:
        setup = signal.setup
        warnings: list[str] = []

        # ─── Rejection rules ───
        if setup.rr_ratio < self.MIN_RR:
            return RiskAssessment(
                approved=False,
                reason=f"R:R ratio {setup.rr_ratio:.1f} below minimum {self.MIN_RR}",
                position_size_pct=0,
                suggested_leverage=0,
                max_loss_pct=0,
                volatility_adjusted_sl=setup.stop_loss,
                warnings=[],
            )

        if signal.risk_score > 75:
            return RiskAssessment(
                approved=False,
                reason=f"Risk score too high ({signal.risk_score:.0f}/100)",
                position_size_pct=0,
                suggested_leverage=0,
                max_loss_pct=0,
                volatility_adjusted_sl=setup.stop_loss,
                warnings=[],
            )

        if current_exposure_pct + self.DEFAULT_RISK_PER_TRADE > self.MAX_CONCURRENT_RISK:
            return RiskAssessment(
                approved=False,
                reason=f"Portfolio exposure limit reached ({current_exposure_pct:.1f}% / {self.MAX_CONCURRENT_RISK}%)",
                position_size_pct=0,
                suggested_leverage=0,
                max_loss_pct=0,
                volatility_adjusted_sl=setup.stop_loss,
                warnings=[],
            )

        if signal.confidence < 50:
            return RiskAssessment(
                approved=False,
                reason=f"Confidence too low ({signal.confidence}%)",
                position_size_pct=0,
                suggested_leverage=0,
                max_loss_pct=0,
                volatility_adjusted_sl=setup.stop_loss,
                warnings=[],
            )

        # ─── Volatility-adjusted stop loss ───
        vol_adjusted_sl = self._volatility_adjust_sl(setup, atr_pct)

        # ─── Position sizing (risk-based) ───
        entry_mid = (setup.entry_low + setup.entry_high) / 2
        risk_per_unit = abs(entry_mid - vol_adjusted_sl)
        risk_pct = (risk_per_unit / entry_mid) * 100 if entry_mid > 0 else 100

        risk_budget = self.DEFAULT_RISK_PER_TRADE
        if signal.confidence >= 80 and signal.final_score >= 75:
            risk_budget = min(self.MAX_RISK_PER_TRADE, risk_budget * 1.5)
            warnings.append("Elevated position size due to high confidence")
        elif signal.confidence < 60:
            risk_budget *= 0.7
            warnings.append("Reduced position size due to moderate confidence")

        position_size_pct = (risk_budget / risk_pct * 100) if risk_pct > 0 else 0
        position_size_pct = min(position_size_pct, 25.0)  # max 25% of portfolio in one position

        # ─── Leverage ───
        is_futures = setup.market_type.value == "futures"
        max_lev = self.MAX_LEVERAGE_FUTURES if is_futures else self.MAX_LEVERAGE_SPOT
        suggested_leverage = self._safe_leverage(risk_pct, max_lev)

        if suggested_leverage > 5:
            warnings.append(f"High leverage ({suggested_leverage}x) — increased liquidation risk")

        max_loss_pct = risk_budget

        # ─── Additional warnings ───
        if atr_pct > 5:
            warnings.append(f"High volatility (ATR {atr_pct:.1f}%) — consider reduced size")

        if setup.rr_ratio < 2.5:
            warnings.append(f"Moderate R:R ({setup.rr_ratio:.1f}) — not an A+ setup")

        return RiskAssessment(
            approved=True,
            reason=None,
            position_size_pct=round(position_size_pct, 2),
            suggested_leverage=suggested_leverage,
            max_loss_pct=round(max_loss_pct, 2),
            volatility_adjusted_sl=round(vol_adjusted_sl, 8),
            warnings=warnings,
        )

    @staticmethod
    def _volatility_adjust_sl(setup: SetupCandidate, atr_pct: float) -> float:
        entry_mid = (setup.entry_low + setup.entry_high) / 2
        current_sl_distance = abs(entry_mid - setup.stop_loss)
        min_sl_distance = entry_mid * (atr_pct / 100) * 1.5

        if current_sl_distance < min_sl_distance:
            if setup.direction.value == "long":
                return entry_mid - min_sl_distance
            return entry_mid + min_sl_distance
        return setup.stop_loss

    @staticmethod
    def _safe_leverage(risk_pct: float, max_leverage: int) -> int:
        if risk_pct <= 0:
            return 1
        # Leverage such that SL hit = max 2% portfolio loss at 1% risk budget
        safe_lev = max(1, int(2.0 / risk_pct))
        return min(safe_lev, max_leverage)
