import asyncio
import logging
import ssl
import time

import aiohttp
import certifi

from app.core.market_data import MarketDataState, OrderBookLevel, OrderBookSnapshot
from app.core.symbols import normalize_symbol, to_gate_symbol, to_okx_spot_symbol


logger = logging.getLogger(__name__)


class OrderBookRestFetcher:
    def __init__(self, state: MarketDataState, symbols: tuple[str, ...], depth_limit: int = 20):
        self.state = state
        self.symbols = symbols
        self.depth_limit = depth_limit
        self.running = False
        self._ssl_context = ssl.create_default_context(cafile=certifi.where())

    def stop(self):
        self.running = False

    async def start(self, interval_seconds: float = 3.0):
        self.running = True
        connector = aiohttp.TCPConnector(ssl=self._ssl_context)
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=8)) as session:
            while self.running:
                started = time.time()
                tasks = []
                for symbol in self.symbols:
                    tasks.extend([
                        self.fetch_binance(session, symbol),
                        self.fetch_bybit(session, symbol),
                        self.fetch_okx(session, symbol),
                        self.fetch_gateio(session, symbol),
                    ])
                results = await asyncio.gather(*tasks, return_exceptions=True)
                updated = 0
                for result in results:
                    if isinstance(result, Exception):
                        logger.warning("order book fetch failed: %s", result)
                        continue
                    if result and self.state.update_order_book(result):
                        updated += 1
                logger.info("order book snapshots updated: %s", updated)
                elapsed = time.time() - started
                await asyncio.sleep(max(0.1, interval_seconds - elapsed))

    async def fetch_binance(self, session: aiohttp.ClientSession, symbol: str) -> OrderBookSnapshot | None:
        url = "https://api.binance.com/api/v3/depth"
        async with session.get(url, params={"symbol": symbol, "limit": self.depth_limit}) as resp:
            if resp.status != 200:
                logger.warning("Binance order book status %s for %s", resp.status, symbol)
                return None
            data = await resp.json()
        return self._book_from_lists("BINANCE", symbol, data.get("bids", []), data.get("asks", []))

    async def fetch_bybit(self, session: aiohttp.ClientSession, symbol: str) -> OrderBookSnapshot | None:
        url = "https://api.bybit.com/v5/market/orderbook"
        async with session.get(url, params={"category": "spot", "symbol": symbol, "limit": self.depth_limit}) as resp:
            if resp.status != 200:
                logger.warning("Bybit order book status %s for %s", resp.status, symbol)
                return None
            data = await resp.json()
        result = data.get("result", {})
        return self._book_from_lists("BYBIT", symbol, result.get("b", []), result.get("a", []))

    async def fetch_okx(self, session: aiohttp.ClientSession, symbol: str) -> OrderBookSnapshot | None:
        url = "https://www.okx.com/api/v5/market/books"
        async with session.get(url, params={"instId": to_okx_spot_symbol(symbol), "sz": self.depth_limit}) as resp:
            if resp.status != 200:
                logger.warning("OKX order book status %s for %s", resp.status, symbol)
                return None
            data = await resp.json()
        item = (data.get("data") or [{}])[0]
        return self._book_from_lists("OKX", symbol, item.get("bids", []), item.get("asks", []))

    async def fetch_gateio(self, session: aiohttp.ClientSession, symbol: str) -> OrderBookSnapshot | None:
        url = "https://api.gateio.ws/api/v4/spot/order_book"
        async with session.get(url, params={"currency_pair": to_gate_symbol(symbol), "limit": self.depth_limit}) as resp:
            if resp.status != 200:
                logger.warning("Gate.io order book status %s for %s", resp.status, symbol)
                return None
            data = await resp.json()
        return self._book_from_lists("GATEIO", symbol, data.get("bids", []), data.get("asks", []))

    def _book_from_lists(
        self,
        exchange: str,
        symbol: str,
        bids: list,
        asks: list,
    ) -> OrderBookSnapshot | None:
        parsed_bids = self._levels(bids, reverse=True)
        parsed_asks = self._levels(asks, reverse=False)
        book = OrderBookSnapshot(
            exchange=exchange,
            symbol=normalize_symbol(symbol),
            bids=parsed_bids,
            asks=parsed_asks,
        )
        return book if book.is_valid() else None

    def _levels(self, raw_levels: list, reverse: bool) -> list[OrderBookLevel]:
        levels = []
        for raw in raw_levels[: self.depth_limit]:
            try:
                price = float(raw[0])
                size = float(raw[1])
            except (TypeError, ValueError, IndexError):
                continue
            level = OrderBookLevel(price=price, size=size)
            if level.is_valid():
                levels.append(level)
        return sorted(levels, key=lambda item: item.price, reverse=reverse)
