"""
Pluggable take-profit methods. Methods A/B/C produce a single fixed
target price computed at entry time. Methods D/E are trailing exits --
they don't have one fixed target; instead they provide a function the
engine calls every bar to compute the current trailing stop level.
"""
from dataclasses import dataclass
from typing import List, Callable, Optional, Dict
import numpy as np
from app.market_data.base_exchange import Candle
from backtesting.strategy_trendline_bounce import Signal
from backtesting.swing_detector import swing_highs
from backtesting.config import TakeProfitConfig, SwingConfig


@dataclass
class TakeProfitPlan:
    kind: str  # "fixed" or "trailing"
    target_price: Optional[float] = None
    # trail_fn(candles, current_index) -> current trailing stop level.
    # Called once per bar while the trade is open; the trade exits when
    # price crosses back through this level.
    trail_fn: Optional[Callable[[List[Candle], int], float]] = None


def _r_multiple_target(entry_price: float, stop_loss: float, r_multiple: float) -> float:
    risk = entry_price - stop_loss
    return entry_price + risk * r_multiple


def tp_method_a(candles: List[Candle], signal: Signal, entry_price: float, stop_loss: float, config: TakeProfitConfig) -> TakeProfitPlan:
    """Method A: fixed 2R target."""
    return TakeProfitPlan(kind="fixed", target_price=_r_multiple_target(entry_price, stop_loss, 2.0))


def tp_method_b(candles: List[Candle], signal: Signal, entry_price: float, stop_loss: float, config: TakeProfitConfig) -> TakeProfitPlan:
    """Method B: fixed 3R target."""
    return TakeProfitPlan(kind="fixed", target_price=_r_multiple_target(entry_price, stop_loss, 3.0))


def tp_method_c(candles: List[Candle], signal: Signal, entry_price: float, stop_loss: float, config: TakeProfitConfig) -> TakeProfitPlan:
    """Method C: nearest prior swing high above entry."""
    history = candles[: signal.entry_index + 1]
    highs = swing_highs(history, SwingConfig())
    candidates = [h.price for h in highs if h.price > entry_price]
    target = min(candidates) if candidates else entry_price + (entry_price - stop_loss) * 2.0
    return TakeProfitPlan(kind="fixed", target_price=target)


def _ema_series(closes: List[float], period: int) -> List[float]:
    if not closes:
        return []
    k = 2 / (period + 1)
    ema = [closes[0]]
    for price in closes[1:]:
        ema.append(price * k + ema[-1] * (1 - k))
    return ema


def tp_method_d(candles: List[Candle], signal: Signal, entry_price: float, stop_loss: float, config: TakeProfitConfig) -> TakeProfitPlan:
    """Method D: trailing stop using the 20 EMA -- exit when price closes below it."""
    def trail_fn(all_candles: List[Candle], current_index: int) -> float:
        closes = [c.close for c in all_candles[: current_index + 1]]
        ema = _ema_series(closes, config.ema_period)
        return ema[-1] if ema else stop_loss

    return TakeProfitPlan(kind="trailing", trail_fn=trail_fn)


def tp_method_e(candles: List[Candle], signal: Signal, entry_price: float, stop_loss: float, config: TakeProfitConfig) -> TakeProfitPlan:
    """Method E: trail below the trendline itself as it extends forward."""
    trendline = signal.trendline

    def trail_fn(all_candles: List[Candle], current_index: int) -> float:
        return trendline.value_at(current_index)

    return TakeProfitPlan(kind="trailing", trail_fn=trail_fn)


TAKE_PROFIT_METHODS: Dict[str, Callable[..., TakeProfitPlan]] = {
    "A": tp_method_a,
    "B": tp_method_b,
    "C": tp_method_c,
    "D": tp_method_d,
    "E": tp_method_e,
}


def compute_take_profit_plan(
    candles: List[Candle], signal: Signal, entry_price: float, stop_loss: float, config: TakeProfitConfig
) -> TakeProfitPlan:
    method = TAKE_PROFIT_METHODS.get(config.method)
    if method is None:
        raise ValueError(f"Unknown take-profit method '{config.method}'")
    return method(candles, signal, entry_price, stop_loss, config)
