# Kalshi Quant Auto-Trader (minimal, extensible)

This is a **starter codebase** for a production-ish quant trading system on Kalshi:
- Public market data (markets / orderbook)
- Authenticated portfolio + order execution
- Risk checks (position + max loss caps)
- Strategy plug-in interface (your model goes here)
- Demo environment support (recommended)

## 0) Important
This repo is **not financial advice**. Use the **demo environment** first. You are responsible for complying with Kalshi's rules and your local laws.

## 1) Setup (Demo strongly recommended)
Kalshi provides a demo environment with mock funds and separate credentials. Demo API root:
`https://demo-api.kalshi.co/trade-api/v2` (see docs). 

### Create API keys
In Kalshi UI: Account settings → API keys → create key. You'll get:
- API Key ID (UUID-like)
- Private key file (.key/.pem). Store it securely.

## 2) Install
Python 3.10+

```bash
python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
```

## 3) Configure
Copy `.env.example` to `.env` and fill values:

- `KALSHI_ENV=demo` or `prod`
- `KALSHI_API_KEY_ID=...`
- `KALSHI_PRIVATE_KEY_PATH=/path/to/private_key.pem`
- `TICKERS=FED-23DEC-T3.00,ANOTHER-TICKER`  (comma-separated)
- Optional: `FAIR_PROBS_JSON={"FED-23DEC-T3.00": 0.42}` (used as your model prior)

Fee-aware settings (recommended so you don't mistake micro-edges for alpha):
- `FEE_KIND=taker|maker|none` (default: taker)
- `TAKER_FEE_RATE=0.07`, `MAKER_FEE_RATE=0.0175` (override if Kalshi updates)
- `MIN_NET_EV_PER_CONTRACT=0.00` (raise this to be conservative)
- `POST_ONLY=true` (maker-style) or `POST_ONLY=false` (cross spread)

Optional sports/in-play hook:
- `USE_LIVE_DATA=true` enables a **toy** in-play win-prob provider based on Kalshi milestones + live_data.
  You'll want to replace/tune the coefficients after backtesting.

## 4) Run (paper or live)
Paper mode (no orders submitted):
```bash
python -m kalshi_bot.run --paper
```

Live mode (submits orders):
```bash
python -m kalshi_bot.run
```

## 5) How it works (high level)
- Polls orderbooks for configured tickers.
- Computes best bid/ask using Kalshi's **reciprocal orderbook** rules.
- Calls a Strategy to generate target orders.
- Risk module approves/rejects orders.
- Executor submits/cancels orders via authenticated REST.

## 6) Next upgrades (recommended)
- Replace polling with WebSocket orderbook deltas (see Kalshi WebSocket docs).
- Implement your real sports win-prob model + external odds ingestion.
- Persist fills/orders in Postgres + add dashboard/alerts.
- Add unit tests for strategy + risk.

