import time
from typing import List, Optional

from app.market_data.base_exchange import BaseExchangeClient, SymbolInfo
from app.config import settings


class SymbolCache:
    """
    Caches the tradable symbol list per exchange in memory.
    Symbol lists change rarely, so a long TTL is fine.
    """

    def __init__(self):
        self._symbols: dict[str, List[SymbolInfo]] = {}
        self._cached_at: dict[str, float] = {}

    async def get_symbols(
        self, client: BaseExchangeClient, quote_asset: str = "USDT"
    ) -> List[SymbolInfo]:
        key = f"{client.exchange_name}:{quote_asset}"
        cached_at = self._cached_at.get(key)
        if cached_at and (time.time() - cached_at) < settings.symbol_cache_ttl_seconds:
            return self._symbols[key]

        symbols = await client.get_symbols(quote_asset)
        self._symbols[key] = symbols
        self._cached_at[key] = time.time()
        return symbols


symbol_cache = SymbolCache()