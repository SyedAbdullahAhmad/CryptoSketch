import time
from typing import List, Optional
import diskcache

from app.market_data.base_exchange import Candle
from app.config import settings


class CandleCache:
    """
    Caches OHLCV candles per (exchange, symbol, interval) on disk.
    """

    def __init__(self, cache_dir: str = None):
        self._cache = diskcache.Cache(cache_dir or settings.cache_dir)

    @staticmethod
    def _key(exchange: str, symbol: str, interval: str) -> str:
        return f"{exchange}:{symbol}:{interval}"

    def get(self, exchange: str, symbol: str, interval: str) -> Optional[List[Candle]]:
        entry = self._cache.get(self._key(exchange, symbol, interval))
        if entry is None:
            return None
        candles_raw, cached_at = entry
        return [Candle(**c) for c in candles_raw]

    def get_cached_at(self, exchange: str, symbol: str, interval: str) -> Optional[float]:
        entry = self._cache.get(self._key(exchange, symbol, interval))
        if entry is None:
            return None
        return entry[1]

    def set(self, exchange: str, symbol: str, interval: str, candles: List[Candle]):
        payload = ([c.model_dump() for c in candles], time.time())
        self._cache.set(self._key(exchange, symbol, interval), payload)

    def is_fresh(self, exchange: str, symbol: str, interval: str, ttl: int = None) -> bool:
        cached_at = self.get_cached_at(exchange, symbol, interval)
        if cached_at is None:
            return False
        ttl = ttl if ttl is not None else settings.cache_ttl_seconds
        return (time.time() - cached_at) < ttl

    def merge_incremental(
        self, exchange: str, symbol: str, interval: str, new_candles: List[Candle]
    ) -> List[Candle]:
        existing = self.get(exchange, symbol, interval) or []
        by_time = {c.open_time: c for c in existing}
        for c in new_candles:
            by_time[c.open_time] = c
        merged = sorted(by_time.values(), key=lambda c: c.open_time)
        self.set(exchange, symbol, interval, merged)
        return merged


candle_cache = CandleCache()