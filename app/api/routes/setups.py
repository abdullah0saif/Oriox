"""Setup & Signal API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query

from app.api.schemas import ScanResponse, SignalResponse
from app.services.alerting import send_alert
from app.services.scanner import ScannerService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/setups", tags=["setups"])

_scanner: ScannerService | None = None


async def get_scanner() -> ScannerService:
    global _scanner
    if _scanner is None:
        _scanner = ScannerService()
        await _scanner.initialize()
    return _scanner


@router.get("/scan", response_model=ScanResponse)
async def scan_market(
    exchange: str = Query("binance", description="Exchange to scan"),
    timeframe: str = Query("4h", description="Timeframe for analysis"),
    include_futures: bool = Query(True, description="Include futures setups"),
) -> ScanResponse:
    """Run a full market scan and return detected setups."""
    scanner = await get_scanner()
    result = await scanner.run_full_scan(exchange, timeframe, include_futures)

    signals: list[SignalResponse] = []
    for ranked in result.signals:
        risk = result.risk_assessments.get(ranked.setup.symbol)
        signals.append(
            SignalResponse(
                symbol=ranked.setup.symbol,
                exchange=ranked.setup.exchange,
                market_type=ranked.setup.market_type.value,
                direction=ranked.setup.direction.value,
                setup_type=ranked.setup.setup_type.value,
                timeframe=ranked.setup.timeframe,
                entry_low=ranked.setup.entry_low,
                entry_high=ranked.setup.entry_high,
                stop_loss=ranked.setup.stop_loss,
                tp1=ranked.setup.tp1,
                tp2=ranked.setup.tp2,
                tp3=ranked.setup.tp3,
                rr_ratio=ranked.setup.rr_ratio,
                confidence=ranked.confidence,
                quality_score=ranked.quality_score,
                confluence_score=ranked.confluence_score,
                risk_score=ranked.risk_score,
                market_condition_score=ranked.market_condition_score,
                final_score=ranked.final_score,
                confluence_factors=ranked.setup.confluence_factors,
                risk_factors=ranked.setup.risk_factors,
                invalidation=ranked.setup.invalidation,
                explanation=ranked.reasoning.explanation,
                risk_summary=ranked.reasoning.risk_summary,
                market_context=ranked.reasoning.market_context,
                position_size_pct=risk.position_size_pct if risk else None,
                suggested_leverage=risk.suggested_leverage if risk else None,
                max_loss_pct=risk.max_loss_pct if risk else None,
                risk_approved=risk.approved if risk else True,
                risk_rejection_reason=risk.reason if risk else None,
                risk_warnings=risk.warnings if risk else [],
            )
        )

    return ScanResponse(
        signals=signals,
        market_trend=result.market_data.market_trend,
        btc_price=result.market_data.btc_price,
        btc_dominance=result.market_data.btc_dominance,
        fear_greed_index=result.market_data.fear_greed_index,
        breadth_bullish_pct=result.market_data.breadth_bullish_pct,
        symbols_scanned=result.symbols_scanned,
        setups_found=result.setups_found,
        setups_approved=result.setups_approved,
        scan_duration_seconds=result.scan_duration_seconds,
    )


@router.post("/scan/alert")
async def scan_and_alert(
    exchange: str = Query("binance"),
    timeframe: str = Query("4h"),
) -> dict:
    """Run a scan and send alerts for detected setups."""
    scanner = await get_scanner()
    result = await scanner.run_full_scan(exchange, timeframe)

    alerts_sent = 0
    for ranked in result.signals[:5]:
        risk = result.risk_assessments.get(ranked.setup.symbol)
        await send_alert(ranked, risk)
        alerts_sent += 1

    return {
        "setups_found": result.setups_found,
        "setups_approved": result.setups_approved,
        "alerts_sent": alerts_sent,
    }
