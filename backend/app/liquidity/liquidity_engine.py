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