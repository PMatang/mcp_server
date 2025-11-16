import asyncio
import ccxt.async_support as ccxt
from typing import Optional, List
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class ExchangeWrapper:
    def __init__(self, exchange_id: str):
        self.exchange_id = exchange_id.lower()
        self._exchange = None

    async def _get_exchange(self):
        if self._exchange is None:
            try:
                klass = getattr(ccxt, self.exchange_id)
            except AttributeError:
                raise ValueError(f"Unsupported exchange: {self.exchange_id}")
            self._exchange = klass({
                'enableRateLimit': True,
                'timeout': settings.CCXT_TIMEOUT * 1000,
            })
        return self._exchange

    async def fetch_ticker(self, symbol: str):
        exch = await self._get_exchange()
        try:
            return await exch.fetch_ticker(symbol)
        finally:
            # keep instance open to reuse connections; don't close here
            pass

    async def fetch_ohlcv(self, symbol: str, timeframe: str = '1m', since: Optional[int] = None, limit: Optional[int] = 100):
        exch = await self._get_exchange()
        # Some exchanges may not support since/limit simultaneously; handle gracefully.
        return await exch.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)

    async def close(self):
        if self._exchange is not None:
            try:
                await self._exchange.close()
            except Exception as e:
                logger.exception("Error closing exchange connection: %s", e)
            self._exchange = None
