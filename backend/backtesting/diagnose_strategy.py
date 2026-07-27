"""
Diagnoses why the trendline-bounce strategy fires zero signals by
instrumenting every gate separately and reporting real pass/fail counts
and distributions, using real historical data.

Usage: python -m backtesting.diagnose_strategy
       python -m backtesting.diagnose_strategy --symbol ETHUSDT --timeframe 1h
"""
import argparse
import asyncio
from typing import List
import numpy as np

from app.market_data.base_exchange import Candle
from backtesting.config import BacktestConfig
from backtesting.data_loader import fetch_history
from backtesting.swing_detector import swing_highs, swing_lows
from backtesting.trendline_engine import build_trendlines, best_trendline
from app.market_data.binance_client import BinanceClient


async def main(symbol: str, timeframe: str, days: float):
    client = BinanceClient()
    print(f"Fetching {symbol} {timeframe} ({days} days)...")
    candles: List[Candle] = await fetch_history(client, symbol, timeframe, days)
    await client.aclose()
    print(f"  -> {len(candles)} candles\n")

    config = BacktestConfig()

    # --- Stage 1: swing detection sanity check ---
    highs = swing_highs(candles, config.swing)
    lows = swing_lows(candles, config.swing)
    print(f"Swing detection (strength={config.swing.strength}):")
    print(f"  swing highs found: {len(highs)}")
    print(f"  swing lows found: {len(lows)}")
    print()

    # --- Stage 2: HH/HL structure over rolling windows ---
    lookback = config.trendline.lookback_bars
    hh_hl_pass = 0
    hh_hl_total = 0
    for i in range(lookback, len(candles)):
        window_start = max(0, i - lookback)
        recent = candles[window_start:i + 1]
        wh = swing_highs(recent, config.swing)
        wl = swing_lows(recent, config.swing)
        hh_hl_total += 1
        if len(wh) < 2 or len(wl) < 2:
            continue
        hh = all(wh[j].price < wh[j + 1].price for j in range(len(wh) - 1))
        hl = all(wl[j].price < wl[j + 1].price for j in range(len(wl) - 1))
        if hh and hl:
            hh_hl_pass += 1
    print(f"HH/HL structure filter (lookback={lookback} bars):")
    print(f"  windows checked: {hh_hl_total}")
    print(f"  windows passing (strict monotonic HH+HL): {hh_hl_pass} ({hh_hl_pass/max(1,hh_hl_total)*100:.2f}%)")
    print()

    # --- Stage 3: trendline validity + quality score distribution ---
    sample_indices = list(range(lookback, len(candles), max(1, (len(candles) - lookback) // 300)))
    quality_scores = []
    any_trendline_count = 0
    slopes_pct = []
    touch_counts = []

    for i in sample_indices:
        lines = build_trendlines(candles, i, config.trendline, config.swing)
        if lines:
            any_trendline_count += 1
            for line in lines:
                quality_scores.append(line.quality_score)
                touch_counts.append(line.touches)
                ref_price = candles[line.p2.index].close
                slopes_pct.append(abs(line.slope) / ref_price * 100)

    print(f"Trendline detection (sampled {len(sample_indices)} points across the series):")
    print(f"  sample points with >=1 valid ascending trendline (pre-quality-filter): {any_trendline_count} "
          f"({any_trendline_count/max(1,len(sample_indices))*100:.2f}%)")
    if quality_scores:
        qs = np.array(quality_scores)
        print(f"  quality score distribution: min={qs.min():.1f} p25={np.percentile(qs,25):.1f} "
              f"median={np.median(qs):.1f} p75={np.percentile(qs,75):.1f} max={qs.max():.1f}")
        print(f"  fraction >= current threshold ({config.trendline.min_quality_score}): "
              f"{(qs >= config.trendline.min_quality_score).mean()*100:.1f}%")
    else:
        print("  NO trendlines found at all in the sample -- check slope bounds / touch tolerance.")

    if slopes_pct:
        sp = np.array(slopes_pct)
        print(f"  slope %/candle distribution: min={sp.min():.4f} median={np.median(sp):.4f} max={sp.max():.4f}")
        print(f"  configured bounds: [{config.trendline.min_slope_pct_per_candle*100:.4f}, "
              f"{config.trendline.max_slope_pct_per_candle*100:.4f}]")

    if touch_counts:
        tc = np.array(touch_counts)
        print(f"  touch count distribution: min={tc.min()} median={np.median(tc):.1f} max={tc.max()}")
    print()

    # --- Stage 4: red-touch + green-confirmation frequency (independent of trendlines) ---
    red_green_pairs = 0
    for i in range(1, len(candles)):
        red = candles[i - 1]
        green = candles[i]
        if red.close < red.open and green.close > green.open:
            red_green_pairs += 1
    print(f"Raw red-then-green candle pairs in series: {red_green_pairs} "
          f"({red_green_pairs/len(candles)*100:.1f}% of bars)")
    print()

    print("=" * 70)
    print("LIKELY BOTTLENECK SUMMARY")
    print("=" * 70)
    if hh_hl_pass / max(1, hh_hl_total) < 0.05:
        print("-> HH/HL structure filter is extremely strict (< 5% pass). This is")
        print("   the most likely reason for zero trades: requiring ALL swing highs")
        print("   AND ALL swing lows in a 150-bar window to be strictly monotonic")
        print("   is a very high bar for real, noisy price action.")
    if quality_scores and (np.array(quality_scores) >= config.trendline.min_quality_score).mean() < 0.1:
        print("-> Quality score threshold may also be filtering out most real trendlines.")
    if not quality_scores:
        print("-> No trendlines are being built at all -- slope bounds or touch")
        print("   tolerance may be miscalibrated for this symbol/timeframe.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--timeframe", default="30m")
    parser.add_argument("--days", type=float, default=60.0)
    args = parser.parse_args()

    asyncio.run(main(args.symbol, args.timeframe, args.days))
