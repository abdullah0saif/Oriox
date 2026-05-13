"""Alerting System — sends structured alerts via Telegram and Discord."""

from __future__ import annotations

import logging

import httpx

from app.core.config import settings
from app.engines.risk_management import RiskAssessment
from app.engines.signal_ranking import RankedSignal

logger = logging.getLogger(__name__)


def format_alert(signal: RankedSignal, risk: RiskAssessment | None = None) -> str:
    s = signal.setup
    r = signal.reasoning

    lines = [
        f"{'🟢' if s.direction.value == 'long' else '🔴'} *{s.symbol}* — {s.direction.value.upper()}",
        f"Setup: {s.setup_type.value.replace('_', ' ').title()}",
        f"Market: {s.market_type.value.upper()} | Exchange: {s.exchange}",
        f"Timeframe: {s.timeframe}",
        "",
        f"*ENTRY:* {s.entry_low:.4f} — {s.entry_high:.4f}",
        f"*STOP LOSS:* {s.stop_loss:.4f}",
        f"*TP1:* {s.tp1:.4f}",
    ]
    if s.tp2:
        lines.append(f"*TP2:* {s.tp2:.4f}")
    if s.tp3:
        lines.append(f"*TP3:* {s.tp3:.4f}")

    lines.extend(
        [
            "",
            f"*R:R:* {s.rr_ratio}",
            f"*Confidence:* {signal.confidence}%",
            f"*Quality:* {signal.quality_score:.0f} | *Confluence:* {signal.confluence_score:.0f}",
            "",
            "*WHY THIS SETUP EXISTS:*",
        ]
    )
    for factor in s.confluence_factors:
        lines.append(f"  • {factor}")

    if r.explanation:
        lines.extend(["", f"*AI Analysis:* {r.explanation}"])

    if s.risk_factors or r.risk_summary:
        lines.append("\n*RISKS:*")
        for rf in s.risk_factors:
            lines.append(f"  ⚠ {rf}")
        if r.risk_summary:
            lines.append(f"  ⚠ {r.risk_summary}")

    lines.extend(["", f"*Invalidation:* {s.invalidation}"])

    if risk and risk.approved:
        lines.extend(
            [
                "",
                f"*Position Size:* {risk.position_size_pct:.1f}% of portfolio",
                f"*Suggested Leverage:* {risk.suggested_leverage}x",
                f"*Max Loss:* {risk.max_loss_pct:.1f}%",
            ]
        )
        for w in risk.warnings:
            lines.append(f"  ⚠ {w}")
    elif risk and not risk.approved:
        lines.extend(["", f"❌ *REJECTED:* {risk.reason}"])

    lines.append("\n_This is not financial advice. DYOR._")

    return "\n".join(lines)


async def send_telegram(message: str) -> bool:
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        logger.warning("Telegram not configured")
        return False
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                url,
                json={
                    "chat_id": settings.telegram_chat_id,
                    "text": message,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": True,
                },
            )
            return resp.status_code == 200
    except Exception:
        logger.exception("Telegram send failed")
        return False


async def send_discord(message: str) -> bool:
    if not settings.discord_webhook_url:
        logger.warning("Discord not configured")
        return False
    # Convert Markdown bold from * to ** for Discord
    discord_msg = message.replace("*", "**")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                settings.discord_webhook_url,
                json={"content": discord_msg},
            )
            return resp.status_code in (200, 204)
    except Exception:
        logger.exception("Discord send failed")
        return False


async def send_alert(signal: RankedSignal, risk: RiskAssessment | None = None) -> dict[str, bool]:
    message = format_alert(signal, risk)
    results: dict[str, bool] = {}

    if settings.telegram_bot_token:
        results["telegram"] = await send_telegram(message)
    if settings.discord_webhook_url:
        results["discord"] = await send_discord(message)

    return results
