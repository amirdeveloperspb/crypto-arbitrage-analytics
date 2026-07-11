# app/exchanges/gateio.py
import json
import time

from app.core.market_data import MarketSnapshot
from app.core.symbols import normalize_symbol, to_gate_symbol
from app.exchanges.base import BaseExchangeWebSocket


class GateIOWebSocket(BaseExchangeWebSocket):
    WS_URL = "wss://api.gateio.ws/ws/v4/"
    EXCHANGE_NAME = "GATEIO"
    MAX_SIZE = 4096

    async def _subscribe(self, ws):
        msg = {
            "time": int(time.time()),
            "channel": "spot.book_ticker",
            "event": "subscribe",
            "payload": [to_gate_symbol(symbol) for symbol in self.symbols],
        }
        await ws.send(json.dumps(msg))

    def _parse_message(self, data: dict) -> MarketSnapshot | None:
        if data.get("channel") != "spot.book_ticker" or data.get("event") != "update":
            return None

        ticker = data.get("result", {})
        if not {"s", "b", "a"}.issubset(ticker):
            return None

        return MarketSnapshot(
            exchange=self.EXCHANGE_NAME,
            symbol=normalize_symbol(ticker["s"]),
            bid_price=float(ticker["b"]),
            ask_price=float(ticker["a"]),
            bid_size=float(ticker.get("B", 0) or 0),
            ask_size=float(ticker.get("A", 0) or 0),
        )
