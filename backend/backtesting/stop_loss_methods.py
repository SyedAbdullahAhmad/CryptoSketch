"""
Pluggable stop-loss methods. Each takes the full candle series and the
signal, and returns a stop price. Adding a new method = adding a new
function + registering it in STOP_LOSS_METHODS.
"""
from typing import List, Callable, Dict
import numpy as np
from app.market_data.base_exchange import Candle
from backtesting.strategy_trendline_bounce import Signal
from backtesting.config import StopLossConfig


def _atr(candles: List[Candle], period: int) -> float:
    period = max(1, min(period, len(candles)))
    window = candles[-period:]
    tr = [c.high - c.low for c in window]
    return float(np.mean(tr)) if tr else 0.0


def stop_method_a(candles: List[Candle], signal: Signal, config: StopLossConfig) -> float:
    """Method A: below the red touch candle's low."""
    return candles[signal.red_touch_index].low


def stop_method_b(candles: List[Candle], signal: Signal, config: StopLossConfig) -> float:
    """Method B: below red candle low - 0.25 * ATR(14)."""
    red_low = candles[signal.red_touch_index].low
    atr_window = candles[: signal.red_touch_index + 1]
    atr = _atr(atr_window, config.atr_period)
    return red_low - config.atr_buffer_multiple * atr


def stop_method_c(candles: List[Candle], signal: Signal, config: StopLossConfig) -> float:
    """Method C: below the trendline (at the entry index) by an ATR buffer."""
    line_value = signal.trendline.value_at(signal.entry_index)
    atr_window = candles[: signal.entry_index + 1]
    atr = _atr(atr_window, config.atr_period)
    return line_value - config.atr_buffer_multiple * atr


STOP_LOSS_METHODS: Dict[str, Callable[[List[Candle], Signal, StopLossConfig], float]] = {
    "A": stop_method_a,
    "B": stop_method_b,
    "C": stop_method_c,
}


def compute_stop_loss(candles: List[Candle], signal: Signal, config: StopLossConfig) -> float:
    method = STOP_LOSS_METHODS.get(config.method)
    if method is None:
        raise ValueError(f"Unknown stop-loss method '{config.method}'")
    return method(candles, signal, config)
