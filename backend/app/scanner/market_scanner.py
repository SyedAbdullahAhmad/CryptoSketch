import asyncio
from typing import List
from pydantic import BaseModel

from app.market_data.base_exchange import BaseExchangeClient
from app.market_data.symbol_cache import symbol_cache
from app.cache.candle_cache import candle_cache
from app.rolling_window.window_generator import generate_rolling_windows
from app.normalization.normalizer import normalize_window, normalize_drawing
from app.similarity_engine.engine import similarity_engine
from app.config import settings


class MatchResult(BaseModel):
    symbol: str
    exchange: str
    timeframe: str
    similarity: float
    start_time: int
    end_time: int
    closes: List[float]  # for mini chart rendering


class MarketScanner:
    """
    Single responsibility: given a user drawing, scan every symbol on a
    given exchange/timeframe and return ranked similarity matches.
    Fetching is parallelized and cache-aware to avoid redundant downloads.
    """

    def __init__(self, client: BaseExchangeClient):
        self.client = client

    async def _get_candles_for_symbol(self, symbol: str, interval: str):
        exchange = self.client.exchange_name

        if candle_cache.is_fresh(exchange, symbol, interval):
            return candle_cache.get(exchange, symbol, interval)

        try:
            fresh = await self.client.get_klines(
                symbol=symbol, interval=interval, limit=settings.binance_klines_limit
            )
        except Exception:
            return candle_cache.get(exchange, symbol, interval) or []

        return candle_cache.merge_incremental(exchange, symbol, interval, fresh)

    async def scan(
        self,
        drawing_points_y: List[float],
        interval: str = None,
        window_size: int = None,
        algorithm: str = "dtw",
        top_n: int = None,
    ) -> List[MatchResult]:
        interval = interval or settings.default_timeframe
        window_size = window_size or settings.default_window_size
        top_n = top_n or settings.top_n_results

        normalized_drawing = normalize_drawing(drawing_points_y, window_size)

        symbols = await symbol_cache.get_symbols(self.client, settings.quote_asset_filter)
        symbols = symbols[:20]  # TEMP: cap for testing, remove once performance is confirmed

        semaphore = asyncio.Semaphore(settings.max_concurrent_requests)

        async def process_symbol(sym_info) -> List[MatchResult]:
            async with semaphore:
                candles = await self._get_candles_for_symbol(sym_info.symbol, interval)

            if len(candles) < window_size:
                return []

            windows = generate_rolling_windows(
                sym_info.symbol, interval, candles, window_size, stride=10
            )

            results: List[MatchResult] = []
            for w in windows:
                normalized_window = normalize_window(w.closes)
                sim = similarity_engine.score(
                    normalized_drawing, normalized_window, algorithm=algorithm
                )
                results.append(
                    MatchResult(
                        symbol=sym_info.symbol,
                        exchange=self.client.exchange_name,
                        timeframe=interval,
                        similarity=sim,
                        start_time=w.start_time,
                        end_time=w.end_time,
                        closes=w.closes,
                    )
                )

            if results:
                return [max(results, key=lambda r: r.similarity)]
            return []

        per_symbol_results = await asyncio.gather(
            *(process_symbol(s) for s in symbols), return_exceptions=False
        )

        flat: List[MatchResult] = [r for sub in per_symbol_results for r in sub]
        flat.sort(key=lambda r: r.similarity, reverse=True)
        return flat[:top_n]