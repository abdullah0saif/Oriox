"""Oriox — AI-powered crypto market setup hunter."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import backtest, dashboard, market, setups
from app.core.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Oriox",
    description="AI-powered crypto market setup hunter — confluence-based trade setup detection",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(setups.router)
app.include_router(market.router)
app.include_router(backtest.router)
app.include_router(dashboard.router)


@app.get("/api/health")
async def health() -> dict:
    """Health check endpoint."""
    import datetime

    return {
        "status": "ok",
        "version": "0.1.0",
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    }


@app.on_event("shutdown")
async def shutdown() -> None:
    # Clean up scanner connections
    from app.api.routes.setups import _scanner

    if _scanner:
        await _scanner.shutdown()
