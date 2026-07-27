"""
Detects significant swing highs/lows -- not every local min/max, but
pivots confirmed by `strength` candles on both sides.
"""
from dataclasses import dataclass
from typing import List
from app.market_data.base_exchange import Candle
from backtesting.config import SwingConfig


@dataclass
class SwingPoint:
    index: int          # index into the candle array
    price: float
    time: int            # candle open_time (ms)
    kind: str             # "high" or "low"


def detect_swings(candles: List[Candle], config: SwingConfig) -> List[SwingPoint]:
    """
    A candle at index i is a swing low if its low is <= every low in
    [i-strength, i+strength]; symmetric for swing highs. Only interior
    candles (with full look-around available) are considered, which
    naturally avoids using unconfirmed/incomplete pivots at the edges.
    """
    strength = config.strength
    n = len(candles)
    swings: List[SwingPoint] = []

    for i in range(strength, n - strength):
        window = candles[i - strength: i + strength + 1]
        low_i = candles[i].low
        high_i = candles[i].high

        if all(low_i <= c.low for c in window):
            swings.append(SwingPoint(index=i, price=low_i, time=candles[i].open_time, kind="low"))
        if all(high_i >= c.high for c in window):
            swings.append(SwingPoint(index=i, price=high_i, time=candles[i].open_time, kind="high"))

    return swings


def swing_lows(candles: List[Candle], config: SwingConfig) -> List[SwingPoint]:
    return [s for s in detect_swings(candles, config) if s.kind == "low"]


def swing_highs(candles: List[Candle], config: SwingConfig) -> List[SwingPoint]:
    return [s for s in detect_swings(candles, config) if s.kind == "high"]
