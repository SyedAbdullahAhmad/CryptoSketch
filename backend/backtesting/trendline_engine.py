"""
Builds ascending trendlines by connecting swing lows, validates them
against the strategy's rules, and scores their quality.
"""
from dataclasses import dataclass
from typing import List, Optional
from app.market_data.base_exchange import Candle
from backtesting.config import TrendlineConfig, SwingConfig
from backtesting.swing_detector import SwingPoint, swing_lows


@dataclass
class Trendline:
    p1: SwingPoint          # first touch (earlier swing low)
    p2: SwingPoint          # second touch (later swing low) -- activates the line
    slope: float             # price change per candle index
    intercept: float         # price at index 0
    activated_index: int     # candle index at which this line became tradeable (p2.index)
    quality_score: float = 0.0
    touches: int = 2

    def value_at(self, index: int) -> float:
        return self.slope * index + self.intercept


def _fit_line(p1: SwingPoint, p2: SwingPoint) -> tuple[float, float]:
    """Returns (slope, intercept) such that price = slope * index + intercept."""
    if p2.index == p1.index:
        return 0.0, p1.price
    slope = (p2.price - p1.price) / (p2.index - p1.index)
    intercept = p1.price - slope * p1.index
    return slope, intercept


def _is_valid_slope(slope: float, ref_price: float, config: TrendlineConfig) -> bool:
    pct_slope = abs(slope) / (ref_price + 1e-9)
    return config.min_slope_pct_per_candle <= pct_slope <= config.max_slope_pct_per_candle


def _no_meaningful_close_below(
    candles: List[Candle], slope: float, intercept: float, start_index: int, end_index: int, config: TrendlineConfig
) -> bool:
    """'No candle has closed meaningfully below it' -- checked from the first touch to the current bar."""
    for i in range(start_index, min(end_index + 1, len(candles))):
        line_value = slope * i + intercept
        if line_value <= 0:
            continue
        if candles[i].close < line_value * (1 - config.break_tolerance_pct):
            return False
    return True


def _count_touches(
    candles: List[Candle], slope: float, intercept: float, start_index: int, end_index: int, config: TrendlineConfig
) -> int:
    touches = 0
    for i in range(start_index, min(end_index + 1, len(candles))):
        line_value = slope * i + intercept
        if line_value <= 0:
            continue
        if abs(candles[i].low - line_value) <= line_value * config.touch_tolerance_pct:
            touches += 1
    return touches


def _score_trendline(
    candles: List[Candle], line: Trendline, current_index: int, config: TrendlineConfig
) -> float:
    """
    0-100 quality score based on: touch count, slope quality (closer to
    a "moderate" mid-range slope scores higher), trend duration, cleanliness
    (no closes below), and recent respect (closeness of most recent touch).
    """
    ref_price = candles[line.p2.index].close
    pct_slope = abs(line.slope) / (ref_price + 1e-9)

    # Slope quality: peak score at the geometric midpoint of the valid range.
    mid = (config.min_slope_pct_per_candle * config.max_slope_pct_per_candle) ** 0.5
    slope_range = config.max_slope_pct_per_candle - config.min_slope_pct_per_candle
    slope_quality = max(0.0, 1 - abs(pct_slope - mid) / (slope_range + 1e-9))

    touches = _count_touches(candles, line.slope, line.intercept, line.p1.index, current_index, config)
    touch_score = min(1.0, touches / 5.0)  # saturates at 5 touches

    duration = current_index - line.p1.index
    duration_score = min(1.0, duration / config.lookback_bars)

    clean = _no_meaningful_close_below(candles, line.slope, line.intercept, line.p1.index, current_index, config)
    clean_score = 1.0 if clean else 0.0

    recency = max(0.0, 1 - (current_index - line.p2.index) / max(1, config.lookback_bars))

    score = (
        touch_score * 30
        + slope_quality * 25
        + duration_score * 15
        + clean_score * 20
        + recency * 10
    )
    return round(score, 1)


def build_trendlines(
    candles: List[Candle], current_index: int, config: TrendlineConfig, swing_config: SwingConfig = None
) -> List[Trendline]:
    """
    Finds all valid, currently-active ascending trendlines as of
    `current_index` (no lookahead -- only uses candles[0:current_index+1]).
    A trendline activates after its SECOND swing-low touch (not three).
    """
    swing_config = swing_config or SwingConfig()
    lookback_start = max(0, current_index - config.lookback_bars)
    window = candles[: current_index + 1]

    lows = [s for s in swing_lows(window, swing_config) if s.index >= lookback_start]

    lines: List[Trendline] = []
    for i in range(len(lows)):
        for j in range(i + 1, len(lows)):
            p1, p2 = lows[i], lows[j]
            if p2.price <= p1.price:
                continue  # must be ascending (later low higher than earlier low)

            slope, intercept = _fit_line(p1, p2)
            ref_price = candles[p2.index].close
            if not _is_valid_slope(slope, ref_price, config):
                continue

            if not _no_meaningful_close_below(candles, slope, intercept, p1.index, current_index, config):
                continue

            line = Trendline(
                p1=p1, p2=p2, slope=slope, intercept=intercept, activated_index=p2.index,
            )
            line.quality_score = _score_trendline(candles, line, current_index, config)
            line.touches = _count_touches(candles, slope, intercept, p1.index, current_index, config)

            if line.quality_score >= config.min_quality_score:
                lines.append(line)

    return lines


def best_trendline(
    candles: List[Candle], current_index: int, config: TrendlineConfig, swing_config: SwingConfig = None
) -> Optional[Trendline]:
    lines = build_trendlines(candles, current_index, config, swing_config)
    if not lines:
        return None
    return max(lines, key=lambda l: l.quality_score)
