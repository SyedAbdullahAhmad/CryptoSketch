import httpx
from typing import List, Optional

from app.market_data.base_exchange import BaseExchangeClient, Candle, SymbolInfo
from app.config import settings


class BinanceClient(BaseExchangeClient):
    """
    Uses only Binance's free, public Spot REST endpoints.
    No API key required for market data.
    Docs: https://binance-docs.github.io/apidocs/spot/en/
    """

    exchange_name = "binance"

    def __init__(self, base_url: str = None, client: Optional[httpx.AsyncClient] = None):
        self.base_url = base_url or settings.binance_base_url
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=settings.request_timeout_seconds,
        )

    async def get_symbols(self, quote_asset: str = "USDT") -> List[SymbolInfo]:
        resp = await self._client.get("/api/v3/exchangeInfo")
        resp.raise_for_status()
        data = resp.json()

        symbols: List[SymbolInfo] = []
        for s in data.get("symbols", []):
            if (
                s.get("quoteAsset") == quote_asset
                and s.get("status") == "TRADING"
                and s.get("isSpotTradingAllowed", True)
            ):
                symbols.append(
                    SymbolInfo(
                        symbol=s["symbol"],
                        base_asset=s["baseAsset"],
                        quote_asset=s["quoteAsset"],
                        status=s["status"],
                    )
                )
        return symbols

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 200,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> List[Candle]:
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time

        resp = await self._client.get("/api/v3/klines", params=params)
        resp.raise_for_status()
        raw = resp.json()

        candles: List[Candle] = []
        for k in raw:
            candles.append(
                Candle(
                    open_time=k[0],
                    open=float(k[1]),
                    high=float(k[2]),
                    low=float(k[3]),
                    close=float(k[4]),
                    volume=float(k[5]),
                    close_time=k[6],
                )
            )
        return candles

    async def aclose(self):
        await self._client.aclose()