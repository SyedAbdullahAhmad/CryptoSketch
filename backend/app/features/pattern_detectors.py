from typing import List, Callable, Dict, Tuple, Optional
import numpy as np

from app.market_data.base_exchange import Candle

DetectorResult = Tuple[bool, float, List[str]]


def _closes(c: List[Candle]) -> List[float]:
    return [x.close for x in c]


def _highs(c: List[Candle]) -> List[float]:
    return [x.high for x in c]


def _lows(c: List[Candle]) -> List[float]:
    return [x.low for x in c]


def _swings(values: List[float], mode: str, order: int) -> List[int]:
    idx = []
    n = len(values)
    for i in range(order, n - order):
        window = values[i - order: i + order + 1]
        if mode == "high" and values[i] == max(window):
            idx.append(i)
        elif mode == "low" and values[i] == min(window):
            idx.append(i)
    return idx


def _swing_order(n: int) -> int:
    return max(1, n // 10)


def _structure(c: List[Candle]):
    highs, lows = _highs(c), _lows(c)
    order = _swing_order(len(c))
    hi_idx = _swings(highs, "high", order)
    lo_idx = _swings(lows, "low", order)
    return [highs[i] for i in hi_idx], [lows[i] for i in lo_idx]


def _quad_curvature(values: List[float]) -> float:
    x = np.linspace(-1, 1, len(values))
    return float(np.polyfit(x, values, 2)[0])


def detect_trend(c: List[Candle]) -> DetectorResult:
    closes = _closes(c)
    if len(closes) < 5:
        return False, 0, []
    change = (closes[-1] - closes[0]) / (abs(closes[0]) + 1e-9)
    if change > 0.03:
        return True, min(100, abs(change) * 400), ["Uptrend", "Bullish trend"]
    if change < -0.03:
        return True, min(100, abs(change) * 400), ["Downtrend", "Bearish trend"]
    return False, 0, []


def detect_higher_highs(c: List[Candle]) -> DetectorResult:
    sh, _ = _structure(c)
    ok = len(sh) >= 2 and all(sh[i] < sh[i + 1] for i in range(len(sh) - 1))
    return ok, 85 if ok else 0, ["Higher Highs"] if ok else []


def detect_higher_lows(c: List[Candle]) -> DetectorResult:
    _, sl = _structure(c)
    ok = len(sl) >= 2 and all(sl[i] < sl[i + 1] for i in range(len(sl) - 1))
    return ok, 85 if ok else 0, ["Higher Lows"] if ok else []


def detect_lower_highs(c: List[Candle]) -> DetectorResult:
    sh, _ = _structure(c)
    ok = len(sh) >= 2 and all(sh[i] > sh[i + 1] for i in range(len(sh) - 1))
    return ok, 85 if ok else 0, ["Lower Highs"] if ok else []


def detect_lower_lows(c: List[Candle]) -> DetectorResult:
    _, sl = _structure(c)
    ok = len(sl) >= 2 and all(sl[i] > sl[i + 1] for i in range(len(sl) - 1))
    return ok, 85 if ok else 0, ["Lower Lows"] if ok else []


def detect_consolidation(c: List[Candle]) -> DetectorResult:
    closes = _closes(c)
    rng = max(closes) - min(closes)
    ratio = rng / (float(np.mean(closes)) + 1e-9)
    ok = ratio < 0.06
    score = max(0.0, 100 - ratio * 1500)
    return ok, score if ok else 0, ["Consolidation / Sideways range", "Low volatility"] if ok else []


def detect_support(c: List[Candle]) -> DetectorResult:
    _, sl = _structure(c)
    if len(sl) < 2:
        return False, 0, []
    tolerance = (max(sl) - min(sl)) / (float(np.mean(sl)) + 1e-9)
    ok = tolerance < 0.02
    return ok, 90 if ok else 0, ["Support level respected"] if ok else []


def detect_resistance(c: List[Candle]) -> DetectorResult:
    sh, _ = _structure(c)
    if len(sh) < 2:
        return False, 0, []
    tolerance = (max(sh) - min(sh)) / (float(np.mean(sh)) + 1e-9)
    ok = tolerance < 0.02
    return ok, 90 if ok else 0, ["Resistance level respected"] if ok else []


def detect_trendline(c: List[Candle]) -> DetectorResult:
    sh, sl = _structure(c)
    pts = sl if len(sl) >= 3 else sh
    if len(pts) < 3:
        return False, 0, []
    x = np.arange(len(pts))
    slope, intercept = np.polyfit(x, pts, 1)
    fitted = slope * x + intercept
    residual = float(np.mean(np.abs(np.array(pts) - fitted))) / (float(np.mean(pts)) + 1e-9)
    ok = residual < 0.015
    return ok, 90 if ok else 0, ["Clean trendline structure"] if ok else []


def detect_ascending_triangle(c: List[Candle]) -> DetectorResult:
    sh, sl = _structure(c)
    if len(sh) < 2 or len(sl) < 2:
        return False, 0, []
    flat_res = (max(sh) - min(sh)) / (float(np.mean(sh)) + 1e-9) < 0.02
    rising_sup = all(sl[i] < sl[i + 1] for i in range(len(sl) - 1))
    ok = flat_res and rising_sup
    return ok, 88 if ok else 0, ["Flat resistance", "Rising support", "Compression / breakout setup"] if ok else []


def detect_descending_triangle(c: List[Candle]) -> DetectorResult:
    sh, sl = _structure(c)
    if len(sh) < 2 or len(sl) < 2:
        return False, 0, []
    flat_sup = (max(sl) - min(sl)) / (float(np.mean(sl)) + 1e-9) < 0.02
    falling_res = all(sh[i] > sh[i + 1] for i in range(len(sh) - 1))
    ok = flat_sup and falling_res
    return ok, 88 if ok else 0, ["Flat support", "Falling resistance", "Compression / breakdown setup"] if ok else []


def detect_symmetrical_triangle(c: List[Candle]) -> DetectorResult:
    sh, sl = _structure(c)
    if len(sh) < 2 or len(sl) < 2:
        return False, 0, []
    falling_res = all(sh[i] > sh[i + 1] for i in range(len(sh) - 1))
    rising_sup = all(sl[i] < sl[i + 1] for i in range(len(sl) - 1))
    ok = falling_res and rising_sup
    return ok, 88 if ok else 0, ["Converging highs and lows", "Compression / breakout setup"] if ok else []


def detect_channel(c: List[Candle]) -> DetectorResult:
    sh, sl = _structure(c)
    if len(sh) < 2 or len(sl) < 2:
        return False, 0, []
    slope_h = float(np.polyfit(np.arange(len(sh)), sh, 1)[0])
    slope_l = float(np.polyfit(np.arange(len(sl)), sl, 1)[0])
    same_dir = (slope_h > 0) == (slope_l > 0)
    similar_slope = abs(slope_h - slope_l) / (abs(slope_h) + abs(slope_l) + 1e-9) < 0.4
    ok = same_dir and similar_slope
    direction = "ascending" if slope_h > 0 else "descending"
    return ok, 85 if ok else 0, [f"Parallel {direction} channel"] if ok else []


def detect_bull_flag(c: List[Candle]) -> DetectorResult:
    closes = _closes(c)
    n = len(closes)
    if n < 8:
        return False, 0, []
    split = int(n * 0.6)
    pole = (closes[split] - closes[0]) / (abs(closes[0]) + 1e-9)
    flag = closes[split:]
    flag_range = (max(flag) - min(flag)) / (float(np.mean(flag)) + 1e-9)
    ok = pole > 0.05 and flag_range < 0.04
    return ok, 85 if ok else 0, ["Strong impulsive move up", "Tight consolidation (flag)"] if ok else []


def detect_bear_flag(c: List[Candle]) -> DetectorResult:
    closes = _closes(c)
    n = len(closes)
    if n < 8:
        return False, 0, []
    split = int(n * 0.6)
    pole = (closes[split] - closes[0]) / (abs(closes[0]) + 1e-9)
    flag = closes[split:]
    flag_range = (max(flag) - min(flag)) / (float(np.mean(flag)) + 1e-9)
    ok = pole < -0.05 and flag_range < 0.04
    return ok, 85 if ok else 0, ["Strong impulsive move down", "Tight consolidation (flag)"] if ok else []


def detect_double_top(c: List[Candle]) -> DetectorResult:
    sh, _ = _structure(c)
    if len(sh) < 2:
        return False, 0, []
    a, b = sh[-2], sh[-1]
    diff = abs(a - b) / (float(np.mean([a, b])) + 1e-9)
    ok = diff < 0.015
    return ok, 88 if ok else 0, ["Two similar swing highs", "Potential double top"] if ok else []


def detect_double_bottom(c: List[Candle]) -> DetectorResult:
    _, sl = _structure(c)
    if len(sl) < 2:
        return False, 0, []
    a, b = sl[-2], sl[-1]
    diff = abs(a - b) / (float(np.mean([a, b])) + 1e-9)
    ok = diff < 0.015
    return ok, 88 if ok else 0, ["Two similar swing lows", "Potential double bottom"] if ok else []


def detect_head_and_shoulders(c: List[Candle]) -> DetectorResult:
    sh, _ = _structure(c)
    if len(sh) < 3:
        return False, 0, []
    l, h, r = sh[-3], sh[-2], sh[-1]
    ok = h > l and h > r and abs(l - r) / (float(np.mean([l, r])) + 1e-9) < 0.03
    return ok, 85 if ok else 0, ["Three peaks with higher middle peak", "Head & Shoulders structure"] if ok else []


def detect_inverse_head_and_shoulders(c: List[Candle]) -> DetectorResult:
    _, sl = _structure(c)
    if len(sl) < 3:
        return False, 0, []
    l, h, r = sl[-3], sl[-2], sl[-1]
    ok = h < l and h < r and abs(l - r) / (float(np.mean([l, r])) + 1e-9) < 0.03
    return ok, 85 if ok else 0, ["Three troughs with lower middle trough", "Inverse Head & Shoulders structure"] if ok else []


def detect_rounded_bottom(c: List[Candle]) -> DetectorResult:
    closes = _closes(c)
    if len(closes) < 8:
        return False, 0, []
    a = _quad_curvature(closes)
    ok = a > 0
    return ok, min(100, abs(a) * 5000) if ok else 0, ["Gradual U-shaped recovery", "Rounded bottom"] if ok else []


def detect_rounded_top(c: List[Candle]) -> DetectorResult:
    closes = _closes(c)
    if len(closes) < 8:
        return False, 0, []
    a = _quad_curvature(closes)
    ok = a < 0
    return ok, min(100, abs(a) * 5000) if ok else 0, ["Gradual inverted-U rollover", "Rounded top"] if ok else []


def detect_cup_and_handle(c: List[Candle]) -> DetectorResult:
    closes = _closes(c)
    n = len(closes)
    if n < 12:
        return False, 0, []
    cup = closes[: int(n * 0.8)]
    handle = closes[int(n * 0.8):]
    a = _quad_curvature(cup)
    handle_pullback = (max(handle) - handle[-1]) / (float(np.mean(handle)) + 1e-9)
    ok = a > 0 and 0.005 < handle_pullback < 0.05
    return ok, 82 if ok else 0, ["Rounded cup formation", "Small handle pullback"] if ok else []


def detect_bos(c: List[Candle]) -> DetectorResult:
    sh, sl = _structure(c)
    closes = _closes(c)
    if sh and closes[-1] > sh[-1]:
        return True, 87, ["Break of Structure (bullish)", "Price closed above prior swing high"]
    if sl and closes[-1] < sl[-1]:
        return True, 87, ["Break of Structure (bearish)", "Price closed below prior swing low"]
    return False, 0, []


def detect_choch(c: List[Candle]) -> DetectorResult:
    sh, sl = _structure(c)
    closes = _closes(c)
    if len(closes) < 6 or not sh or not sl:
        return False, 0, []
    prior_down = closes[len(closes) // 2] < closes[0]
    prior_up = closes[len(closes) // 2] > closes[0]
    if prior_down and closes[-1] > sh[-1]:
        return True, 85, ["Change of Character (bullish)", "Prior downtrend broken to the upside"]
    if prior_up and closes[-1] < sl[-1]:
        return True, 85, ["Change of Character (bearish)", "Prior uptrend broken to the downside"]
    return False, 0, []


def detect_equal_highs(c: List[Candle]) -> DetectorResult:
    sh, _ = _structure(c)
    if len(sh) < 2:
        return False, 0, []
    diff = abs(sh[-1] - sh[-2]) / (float(np.mean(sh[-2:])) + 1e-9)
    ok = diff < 0.005
    return ok, 90 if ok else 0, ["Equal Highs (liquidity resting above)"] if ok else []


def detect_equal_lows(c: List[Candle]) -> DetectorResult:
    _, sl = _structure(c)
    if len(sl) < 2:
        return False, 0, []
    diff = abs(sl[-1] - sl[-2]) / (float(np.mean(sl[-2:])) + 1e-9)
    ok = diff < 0.005
    return ok, 90 if ok else 0, ["Equal Lows (liquidity resting below)"] if ok else []


def detect_fvg(c: List[Candle]) -> DetectorResult:
    for i in range(max(1, len(c) - 4), len(c) - 1):
        prev_high, prev_low = c[i - 1].high, c[i - 1].low
        next_high, next_low = c[i + 1].high, c[i + 1].low
        if prev_high < next_low:
            return True, 82, ["Bullish Fair Value Gap detected", "Imbalance left unfilled"]
        if prev_low > next_high:
            return True, 82, ["Bearish Fair Value Gap detected", "Imbalance left unfilled"]
    return False, 0, []


def detect_liquidity_sweep(c: List[Candle]) -> DetectorResult:
    sh, sl = _structure(c)
    if len(c) < 5:
        return False, 0, []
    last = c[-1]
    if sh and last.high > sh[-1] and last.close < sh[-1]:
        return True, 80, ["Liquidity sweep above prior high", "Wick rejected, closed back inside"]
    if sl and last.low < sl[-1] and last.close > sl[-1]:
        return True, 80, ["Liquidity sweep below prior low", "Wick rejected, closed back inside"]
    return False, 0, []


def detect_order_block(c: List[Candle]) -> DetectorResult:
    if len(c) < 6:
        return False, 0, []
    for i in range(len(c) - 5, len(c) - 1):
        cur, nxt = c[i], c[i + 1]
        move = (nxt.close - cur.close) / (abs(cur.close) + 1e-9)
        if cur.close < cur.open and move > 0.02:
            return True, 78, ["Bullish order block", "Last down candle before strong up move"]
        if cur.close > cur.open and move < -0.02:
            return True, 78, ["Bearish order block", "Last up candle before strong down move"]
    return False, 0, []


def detect_breaker_block(c: List[Candle]) -> DetectorResult:
    ob_ok, _, _ = detect_order_block(c)
    bos_ok, _, _ = detect_bos(c)
    ok = ob_ok and bos_ok
    return ok, 75 if ok else 0, ["Breaker block: order block invalidated by structure break"] if ok else []


def detect_mitigation_block(c: List[Candle]) -> DetectorResult:
    ob_ok, _, _ = detect_order_block(c)
    closes = _closes(c)
    retest = len(closes) >= 3 and abs(closes[-1] - closes[-3]) / (abs(closes[-3]) + 1e-9) < 0.01
    ok = ob_ok and retest
    return ok, 72 if ok else 0, ["Mitigation block: price returned to rebalance prior inefficiency"] if ok else []


def detect_trendline_support_bounce(c: List[Candle]) -> DetectorResult:
    """
    Fits a rising trendline through swing lows. Looks for: a red candle
    whose wick touches (or pierces) the trendline but closes above it
    (support holds), immediately followed by a green candle that closes
    above the trendline too — whether or not it touches the line.
    """
    lows = _lows(c)
    n = len(lows)
    if n < 6:
        return False, 0, []

    order = _swing_order(n)
    lo_idx = _swings(lows, "low", order)
    if len(lo_idx) < 2:
        return False, 0, []

    idx_arr = np.array(lo_idx, dtype=float)
    val_arr = np.array([lows[i] for i in lo_idx], dtype=float)
    slope, intercept = np.polyfit(idx_arr, val_arr, 1)

    # Only interested in rising trendlines (dynamic support), matching the
    # example chart: a line drawn upward connecting higher swing lows.
    if slope <= 0:
        return False, 0, []

    lookback = min(15, n - 1)
    start_check = max(1, n - lookback)

    match_at = None
    for i in range(start_check, n):
        prev, cur = c[i - 1], c[i]
        trend_prev = slope * (i - 1) + intercept
        trend_cur = slope * i + intercept

        prev_red = prev.close < prev.open
        prev_touched = prev.low <= trend_prev
        prev_closed_above = prev.close > trend_prev

        cur_green = cur.close > cur.open
        cur_closed_above = cur.close > trend_cur

        if prev_red and prev_touched and prev_closed_above and cur_green and cur_closed_above:
            match_at = i  # keep the most recent match

    if match_at is None:
        return False, 0, []

    recency_penalty = (n - 1 - match_at) * 3
    score = max(60.0, min(100.0, 95.0 - recency_penalty))

    reasons = [
        "Rising trendline support detected",
        "Red candle wicked the trendline and closed above it",
        "Following green candle closed above trendline support",
        "Trendline support bounce confirmed",
    ]
    return True, score, reasons


CONCEPT_REGISTRY: Dict[str, Callable[[List[Candle]], DetectorResult]] = {
    "trend": detect_trend,
    "higher_highs": detect_higher_highs,
    "higher_lows": detect_higher_lows,
    "lower_highs": detect_lower_highs,
    "lower_lows": detect_lower_lows,
    "consolidation": detect_consolidation,
    "support": detect_support,
    "resistance": detect_resistance,
    "trendline": detect_trendline,
    "ascending_triangle": detect_ascending_triangle,
    "descending_triangle": detect_descending_triangle,
    "symmetrical_triangle": detect_symmetrical_triangle,
    "channel": detect_channel,
    "bull_flag": detect_bull_flag,
    "bear_flag": detect_bear_flag,
    "double_top": detect_double_top,
    "double_bottom": detect_double_bottom,
    "head_and_shoulders": detect_head_and_shoulders,
    "inverse_head_and_shoulders": detect_inverse_head_and_shoulders,
    "rounded_bottom": detect_rounded_bottom,
    "rounded_top": detect_rounded_top,
    "cup_and_handle": detect_cup_and_handle,
    "break_of_structure": detect_bos,
    "change_of_character": detect_choch,
    "equal_highs": detect_equal_highs,
    "equal_lows": detect_equal_lows,
    "fair_value_gap": detect_fvg,
    "imbalance": detect_fvg,
    "liquidity_sweep": detect_liquidity_sweep,
    "order_block": detect_order_block,
    "breaker_block": detect_breaker_block,
    "mitigation_block": detect_mitigation_block,
    "trendline_support_bounce": detect_trendline_support_bounce,
}


def run_detector(concept: str, symbol: str, candles_raw: List[dict]) -> Optional[dict]:
    """Module-level so it's picklable for ProcessPoolExecutor."""
    candles = [Candle(**c) for c in candles_raw]
    detector = CONCEPT_REGISTRY.get(concept)
    if detector is None:
        return None
    matched, score, reasons = detector(candles)
    if not matched:
        return None
    return {
        "symbol": symbol,
        "score": score,
        "reasons": reasons,
        "start_time": candles[0].open_time,
        "end_time": candles[-1].close_time,
        "closes": [c.close for c in candles][-30:],
    }