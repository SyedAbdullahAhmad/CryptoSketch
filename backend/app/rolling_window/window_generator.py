from typing import List
from app.market_data.base_exchange import Candle


class RollingWindow:
    def __init__(self, symbol: str, interval: str, start_index: int, candles: List[Candle]):
        self.symbol = symbol
        self.interval = interval
        self.start_index = start_index
        self.candles = candles

    @property
    def closes(self) -> List[float]:
        return [c.close for c in self.candles]

    @property
    def start_time(self) -> int:
        return self.candles[0].open_time

    @property
    def end_time(self) -> int:
        return self.candles[-1].close_time


def generate_rolling_windows(
    symbol: str,
    interval: str,
    candles: List[Candle],
    window_size: int,
    stride: int = 1,
) -> List[RollingWindow]:
    """
    Slide a fixed-size window across the candle series.
    stride=1 gives maximum resolution (every possible offset);
    increase stride to reduce compute cost on long series.
    """
    windows: List[RollingWindow] = []
    n = len(candles)
    if n < window_size:
        return windows

    for start in range(0, n - window_size + 1, stride):
        segment = candles[start : start + window_size]
        windows.append(RollingWindow(symbol, interval, start, segment))

    return windows