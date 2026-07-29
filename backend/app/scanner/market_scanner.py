import asyncio
from concurrent.futures import ProcessPoolExecutor
from typing import List, Dict
from pydantic import BaseModel

from app.market_data.base_exchange import BaseExchangeClient, Candle
from app.market_data.symbol_cache import symbol_cache
from app.cache.candle_cache import candle_cache
from app.rolling_window.window_generator import generate_rolling_windows
from app.normalization.normalizer import normalize_window, normalize_drawing
from app.similarity_engine.engine import similarity_engine
from app.features.structure_features import extract_features, generate_reasons
from app.features.pattern_detectors import CONCEPT_REGISTRY, run_detector
from app.liquidity.liquidity_engine import detect_htf_bias, detect_ltf_signal, HTF_CONFLUENCE_TFS
from app.config import settings


class MatchResult(BaseModel):
    symbol: str
    exchange: str
    timeframe: str
    similarity: float
    start_time: int
    end_time: int
    closes: List[float]
    reasons: List[str] = []


def _compute_matches_for_symbol(
    symbol: str,
    exchange: str,
    interval: str,
    candles_raw: list,
    window_size: int,
    stride: int,
    algorithm: str,
    normalized_drawing: list,
) -> List[dict]:
    candles = [Candle(**c) for c in candles_raw]
    windows = generate_rolling_windows(symbol, interval, candles, window_size, stride=stride)

    best = None
    for w in windows:
        normalized_window = normalize_window(w.closes)
        sim = similarity_engine.score(normalized_drawing, normalized_window, algorithm=algorithm)
        if best is None or sim > best["similarity"]:
            reasons = generate_reasons(extract_features(w.closes))
            best = {
                "symbol": symbol,
                "exchange": exchange,
                "timeframe": interval,
                "similarity": sim,
                "start_time": w.start_time,
                "end_time": w.end_time,
                "closes": w.closes,
                "reasons": reasons,
            }
    return [best] if best else []


def _compute_htf_bias_for_symbol(
    symbol: str, exchange: str, primary_interval: str, candles_raw_by_tf: Dict[str, list]
) -> dict:
    candles_by_tf = {tf: [Candle(**c) for c in raw] for tf, raw in candles_raw_by_tf.items()}
    bias = detect_htf_bias(candles_by_tf, primary_interval)
    event_note = "(event-level, confirmed across HTFs) " if bias["event_liquidity"] else ""
    taken_note = "already taken" if bias["liquidity_taken"] else "not yet taken"
    reason = (
        f"{bias['trend'].capitalize()} HTF trend with {bias['liquidity_type']} liquidity "
        f"{event_note}at {bias['liquidity_zone']:.6g} ({taken_note})."
    )
    primary_candles = candles_by_tf[primary_interval]
    return {
        "symbol": symbol,
        "exchange": exchange,
        "timeframe": primary_interval,
        "trend": bias["trend"],
        "liquidity_zone": bias["liquidity_zone"],
        "liquidity_type": bias["liquidity_type"],
        "liquidity_taken": bias["liquidity_taken"],
        "event_liquidity": bias["event_liquidity"],
        "bias": bias["bias"],
        "confidence": "High" if bias["event_liquidity"] else "Medium",
        "reason": reason,
        "closes": [c.close for c in primary_candles][-30:],
    }


def _compute_ltf_signal_for_symbol(
    symbol: str,
    exchange: str,
    ltf_interval: str,
    htf_interval: str,
    ltf_candles_raw: list,
    htf_candles_raw_by_tf: Dict[str, list],
):
    htf_candles_by_tf = {tf: [Candle(**c) for c in raw] for tf, raw in htf_candles_raw_by_tf.items()}
    ltf_candles = [Candle(**c) for c in ltf_candles_raw]

    htf_bias = detect_htf_bias(htf_candles_by_tf, htf_interval)
    if htf_bias["bias"] == "neutral":
        return None

    signal = detect_ltf_signal(ltf_candles, htf_bias)
    if signal is None:
        return None

    return {
        "symbol": symbol,
        "exchange": exchange,
        "timeframe": ltf_interval,
        "htf_timeframe": htf_interval,
        "trend": signal["trend"],
        "htf_bias": signal["htf_bias"],
        "liquidity_type": signal["liquidity_type"],
        "liquidity_price": signal["liquidity_price"],
        "liquidity_status": signal["liquidity_status"],
        "signal": signal["signal"],
        "confidence": signal["confidence"],
        "entry_price": signal["entry_price"],
        "stop_loss": signal["stop_loss"],
        "target_price": signal["target_price"],
        "reason": signal["reason"],
        "closes": [c.close for c in ltf_candles][-30:],
    }


class MarketScanner:
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
        algorithm: str = None,
        top_n: int = None,
        stride: int = 10,
    ) -> List[MatchResult]:
        interval = interval or settings.default_timeframe
        window_size = window_size or settings.default_window_size
        algorithm = algorithm or settings.default_algorithm
        top_n = top_n or settings.top_n_results

        normalized_drawing = normalize_drawing(drawing_points_y, window_size).tolist()

        symbols = await symbol_cache.get_symbols(self.client, settings.quote_asset_filter)

        semaphore = asyncio.Semaphore(settings.max_concurrent_requests)

        async def fetch(sym_info):
            async with semaphore:
                candles = await self._get_candles_for_symbol(sym_info.symbol, interval)
            if len(candles) < window_size:
                return None
            return (sym_info.symbol, [c.model_dump() for c in candles])

        fetched = await asyncio.gather(*(fetch(s) for s in symbols))
        fetched = [f for f in fetched if f is not None]

        loop = asyncio.get_running_loop()
        with ProcessPoolExecutor() as pool:
            tasks = [
                loop.run_in_executor(
                    pool,
                    _compute_matches_for_symbol,
                    symbol,
                    self.client.exchange_name,
                    interval,
                    candles_raw,
                    window_size,
                    stride,
                    algorithm,
                    normalized_drawing,
                )
                for symbol, candles_raw in fetched
            ]
            per_symbol_results = await asyncio.gather(*tasks)

        flat = [MatchResult(**r) for sub in per_symbol_results for r in sub]
        flat.sort(key=lambda r: r.similarity, reverse=True)
        return flat[:top_n]

    async def scan_concept(
        self,
        concept: str,
        interval: str = None,
        top_n: int = None,
        lookback: int = None,
    ) -> List[MatchResult]:
        if concept not in CONCEPT_REGISTRY:
            raise ValueError(f"Unknown concept '{concept}'")

        interval = interval or settings.default_timeframe
        top_n = top_n or settings.top_n_results
        lookback = lookback or settings.concept_lookback_candles

        symbols = await symbol_cache.get_symbols(self.client, settings.quote_asset_filter)
        semaphore = asyncio.Semaphore(settings.max_concurrent_requests)

        async def fetch(sym_info):
            async with semaphore:
                candles = await self._get_candles_for_symbol(sym_info.symbol, interval)
            if len(candles) < 10:
                return None
            tail = candles[-lookback:]
            return (sym_info.symbol, [c.model_dump() for c in tail])

        fetched = await asyncio.gather(*(fetch(s) for s in symbols))
        fetched = [f for f in fetched if f is not None]

        loop = asyncio.get_running_loop()
        with ProcessPoolExecutor() as pool:
            tasks = [
                loop.run_in_executor(pool, run_detector, concept, symbol, candles_raw)
                for symbol, candles_raw in fetched
            ]
            raw_results = await asyncio.gather(*tasks)

        matches = [
            MatchResult(
                symbol=r["symbol"],
                exchange=self.client.exchange_name,
                timeframe=interval,
                similarity=r["score"],
                start_time=r["start_time"],
                end_time=r["end_time"],
                closes=r["closes"],
                reasons=r["reasons"],
            )
            for r in raw_results if r is not None
        ]
        matches.sort(key=lambda m: m.similarity, reverse=True)
        return matches[:top_n]

    async def scan_htf_liquidity(self, interval: str = "1h", top_n: int = None) -> List[dict]:
        top_n = top_n or settings.top_n_results
        symbols = await symbol_cache.get_symbols(self.client, settings.quote_asset_filter)
        semaphore = asyncio.Semaphore(settings.max_concurrent_requests)

        async def fetch(sym_info):
            async with semaphore:
                tf_results = await asyncio.gather(
                    *(self._get_candles_for_symbol(sym_info.symbol, tf) for tf in HTF_CONFLUENCE_TFS)
                )
            candles_by_tf = dict(zip(HTF_CONFLUENCE_TFS, tf_results))
            if any(len(c) < 20 for c in candles_by_tf.values()):
                return None
            candles_by_tf = {tf: c[-60:] for tf, c in candles_by_tf.items()}
            return (sym_info.symbol, {tf: [c.model_dump() for c in cs] for tf, cs in candles_by_tf.items()})

        fetched = await asyncio.gather(*(fetch(s) for s in symbols))
        fetched = [f for f in fetched if f is not None]

        loop = asyncio.get_running_loop()
        with ProcessPoolExecutor() as pool:
            tasks = [
                loop.run_in_executor(
                    pool, _compute_htf_bias_for_symbol, symbol, self.client.exchange_name, interval, candles_by_tf_raw
                )
                for symbol, candles_by_tf_raw in fetched
            ]
            results = await asyncio.gather(*tasks)

        results.sort(key=lambda r: (r["event_liquidity"], r["confidence"] == "High"), reverse=True)
        return results[:top_n]

    async def scan_ltf_liquidity(
        self, ltf_interval: str = "5m", htf_interval: str = "1h", top_n: int = None
    ) -> List[dict]:
        top_n = top_n or settings.top_n_results
        symbols = await symbol_cache.get_symbols(self.client, settings.quote_asset_filter)
        semaphore = asyncio.Semaphore(settings.max_concurrent_requests)

        async def fetch(sym_info):
            async with semaphore:
                all_tfs = [ltf_interval] + HTF_CONFLUENCE_TFS
                results = await asyncio.gather(
                    *(self._get_candles_for_symbol(sym_info.symbol, tf) for tf in all_tfs)
                )
            candles_by_tf = dict(zip(all_tfs, results))

            ltf_candles = candles_by_tf[ltf_interval]
            if len(ltf_candles) < 30:
                return None
            if any(len(candles_by_tf[tf]) < 20 for tf in HTF_CONFLUENCE_TFS):
                return None

            htf_candles_by_tf = {tf: candles_by_tf[tf][-60:] for tf in HTF_CONFLUENCE_TFS}

            return (
                sym_info.symbol,
                [c.model_dump() for c in ltf_candles[-50:]],
                {tf: [c.model_dump() for c in cs] for tf, cs in htf_candles_by_tf.items()},
            )

        fetched = await asyncio.gather(*(fetch(s) for s in symbols))
        fetched = [f for f in fetched if f is not None]

        loop = asyncio.get_running_loop()
        with ProcessPoolExecutor() as pool:
            tasks = [
                loop.run_in_executor(
                    pool,
                    _compute_ltf_signal_for_symbol,
                    symbol,
                    self.client.exchange_name,
                    ltf_interval,
                    htf_interval,
                    ltf_raw,
                    htf_raw_by_tf,
                )
                for symbol, ltf_raw, htf_raw_by_tf in fetched
            ]
            results = await asyncio.gather(*tasks)

        signals = [r for r in results if r is not None]
        signals.sort(key=lambda r: r["confidence"] == "High", reverse=True)
        return signals[:top_n]