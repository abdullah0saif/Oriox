"""News & Sentiment Engine — collects and scores market sentiment."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass
class SentimentResult:
    symbol: str | None
    source: str
    score: float  # -1.0 (extreme fear) to 1.0 (extreme greed)
    summary: str
    narratives: list[str]
    article_count: int


class SentimentEngine:
    """Collects sentiment data from CryptoPanic and public APIs.

    Sentiment is supplementary — it must NOT override technical structure.
    """

    CRYPTOPANIC_URL = "https://cryptopanic.com/api/v1/posts/"

    def __init__(self, cryptopanic_api_key: str = "") -> None:
        self.cryptopanic_api_key = cryptopanic_api_key

    async def fetch_cryptopanic(
        self, symbol: str | None = None, limit: int = 20
    ) -> SentimentResult:
        if not self.cryptopanic_api_key:
            return SentimentResult(
                symbol=symbol,
                source="cryptopanic",
                score=0.0,
                summary="No API key configured",
                narratives=[],
                article_count=0,
            )

        params: dict[str, str | int] = {
            "auth_token": self.cryptopanic_api_key,
            "public": "true",
            "kind": "news",
        }
        if symbol:
            clean = symbol.replace("/USDT", "").replace("/", "")
            params["currencies"] = clean

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(self.CRYPTOPANIC_URL, params=params)
                if resp.status_code != 200:
                    return SentimentResult(
                        symbol=symbol,
                        source="cryptopanic",
                        score=0.0,
                        summary="API error",
                        narratives=[],
                        article_count=0,
                    )
                data = resp.json()
                posts = data.get("results", [])[:limit]
        except Exception:
            logger.exception("CryptoPanic fetch failed")
            return SentimentResult(
                symbol=symbol,
                source="cryptopanic",
                score=0.0,
                summary="Fetch error",
                narratives=[],
                article_count=0,
            )

        bullish = sum(1 for p in posts if _vote_sentiment(p) > 0)
        bearish = sum(1 for p in posts if _vote_sentiment(p) < 0)
        total = len(posts) or 1
        score = (bullish - bearish) / total

        titles = [p.get("title", "") for p in posts[:5]]
        narratives = _extract_narratives(titles)

        summary_parts = [f"{bullish} bullish, {bearish} bearish out of {len(posts)} articles"]
        if narratives:
            summary_parts.append(f"Narratives: {', '.join(narratives[:3])}")

        return SentimentResult(
            symbol=symbol,
            source="cryptopanic",
            score=round(score, 2),
            summary=" | ".join(summary_parts),
            narratives=narratives,
            article_count=len(posts),
        )

    async def fetch_fear_greed(self) -> int | None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get("https://api.alternative.me/fng/?limit=1")
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    if data:
                        return int(data[0].get("value", 50))
        except Exception:
            logger.exception("Fear & Greed fetch failed")
        return None

    async def get_market_sentiment(self) -> SentimentResult:
        return await self.fetch_cryptopanic(symbol=None)


def _vote_sentiment(post: dict) -> int:
    votes = post.get("votes", {})
    positive = votes.get("positive", 0) + votes.get("liked", 0)
    negative = votes.get("negative", 0) + votes.get("disliked", 0)
    if positive > negative:
        return 1
    if negative > positive:
        return -1
    return 0


def _extract_narratives(titles: list[str]) -> list[str]:
    keywords_map = {
        "AI": ["ai", "artificial intelligence", "machine learning"],
        "DeFi": ["defi", "decentralized finance", "dex", "lending"],
        "L2": ["layer 2", "l2", "rollup", "optimism", "arbitrum"],
        "Meme": ["meme", "doge", "shib", "pepe", "bonk", "wif"],
        "RWA": ["rwa", "real world asset", "tokeniz"],
        "Gaming": ["gaming", "gamefi", "metaverse"],
        "Regulation": ["sec", "regulation", "etf", "approval"],
        "Bitcoin ETF": ["bitcoin etf", "btc etf", "spot etf"],
    }
    found: list[str] = []
    combined = " ".join(titles).lower()
    for narrative, kws in keywords_map.items():
        if any(kw in combined for kw in kws):
            found.append(narrative)
    return found
