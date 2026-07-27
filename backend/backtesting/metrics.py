"""
Computes the full statistics report from a list of closed Trade objects.
Kept independent of the engine and strategy -- works on any List[Trade].
"""
from dataclasses import dataclass
from typing import List
import numpy as np
from backtesting.backtest_engine import Trade


@dataclass
class BacktestReport:
    group_label: str
    total_trades: int
    win_rate: float
    profit_factor: float
    expectancy_r: float
    avg_r: float
    avg_hold_bars: float
    max_drawdown_pct: float
    max_consecutive_losses: int
    max_consecutive_wins: int
    net_profit_pct: float
    avg_trade_pct: float
    sharpe_ratio: float
    equity_curve: List[float]


def _max_drawdown(equity_curve: List[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        dd = (peak - value) / peak * 100 if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
    return max_dd


def _max_consecutive(trades: List[Trade], win: bool) -> int:
    streak = 0
    best = 0
    for t in trades:
        is_win = t.r_multiple > 0
        if is_win == win:
            streak += 1
            best = max(best, streak)
        else:
            streak = 0
    return best


def compute_report(trades: List[Trade], group_label: str, initial_equity: float, risk_per_trade_pct: float) -> BacktestReport:
    if not trades:
        return BacktestReport(
            group_label=group_label, total_trades=0, win_rate=0.0, profit_factor=0.0,
            expectancy_r=0.0, avg_r=0.0, avg_hold_bars=0.0, max_drawdown_pct=0.0,
            max_consecutive_losses=0, max_consecutive_wins=0, net_profit_pct=0.0,
            avg_trade_pct=0.0, sharpe_ratio=0.0, equity_curve=[initial_equity],
        )

    r_multiples = np.array([t.r_multiple for t in trades])
    wins = r_multiples[r_multiples > 0]
    losses = r_multiples[r_multiples <= 0]

    win_rate = len(wins) / len(trades) * 100
    gross_win = float(wins.sum()) if len(wins) else 0.0
    gross_loss = float(-losses.sum()) if len(losses) else 0.0
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else (float("inf") if gross_win > 0 else 0.0)

    expectancy_r = float(r_multiples.mean())
    avg_r = expectancy_r
    avg_hold = float(np.mean([t.duration_bars for t in trades]))
    avg_trade_pct = float(np.mean([t.pnl_pct for t in trades]))

    # Equity curve: risk a fixed % of current equity per trade, scaled by R multiple.
    equity = initial_equity
    equity_curve = [equity]
    risk_amount_fn = lambda eq: eq * (risk_per_trade_pct / 100)
    for t in trades:
        equity += risk_amount_fn(equity) * t.r_multiple
        equity_curve.append(equity)

    net_profit_pct = (equity_curve[-1] - initial_equity) / initial_equity * 100
    max_dd = _max_drawdown(equity_curve)

    max_cons_losses = _max_consecutive(trades, win=False)
    max_cons_wins = _max_consecutive(trades, win=True)

    std_r = float(r_multiples.std())
    sharpe = (expectancy_r / std_r * np.sqrt(len(trades))) if std_r > 0 else 0.0

    return BacktestReport(
        group_label=group_label,
        total_trades=len(trades),
        win_rate=round(win_rate, 2),
        profit_factor=round(profit_factor, 2) if profit_factor != float("inf") else float("inf"),
        expectancy_r=round(expectancy_r, 3),
        avg_r=round(avg_r, 3),
        avg_hold_bars=round(avg_hold, 1),
        max_drawdown_pct=round(max_dd, 2),
        max_consecutive_losses=max_cons_losses,
        max_consecutive_wins=max_cons_wins,
        net_profit_pct=round(net_profit_pct, 2),
        avg_trade_pct=round(avg_trade_pct, 3),
        sharpe_ratio=round(sharpe, 3),
        equity_curve=equity_curve,
    )
