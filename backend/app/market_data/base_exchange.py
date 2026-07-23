from abc import ABC, abstractmethod
from typing import List
from pydantic import BaseModel


class Candle(BaseModel):
    open_time: int  # ms epoch
    open: float
    high: float
    low: float
    close: float
    volume: float
    close_time: int


class SymbolInfo(BaseModel):
    symbol: str
    base_asset: str
    quote_asset: str
    status: str


class BaseExchangeClient(ABC):
    """
    Every exchange adapter (Binance, Bybit, OKX, KuCoin...) must implement
    this interface so the scanner/market_data layer stays exchange-agnostic.
    """

    exchange_name: str = "base"

    @abstractmethod
    async def get_symbols(self, quote_asset: str = "USDT") -> List[SymbolInfo]:
        """Return all tradable spot symbols for the given quote asset."""
        raise NotImplementedError

    @abstractmethod
    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 200,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> List[Candle]:
        """Fetch OHLCV candles for a symbol/interval."""
        raise NotImplementedError