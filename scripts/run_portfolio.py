#!/usr/bin/env python3
"""
FOREXBOT Master Portfolio Engine
Runs backtests across all configured symbols and aggregates results into a single portfolio view.
"""

import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import numpy as np
from loguru import logger

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.config import get_settings
from app.backtesting.engine import BacktestEngine
from app.data.storage import DataStorage
from app.core.constants import ExecutionMode

def main():
    # 1. Load configuration
    settings = get_settings()
    symbols = list(settings.symbols.keys())
    
    logger.info(f"🚀 Starting Master Portfolio Backtest for: {', '.join(symbols)}")
    
    all_trades = []
    portfolio_results = {}
    
    # 2. Setup Engine and Storage
    engine = BacktestEngine(settings)
    storage = DataStorage()
    
    for symbol in symbols:
        logger.info(f"🔍 Testing {symbol}...")
        try:
            # Load data
            h1_df = storage.load(symbol, settings.timeframes.execution)
            h4_df = storage.load(symbol, settings.timeframes.trend)
            
            if h1_df.empty or h4_df.empty:
                logger.warning(f"   ⚠️  Skipping {symbol}: Missing H1 or H4 data files.")
                continue
                
            # Run backtest
            result = engine.run(h1_df, h4_df, symbol)
            trades = result.trades
            
            all_trades.extend(trades)
            portfolio_results[symbol] = trades
            logger.info(f"   ✅ {symbol}: {len(trades)} trades")
        except Exception as e:
            logger.error(f"   ❌ Failed to test {symbol}: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            
    if not all_trades:
        logger.error("No trades found across any symbols. Check your data and strategy filters.")
        return

    # 3. Sort all trades by exit time to simulate portfolio equity
    all_trades.sort(key=lambda t: t.exit_time)
    
    # 4. Generate Master Portfolio Report
    logger.info("📊 Aggregating Portfolio Results...")
    
    # Calculate portfolio-wide metrics
    total_pnl = sum(t.pnl for t in all_trades)
    winners = [t for t in all_trades if t.pnl > 0]
    losers = [t for t in all_trades if t.pnl <= 0]
    win_rate = len(winners) / len(all_trades)
    
    # Profit Factor
    gross_profit = sum(t.pnl for t in winners)
    gross_loss = abs(sum(t.pnl for t in losers))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
    
    # Calculate average trades per week
    start_date = min(t.trade_idea.timestamp for t in all_trades)
    end_date = max(t.exit_time for t in all_trades)
    weeks = (end_date - start_date).days / 7
    trades_per_week = len(all_trades) / weeks if weeks > 0 else 0

    # 5. Print Portfolio Summary
    print("\n" + "═"*75)
    print(f"  FOREXBOT MASTER PORTFOLIO REPORT")
    print("═"*75)
    print(f"  Total Trades:    {len(all_trades):<10} | Trades/Week:     {trades_per_week:.2f}")
    print(f"  Win Rate:        {win_rate*100:.1f}%      | Profit Factor:   {profit_factor:.2f}")
    print(f"  Total PnL:       ${total_pnl:<10.2f} | Expected Value:  ${(total_pnl/len(all_trades)):.2f}")
    print(f"  Final Balance:   ${settings.backtest.initial_balance + total_pnl:<10.2f}")
    print("-" * 75)
    
    # Breakdown by symbol
    print(f"  {'Symbol':<10} | {'Trades':<8} | {'PnL (USD)':<12} | {'Win Rate':<8} | {'PF':<5}")
    print("-" * 75)
    for symbol, trades in portfolio_results.items():
        if not trades:
            continue
        s_pnl = sum(t.pnl for t in trades)
        s_winners = [t for t in trades if t.pnl > 0]
        s_losers = [t for t in trades if t.pnl <= 0]
        s_wr = len(s_winners) / len(trades)
        
        s_gp = sum(t.pnl for t in s_winners)
        s_gl = abs(sum(t.pnl for t in s_losers))
        s_pf = s_gp / s_gl if s_gl > 0 else float('inf')
        
        print(f"  {symbol:<10} | {len(trades):<8} | ${s_pnl:<11.2f} | {s_wr*100:>7.1f}% | {s_pf:.2f}")
    print("═"*75)

    # 6. Save combined results
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    master_log_path = output_dir / "portfolio_trades.csv"
    trade_dicts = []
    balance = settings.backtest.initial_balance
    
    for t in all_trades:
        balance += t.pnl
        d = {
            "entry_time": t.trade_idea.timestamp,
            "exit_time": t.exit_time,
            "symbol": t.trade_idea.symbol,
            "direction": t.trade_idea.direction.value,
            "entry_price": t.trade_idea.entry_price,
            "exit_price": t.exit_price,
            "pnl": round(t.pnl, 2) if t.pnl is not None else 0.0,
            "pnl_pips": round(t.pnl_pips, 1) if t.pnl_pips is not None else 0.0,
            "portfolio_balance": round(balance, 2)
        }
        trade_dicts.append(d)
        
    df = pd.DataFrame(trade_dicts)
    df.to_csv(master_log_path, index=False)
    
    logger.info(f"✅ Master Portfolio Trade Log saved to: {master_log_path}")
    logger.info("Done.")

if __name__ == "__main__":
    main()
