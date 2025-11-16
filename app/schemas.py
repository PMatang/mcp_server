from pydantic import BaseModel
from typing import List, Optional

class Ticker(BaseModel):
    symbol: str
    bid: Optional[float]
    ask: Optional[float]
    last: Optional[float]
    timestamp: Optional[int]
    info: Optional[dict]

class OHLCV(BaseModel):
    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float

class ErrorResponse(BaseModel):
    error: str
