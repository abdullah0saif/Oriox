---
name: testing-oriox
description: Test the Oriox crypto setup hunter system end-to-end. Use when verifying API, scan pipeline, or dashboard UI changes.
---

# Testing Oriox

## Prerequisites

- Python 3.11+ with the project installed: `pip install -e ".[dev,ai]"`
- Node.js for frontend: `cd frontend && npm install`
- No database (PostgreSQL/Redis) needed for API testing — scan/backtest endpoints work in-memory via CCXT
- No exchange API keys needed — CCXT public endpoints work without auth for OHLCV data
- No AI API keys needed — AI reasoning gracefully falls back to deterministic summaries

## Environment Constraints

- **Binance and Bybit APIs may be geo-blocked** from certain cloud/VM IPs. If you get 451 or 403 errors from these exchanges, use `exchange=mexc` instead — MEXC is generally accessible.
- CoinGecko global market data (BTC price, dominance, Fear & Greed) works from any IP without auth.
- When testing with a geo-blocked exchange, `symbols_scanned` will be 0 but `btc_price` will still be populated (from CoinGecko). This is expected behavior, not a bug.

## Starting the Servers

### Backend API
```bash
cd /home/ubuntu/Oriox
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Frontend Dev Server
```bash
cd /home/ubuntu/Oriox/frontend
npx vite --port 3000 --host 0.0.0.0
```

The Vite dev server proxies `/api` requests to `http://localhost:8000`.

## API Testing

### Health Check
```bash
curl http://localhost:8000/api/health
```
Expect: `{"status": "ok", "version": "0.1.0", "timestamp": "..."}`

### Market Scan (primary endpoint)
```bash
curl "http://localhost:8000/api/setups/scan?exchange=mexc&timeframe=4h&include_futures=false"
```
Expect: JSON with `symbols_scanned > 0`, `signals` array, `btc_price > 0`, `market_trend` in (bullish/bearish/neutral). First scan takes ~8-10s (CCXT needs to load markets). Subsequent scans are faster (~2-3s).

### Signal Validation Checklist
For each signal in the response, verify:
- `symbol` matches `XXX/USDT` pattern
- `direction` is "long" or "short"
- `entry_low < entry_high`
- For longs: `stop_loss < entry_low` and `tp1 > entry_high`
- `rr_ratio >= 2.0` (enforced minimum)
- `confidence` between 0 and 100
- `confluence_factors` has >= 2 items
- `invalidation` and `explanation` are non-empty strings
- `risk_approved` is true

### Backtest
```bash
curl -X POST "http://localhost:8000/api/backtest/run" \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTC/USDT", "exchange": "mexc", "timeframe": "4h", "limit": 500}'
```
Expect: JSON with `total_trades >= 0`, `wins + losses + expired == total_trades`, `win_rate` between 0-100.

### Market Overview
```bash
curl http://localhost:8000/api/market/overview
```

## UI Testing

1. Navigate to `http://localhost:3000`
2. Verify initial state: "Oriox" header, exchange/timeframe dropdowns, "Scan Market" button, placeholder text
3. Change exchange to MEXC (or whichever exchange is accessible)
4. Click "Scan Market" — button should change to "Scanning..."
5. After completion: Market overview cards appear (BTC Price, Dominance, Fear & Greed, Trend, Breadth, Scan Results)
6. Setup list shows "Detected Setups (N)" with scrollable rows
7. Click a setup row — detail panel shows scores, trade levels, confluence factors, AI analysis, risks, invalidation, risk management

## Unit Tests
```bash
cd /home/ubuntu/Oriox
python -m pytest tests/ -v
```
8 unit tests covering TA engine, setup detection, signal ranking, risk management.

## Linting
```bash
ruff check app/ tests/
ruff format --check app/ tests/
```

## Common Issues

- **0 symbols scanned**: Exchange API is geo-blocked. Switch to MEXC.
- **Slow first scan**: CCXT loads exchange markets on first call. Subsequent scans are faster.
- **No AI analysis text**: No LLM API key configured. System falls back to deterministic summaries — this is expected.
- **Frontend build warnings about CommonJS/ESM**: Harmless Vite warning about loading ESM via require(). Does not affect functionality.

## Devin Secrets Needed

No secrets are required for basic testing. Optional secrets for enhanced functionality:
- `OPENAI_API_KEY` — for AI reasoning layer (falls back to deterministic without it)
- `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` — for alert testing
- `DISCORD_WEBHOOK_URL` — for Discord alert testing
