"""
Runs the full trendline-bounce backtest matrix:
  symbols x timeframes x stop_loss_methods x take_profit_methods

For each (timeframe, stop_loss_method, take_profit_method) combination,
aggregates trades across ALL symbols and reports one row -- per spec:
"For EACH timeframe, for EACH stop-loss method, for EACH take-profit
method, report [stats]."

Usage (from backend/ directory):
    python -m backtesting.run_backtest
    python -m backtesting.run_backtest --symbols BTCUSDT ETHUSDT --days 90
    python -m backtesting.run_backtest --entry-version B --min-quality 50
"""
import argparse
import asyncio
import copy
from typing import List, Dict

from app.market_data.base_exchange import Candle
from backtesting.config import BacktestConfig
from backtesting.data_loader import load_all
from backtesting.strategy_trendline_bounce import generate_signal
from backtesting.backtest_engine import run_single_backtest, Trade
from backtesting.metrics import compute_report
from backtesting.report import print_report, export_trades_csv


async def main(config: BacktestConfig):
    print(f"Loading historical data for {len(config.symbols)} symbols x {len(config.timeframes)} timeframes...")
    data: Dict[str, Dict[str, List[Candle]]] = await load_all(config.symbols, config.timeframes, config.history_days)

    all_trades_by_group: Dict[str, List[Trade]] = {}
    all_trades_flat: List[Trade] = []

    for timeframe in config.timeframes:
        for sl_method in config.stop_loss_methods:
            for tp_method in config.take_profit_methods:
                group_key = f"{timeframe} | SL={sl_method} | TP={tp_method}"
                group_trades: List[Trade] = []

                run_config = copy.deepcopy(config)
                run_config.stop_loss.method = sl_method
                run_config.take_profit.method = tp_method

                for symbol in config.symbols:
                    candles = data[symbol][timeframe]
                    if len(candles) < config.trendline.lookback_bars:
                        continue
                    trades = run_single_backtest(candles, symbol, timeframe, run_config, generate_signal)
                    group_trades.extend(trades)

                all_trades_by_group[group_key] = group_trades
                all_trades_flat.extend(group_trades)
                print(f"  {group_key}: {len(group_trades)} trades")

    print("\n" + "=" * 100)
    print("BACKTEST REPORT (aggregated across all symbols per group)")
    print("=" * 100 + "\n")

    reports = [
        compute_report(trades, label, config.initial_equity, config.risk_per_trade_pct)
        for label, trades in all_trades_by_group.items()
    ]
    print_report(reports)

    print(f"\nExporting {len(all_trades_flat)} total trades to CSV...")
    path = export_trades_csv(all_trades_flat, config.output_dir)
    print(f"  -> {path}")


def build_config_from_args(args: argparse.Namespace) -> BacktestConfig:
    config = BacktestConfig()
    if args.symbols:
        config.symbols = args.symbols
    if args.timeframes:
        config.timeframes = args.timeframes
    if args.days:
        config.history_days = args.days
    if args.entry_version:
        config.entry.entry_version = args.entry_version
    if args.min_quality is not None:
        config.trendline.min_quality_score = args.min_quality
    if args.swing_strength is not None:
        config.swing.strength = args.swing_strength
    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest the trendline touch-bounce strategy.")
    parser.add_argument("--symbols", nargs="+", default=None)
    parser.add_argument("--timeframes", nargs="+", default=None, choices=["30m", "1h"])
    parser.add_argument("--days", type=float, default=None)
    parser.add_argument("--entry-version", choices=["A", "B"], default=None)
    parser.add_argument("--min-quality", type=float, default=None)
    parser.add_argument("--swing-strength", type=int, default=None)
    args = parser.parse_args()

    cfg = build_config_from_args(args)
    asyncio.run(main(cfg))
