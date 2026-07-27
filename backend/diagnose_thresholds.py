"""
One-off diagnostic: prints the real distribution of trend-efficiency,
z-score, and ATR-multiple values computed on live Binance data, so
thresholds in liquidity_engine.py are set from actual data, not guesses.

Usage:
    python diagnose_thresholds.py --interval 1h --window 169   # HTF-style
    python diagnose_thresholds.py --interval 5m --window 50    # LTF-style
"""
import argparse
import asyncio
import numpy as np
from datetime import datetime, timezone

from app.market_data.binance_client import BinanceClient
from app.liquidity.liquidity_engine import _path_efficiency, _atr


async def main(symbol: str, interval: str, window: int, history_days: float):
    client = BinanceClient()
    print(f"Fetching {interval} candles for {symbol} ({history_days} days of history, window={window})...")

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ms = now_ms - int(history_days * 86400 * 1000)

    all_candles = []
    cursor = start_ms
    while cursor < now_ms:
        batch = await client.get_klines(symbol=symbol, interval=interval, limit=1000, start_time=cursor)
        if not batch:
            break
        all_candles.extend(batch)
        cursor = batch[-1].close_time + 1
        if len(batch) < 1000:
            break
    await client.aclose()
    print(f"Fetched {len(all_candles)} total {interval} candles.\n")

    efficiencies, zscores, atr_multiples = [], [], []

    for i in range(window, len(all_candles)):
        w = all_candles[i - window:i]
        closes = [c.close for c in w]

        efficiencies.append(_path_efficiency(closes))

        arr = np.array(closes, dtype=float)
        diffs = np.diff(arr)
        net = float(arr[-1] - arr[0])
        std = float(np.std(diffs)) + 1e-9
        zscores.append(abs(net / (std * np.sqrt(len(diffs)))))

        atr = _atr(w, min(14, len(w) - 1))
        if atr > 0:
            atr_multiples.append(abs(w[-1].close - w[0].close) / atr)

    def stats(name, arr, current_threshold=None):
        arr = np.array(arr)
        print(f"{name}:")
        print(f"  min={arr.min():.3f}  p25={np.percentile(arr,25):.3f}  "
              f"median={np.median(arr):.3f}  p75={np.percentile(arr,75):.3f}  "
              f"p90={np.percentile(arr,90):.3f}  max={arr.max():.3f}")
        if current_threshold is not None:
            frac = (arr >= current_threshold).mean() * 100
            print(f"  fraction >= {current_threshold}: {frac:.1f}%   (current threshold)")
        print()

    print(f"Sampled {len(efficiencies)} rolling {window}-candle windows.\n")
    stats("Path efficiency (net move / total distance)", efficiencies, current_threshold=0.3)
    stats("Z-score (|net move| in std-devs of step size)", zscores, current_threshold=0.8)
    stats("ATR multiple (net move / ATR)", atr_multiples, current_threshold=1.2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--window", type=int, default=169)
    parser.add_argument("--history-days", type=float, default=45.0)
    args = parser.parse_args()

    asyncio.run(main(args.symbol, args.interval, args.window, args.history_days))