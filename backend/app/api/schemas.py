from typing import List, Optional
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    drawing_points_y: List[float] = Field(
        ..., description="Y-coordinates of the user's drawing, left to right, canvas space (0=top)."
    )
    timeframe: Optional[str] = Field(default=None, description="e.g. 1m, 5m, 15m, 1h, 4h, 1d")
    window_size: Optional[int] = Field(default=None, description="Number of candles to compare against")
    algorithm: Optional[str] = Field(default="dtw", description="Similarity algorithm name")
    top_n: Optional[int] = Field(default=None, description="Number of results to return")


class MatchResultResponse(BaseModel):
    symbol: str
    exchange: str
    timeframe: str
    similarity: float
    start_time: int
    end_time: int
    closes: List[float]


class SearchResponse(BaseModel):
    results: List[MatchResultResponse]
    scanned_symbols: int
    timeframe: str
    algorithm: str