from typing import List, Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    drawing_points_y: List[float] = Field(
        ..., description="Y-coordinates of the user's drawing, left to right, canvas space (0=top)."
    )
    timeframe: Optional[str] = Field(default=None, description="e.g. 1m, 5m, 15m, 30m, 1h, 4h, 1d")
    window_size: Optional[int] = Field(default=None, description="Number of candles to compare against")
    algorithm: Optional[str] = Field(default="feature", description="Similarity algorithm name")
    top_n: Optional[int] = Field(default=None, description="Number of results to return")


class MatchResultResponse(BaseModel):
    symbol: str
    exchange: str
    timeframe: str
    similarity: float
    start_time: int
    end_time: int
    closes: List[float]
    reasons: List[str] = []


class SearchResponse(BaseModel):
    results: List[MatchResultResponse]
    scanned_symbols: int
    timeframe: str
    algorithm: str


class ConceptScanRequest(BaseModel):
    concept: str = Field(..., description="Concept key, e.g. 'trend', 'fair_value_gap', 'bull_flag'")
    timeframe: Optional[str] = Field(default=None)
    top_n: Optional[int] = Field(default=None)


class ConceptScanResponse(BaseModel):
    results: List[MatchResultResponse]
    scanned_symbols: int
    timeframe: str
    concept: str


class HTFLiquidityScanRequest(BaseModel):
    timeframe: Optional[str] = Field(default="1h", description="1h, 4h, or 1d")
    top_n: Optional[int] = Field(default=None)


class HTFLiquidityResult(BaseModel):
    symbol: str
    exchange: str
    timeframe: str
    trend: str
    liquidity_zone: float
    liquidity_type: str
    liquidity_taken: bool
    event_liquidity: bool
    bias: str
    confidence: str
    reason: str
    closes: List[float]


class HTFLiquidityScanResponse(BaseModel):
    results: List[HTFLiquidityResult]
    scanned_symbols: int
    timeframe: str


class LTFLiquidityScanRequest(BaseModel):
    ltf_timeframe: Optional[str] = Field(default="5m", description="1m or 5m")
    htf_timeframe: Optional[str] = Field(default="1h", description="1h, 4h, or 1d")
    top_n: Optional[int] = Field(default=None)


class LTFLiquiditySignal(BaseModel):
    symbol: str
    exchange: str
    timeframe: str
    htf_timeframe: str
    trend: str
    htf_bias: str
    liquidity_type: str
    liquidity_price: float
    liquidity_status: str
    signal: str
    confidence: str
    entry_price: float
    stop_loss: float
    target_price: float
    reason: str
    closes: List[float]


class LTFLiquidityScanResponse(BaseModel):
    results: List[LTFLiquiditySignal]
    scanned_symbols: int
    ltf_timeframe: str
    htf_timeframe: str