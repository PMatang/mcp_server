# mcp_server
The MCP (Market Data Provider) Server is a high-performance, Python-based backend service designed to deliver real-time and historical cryptocurrency market data from major global exchanges.Built using FastAPI, CCXT, and modern asynchronous programming.

1. Create virtualenv:
   python -m venv .venv
   .venv\Scripts\activate

2. Install Requirements / dependencies:
   pip install -r requirements.txt


3. Start:
   uvicorn app.main:app --reload --port 8000


4. Endpoints:
- `GET /tickers/{exchange_id}/{symbol}` — return last known ticker and start background polling.
  - Example: `/tickers/binance/BTC/USDT`
- `GET /ohlcv/{exchange_id}/{symbol}?timeframe=1m&limit=100` — fetch historical OHLCV via CCXT.
- `GET /cmc/quotes/{symbol}` — CoinMarketCap proxied quote (requires `COINMARKETCAP_API_KEY`).
- WebSocket: `ws://localhost:8000/ws/ticker/{exchange}/{symbol}` — realtime push (server polls exchanges).

## Tests
## server will start at:
http://localhost:8000

## swagger UI:
http://localhost:8000/docs

## Ticker:
http://127.0.0.1:8000/tickers/binance/BTCUSDT

## OHLCV:
http://127.0.0.1:8000/ohlcv/binance/BTCUSDT?timeframe=1m&limit=5
