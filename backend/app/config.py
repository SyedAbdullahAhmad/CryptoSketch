from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Exchange API
    binance_base_url: str = "https://api.binance.com"
    binance_klines_limit: int = 200  # candles per request

    # Symbols / scanning
    quote_asset_filter: str = "USDT"
    supported_timeframes: List[str] = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
    default_timeframe: str = "1h"

    # Rolling windows
    default_window_size: int = 30  # number of candles compared to a drawing
    concept_lookback_candles: int = 60  # candles used for concept/pattern detectors

    # Similarity
    default_algorithm: str = "feature"
    top_n_results: int = 20

    # Liquidity scanner (HTF/LTF)
    htf_confluence_lookback_days: float = 7.0  # calendar window aligned across 1h/4h/1d
    htf_min_candles_for_structure: int = 15    # floor so swing detection has enough data
    max_htf_confluence_candles: int = 500      # ceiling so 1h fetches don't explode

    # Caching
    cache_dir: str = ".cache/candles"
    cache_ttl_seconds: int = 60
    symbol_cache_ttl_seconds: int = 3600

    # Concurrency
    max_concurrent_requests: int = 15
    request_timeout_seconds: float = 10.0

    class Config:
        env_prefix = "CRYPTOSKETCH_"
        env_file = ".env"


settings = Settings()