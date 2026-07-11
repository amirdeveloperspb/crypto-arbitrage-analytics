# app/exchanges/bybit.py
import json

from app.exchanges.base import BaseExchangeWebSocket
from app.core.market_data import MarketSnapshot
from app.core.symbols import normalize_symbol


class BybitWebSocket(BaseExchangeWebSocket):
    WS_URL = "wss://stream.bybit.com/v5/public/linear"
    EXCHANGE_NAME = "BYBIT"
    MAX_SIZE = 2048

    async def _subscribe(self, ws):
        msg = {
            "op": "subscribe",
            "args": [f"tickers.{symbol}" for symbol in self.symbols]
        }
        await ws.send(json.dumps(msg))

    def _parse_message(self, data: dict) -> MarketSnapshot | None:
        if "data" not in data:
            return None

        ticker = data["data"]
        if "bid1Price" not in ticker or "ask1Price" not in ticker:
            return None

        return MarketSnapshot(
            exchange=self.EXCHANGE_NAME,
            symbol=normalize_symbol(ticker.get("symbol", "")),
            bid_price=float(ticker["bid1Price"]),
            ask_price=float(ticker["ask1Price"]),
            bid_size=float(ticker.get("bid1Size", 0) or 0),
            ask_size=float(ticker.get("ask1Size", 0) or 0),
            last_price=float(ticker["lastPrice"]) if ticker.get("lastPrice") else None,
        )
