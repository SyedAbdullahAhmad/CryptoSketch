"""
Standalone backtest for the HTF/LTF liquidity strategy.
Reuses the real BinanceClient and the exact liquidity_engine detection
functions used by the live app -- this is not a reimplementation.

Usage (from the backend/ directory):
    python backtest.py                          # BTCUSDT, 5m, last 21 days
    python backtest.py --symbol ETHUSDT --days 30
    python backtest.py --symbol BTCUSDT --ltf 1m --days 10
    python backtest.py --debug                  # show funnel diagnostics

No lookahead: at each simulated moment, only candles with close_time <=
"now" are visible to the detector, same as the live scanner would see.
"""
import argparse
import asyncio
from datetime import datetime, timezone
from typing import List, Dict

from app.market_data.binance_client import BinanceClient
from app.market_data.base_exchange import Candle
from app.liquidity.liquidity_engine import (
    detect_htf_bias,
    detect_ltf_signal,
    HTF_CONFLUENCE_TFS,
    candles_for_lookback,
    _trend_from_closes,
    _is_strong_move,
    _atr,
    _structure,
)
from app.config import settings


async def fetch_history(client: BinanceClient, symbol: str, interval: str, days: float) -> List[Candle]:
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ms = now_ms - int(days * 86400 * 1000)

    all_candles: List[Candle] = []
    cursor = start_ms
    while cursor < now_ms:
        batch = await client.get_klines(symbol=symbol, interval=interval, limit=1000, start_time=cursor)
        if not batch:
            break
        all_candles.extend(batch)
        cursor = batch[-1].close_time + 1
        if len(batch) < 1000:
            break
    return all_candles


def fmt_time(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


async def run_backtest(symbol: str, ltf_interval: str, htf_interval: str, days: float, debug: bool):
    client = BinanceClient()

    htf_lookback_days = settings.htf_confluence_lookback_days
    total_htf_days = days + htf_lookback_days + 1

    print(f"Fetching real historical data for {symbol}...")
    ltf_candles = await fetch_history(client, symbol, ltf_interval, days)
    htf_data: Dict[str, List[Candle]] = {}
    for tf in HTF_CONFLUENCE_TFS:
        htf_data[tf] = await fetch_history(client, symbol, tf, total_htf_days)
        print(f"  {tf}: {len(htf_data[tf])} candles fetched")
    print(f"  {ltf_interval}: {len(ltf_candles)} candles fetched")
    await client.aclose()

    needed_by_tf = {
        tf: candles_for_lookback(
            tf, htf_lookback_days,
            min_candles=settings.htf_min_candles_for_structure,
            max_candles=settings.max_htf_confluence_candles,
        )
        for tf in HTF_CONFLUENCE_TFS
    }
    ltf_needed = 50

    trades = []
    in_position = False
    position = None

    # Diagnostic funnel counters
    funnel = {
        "bars_walked": 0,
        "insufficient_htf_data": 0,
        "htf_bias_neutral": 0,
        "htf_bias_non_neutral": 0,
        "htf_event_liquidity": 0,
        "ltf_trend_neutral": 0,
        "ltf_trend_disagrees_with_htf": 0,
        "not_near_liquidity": 0,
        "prior_extreme_already_broken": 0,
        "signals_fired": 0,
    }

    print(f"\nWalking forward through {len(ltf_candles)} {ltf_interval} candles (no lookahead)...\n")

    for i in range(ltf_needed, len(ltf_candles)):
        current_time = ltf_candles[i].close_time
        funnel["bars_walked"] += 1

        if in_position:
            c = ltf_candles[i]
            direction = position["signal"]
            if direction == "BUY":
                hit_target = c.high >= position["target_price"]
                hit_stop = c.low <= position["stop_loss"]
            else:
                hit_target = c.low <= position["target_price"]
                hit_stop = c.high >= position["stop_loss"]

            if hit_stop:
                outcome, exit_price = "LOSS", position["stop_loss"]
            elif hit_target:
                outcome, exit_price = "WIN", position["target_price"]
            else:
                continue

            position["outcome"] = outcome
            position["exit_price"] = exit_price
            position["exit_time"] = current_time
            position["bars_held"] = i - position["entry_index"]
            trades.append(position)
            print(
                f"  [{fmt_time(position['entry_time'])}] {direction} {symbol} "
                f"@ {position['entry_price']:.6g} -> {outcome} @ {exit_price:.6g} "
                f"({position['bars_held']} bars, conf={position['confidence']})"
            )
            in_position = False
            position = None
            continue

        htf_candles_by_tf = {}
        skip = False
        for tf in HTF_CONFLUENCE_TFS:
            visible = [c for c in htf_data[tf] if c.close_time <= current_time]
            needed = needed_by_tf[tf]
            if len(visible) < needed:
                skip = True
                break
            htf_candles_by_tf[tf] = visible[-needed:]
        if skip:
            funnel["insufficient_htf_data"] += 1
            continue

        htf_bias = detect_htf_bias(htf_candles_by_tf, htf_interval)
        if htf_bias["bias"] == "neutral":
            funnel["htf_bias_neutral"] += 1
            continue
        funnel["htf_bias_non_neutral"] += 1
        if htf_bias["event_liquidity"]:
            funnel["htf_event_liquidity"] += 1

        ltf_window = ltf_candles[i - ltf_needed + 1: i + 1]

        if debug:
            closes = [c.close for c in ltf_window]
            ltf_trend = _trend_from_closes(closes, min_efficiency=0.3, min_zscore=0.6)
            strong = _is_strong_move(ltf_window, min_atr_multiple=1.0)
            sh, sl = _structure(ltf_window)
            atr = _atr(ltf_window, min(14, len(ltf_window) - 1))
            last_close = ltf_window[-1].close
            if ltf_trend == "neutral" or not strong:
                funnel["ltf_trend_neutral"] += 1
                continue
            if ltf_trend != ("bullish" if htf_bias["bias"] == "buy" else "bearish"):
                funnel["ltf_trend_disagrees_with_htf"] += 1
                continue
            if sh and sl and atr > 0:
                near_low = abs(last_close - sl[-1]) <= 0.75 * atr
                near_high = abs(last_close - sh[-1]) <= 0.75 * atr
                if htf_bias["bias"] == "buy" and not near_low:
                    funnel["not_near_liquidity"] += 1
                    continue
                if htf_bias["bias"] == "sell" and not near_high:
                    funnel["not_near_liquidity"] += 1
                    continue

        signal = detect_ltf_signal(ltf_window, htf_bias)
        if signal is None:
            continue

        funnel["signals_fired"] += 1
        position = {
            "entry_index": i,
            "entry_time": current_time,
            "signal": signal["signal"],
            "entry_price": signal["entry_price"],
            "stop_loss": signal["stop_loss"],
            "target_price": signal["target_price"],
            "confidence": signal["confidence"],
            "reason": signal["reason"],
        }
        in_position = True

    print(f"\n{'='*70}")
    print(f"BACKTEST SUMMARY: {symbol} | LTF={ltf_interval} HTF={htf_interval} | {days} days")
    print(f"{'='*70}")

    closed = trades
    wins = [t for t in closed if t["outcome"] == "WIN"]
    losses = [t for t in closed if t["outcome"] == "LOSS"]

    print(f"Total signals fired (closed): {len(closed)}")
    if in_position:
        print(f"1 trade still open at end of data (excluded from win rate)")

    if closed:
        win_rate = len(wins) / len(closed) * 100
        print(f"Wins: {len(wins)}  Losses: {len(losses)}  Win rate: {win_rate:.1f}%")

        r_multiples = []
        for t in closed:
            risk = abs(t["entry_price"] - t["stop_loss"])
            reward = abs(t["exit_price"] - t["entry_price"])
            if risk <= 0:
                continue
            r = reward / risk if t["outcome"] == "WIN" else -1.0
            r_multiples.append(r)
        if r_multiples:
            avg_r = sum(r_multiples) / len(r_multiples)
            print(f"Average R multiple per trade: {avg_r:.2f}")
            print(f"Total R (sum): {sum(r_multiples):.2f}")

        high_conf = [t for t in closed if t["confidence"] == "High"]
        if high_conf:
            hc_wins = [t for t in high_conf if t["outcome"] == "WIN"]
            print(f"\nHigh-confidence signals: {len(high_conf)}  Win rate: {len(hc_wins)/len(high_conf)*100:.1f}%")
    else:
        print("No signals fired in this period.")

    if debug:
        print(f"\n{'='*70}")
        print("DIAGNOSTIC FUNNEL (where bars got filtered out)")
        print(f"{'='*70}")
        for k, v in funnel.items():
            print(f"  {k:35s}: {v}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backtest the HTF/LTF liquidity strategy on real Binance data.")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--ltf", default="5m", choices=["1m", "5m"])
    parser.add_argument("--htf", default="1h", choices=["1h", "4h", "1d"])
    parser.add_argument("--days", type=float, default=21.0)
    parser.add_argument("--debug", action="store_true", help="Show stage-by-stage filter funnel")
    args = parser.parse_args()

    asyncio.run(run_backtest(args.symbol, args.ltf, args.htf, args.days, args.debug))