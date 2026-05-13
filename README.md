# Oriox — AI-Powered Crypto Market Setup Hunter

A modular, confluence-based crypto trade setup detection system that scans markets in real time, identifies high-probability setups, and delivers structured, explainable alerts.

**This is NOT a trading bot.** It is an intelligence tool that helps you find A+ setups with clear reasoning, risk management, and invalidation levels.

## Core Principles

- **Setup quality over quantity** — only A+ setups with strong confluence
- **Explainability over blind signals** — every signal includes reasoning and invalidation
- **Deterministic detection** — setup logic is rule-based, AI is only used for explanation
- **Risk-first approach** — position sizing, leverage safety, and drawdown tracking built in

## Architecture

```
┌──────────────┐     ┌─────────────┐     ┌──────────────────┐
│  Market Data │────▶│  Technical  │────▶│  Setup Detection │
│    Engine    │     │  Analysis   │     │    (Rules-based) │
│  (CCXT/WS)  │     │   Engine    │     └────────┬─────────┘
└──────────────┘     └─────────────┘              │
                                                  ▼
┌──────────────┐     ┌─────────────┐     ┌──────────────────┐
│   Futures    │────▶│  AI Reason  │◀────│  Signal Ranking  │
│   Metrics    │     │   Layer     │     │    System        │
└──────────────┘     └─────────────┘     └────────┬─────────┘
                                                  │
┌──────────────┐     ┌─────────────┐              ▼
│  Sentiment   │     │    Risk     │     ┌──────────────────┐
│   Engine     │     │ Management  │◀────│   Alerting       │
└──────────────┘     └─────────────┘     │ (TG / Discord)   │
                                         └──────────────────┘
```

### Modules

| Module | Description |
|--------|-------------|
| **Market Data Engine** | Collects OHLCV, tickers, global data via CCXT (Binance, Bybit, MEXC) |
| **Technical Analysis Engine** | S/R, EMAs, RSI, ATR, VWAP, breakout detection, divergences |
| **Futures Metrics Engine** | Funding rates, OI, liquidations, squeeze probability |
| **Setup Detection Engine** | Deterministic rules for 9 setup types (spot + futures) |
| **AI Reasoning Layer** | LLM-powered explanation of why setups exist (OpenAI/Anthropic/Gemini) |
| **Signal Ranking System** | Multi-dimensional scoring (quality, confluence, risk, market) |
| **Risk Management Layer** | Position sizing, leverage safety, RR validation |
| **Alerting System** | Telegram and Discord structured alerts |
| **Backtesting Engine** | Historical replay for strategy evaluation |
| **Dashboard** | React UI with market overview and setup details |

## Supported Setup Types

### Spot
- Accumulation Breakout
- Trend Continuation
- Volume Expansion
- Narrative Rotation

### Futures
- Breakout + Volume Confirmation
- Liquidity Sweep Reversal
- Trend Continuation
- Funding Reset Entry
- Short/Long Squeeze
- Pullback Entry

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI |
| Data | Pandas, NumPy, CCXT, ta |
| Database | PostgreSQL (via SQLAlchemy async), Redis |
| AI | OpenAI, Anthropic, Google Gemini (configurable) |
| Frontend | React 18, Vite, Lightweight Charts |
| Alerting | Telegram Bot API, Discord Webhooks |
| Deployment | Docker, Docker Compose |

## Quick Start

### 1. Clone & Configure

```bash
git clone https://github.com/abdullah0saif/Oriox.git
cd Oriox
cp .env.example .env
# Edit .env with your API keys
```

### 2. Start with Docker Compose

```bash
docker compose up -d
```

This starts:
- **PostgreSQL** on port 5432
- **Redis** on port 6379
- **API server** on port 8000
- **Scanner worker** (periodic scans)

### 3. Manual Setup (without Docker)

```bash
# Backend
pip install -e ".[dev,ai]"
uvicorn app.main:app --reload --port 8000

# Scanner worker (separate terminal)
python -m app.workers.scanner_worker

# Frontend
cd frontend
npm install
npm run dev
```

### 4. Run a Scan

```bash
# Via API
curl http://localhost:8000/api/setups/scan?exchange=binance&timeframe=4h

# Trigger scan with alerts
curl -X POST http://localhost:8000/api/setups/scan/alert
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/setups/scan` | Run market scan |
| POST | `/api/setups/scan/alert` | Scan + send alerts |
| GET | `/api/market/overview` | Global market data |
| GET | `/api/market/candles` | OHLCV candle data |
| GET | `/api/market/tickers` | Current tickers |
| POST | `/api/backtest/run` | Run backtest |
| GET | `/api/dashboard/summary` | Dashboard data |

## Alert Format

```
🟢 ETHUSDT — LONG
Setup: Breakout Volume
Market: FUTURES | Exchange: binance
Timeframe: 4h

ENTRY: 2450.0000 — 2470.0000
STOP LOSS: 2380.0000
TP1: 2550.0000
TP2: 2620.0000
TP3: 2700.0000

R:R: 2.8
Confidence: 78%
Quality: 72 | Confluence: 80

WHY THIS SETUP EXISTS:
  • Strong breakout retest
  • Bullish structure intact
  • Volume expansion confirmed
  • Funding reset healthy

AI Analysis: ETH shows a clean breakout retest on the 4H
with bullish EMA alignment and healthy funding...

RISKS:
  ⚠ BTC weakness could invalidate move
  ⚠ Resistance overhead near 2620

Invalidation: Close below 2380.0000

Position Size: 2.5% of portfolio
Suggested Leverage: 3x
Max Loss: 1.0%
```

## Configuration

All settings in `.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `SCANNER_INTERVAL_SECONDS` | Scan frequency | 300 (5 min) |
| `MIN_SETUP_CONFIDENCE` | Minimum confidence to alert | 65 |
| `MIN_RR_RATIO` | Minimum risk/reward ratio | 2.0 |
| `AI_PROVIDER` | LLM provider | openai |

## Project Structure

```
Oriox/
├── app/
│   ├── api/           # FastAPI routes
│   │   └── routes/    # setups, market, backtest, dashboard
│   ├── core/          # config, database
│   ├── engines/       # market_data, ta, futures, setup_detection,
│   │                  # ai_reasoning, signal_ranking, risk_management
│   ├── models/        # SQLAlchemy models
│   ├── services/      # scanner, alerting, backtesting
│   └── workers/       # scanner_worker
├── frontend/          # React dashboard
├── alembic/           # DB migrations
├── tests/
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

## Database Schema

- `ohlcv_candles` — historical OHLCV data
- `signals` — detected trade setups with full metadata
- `signal_performance` — outcome tracking for evaluation
- `market_state` — BTC dominance, breadth, trend snapshots
- `futures_metrics` — funding, OI, liquidation data
- `sentiment_snapshots` — news & social sentiment

## Deployment

### Cloud Recommendations

- **Compute**: Any VPS (2 vCPU, 4GB RAM minimum)
- **Database**: Managed PostgreSQL (Supabase, Neon, RDS)
- **Cache**: Managed Redis (Upstash, ElastiCache)
- **Container**: Docker on Fly.io, Railway, or DigitalOcean

### Security

- API keys stored in `.env` (never committed)
- No auto-trading — read-only exchange access sufficient
- CORS configured for frontend origin in production
- Rate limiting on exchange APIs via CCXT built-in

## Disclaimer

This system is for **personal educational use only**. It does not guarantee profits. Always do your own research before trading. The authors are not responsible for any financial losses.
