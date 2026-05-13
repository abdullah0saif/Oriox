"""Dashboard API routes — aggregated data for the frontend."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.api.routes.setups import get_scanner

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary() -> dict:
    """Get a dashboard summary with top setups and market overview."""
    scanner = await get_scanner()

    result = await scanner.run_full_scan(
        exchange_name="binance",
        timeframe="4h",
        include_futures=True,
    )

    top_setups = []
    for ranked in result.signals[:10]:
        risk = result.risk_assessments.get(ranked.setup.symbol)
        top_setups.append(
            {
                "symbol": ranked.setup.symbol,
                "direction": ranked.setup.direction.value,
                "setup_type": ranked.setup.setup_type.value,
                "timeframe": ranked.setup.timeframe,
                "confidence": ranked.confidence,
                "final_score": ranked.final_score,
                "rr_ratio": ranked.setup.rr_ratio,
                "entry": f"{ranked.setup.entry_low:.4f} - {ranked.setup.entry_high:.4f}",
                "stop_loss": ranked.setup.stop_loss,
                "tp1": ranked.setup.tp1,
                "explanation": ranked.reasoning.explanation,
                "risk_approved": risk.approved if risk else False,
                "position_size_pct": risk.position_size_pct if risk and risk.approved else 0,
            }
        )

    return {
        "market": {
            "btc_price": result.market_data.btc_price,
            "eth_price": result.market_data.eth_price,
            "btc_dominance": result.market_data.btc_dominance,
            "fear_greed_index": result.market_data.fear_greed_index,
            "market_trend": result.market_data.market_trend,
            "breadth_bullish_pct": result.market_data.breadth_bullish_pct,
        },
        "scan": {
            "symbols_scanned": result.symbols_scanned,
            "setups_found": result.setups_found,
            "setups_approved": result.setups_approved,
            "duration_seconds": result.scan_duration_seconds,
        },
        "top_setups": top_setups,
    }
