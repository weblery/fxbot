# 🧠 FOREXBOT

A modular, rule-based Forex trading decision engine.

## Architecture

```
Data Layer → Strategy Engine → Risk Manager → Execution → Analytics
```

**Strategy v1**: EMA trend (H4) + EMA pullback (H1) + ATR exits — 3 degrees of freedom, locked.

## Quick Start

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Configure
cp .env.example .env
# Edit .env with your MT5 credentials

# 4. Run backtest
python scripts/run_backtest.py

# 5. Run tests
pytest tests/ -v
```

## Project Structure

```
app/
├── core/          # Config, constants, logging
├── models/        # TradeIdea, TradeResult, Signal, Position
├── data/          # MT5 client, data fetching, storage
├── strategy/      # Trend, pullback, ATR, entry, exit, engine
├── risk/          # Position sizing, risk validation, drawdown
├── backtesting/   # Engine, simulator, metrics, reports
├── execution/     # Broker ABC, MT5 implementation (Phase 3)
├── signals/       # Signal generation pipeline (Phase 2)
├── analytics/     # Trade journal, performance (Phase 2)
├── services/      # Telegram, scheduler, API (Phase 2/3)
└── utils/         # Pip math, time helpers, decorators
```

## Design Principles

1. **Separation of concerns** — each module does ONE thing
2. **Deterministic logic** — no guessing, no hidden behavior
3. **Config-driven** — zero hardcoded strategy parameters
4. **No data leakage** — closed candles only, entry on next open
5. **Realistic backtesting** — spread, slippage, candle ambiguity modes
6. **Logging-first** — every decision is traceable via structured JSON

## Phases

- **Phase 1**: Data + Strategy + Risk + Backtesting ← current
- **Phase 2**: Signals + Analytics + Telegram
- **Phase 3**: Live Execution + Services
