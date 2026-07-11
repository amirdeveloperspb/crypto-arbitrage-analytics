import asyncio
import math
import time

from app.core.market_data import MarketDataState, MarketSnapshot, OrderBookLevel, OrderBookSnapshot


BASE_PRICES = {
    "SOLUSDT": 78.0,
    "BTCUSDT": 118000.0,
    "ETHUSDT": 3600.0,
}

EXCHANGE_OFFSETS = {
    "BINANCE": -0.0002,
    "BYBIT": 0.0,
    "OKX": 0.00035,
    "GATEIO": 0.0035,
}


async def demo_market_loop(state: MarketDataState, symbols: tuple[str, ...]) -> None:
    step = 0
    while True:
        now = time.time()
        for symbol in symbols:
            base = BASE_PRICES.get(symbol, 100.0)
            wave = math.sin(step / 6) * 0.0008
            for exchange, offset in EXCHANGE_OFFSETS.items():
                mid = base * (1 + wave + offset)
                spread = max(base * 0.00012, 0.01)
                state.update(
                    MarketSnapshot(
                        exchange=exchange,
                        symbol=symbol,
                        bid_price=mid - spread / 2,
                        ask_price=mid + spread / 2,
                        bid_size=15 + (step % 7),
                        ask_size=14 + (step % 5),
                        last_price=mid,
                        timestamp=now,
                    )
                )
                state.update_order_book(_demo_order_book(exchange, symbol, mid, base, now, step))
        step += 1
        await asyncio.sleep(0.5)


def _demo_order_book(exchange: str, symbol: str, mid: float, base: float, now: float, step: int) -> OrderBookSnapshot:
    spread = max(base * 0.00012, 0.01)
    level_gap = max(base * 0.00008, 0.01)
    base_size = 8 + (step % 4)
    bids = [
        OrderBookLevel(price=mid - spread / 2 - i * level_gap, size=base_size + i * 3)
        for i in range(6)
    ]
    asks = [
        OrderBookLevel(price=mid + spread / 2 + i * level_gap, size=base_size + i * 2)
        for i in range(6)
    ]
    return OrderBookSnapshot(
        exchange=exchange,
        symbol=symbol,
        bids=bids,
        asks=asks,
        timestamp=now,
    )
