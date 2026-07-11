# app/exchanges/okx.py
import json

from app.exchanges.base import BaseExchangeWebSocket
from app.core.market_data import MarketSnapshot
from app.core.symbols import normalize_symbol, to_okx_spot_symbol


class OKXWebSocket(BaseExchangeWebSocket):
    WS_URL = "wss://ws.okx.com:8443/ws/v5/public"
    EXCHANGE_NAME = "OKX"
    MAX_SIZE = 2048

    async def _subscribe(self, ws):
        msg = {
            "op": "subscribe",
            "args": [
                {"channel": "tickers", "instId": to_okx_spot_symbol(symbol)}
                for symbol in self.symbols
            ]
        }
        await ws.send(json.dumps(msg))

    def _parse_message(self, data: dict) -> MarketSnapshot | None:
        # OKX присылает {"arg": {...}, "data": [{...}]}
        if "data" not in data:
            return None

        tickers = data.get("data", [])
        if not tickers:
            return None

        ticker = tickers[0]
        if ticker.get("bidPx") is None or ticker.get("askPx") is None:
            return None

        return MarketSnapshot(
            exchange=self.EXCHANGE_NAME,
            symbol=normalize_symbol(ticker.get("instId", "")),
            bid_price=float(ticker["bidPx"]),
            ask_price=float(ticker["askPx"]),
            bid_size=float(ticker.get("bidSz", 0) or 0),
            ask_size=float(ticker.get("askSz", 0) or 0),
            last_price=float(ticker["last"]) if ticker.get("last") else None,
        )
