from fastapi import APIRouter, HTTPException

from app.api.schemas import (
    SearchRequest,
    SearchResponse,
    MatchResultResponse,
    ConceptScanRequest,
    ConceptScanResponse,
    HTFLiquidityScanRequest,
    HTFLiquidityScanResponse,
    HTFLiquidityResult,
    LTFLiquidityScanRequest,
    LTFLiquidityScanResponse,
    LTFLiquiditySignal,
)
from app.market_data.binance_client import BinanceClient
from app.market_data.symbol_cache import symbol_cache
from app.scanner.market_scanner import MarketScanner
from app.features.pattern_detectors import CONCEPT_REGISTRY
from app.config import settings

router = APIRouter()

_binance_client = BinanceClient()

HTF_TIMEFRAMES = ["1h", "4h", "1d"]
LTF_TIMEFRAMES = ["1m", "5m"]


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
            algorithm=payload.algorithm or settings.default_algorithm,
            top_n=payload.top_n,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    symbols = await symbol_cache.get_symbols(_binance_client, settings.quote_asset_filter)

    return SearchResponse(
        results=[MatchResultResponse(**r.model_dump()) for r in results],
        scanned_symbols=len(symbols),
        timeframe=timeframe,
        algorithm=payload.algorithm or settings.default_algorithm,
    )


@router.post("/concept-scan", response_model=ConceptScanResponse)
async def concept_scan(payload: ConceptScanRequest):
    if payload.concept not in CONCEPT_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown concept '{payload.concept}'. Available: {list(CONCEPT_REGISTRY.keys())}",
        )

    timeframe = payload.timeframe or settings.default_timeframe
    if timeframe not in settings.supported_timeframes:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported timeframe. Choose from {settings.supported_timeframes}",
        )

    scanner = MarketScanner(_binance_client)
    try:
        results = await scanner.scan_concept(
            concept=payload.concept,
            interval=timeframe,
            top_n=payload.top_n,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    symbols = await symbol_cache.get_symbols(_binance_client, settings.quote_asset_filter)

    return ConceptScanResponse(
        results=[MatchResultResponse(**r.model_dump()) for r in results],
        scanned_symbols=len(symbols),
        timeframe=timeframe,
        concept=payload.concept,
    )


@router.post("/htf-liquidity-scan", response_model=HTFLiquidityScanResponse)
async def htf_liquidity_scan(payload: HTFLiquidityScanRequest):
    timeframe = payload.timeframe or "1h"
    if timeframe not in HTF_TIMEFRAMES:
        raise HTTPException(
            status_code=400, detail=f"Unsupported HTF timeframe. Choose from {HTF_TIMEFRAMES}"
        )

    scanner = MarketScanner(_binance_client)
    results = await scanner.scan_htf_liquidity(interval=timeframe, top_n=payload.top_n)
    symbols = await symbol_cache.get_symbols(_binance_client, settings.quote_asset_filter)

    return HTFLiquidityScanResponse(
        results=[HTFLiquidityResult(**r) for r in results],
        scanned_symbols=len(symbols),
        timeframe=timeframe,
    )


@router.post("/ltf-liquidity-scan", response_model=LTFLiquidityScanResponse)
async def ltf_liquidity_scan(payload: LTFLiquidityScanRequest):
    ltf_timeframe = payload.ltf_timeframe or "5m"
    htf_timeframe = payload.htf_timeframe or "1h"
    if ltf_timeframe not in LTF_TIMEFRAMES:
        raise HTTPException(
            status_code=400, detail=f"Unsupported LTF timeframe. Choose from {LTF_TIMEFRAMES}"
        )
    if htf_timeframe not in HTF_TIMEFRAMES:
        raise HTTPException(
            status_code=400, detail=f"Unsupported HTF timeframe. Choose from {HTF_TIMEFRAMES}"
        )

    scanner = MarketScanner(_binance_client)
    results = await scanner.scan_ltf_liquidity(
        ltf_interval=ltf_timeframe, htf_interval=htf_timeframe, top_n=payload.top_n
    )
    symbols = await symbol_cache.get_symbols(_binance_client, settings.quote_asset_filter)

    return LTFLiquidityScanResponse(
        results=[LTFLiquiditySignal(**r) for r in results],
        scanned_symbols=len(symbols),
        ltf_timeframe=ltf_timeframe,
        htf_timeframe=htf_timeframe,
    )