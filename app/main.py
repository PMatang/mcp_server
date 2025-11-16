import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Set, Any, List, Optional
from app.exchangewrapper import ExchangeWrapper
from app.config import settings
from app.schemas import Ticker, OHLCV, ErrorResponse
from app.cache import get_cache
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp_server")

app = FastAPI(title=settings.APP_NAME)

# Allow CORS for local dev (tweak in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# In-memory pubsub for websockets — for simple demo use. Replace with Redis pub/sub for scaling.
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, topic: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(topic, set()).add(websocket)
        logger.info("WebSocket connected to topic %s; connections=%s", topic, len(self.active_connections[topic]))

    def disconnect(self, topic: str, websocket: WebSocket):
        conns = self.active_connections.get(topic)
        if conns and websocket in conns:
            conns.remove(websocket)

    async def broadcast(self, topic: str, message: Any):
        conns = list(self.active_connections.get(topic, []))
        for conn in conns:
            try:
                await conn.send_json(message)
            except Exception:
                logger.exception("Failed to send to websocket; removing.")
                self.disconnect(topic, conn)


manager = ConnectionManager()

# Background polling tasks store
_poll_tasks: Dict[str, asyncio.Task] = {}
_cache = get_cache()

async def _poll_ticker(exchange_id: str, symbol: str):
    key = f"ticker::{exchange_id}::{symbol}"
    wrapper = ExchangeWrapper(exchange_id)
    try:
        while True:
            try:
                data = await wrapper.fetch_ticker(symbol)
                _cache[key] = data
                await manager.broadcast(key, {"type": "ticker", "exchange": exchange_id, "symbol": symbol, "data": data})
            except Exception as e:
                logger.exception("Polling error for %s:%s - %s", exchange_id, symbol, e)
            await asyncio.sleep(settings.POLL_INTERVAL_SECONDS)
    finally:
        await wrapper.close()

def ensure_polling(exchange_id: str, symbol: str):
    key = f"ticker::{exchange_id}::{symbol}"
    if key not in _poll_tasks or _poll_tasks[key].done():
        _poll_tasks[key] = asyncio.create_task(_poll_ticker(exchange_id, symbol))
        logger.info("Started polling for %s", key)

@app.get("/tickers/{exchange_id}/{symbol}", response_model=Ticker, responses={404: {"model": ErrorResponse}})
async def get_ticker(exchange_id: str, symbol: str):
    key = f"ticker::{exchange_id}::{symbol}"
    # Start background polling to keep cache warm
    ensure_polling(exchange_id, symbol)

    # Return cached result if available, else attempt one fetch
    if key in _cache:
        data = _cache[key]
        return _map_ticker(data, symbol)
    else:
        wrapper = ExchangeWrapper(exchange_id)
        try:
            data = await wrapper.fetch_ticker(symbol)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.exception("Fetch ticker failed: %s", e)
            raise HTTPException(status_code=502, detail="Upstream fetch failed")
        _cache[key] = data
        return _map_ticker(data, symbol)

def _map_ticker(raw: dict, symbol: str):
    return {
        "symbol": symbol,
        "bid": raw.get("bid"),
        "ask": raw.get("ask"),
        "last": raw.get("last"),
        "timestamp": raw.get("timestamp"),
        "info": raw.get("info"),
    }

@app.get("/ohlcv/{exchange_id}/{symbol}", response_model=List[OHLCV])
async def get_ohlcv(exchange_id: str, symbol: str, timeframe: str = "1m", since: Optional[int] = None, limit: int = 100):
    wrapper = ExchangeWrapper(exchange_id)
    try:
        rows = await wrapper.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Fetch ohlcv failed: %s", e)
        raise HTTPException(status_code=502, detail="Upstream fetch failed")
    # ccxt returns list of [ts, open, high, low, close, volume]
    results = [{"ts": r[0], "open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": r[5]} for r in rows]
    return results

@app.websocket("/ws/ticker/{exchange_id}/{symbol}")
async def ws_ticker(websocket: WebSocket, exchange_id: str, symbol: str):
    key = f"ticker::{exchange_id}::{symbol}"
    await manager.connect(key, websocket)
    # ensure background polling
    ensure_polling(exchange_id, symbol)
    try:
        while True:
            # Keep connection alive; client can send pings or subscribe/unsubscribe in extended versions.
            data = await websocket.receive_text()
            # We simply echo back a heartbeat to keep things alive.
            await websocket.send_text(f"received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(key, websocket)

# Optional CoinMarketCap passthrough endpoint (requires API key in env)
import os
import httpx

@app.get("/cmc/quotes/{symbol}")
async def cmc_quote(symbol: str):
    api_key = settings.COINMARKETCAP_API_KEY
    if not api_key:
        raise HTTPException(status_code=400, detail="CMC API key not configured")
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    params = {"symbol": symbol}
    headers = {"X-CMC_PRO_API_KEY": api_key}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params, headers=headers)
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="CMC upstream error")
        return resp.json()

@app.on_event("shutdown")
async def shutdown_event():
    # Cancel polling tasks nicely
    for k, t in list(_poll_tasks.items()):
        if not t.done():
            t.cancel()
    logger.info("MCP server shutting down")
