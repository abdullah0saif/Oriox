"""Signal Ranking System — scores and ranks detected setups by quality."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.engines.ai_reasoning import AIReasoning
from app.engines.market_data import GlobalMarketData
from app.engines.setup_detection import SetupCandidate

logger = logging.getLogger(__name__)


@dataclass
class RankedSignal:
    """A fully scored and ranked setup ready for alerting."""

    setup: SetupCandidate
    reasoning: AIReasoning

    quality_score: float  # 0-100
    confidence: int  # 0-100
    confluence_score: float  # 0-100
    risk_score: float  # 0-100 (higher = more risky)
    market_condition_score: float  # 0-100
    final_score: float  # weighted composite


class SignalRankingEngine:
    """Scores each setup on multiple dimensions and produces a final rank."""

    WEIGHTS = {
        "quality": 0.25,
        "confluence": 0.30,
        "risk": 0.20,
        "market": 0.15,
        "confidence": 0.10,
    }

    def rank(
        self,
        setup: SetupCandidate,
        reasoning: AIReasoning,
        market_data: GlobalMarketData | None = None,
    ) -> RankedSignal:
        quality = self._score_quality(setup)
        confluence = self._score_confluence(setup)
        risk = self._score_risk(setup)
        market = self._score_market_conditions(setup, market_data)
        base_confidence = self._base_confidence(setup)
        confidence = max(0, min(100, base_confidence + reasoning.confidence_adjustment))

        final = (
            quality * self.WEIGHTS["quality"]
            + confluence * self.WEIGHTS["confluence"]
            + (100 - risk) * self.WEIGHTS["risk"]  # invert: low risk = good
            + market * self.WEIGHTS["market"]
            + confidence * self.WEIGHTS["confidence"]
        )

        return RankedSignal(
            setup=setup,
            reasoning=reasoning,
            quality_score=round(quality, 1),
            confidence=confidence,
            confluence_score=round(confluence, 1),
            risk_score=round(risk, 1),
            market_condition_score=round(market, 1),
            final_score=round(final, 1),
        )

    def rank_batch(
        self,
        setups_with_reasoning: list[tuple[SetupCandidate, AIReasoning]],
        market_data: GlobalMarketData | None = None,
    ) -> list[RankedSignal]:
        ranked = [self.rank(s, r, market_data) for s, r in setups_with_reasoning]
        ranked.sort(key=lambda r: r.final_score, reverse=True)
        return ranked

    @staticmethod
    def _score_quality(setup: SetupCandidate) -> float:
        score = 30.0  # lower base to spread scores

        # RR contribution — more granular
        if setup.rr_ratio >= 4.0:
            score += 30
        elif setup.rr_ratio >= 3.0:
            score += 22
        elif setup.rr_ratio >= 2.5:
            score += 15
        elif setup.rr_ratio >= 2.0:
            score += 8

        # Clean structure — confluence vs risk factors
        confluence_ratio = len(setup.confluence_factors) / max(
            1, len(setup.risk_factors) + len(setup.confluence_factors)
        )
        score += confluence_ratio * 25

        # Bonus for many confluence factors
        if len(setup.confluence_factors) >= 5:
            score += 10
        elif len(setup.confluence_factors) >= 4:
            score += 5

        # Penalize risk factors more
        score -= len(setup.risk_factors) * 8

        return max(0, min(100, score))

    @staticmethod
    def _score_confluence(setup: SetupCandidate) -> float:
        count = len(setup.confluence_factors)
        if count >= 6:
            return 95
        if count >= 5:
            return 85
        if count >= 4:
            return 72
        if count >= 3:
            return 55
        if count >= 2:
            return 35
        return 15

    @staticmethod
    def _score_risk(setup: SetupCandidate) -> float:
        score = 20.0  # base risk

        score += len(setup.risk_factors) * 15

        if setup.rr_ratio < 2.0:
            score += 20
        if setup.rr_ratio < 1.5:
            score += 20

        return min(100, score)

    @staticmethod
    def _score_market_conditions(
        setup: SetupCandidate, market_data: GlobalMarketData | None
    ) -> float:
        if not market_data:
            return 50  # neutral if unknown

        score = 50.0

        # Fear & Greed alignment
        if market_data.fear_greed_index is not None:
            fg = market_data.fear_greed_index
            if setup.direction.value == "long":
                if fg < 25:
                    score -= 10  # extreme fear — risky for longs
                elif fg > 60:
                    score += 10  # greed supports longs
            else:
                if fg > 75:
                    score -= 10
                elif fg < 40:
                    score += 10

        # Market trend alignment
        if market_data.market_trend == "bullish" and setup.direction.value == "long":
            score += 15
        elif market_data.market_trend == "bearish" and setup.direction.value == "short":
            score += 15
        elif market_data.market_trend == "bullish" and setup.direction.value == "short":
            score -= 10
        elif market_data.market_trend == "bearish" and setup.direction.value == "long":
            score -= 10

        # Breadth
        if market_data.breadth_bullish_pct > 60 and setup.direction.value == "long":
            score += 10
        elif market_data.breadth_bullish_pct < 40 and setup.direction.value == "short":
            score += 10

        return max(0, min(100, score))

    @staticmethod
    def _base_confidence(setup: SetupCandidate) -> int:
        base = 45  # lower base for more spread

        base += min(25, len(setup.confluence_factors) * 6)
        base -= min(25, len(setup.risk_factors) * 10)

        if setup.rr_ratio >= 4.0:
            base += 12
        elif setup.rr_ratio >= 3.0:
            base += 8
        elif setup.rr_ratio >= 2.5:
            base += 4

        return max(25, min(95, base))
