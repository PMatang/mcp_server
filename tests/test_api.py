import pytest
import time
from app.config import settings

def test_get_ticker_invalid_exchange(client):
    r = client.get("/tickers/invalidexchange/BTC/USDT")
    assert r.status_code == 404 or r.status_code == 400

def test_get_ohlcv_invalid_exchange(client):
    r = client.get("/ohlcv/invalidexchange/BTC/USDT")
    assert r.status_code == 404 or r.status_code == 400

# Note: the following tests hit real exchanges via ccxt and require internet.
# They are marked optional to avoid breaking CI without internet or exchange support.

@pytest.mark.skip(reason="requires internet and supported exchange/symbol")
def test_binance_ticker_live(client):
    r = client.get("/tickers/binance/BTC/USDT")
    assert r.status_code == 200
    json = r.json()
    assert "last" in json

@pytest.mark.skip(reason="requires internet and supported exchange/symbol")
def test_binance_ohlcv_live(client):
    r = client.get("/ohlcv/binance/BTC/USDT?timeframe=1m&limit=2")
    assert r.status_code == 200
    arr = r.json()
    assert isinstance(arr, list)
