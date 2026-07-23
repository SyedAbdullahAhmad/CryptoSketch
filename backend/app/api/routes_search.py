from fastapi import APIRouter, HTTPException

from app.api.schemas import SearchRequest, SearchResponse, MatchResultResponse
from app.market_data.binance_client import BinanceClient
from app.market_data.symbol_cache import symbol_cache
from app.scanner.market_scanner import MarketScanner
from app.config import settings

router = APIRouter()

_binance_client = BinanceClient()


@router.post("/search", response_model=SearchResponse)
async def search(payload: SearchRequest):
    if not payload.drawing_points_y or len(payload.drawing_points_y) < 2:
        raise HTTPException(status_code=400, detail="Drawing must contain at least 2 points.")

    timeframe = payload.timeframe or settings.default_timeframe
    if timeframe not in settings.supported_timeframes:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported timeframe. Choose from {settings.supported_timeframes}",
        )

    flipped_y = [-y for y in payload.drawing_points_y]

    scanner = MarketScanner(_binance_client)
    try:
        results = await scanner.scan(
            drawing_points_y=flipped_y,
            interval=timeframe,
            window_size=payload.window_size,
            algorithm=payload.algorithm or "dtw",
            top_n=payload.top_n,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    symbols = await symbol_cache.get_symbols(_binance_client, settings.quote_asset_filter)

    return SearchResponse(
        results=[MatchResultResponse(**r.model_dump()) for r in results],
        scanned_symbols=len(symbols),
        timeframe=timeframe,
        algorithm=payload.algorithm or "dtw",
    )