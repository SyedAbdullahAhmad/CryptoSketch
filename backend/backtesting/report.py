"""
Prints the per-timeframe / per-stop-loss / per-take-profit breakdown
table, and writes the full trade log (all trades, all combinations) to CSV.
"""
import csv
import os
from datetime import datetime, timezone
from typing import List, Dict
from backtesting.backtest_engine import Trade
from backtesting.metrics import BacktestReport


def print_report(reports: List[BacktestReport]) -> None:
    header = (
        f"{'Group':<30} {'Trades':>7} {'WinRate%':>9} {'PF':>6} {'Exp(R)':>7} "
        f"{'AvgR':>6} {'AvgHold':>8} {'MaxDD%':>7} {'MaxLoseStk':>10} {'MaxWinStk':>9} "
        f"{'NetProf%':>9} {'AvgTrade%':>9} {'Sharpe':>7}"
    )
    print(header)
    print("-" * len(header))
    for r in reports:
        pf_str = "inf" if r.profit_factor == float("inf") else f"{r.profit_factor:.2f}"
        print(
            f"{r.group_label:<30} {r.total_trades:>7} {r.win_rate:>9.2f} {pf_str:>6} "
            f"{r.expectancy_r:>7.3f} {r.avg_r:>6.3f} {r.avg_hold_bars:>8.1f} "
            f"{r.max_drawdown_pct:>7.2f} {r.max_consecutive_losses:>10} {r.max_consecutive_wins:>9} "
            f"{r.net_profit_pct:>9.2f} {r.avg_trade_pct:>9.3f} {r.sharpe_ratio:>7.3f}"
        )


def export_trades_csv(all_trades: List[Trade], output_dir: str, filename: str = None) -> str:
    os.makedirs(output_dir, exist_ok=True)
    if filename is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"trades_{ts}.csv"
    path = os.path.join(output_dir, filename)

    def fmt_time(ms: int) -> str:
        if not ms:
            return ""
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Date", "Coin", "Timeframe", "Entry", "Stop", "Target", "Exit",
            "PnL%", "R Multiple", "Trade Duration (bars)", "Reason For Exit",
            "StopLossMethod", "TakeProfitMethod", "SignalReason",
        ])
        for t in all_trades:
            writer.writerow([
                fmt_time(t.entry_time), t.symbol, t.timeframe,
                round(t.entry_price, 8), round(t.initial_stop_loss, 8),
                round(t.target_price, 8) if t.target_price is not None else "",
                round(t.exit_price, 8), round(t.pnl_pct, 4), round(t.r_multiple, 4),
                t.duration_bars, t.exit_reason, t.stop_loss_method, t.take_profit_method,
                t.signal_reason,
            ])
    return path
