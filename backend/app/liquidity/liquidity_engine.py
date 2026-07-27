# from typing import List, Dict, Optional, Tuple
# import numpy as np
# from app.market_data.base_exchange import Candle
# from app.features.pattern_detectors import _structure

# HTF_CONFLUENCE_TFS = ["1h", "4h", "1d"]

# INTERVAL_HOURS = {
#     "1m": 1 / 60, "5m": 5 / 60, "15m": 15 / 60, "30m": 0.5,
#     "1h": 1.0, "4h": 4.0, "1d": 24.0,
# }


# def candles_for_lookback(interval: str, days: float, min_candles: int = 15, max_candles: int = 500) -> int:
#     """
#     How many candles of `interval` are needed to cover the same real
#     calendar window (`days`) -- used so 1h/4h/1d confluence checks
#     compare the SAME period, not mismatched spans.
#     """
#     hours_per_candle = INTERVAL_HOURS.get(interval, 1.0)
#     needed = int((days * 24) / hours_per_candle) + 1
#     return max(min_candles, min(needed, max_candles))


# def _atr(candles: List[Candle], period: int = 14) -> float:
#     """Simplified average true range (high-low range only, no gap component)."""
#     period = max(1, min(period, len(candles)))
#     window = candles[-period:]
#     if not window:
#         return 0.0
#     tr = [c.high - c.low for c in window]
#     return float(np.mean(tr)) if tr else 0.0


# def _path_efficiency(closes: List[float]) -> float:
#     """net displacement / total distance traveled -- 1.0 = perfectly clean move, near 0 = choppy."""
#     diffs = np.diff(closes)
#     total_move = float(np.sum(np.abs(diffs))) + 1e-9
#     net_move = abs(closes[-1] - closes[0])
#     return net_move / total_move


# def _trend_from_closes(closes: List[float], min_efficiency: float = 0.3, min_zscore: float = 0.8) -> str:
#     """
#     Volatility-normalized, cleanliness-aware trend read:
#     - direction from net change
#     - REJECTED if the path was choppy (low efficiency) even if net change is positive
#     - REJECTED if the net move isn't large relative to the series' own volatility (z-score)
#     """
#     if len(closes) < 5:
#         return "neutral"

#     arr = np.array(closes, dtype=float)
#     diffs = np.diff(arr)
#     net = float(arr[-1] - arr[0])
#     std = float(np.std(diffs)) + 1e-9
#     zscore = net / (std * np.sqrt(len(diffs)))

#     efficiency = _path_efficiency(closes)
#     if efficiency < min_efficiency or abs(zscore) < min_zscore:
#         return "neutral"

#     return "bullish" if net > 0 else "bearish"


# def _is_strong_move(candles: List[Candle], min_atr_multiple: float = 1.0, atr_period: int = 14) -> bool:
#     """Net displacement must be at least `min_atr_multiple` times the series' own ATR -- adapts per symbol's volatility."""
#     if len(candles) < 5:
#         return False
#     atr = _atr(candles, min(atr_period, len(candles) - 1))
#     if atr <= 0:
#         return False
#     net_move = abs(candles[-1].close - candles[0].close)
#     return (net_move / atr) >= min_atr_multiple


# def _detect_sweep(candles: List[Candle], zone: float, liquidity_type: str, lookback: int = 3) -> Tuple[bool, Optional[float]]:
#     """
#     Multi-candle sweep: within the last `lookback` candles, price wicked
#     beyond the zone at some point AND the most recent candle closed back
#     on the correct side (reclaim) -- not required to happen on one candle.
#     """
#     lookback = min(lookback, len(candles))
#     window = candles[-lookback:]
#     if liquidity_type == "sell-side":
#         swept = any(c.low < zone for c in window)
#         reclaimed = window[-1].close > zone
#         extreme = min(c.low for c in window)
#         return (swept and reclaimed), extreme
#     if liquidity_type == "buy-side":
#         swept = any(c.high > zone for c in window)
#         reclaimed = window[-1].close < zone
#         extreme = max(c.high for c in window)
#         return (swept and reclaimed), extreme
#     return False, None


# def _zone_matches(a: float, b: float, tolerance: float = 0.01) -> bool:
#     return abs(a - b) / (abs(b) + 1e-9) < tolerance


# def detect_htf_bias(candles_by_tf: Dict[str, List[Candle]], primary_tf: str) -> Dict:
#     """
#     Higher timeframe liquidity read:
#     - Trend on the primary HTF, requiring both directional cleanliness
#       (path efficiency) and a move large relative to the market's own
#       volatility (ATR), not a fixed percentage.
#     - Liquidity zone = opposing swing extreme.
#     - "Event-level" = the SAME zone also shows up in the other HTFs'
#       swing structure over the SAME calendar window (via candles_for_lookback).
#     """
#     primary = candles_by_tf[primary_tf]
#     closes = [c.close for c in primary]

#     trend = _trend_from_closes(closes, min_efficiency=0.3, min_zscore=0.8)
#     if trend != "neutral" and not _is_strong_move(primary, min_atr_multiple=1.2):
#         trend = "neutral"

#     swing_highs, swing_lows = _structure(primary)

#     if trend == "bullish":
#         liquidity_type = "sell-side"
#         liquidity_zone = min(swing_lows) if swing_lows else min(c.low for c in primary)
#         bias = "buy"
#         liquidity_taken = any(c.low < liquidity_zone for c in primary[:-1])
#     elif trend == "bearish":
#         liquidity_type = "buy-side"
#         liquidity_zone = max(swing_highs) if swing_highs else max(c.high for c in primary)
#         bias = "sell"
#         liquidity_taken = any(c.high > liquidity_zone for c in primary[:-1])
#     else:
#         liquidity_type = "neutral"
#         liquidity_zone = closes[-1]
#         bias = "neutral"
#         liquidity_taken = False

#     confluence_count = 1  # primary_tf itself
#     if liquidity_type != "neutral":
#         for tf in HTF_CONFLUENCE_TFS:
#             if tf == primary_tf or tf not in candles_by_tf:
#                 continue
#             sh, sl = _structure(candles_by_tf[tf])
#             pool = sl if liquidity_type == "sell-side" else sh
#             if any(_zone_matches(liquidity_zone, lvl) for lvl in pool):
#                 confluence_count += 1

#     event_liquidity = confluence_count >= 2

#     return {
#         "trend": trend,
#         "liquidity_zone": float(liquidity_zone),
#         "liquidity_type": liquidity_type,
#         "liquidity_taken": bool(liquidity_taken),
#         "event_liquidity": bool(event_liquidity),
#         "bias": bias,
#     }


# def detect_ltf_entry(ltf_candles: List[Candle], htf_bias: Dict) -> Optional[Dict]:
#     """
#     Continuation entry:
#     1. LTF trend (cleanliness + volatility-relative strength) must agree with HTF bias.
#     2. Price must be within ATR-relative distance of the liquidity level (retracement, not chasing).
#     3. Prior high/low (the "other party's stop") must be intact across the ENTIRE recent series.
#     Entry/stop/target are priced using ATR rather than fixed percentages.
#     """
#     closes = [c.close for c in ltf_candles]
#     ltf_trend = _trend_from_closes(closes, min_efficiency=0.3, min_zscore=0.6)
#     if ltf_trend != "neutral" and not _is_strong_move(ltf_candles, min_atr_multiple=1.0):
#         ltf_trend = "neutral"

#     swing_highs, swing_lows = _structure(ltf_candles)
#     if not swing_highs or not swing_lows:
#         return None

#     last = ltf_candles[-1]
#     atr = _atr(ltf_candles, min(14, len(ltf_candles) - 1))
#     if atr <= 0:
#         return None

#     prev_high = swing_highs[-1]
#     prev_low = swing_lows[-1]

#     near_low = abs(last.close - prev_low) <= 0.75 * atr
#     near_high = abs(last.close - prev_high) <= 0.75 * atr

#     if htf_bias["bias"] == "buy" and ltf_trend == "bullish" and near_low:
#         prior_high_taken = any(c.high > prev_high for c in ltf_candles[:-1])
#         if prior_high_taken:
#             return None
#         confidence = "High" if htf_bias["event_liquidity"] else "Medium"

#         entry_price = last.close
#         stop_loss = prev_low - 0.5 * atr
#         upside_highs = [h for h in swing_highs if h > entry_price]
#         target_price = min(upside_highs) if upside_highs else prev_high

#         return {
#             "trend": ltf_trend,
#             "htf_bias": htf_bias["bias"],
#             "liquidity_type": "sell-side",
#             "liquidity_price": float(prev_low),
#             "liquidity_status": "Untouched",
#             "signal": "BUY",
#             "confidence": confidence,
#             "entry_price": float(entry_price),
#             "stop_loss": float(stop_loss),
#             "target_price": float(target_price),
#             "reason": (
#                 "Bullish HTF bias + clean/strong LTF trend (ATR-relative) + retracement into liquidity "
#                 "+ previous high still intact (sellers not yet stopped out)."
#             ),
#         }

#     if htf_bias["bias"] == "sell" and ltf_trend == "bearish" and near_high:
#         prior_low_taken = any(c.low < prev_low for c in ltf_candles[:-1])
#         if prior_low_taken:
#             return None
#         confidence = "High" if htf_bias["event_liquidity"] else "Medium"

#         entry_price = last.close
#         stop_loss = prev_high + 0.5 * atr
#         downside_lows = [l for l in swing_lows if l < entry_price]
#         target_price = max(downside_lows) if downside_lows else prev_low

#         return {
#             "trend": ltf_trend,
#             "htf_bias": htf_bias["bias"],
#             "liquidity_type": "buy-side",
#             "liquidity_price": float(prev_high),
#             "liquidity_status": "Untouched",
#             "signal": "SELL",
#             "confidence": confidence,
#             "entry_price": float(entry_price),
#             "stop_loss": float(stop_loss),
#             "target_price": float(target_price),
#             "reason": (
#                 "Bearish HTF bias + clean/strong LTF trend (ATR-relative) + retracement into liquidity "
#                 "+ previous low still intact (buyers not yet stopped out)."
#             ),
#         }
#     return None


# def detect_reversal_entry(ltf_candles: List[Candle], htf_bias: Dict) -> Optional[Dict]:
#     """
#     Reversal entry -- ONLY when HTF liquidity is event-level AND a sweep
#     (wick beyond zone + reclaim, allowed across up to 3 candles) occurred.
#     """
#     if not htf_bias["event_liquidity"]:
#         return None

#     zone = htf_bias["liquidity_zone"]
#     liquidity_type = htf_bias["liquidity_type"]
#     swept, extreme = _detect_sweep(ltf_candles, zone, liquidity_type, lookback=3)
#     if not swept or extreme is None:
#         return None

#     last = ltf_candles[-1]
#     atr = _atr(ltf_candles, min(14, len(ltf_candles) - 1))
#     if atr <= 0:
#         return None

#     swing_highs, swing_lows = _structure(ltf_candles)
#     entry_price = last.close

#     if liquidity_type == "sell-side":
#         stop_loss = extreme - 0.5 * atr
#         upside_highs = [h for h in swing_highs if h > entry_price]
#         target_price = min(upside_highs) if upside_highs else entry_price + 2 * atr
#         return {
#             "trend": "bearish",
#             "htf_bias": htf_bias["bias"],
#             "liquidity_type": liquidity_type,
#             "liquidity_price": float(zone),
#             "liquidity_status": "Swept",
#             "signal": "BUY",
#             "confidence": "High",
#             "entry_price": float(entry_price),
#             "stop_loss": float(stop_loss),
#             "target_price": float(target_price),
#             "reason": "Event-level sell-side liquidity (1H/4H/1D confluence) swept and reclaimed -- reversal setup.",
#         }

#     if liquidity_type == "buy-side":
#         stop_loss = extreme + 0.5 * atr
#         downside_lows = [l for l in swing_lows if l < entry_price]
#         target_price = max(downside_lows) if downside_lows else entry_price - 2 * atr
#         return {
#             "trend": "bullish",
#             "htf_bias": htf_bias["bias"],
#             "liquidity_type": liquidity_type,
#             "liquidity_price": float(zone),
#             "liquidity_status": "Swept",
#             "signal": "SELL",
#             "confidence": "High",
#             "entry_price": float(entry_price),
#             "stop_loss": float(stop_loss),
#             "target_price": float(target_price),
#             "reason": "Event-level buy-side liquidity (1H/4H/1D confluence) swept and reclaimed -- reversal setup.",
#         }
#     return None


# def detect_ltf_signal(ltf_candles: List[Candle], htf_bias: Dict) -> Optional[Dict]:
#     signal = detect_ltf_entry(ltf_candles, htf_bias)
#     if signal is not None:
#         return signal
#     return detect_reversal_entry(ltf_candles, htf_bias)



from typing import List, Dict, Optional
from app.market_data.base_exchange import Candle
from app.features.pattern_detectors import _structure

# The three HTFs the methodology checks for liquidity confluence.
HTF_CONFLUENCE_TFS = ["1h", "4h", "1d"]

# Buffer beyond a liquidity level for stop-loss placement (methodology
# says stop goes just past the level that "proves the other party wrong").
STOP_BUFFER_PCT = 0.003


def _trend_from_closes(closes: List[float], threshold: float = 0.015) -> str:
    if len(closes) < 5:
        return "neutral"
    change = (closes[-1] - closes[0]) / (abs(closes[0]) + 1e-9)
    if change > threshold:
        return "bullish"
    if change < -threshold:
        return "bearish"
    return "neutral"


def _zone_matches(a: float, b: float, tolerance: float = 0.01) -> bool:
    return abs(a - b) / (abs(b) + 1e-9) < tolerance


def detect_htf_bias(candles_by_tf: Dict[str, List[Candle]], primary_tf: str) -> Dict:
    """
    Higher timeframe liquidity read, per methodology:
    - Determine trend on the primary HTF being analyzed.
    - Identify the liquidity zone (opposite-side stops price should sweep
      before continuation).
    - "Event-level" liquidity = the SAME zone also appears as a swing
      extreme on the OTHER higher timeframes too (1H + 4H + 1D
      confluence) — not just an extreme within one timeframe's lookback.
    - Track whether the zone has already been taken (price has already
      traded through it) vs still sitting untouched.
    """
    primary = candles_by_tf[primary_tf]
    closes = [c.close for c in primary]
    trend = _trend_from_closes(closes)
    swing_highs, swing_lows = _structure(primary)

    if trend == "bullish":
        liquidity_type = "sell-side"
        liquidity_zone = min(swing_lows) if swing_lows else min(c.low for c in primary)
        bias = "buy"
        liquidity_taken = any(c.low < liquidity_zone for c in primary[:-1])
    elif trend == "bearish":
        liquidity_type = "buy-side"
        liquidity_zone = max(swing_highs) if swing_highs else max(c.high for c in primary)
        bias = "sell"
        liquidity_taken = any(c.high > liquidity_zone for c in primary[:-1])
    else:
        liquidity_type = "neutral"
        liquidity_zone = closes[-1]
        bias = "neutral"
        liquidity_taken = False

    confluence_count = 1  # primary_tf itself
    if liquidity_type != "neutral":
        for tf in HTF_CONFLUENCE_TFS:
            if tf == primary_tf or tf not in candles_by_tf:
                continue
            sh, sl = _structure(candles_by_tf[tf])
            pool = sl if liquidity_type == "sell-side" else sh
            if any(_zone_matches(liquidity_zone, lvl) for lvl in pool):
                confluence_count += 1

    event_liquidity = confluence_count >= 2

    return {
        "trend": trend,
        "liquidity_zone": float(liquidity_zone),
        "liquidity_type": liquidity_type,
        "liquidity_taken": bool(liquidity_taken),
        "event_liquidity": bool(event_liquidity),
        "bias": bias,
    }


def detect_ltf_entry(ltf_candles: List[Candle], htf_bias: Dict) -> Optional[Dict]:
    """
    Continuation entry, per methodology:
    1. Require a genuinely STRONG trend in the recent lookback.
    2. LTF trend must agree with HTF bias.
    3. Price must have retraced into liquidity.
    4. The prior high (buys) / prior low (sells) must still be intact
       across the ENTIRE recent move.
    Also computes concrete entry / stop-loss / target prices:
    - entry: current close (retracement price)
    - stop: just beyond the liquidity level being defended
    - target: nearest opposing liquidity pool in the trade direction
    """
    closes = [c.close for c in ltf_candles]
    ltf_trend = _trend_from_closes(closes, threshold=0.005)
    swing_highs, swing_lows = _structure(ltf_candles)
    if not swing_highs or not swing_lows:
        return None

    lookback = closes[-30:] if len(closes) >= 30 else closes
    strength = abs(lookback[-1] - lookback[0]) / (abs(lookback[0]) + 1e-9)
    if strength < 0.01:
        return None

    last = ltf_candles[-1]
    prev_high = swing_highs[-1]
    prev_low = swing_lows[-1]

    near_low = abs(last.close - prev_low) / (abs(prev_low) + 1e-9) < 0.01
    near_high = abs(last.close - prev_high) / (abs(prev_high) + 1e-9) < 0.01

    if htf_bias["bias"] == "buy" and ltf_trend == "bullish" and near_low:
        prior_high_taken = any(c.high > prev_high for c in ltf_candles[:-1])
        if prior_high_taken:
            return None
        confidence = "High" if htf_bias["event_liquidity"] else "Medium"

        entry_price = last.close
        stop_loss = prev_low * (1 - STOP_BUFFER_PCT)
        upside_highs = [h for h in swing_highs if h > entry_price]
        target_price = min(upside_highs) if upside_highs else prev_high

        return {
            "trend": ltf_trend,
            "htf_bias": htf_bias["bias"],
            "liquidity_type": "sell-side",
            "liquidity_price": float(prev_low),
            "liquidity_status": "Untouched",
            "signal": "BUY",
            "confidence": confidence,
            "entry_price": float(entry_price),
            "stop_loss": float(stop_loss),
            "target_price": float(target_price),
            "reason": (
                "Bullish HTF bias + strong LTF trend + retracement into liquidity "
                "+ previous high still intact (sellers not yet stopped out)."
            ),
        }

    if htf_bias["bias"] == "sell" and ltf_trend == "bearish" and near_high:
        prior_low_taken = any(c.low < prev_low for c in ltf_candles[:-1])
        if prior_low_taken:
            return None
        confidence = "High" if htf_bias["event_liquidity"] else "Medium"

        entry_price = last.close
        stop_loss = prev_high * (1 + STOP_BUFFER_PCT)
        downside_lows = [l for l in swing_lows if l < entry_price]
        target_price = max(downside_lows) if downside_lows else prev_low

        return {
            "trend": ltf_trend,
            "htf_bias": htf_bias["bias"],
            "liquidity_type": "buy-side",
            "liquidity_price": float(prev_high),
            "liquidity_status": "Untouched",
            "signal": "SELL",
            "confidence": confidence,
            "entry_price": float(entry_price),
            "stop_loss": float(stop_loss),
            "target_price": float(target_price),
            "reason": (
                "Bearish HTF bias + strong LTF trend + retracement into liquidity "
                "+ previous low still intact (buyers not yet stopped out)."
            ),
        }
    return None


def detect_reversal_entry(ltf_candles: List[Candle], htf_bias: Dict) -> Optional[Dict]:
    """
    Reversal entry -- ONLY valid when HTF liquidity is event-level AND a
    strong sweep of that zone has just occurred. Entry/stop/target are
    priced off the sweep candle itself.
    """
    if not htf_bias["event_liquidity"]:
        return None

    zone = htf_bias["liquidity_zone"]
    last = ltf_candles[-1]
    _, swing_lows = _structure(ltf_candles)
    swing_highs, _ = _structure(ltf_candles)

    swept_below = htf_bias["liquidity_type"] == "sell-side" and last.low < zone < last.close
    swept_above = htf_bias["liquidity_type"] == "buy-side" and last.high > zone > last.close

    if swept_below:
        entry_price = last.close
        stop_loss = last.low * (1 - STOP_BUFFER_PCT)
        upside_highs = [h for h in swing_highs if h > entry_price]
        target_price = min(upside_highs) if upside_highs else entry_price * 1.01
        return {
            "trend": "bearish",
            "htf_bias": htf_bias["bias"],
            "liquidity_type": htf_bias["liquidity_type"],
            "liquidity_price": float(zone),
            "liquidity_status": "Swept",
            "signal": "BUY",
            "confidence": "High",
            "entry_price": float(entry_price),
            "stop_loss": float(stop_loss),
            "target_price": float(target_price),
            "reason": "Event-level sell-side liquidity (1H/4H/1D confluence) swept and rejected -- reversal setup.",
        }
    if swept_above:
        entry_price = last.close
        stop_loss = last.high * (1 + STOP_BUFFER_PCT)
        downside_lows = [l for l in swing_lows if l < entry_price]
        target_price = max(downside_lows) if downside_lows else entry_price * 0.99
        return {
            "trend": "bullish",
            "htf_bias": htf_bias["bias"],
            "liquidity_type": htf_bias["liquidity_type"],
            "liquidity_price": float(zone),
            "liquidity_status": "Swept",
            "signal": "SELL",
            "confidence": "High",
            "entry_price": float(entry_price),
            "stop_loss": float(stop_loss),
            "target_price": float(target_price),
            "reason": "Event-level buy-side liquidity (1H/4H/1D confluence) swept and rejected -- reversal setup.",
        }
    return None


def detect_ltf_signal(ltf_candles: List[Candle], htf_bias: Dict) -> Optional[Dict]:
    signal = detect_ltf_entry(ltf_candles, htf_bias)
    if signal is not None:
        return signal
    return detect_reversal_entry(ltf_candles, htf_bias)