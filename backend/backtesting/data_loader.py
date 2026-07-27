"""
Fetches historical OHLCV data for backtesting. Reuses the same
BinanceClient used by the live app -- no separate data source.
"""
import asyncio
from datetime import datetime, timezone
from typing import List, Dict

from app.market_data.binance_client import BinanceClient
from app.market_data.base_exchange import Candle


async def fetch_history(client: BinanceClient, symbol: str, interval: str, days: float) -> List[Candle]:
    """Paginate Binance klines to cover `days` of history."""
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


async def load_all(symbols: List[str], timeframes: List[str], days: float) -> Dict[str, Dict[str, List[Candle]]]:
    """
    Returns: { symbol: { timeframe: [Candle, ...] } }
    Fetches sequentially per symbol to stay within Binance's public rate
    limits (weight-based); this is a one-time backtest data pull, not a
    latency-sensitive path, so simplicity is preferred over max concurrency.
    """
    client = BinanceClient()
    data: Dict[str, Dict[str, List[Candle]]] = {}

    for symbol in symbols:
        data[symbol] = {}
        for tf in timeframes:
            print(f"  Fetching {symbol} {tf} ({days} days)...")
            candles = await fetch_history(client, symbol, tf, days)
            data[symbol][tf] = candles
            print(f"    -> {len(candles)} candles")

    await client.aclose()
    return data
