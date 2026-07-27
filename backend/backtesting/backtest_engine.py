"""
Generic, strategy-agnostic backtesting engine. This is intentionally
NOT specific to the trendline-bounce strategy -- it just needs a
`generate_signal(candles, index, config) -> Signal | None` function,
a stop-loss method, and a take-profit method. Future strategies
(including the liquidity engine) can plug into this same engine.

Rules:
- One position open at a time per (symbol, timeframe).
- No lookahead: at bar i, only candles[0:i+1] are visible.
- Entry fills at the OPEN of the bar after the signal (per spec).
- Exit checks stop-loss and take-profit against each bar's high/low.
  If both are touched in the same bar, stop-loss is assumed to trigger
  first (conservative assumption, since intra-bar order is unknown).
"""
from dataclasses import dataclass, field
from typing import List, Optional, Callable
from app.market_data.base_exchange import Candle
from backtesting.config import BacktestConfig
from backtesting.strategy_trendline_bounce import Signal
from backtesting.stop_loss_methods import compute_stop_loss
from backtesting.take_profit_methods import compute_take_profit_plan, TakeProfitPlan


@dataclass
class Trade:
    symbol: str
    timeframe: str
    direction: str
    entry_time: int
    entry_index: int
    entry_price: float
    stop_loss: float
    initial_stop_loss: float
    target_price: Optional[float]
    exit_time: int = 0
    exit_index: int = 0
    exit_price: float = 0.0
    exit_reason: str = ""
    r_multiple: float = 0.0
    pnl_pct: float = 0.0
    duration_bars: int = 0
    stop_loss_method: str = ""
    take_profit_method: str = ""
    signal_reason: str = ""


SignalGenerator = Callable[[List[Candle], int, BacktestConfig], Optional[Signal]]


def run_single_backtest(
    candles: List[Candle],
    symbol: str,
    timeframe: str,
    config: BacktestConfig,
    generate_signal: SignalGenerator,
) -> List[Trade]:
    """
    Walks forward through `candles` one bar at a time, opens at most one
    trade at a time, and closes it against stop-loss/take-profit (fixed
    or trailing) before allowing a new signal to be evaluated.
    """
    trades: List[Trade] = []
    n = len(candles)
    in_position = False
    open_trade: Optional[Trade] = None
    trail_fn = None

    i = 0
    while i < n:
        if in_position:
            c = candles[i]

            if trail_fn is not None:
                # Trailing methods: the trail level IS the stop; exit on close below it.
                current_trail = trail_fn(candles, i)
                if current_trail > open_trade.stop_loss:
                    open_trade.stop_loss = current_trail
                if c.close < open_trade.stop_loss:
                    open_trade.exit_price = open_trade.stop_loss
                    open_trade.exit_reason = "trailing_stop"
                    _close_trade(open_trade, c, i)
                    trades.append(open_trade)
                    in_position = False
                    open_trade = None
                    trail_fn = None
                    i += 1
                    continue
            else:
                hit_stop = c.low <= open_trade.stop_loss
                hit_target = open_trade.target_price is not None and c.high >= open_trade.target_price

                if hit_stop:
                    open_trade.exit_price = open_trade.stop_loss
                    open_trade.exit_reason = "stop_loss"
                    _close_trade(open_trade, c, i)
                    trades.append(open_trade)
                    in_position = False
                    open_trade = None
                    i += 1
                    continue
                elif hit_target:
                    open_trade.exit_price = open_trade.target_price
                    open_trade.exit_reason = "take_profit"
                    _close_trade(open_trade, c, i)
                    trades.append(open_trade)
                    in_position = False
                    open_trade = None
                    i += 1
                    continue

            i += 1
            continue

        signal = generate_signal(candles, i, config)
        if signal is None:
            i += 1
            continue

        # Per spec: entry fills at the OPEN of the candle after the green
        # confirmation candle. generate_signal already returns entry_index
        # pointing at that candle.
        if signal.entry_index >= n:
            i += 1
            continue

        entry_candle = candles[signal.entry_index]
        entry_price = entry_candle.open

        stop_loss = compute_stop_loss(candles[: signal.entry_index + 1], signal, config.stop_loss)
        if stop_loss >= entry_price:
            i = signal.entry_index + 1  # invalid risk (stop above entry) -- skip
            continue

        tp_plan: TakeProfitPlan = compute_take_profit_plan(
            candles, signal, entry_price, stop_loss, config.take_profit
        )

        open_trade = Trade(
            symbol=symbol,
            timeframe=timeframe,
            direction=signal.direction,
            entry_time=entry_candle.open_time,
            entry_index=signal.entry_index,
            entry_price=entry_price,
            stop_loss=stop_loss,
            initial_stop_loss=stop_loss,
            target_price=tp_plan.target_price,
            stop_loss_method=config.stop_loss.method,
            take_profit_method=config.take_profit.method,
            signal_reason=signal.reason,
        )
        trail_fn = tp_plan.trail_fn
        in_position = True
        i = signal.entry_index + 1  # start checking exits from the bar after entry

    return trades


def _close_trade(trade: Trade, exit_candle: Candle, exit_index: int) -> None:
    trade.exit_time = exit_candle.close_time
    trade.exit_index = exit_index
    trade.duration_bars = exit_index - trade.entry_index
    risk = trade.entry_price - trade.initial_stop_loss
    reward = trade.exit_price - trade.entry_price
    trade.r_multiple = (reward / risk) if risk > 0 else 0.0
    trade.pnl_pct = (trade.exit_price - trade.entry_price) / trade.entry_price * 100
