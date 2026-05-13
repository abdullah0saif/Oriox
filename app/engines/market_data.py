"""Market Data Engine — collects OHLCV, price, volume, and global metrics via CCXT."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import ccxt.async_support as ccxt
import httpx
import pandas as pd

logger = logging.getLogger(__name__)

SUPPORTED_EXCHANGES: dict[str, type[ccxt.Exchange]] = {
    "binance": ccxt.binance,
    "bybit": ccxt.bybit,
    "mexc": ccxt.mexc,
}

DEFAULT_TIMEFRAMES = ["15m", "1h", "4h", "1d"]

TOP_SYMBOLS = [
    "BTC/USDT",
    "ETH/USDT",
    "SOL/USDT",
    "BNB/USDT",
    "XRP/USDT",
    "DOGE/USDT",
    "ADA/USDT",
    "AVAX/USDT",
    "DOT/USDT",
    "LINK/USDT",
    "MATIC/USDT",
    "UNI/USDT",
    "ATOM/USDT",
    "LTC/USDT",
    "FIL/USDT",
    "APT/USDT",
    "ARB/USDT",
    "OP/USDT",
    "SUI/USDT",
    "INJ/USDT",
    "TIA/USDT",
    "SEI/USDT",
    "NEAR/USDT",
    "FET/USDT",
    "RENDER/USDT",
    "WIF/USDT",
    "PEPE/USDT",
    "BONK/USDT",
    "JUP/USDT",
    "AAVE/USDT",
]


@dataclass
class CandleData:
    exchange: str
    symbol: str
    timeframe: str
    df: pd.DataFrame


@dataclass
class GlobalMarketData:
    btc_dominance: float = 0.0
    total_market_cap: float = 0.0
    btc_price: float = 0.0
    eth_price: float = 0.0
    fear_greed_index: int | None = None
    market_trend: str = "neutral"
    breadth_bullish_pct: float = 50.0


@dataclass
class MarketDataEngine:
    """Fetches OHLCV candles and global market data from exchanges."""

    api_keys: dict[str, dict[str, str]] = field(default_factory=dict)
    symbols: list[str] = field(default_factory=lambda: list(TOP_SYMBOLS))
    timeframes: list[str] = field(default_factory=lambda: list(DEFAULT_TIMEFRAMES))
    exchanges: dict[str, Any] = field(default_factory=dict, init=False)

    async def init_exchanges(self) -> None:
        for name, cls in SUPPORTED_EXCHANGES.items():
            keys = self.api_keys.get(name, {})
            self.exchanges[name] = cls(
                {
                    "apiKey": keys.get("api_key", ""),
                    "secret": keys.get("api_secret", ""),
                    "enableRateLimit": True,
                    "options": {"defaultType": "spot"},
                }
            )
        logger.info("Initialized %d exchanges", len(self.exchanges))

    async def close(self) -> None:
        for exchange in self.exchanges.values():
            await exchange.close()

    async def fetch_ohlcv(
        self,
        exchange_name: str,
        symbol: str,
        timeframe: str,
        limit: int = 200,
    ) -> CandleData | None:
        exchange = self.exchanges.get(exchange_name)
        if not exchange:
            return None
        try:
            raw = await exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            if not raw:
                return None
            df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            df.set_index("timestamp", inplace=True)
            return CandleData(exchange=exchange_name, symbol=symbol, timeframe=timeframe, df=df)
        except Exception:
            logger.exception("Failed to fetch %s %s %s", exchange_name, symbol, timeframe)
            return None

    async def fetch_all_candles(
        self,
        exchange_name: str = "binance",
        timeframe: str = "4h",
    ) -> list[CandleData]:
        tasks = [self.fetch_ohlcv(exchange_name, sym, timeframe) for sym in self.symbols]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

    async def fetch_ticker(self, exchange_name: str, symbol: str) -> dict[str, Any] | None:
        exchange = self.exchanges.get(exchange_name)
        if not exchange:
            return None
        try:
            return await exchange.fetch_ticker(symbol)
        except Exception:
            logger.exception("Failed to fetch ticker %s %s", exchange_name, symbol)
            return None

    async def fetch_global_market_data(self) -> GlobalMarketData:
        data = GlobalMarketData()
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get("https://api.coingecko.com/api/v3/global")
                if resp.status_code == 200:
                    g = resp.json().get("data", {})
                    data.btc_dominance = g.get("market_cap_percentage", {}).get("btc", 0.0)
                    data.total_market_cap = g.get("total_market_cap", {}).get("usd", 0.0)

                btc_resp = await client.get(
                    "https://api.coingecko.com/api/v3/simple/price",
                    params={"ids": "bitcoin,ethereum", "vs_currencies": "usd"},
                )
                if btc_resp.status_code == 200:
                    prices = btc_resp.json()
                    data.btc_price = prices.get("bitcoin", {}).get("usd", 0.0)
                    data.eth_price = prices.get("ethereum", {}).get("usd", 0.0)

                fg_resp = await client.get("https://api.alternative.me/fng/?limit=1")
                if fg_resp.status_code == 200:
                    fg_data = fg_resp.json().get("data", [])
                    if fg_data:
                        data.fear_greed_index = int(fg_data[0].get("value", 50))
        except Exception:
            logger.exception("Failed to fetch global market data")
        return data

    async def compute_market_breadth(self, candles: list[CandleData]) -> float:
        """Percentage of symbols above their 20-EMA on the given candle data."""
        if not candles:
            return 50.0
        bullish = 0
        for c in candles:
            if len(c.df) < 20:
                continue
            ema20 = c.df["close"].ewm(span=20, adjust=False).mean()
            if c.df["close"].iloc[-1] > ema20.iloc[-1]:
                bullish += 1
        return round(bullish / len(candles) * 100, 1) if candles else 50.0
