"""AI Reasoning Layer — uses LLMs ONLY for summarization, reasoning, and explanation.

The AI MUST NEVER:
- Blindly predict prices
- Hallucinate certainty
- Generate emotional hype
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

import httpx

from app.core.config import settings
from app.engines.market_data import GlobalMarketData
from app.engines.setup_detection import SetupCandidate

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior crypto market analyst assistant. Your role is to explain
trade setups that have been detected by a deterministic rule-based system.

Rules:
- NEVER predict prices with certainty
- NEVER generate hype or emotional language
- NEVER hallucinate data you don't have
- ALWAYS explain the reasoning behind the setup
- ALWAYS mention what would invalidate the setup
- ALWAYS be balanced — mention both bullish and bearish factors
- Keep explanations concise and professional
- Focus on confluence and risk/reward
"""


@dataclass
class AIReasoning:
    explanation: str
    confidence_adjustment: int  # -20 to +20
    risk_summary: str
    market_context: str


class AIReasoningEngine:
    """Generates setup explanations using configured AI provider."""

    async def explain_setup(
        self,
        setup: SetupCandidate,
        market_data: GlobalMarketData | None = None,
    ) -> AIReasoning:
        prompt = self._build_prompt(setup, market_data)

        try:
            if settings.ai_provider == "openai" and settings.openai_api_key:
                return await self._call_openai(prompt)
            elif settings.ai_provider == "anthropic" and settings.anthropic_api_key:
                return await self._call_anthropic(prompt)
            elif settings.ai_provider == "gemini" and settings.gemini_api_key:
                return await self._call_gemini(prompt)
            else:
                return self._fallback_reasoning(setup)
        except Exception:
            logger.exception("AI reasoning failed, using fallback")
            return self._fallback_reasoning(setup)

    def _build_prompt(self, setup: SetupCandidate, market_data: GlobalMarketData | None) -> str:
        parts = [
            f"Analyze this {setup.setup_type.value} setup for {setup.symbol}:",
            f"Direction: {setup.direction.value.upper()}",
            f"Market type: {setup.market_type.value}",
            f"Timeframe: {setup.timeframe}",
            f"Entry zone: {setup.entry_low:.4f} - {setup.entry_high:.4f}",
            f"Stop loss: {setup.stop_loss:.4f}",
            f"TP1: {setup.tp1:.4f}",
            f"R:R ratio: {setup.rr_ratio}",
            "",
            "Confluence factors:",
        ]
        for f in setup.confluence_factors:
            parts.append(f"  - {f}")

        if setup.risk_factors:
            parts.append("\nRisk factors:")
            for r in setup.risk_factors:
                parts.append(f"  - {r}")

        parts.append(f"\nInvalidation: {setup.invalidation}")

        if market_data:
            parts.extend(
                [
                    "\nMarket context:",
                    f"  BTC: ${market_data.btc_price:,.0f}",
                    f"  BTC Dominance: {market_data.btc_dominance:.1f}%",
                    f"  Fear & Greed: {market_data.fear_greed_index or 'N/A'}",
                    f"  Market trend: {market_data.market_trend}",
                ]
            )

        parts.extend(
            [
                "",
                "Provide a JSON response with these fields:",
                '  "explanation": brief explanation of why this setup exists (2-4 sentences)',
                '  "confidence_adjustment": integer from -20 to +20 adjusting confidence',
                '  "risk_summary": key risks in 1-2 sentences',
                '  "market_context": how market conditions affect this setup (1-2 sentences)',
            ]
        )
        return "\n".join(parts)

    async def _call_openai(self, prompt: str) -> AIReasoning:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"},
                },
            )
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return self._parse_response(content)

    async def _call_anthropic(self, prompt: str) -> AIReasoning:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 512,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            data = resp.json()
            content = data["content"][0]["text"]
            return self._parse_response(content)

    async def _call_gemini(self, prompt: str) -> AIReasoning:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.gemini_api_key}",
                json={
                    "contents": [{"parts": [{"text": f"{SYSTEM_PROMPT}\n\n{prompt}"}]}],
                    "generationConfig": {"temperature": 0.3},
                },
            )
            data = resp.json()
            content = data["candidates"][0]["content"]["parts"][0]["text"]
            return self._parse_response(content)

    @staticmethod
    def _parse_response(content: str) -> AIReasoning:
        # Try to extract JSON from the response
        try:
            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            parsed = json.loads(content.strip())
            return AIReasoning(
                explanation=parsed.get("explanation", ""),
                confidence_adjustment=max(
                    -20, min(20, int(parsed.get("confidence_adjustment", 0)))
                ),
                risk_summary=parsed.get("risk_summary", ""),
                market_context=parsed.get("market_context", ""),
            )
        except (json.JSONDecodeError, KeyError, IndexError):
            return AIReasoning(
                explanation=content[:500] if content else "AI analysis unavailable",
                confidence_adjustment=0,
                risk_summary="Unable to parse structured risk assessment",
                market_context="Unable to parse market context",
            )

    @staticmethod
    def _fallback_reasoning(setup: SetupCandidate) -> AIReasoning:
        confluence_text = ", ".join(setup.confluence_factors[:3])
        risk_text = (
            ", ".join(setup.risk_factors[:2]) if setup.risk_factors else "Standard market risk"
        )

        return AIReasoning(
            explanation=(
                f"{setup.setup_type.value.replace('_', ' ').title()} detected on {setup.symbol} "
                f"({setup.timeframe}). Key confluence: {confluence_text}. "
                f"R:R ratio of {setup.rr_ratio} with clear invalidation level."
            ),
            confidence_adjustment=0,
            risk_summary=risk_text,
            market_context="AI reasoning unavailable — using deterministic analysis only.",
        )
