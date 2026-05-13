"""Scanner Worker — runs periodic market scans and sends alerts."""

from __future__ import annotations

import asyncio
import logging
import signal

from app.core.config import settings
from app.services.alerting import send_alert
from app.services.scanner import ScannerService

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def run_scan_cycle(scanner: ScannerService) -> None:
    logger.info("Starting scan cycle...")

    try:
        result = await scanner.run_full_scan(
            exchange_name="binance",
            timeframe="4h",
            include_futures=True,
        )

        logger.info(
            "Scan complete: %d symbols scanned, %d setups found, %d approved (%.1fs)",
            result.symbols_scanned,
            result.setups_found,
            result.setups_approved,
            result.scan_duration_seconds,
        )

        # Send alerts for top signals
        for signal_result in result.signals[:5]:
            risk = result.risk_assessments.get(signal_result.setup.symbol)
            await send_alert(signal_result, risk)
            logger.info(
                "Alert sent: %s %s %s (confidence: %d%%, score: %.0f)",
                signal_result.setup.symbol,
                signal_result.setup.direction.value,
                signal_result.setup.setup_type.value,
                signal_result.confidence,
                signal_result.final_score,
            )

    except Exception:
        logger.exception("Scan cycle failed")


async def main() -> None:
    scanner = ScannerService()
    await scanner.initialize()

    shutdown = asyncio.Event()

    def _handle_signal() -> None:
        logger.info("Shutdown signal received")
        shutdown.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _handle_signal)

    logger.info(
        "Scanner worker started (interval: %ds)",
        settings.scanner_interval_seconds,
    )

    try:
        while not shutdown.is_set():
            await run_scan_cycle(scanner)
            try:
                await asyncio.wait_for(
                    shutdown.wait(),
                    timeout=settings.scanner_interval_seconds,
                )
            except asyncio.TimeoutError:
                pass
    finally:
        await scanner.shutdown()
        logger.info("Scanner worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
