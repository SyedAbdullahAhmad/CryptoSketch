"""
Step 1-5 of the strategy spec: HH/HL structure filter, trendline
touch detection, red-touch + green-confirmation entry logic.

This module implements the `generate_signal` interface expected by
backtest_engine.py, so it can be swapped for other strategies later
without changing the engine.
"""
from dataclasses import dataclass
from typing import List, Optional
from app.market_data.base_exchange import Candle
from backtesting.config import BacktestConfig
from backtesting.swing_detector import swing_highs, swing_lows
from backtesting.trendline_engine import Trendline, best_trendline


@dataclass
class Signal:
    direction: str          # "LONG" (only long trades per spec)
    signal_index: int        # index of the green confirmation candle
    entry_index: int         # index of the candle whose OPEN is the entry price (signal_index + 1)
    red_touch_index: int     # index of the red candle that touched the trendline
    trendline: Trendline
    reason: str


def _has_hh_hl_structure(candles: List[Candle], current_index: int, config: BacktestConfig) -> bool:
    """Step 1: only trade when the market is making Higher Highs AND Higher Lows."""
    window = candles[: current_index + 1]
    lookback_start = max(0, current_index - config.trendline.lookback_bars)
    recent = window[lookback_start:]

    highs = [s for s in swing_highs(recent, config.swing)]
    lows = [s for s in swing_lows(recent, config.swing)]

    if len(highs) < 2 or len(lows) < 2:
        return False

    hh = all(highs[i].price < highs[i + 1].price for i in range(len(highs) - 1))
    hl = all(lows[i].price < lows[i + 1].price for i in range(len(lows) - 1))
    return hh and hl


def _is_touch(candle: Candle, trendline: Trendline, index: int, config: BacktestConfig) -> bool:
    line_value = trendline.value_at(index)
    if line_value <= 0:
        return False
    tolerance = line_value * config.trendline.touch_tolerance_pct
    return candle.low <= line_value + tolerance


def generate_signal(candles: List[Candle], current_index: int, config: BacktestConfig) -> Optional[Signal]:
    """
    Called once per bar during the walk-forward loop, with `current_index`
    being the most recent CLOSED candle. No lookahead: only candles up to
    and including current_index are used.

    Sequence checked (per spec):
    - current_index - 2: RED candle that touches an active trendline and closes above it
    - current_index - 1: GREEN candle confirming (Version A: just green;
      Version B: closes above the red candle's high)
    - current_index: the entry candle -- its OPEN is the fill price
    """
    if current_index < 2:
        return None

    if not _has_hh_hl_structure(candles, current_index, config):
        return None

    red_idx = current_index - 2
    green_idx = current_index - 1
    entry_idx = current_index

    red_candle = candles[red_idx]
    green_candle = candles[green_idx]

    is_red = red_candle.close < red_candle.open
    is_green = green_candle.close > green_candle.open
    if not (is_red and is_green):
        return None

    # Trendline must have been active (2 touches) BEFORE the red touch candle.
    trendline = best_trendline(candles, red_idx, config.trendline, config.swing)
    if trendline is None or trendline.activated_index >= red_idx:
        return None

    if not _is_touch(red_candle, trendline, red_idx, config):
        return None

    line_value_at_red = trendline.value_at(red_idx)
    if red_candle.close < line_value_at_red:
        return None  # red candle closed below trendline -- ignore setup

    if config.entry.entry_version == "B":
        if green_candle.close <= red_candle.high:
            return None  # Version B requires close above the red candle's high

    return Signal(
        direction="LONG",
        signal_index=green_idx,
        entry_index=entry_idx,
        red_touch_index=red_idx,
        trendline=trendline,
        reason=(
            f"HH/HL structure + ascending trendline (score={trendline.quality_score}, "
            f"{trendline.touches} touches) + red touch/close-above + green confirmation "
            f"(version {config.entry.entry_version})."
        ),
    )
