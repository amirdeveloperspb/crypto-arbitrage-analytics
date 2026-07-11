# app/exchanges/binance.py
from app.exchanges.base import BaseExchangeWebSocket
from app.core.market_data import MarketSnapshot
from app.core.symbols import normalize_symbol, to_lower_stream_symbol


class BinanceWebSocket(BaseExchangeWebSocket):
    EXCHANGE_NAME = "BINANCE"
    MAX_SIZE = 4096

    def __init__(self, state, symbols: tuple[str, ...] = ("SOLUSDT",)):
        super().__init__(state, symbols)
        streams = "/".join(f"{to_lower_stream_symbol(symbol)}@bookTicker" for symbol in symbols)
        self.WS_URL = f"wss://fstream.binance.com/stream?streams={streams}"

    def _parse_message(self, data: dict) -> MarketSnapshot | None:
        payload = data.get("data", data)
        if not {"s", "b", "a"}.issubset(payload):
            return None

        return MarketSnapshot(
            exchange=self.EXCHANGE_NAME,
            symbol=normalize_symbol(payload["s"]),
            bid_price=float(payload["b"]),
            ask_price=float(payload["a"]),
            bid_size=float(payload.get("B", 0) or 0),
            ask_size=float(payload.get("A", 0) or 0),
        )
