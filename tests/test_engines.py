"""Basic tests for the engine modules."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.engines.ai_reasoning import AIReasoning
from app.engines.risk_management import RiskManagementEngine
from app.engines.setup_detection import SetupDetectionEngine
from app.engines.signal_ranking import SignalRankingEngine
from app.engines.technical_analysis import TechnicalAnalysisEngine
from app.models.signal import MarketType


def _make_candles(n: int = 200, trend: str = "up") -> pd.DataFrame:
    """Generate synthetic OHLCV data."""
    np.random.seed(42)
    base = 100.0
    prices = [base]
    for i in range(1, n):
        if trend == "up":
            change = np.random.normal(0.002, 0.01)
        elif trend == "down":
            change = np.random.normal(-0.002, 0.01)
        else:
            change = np.random.normal(0, 0.01)
        prices.append(prices[-1] * (1 + change))

    close = np.array(prices)
    high = close * (1 + np.abs(np.random.normal(0, 0.005, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.005, n)))
    open_ = close * (1 + np.random.normal(0, 0.003, n))
    volume = np.random.uniform(1000, 10000, n)

    df = pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )
    df.index = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
    return df


class TestTechnicalAnalysis:
    def test_analyze_returns_result(self) -> None:
        df = _make_candles(200, "up")
        engine = TechnicalAnalysisEngine()
        result = engine.analyze(df, "BTC/USDT", "4h")
        assert result is not None
        assert result.symbol == "BTC/USDT"
        assert result.timeframe == "4h"
        assert result.current_price > 0

    def test_analyze_short_data_returns_none(self) -> None:
        df = _make_candles(10)
        engine = TechnicalAnalysisEngine()
        result = engine.analyze(df, "BTC/USDT", "4h")
        assert result is None

    def test_rsi_in_range(self) -> None:
        df = _make_candles(200, "up")
        engine = TechnicalAnalysisEngine()
        result = engine.analyze(df, "BTC/USDT", "4h")
        assert result is not None
        assert 0 <= result.rsi <= 100

    def test_ema_values(self) -> None:
        df = _make_candles(200, "up")
        engine = TechnicalAnalysisEngine()
        result = engine.analyze(df, "BTC/USDT", "4h")
        assert result is not None
        assert result.ema_20 > 0
        assert result.ema_50 > 0


class TestSetupDetection:
    def test_detect_returns_list(self) -> None:
        df = _make_candles(200, "up")
        ta_engine = TechnicalAnalysisEngine()
        ta = ta_engine.analyze(df, "BTC/USDT", "4h")
        assert ta is not None

        detection = SetupDetectionEngine()
        setups = detection.detect_setups(ta, None, "binance", MarketType.SPOT)
        assert isinstance(setups, list)

    def test_setups_have_required_fields(self) -> None:
        df = _make_candles(200, "up")
        ta_engine = TechnicalAnalysisEngine()
        ta = ta_engine.analyze(df, "BTC/USDT", "4h")
        assert ta is not None

        detection = SetupDetectionEngine()
        setups = detection.detect_setups(ta, None, "binance", MarketType.SPOT)
        for setup in setups:
            assert setup.symbol == "BTC/USDT"
            assert setup.rr_ratio >= 2.0
            assert len(setup.confluence_factors) >= 2
            assert setup.invalidation


class TestSignalRanking:
    def test_ranking_produces_scores(self) -> None:
        df = _make_candles(200, "up")
        ta_engine = TechnicalAnalysisEngine()
        ta = ta_engine.analyze(df, "BTC/USDT", "4h")
        assert ta is not None

        detection = SetupDetectionEngine()
        setups = detection.detect_setups(ta, None, "binance", MarketType.SPOT)
        if not setups:
            pytest.skip("No setups detected in synthetic data")

        reasoning = AIReasoning(
            explanation="Test",
            confidence_adjustment=0,
            risk_summary="Test risk",
            market_context="Test context",
        )

        ranking = SignalRankingEngine()
        ranked = ranking.rank(setups[0], reasoning)
        assert 0 <= ranked.quality_score <= 100
        assert 0 <= ranked.confidence <= 100
        assert ranked.final_score > 0


class TestRiskManagement:
    def test_rejects_low_rr(self) -> None:
        df = _make_candles(200, "up")
        ta_engine = TechnicalAnalysisEngine()
        ta = ta_engine.analyze(df, "BTC/USDT", "4h")
        assert ta is not None

        detection = SetupDetectionEngine()
        setups = detection.detect_setups(ta, None, "binance", MarketType.SPOT)
        if not setups:
            pytest.skip("No setups detected")

        # Artificially set low RR
        setups[0].rr_ratio = 1.0

        reasoning = AIReasoning(
            explanation="Test",
            confidence_adjustment=0,
            risk_summary="Test",
            market_context="Test",
        )
        ranking = SignalRankingEngine()
        ranked = ranking.rank(setups[0], reasoning)

        risk_engine = RiskManagementEngine()
        assessment = risk_engine.assess(ranked)
        assert not assessment.approved
