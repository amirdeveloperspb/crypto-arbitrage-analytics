import asyncio

from app.core.market_data import MarketDataState
from app.exchanges.binance import BinanceWebSocket
from app.exchanges.bybit import BybitWebSocket
from app.exchanges.funding import FundingRateFetcher
from app.exchanges.gateio import GateIOWebSocket
from app.exchanges.okx import OKXWebSocket


async def check_funding_rates() -> None:
    funding = FundingRateFetcher()
    await funding.update_all()

    print("Funding rates:")
    for exchange, data in funding.rates.items():
        print(f"  {exchange}: {data['rate'] * 100:+.4f}%")

    if not funding.rates:
        raise RuntimeError("No funding rates received")


async def check_websockets() -> None:
    state = MarketDataState(throttle_ms=0)
    exchanges = [
        BinanceWebSocket(state),
        BybitWebSocket(state),
        OKXWebSocket(state),
        GateIOWebSocket(state),
    ]

    tasks = [asyncio.create_task(exchange.start()) for exchange in exchanges]
    await asyncio.sleep(12)

    for exchange in exchanges:
        exchange.stop()

    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)

    prices = state.get_all_for_symbol("SOLUSDT")
    print("\nWebSocket prices:")
    for exchange in ("BINANCE", "BYBIT", "OKX", "GATEIO"):
        tick = prices.get(exchange)
        if tick:
            print(f"  {exchange}: ${tick.price:.2f}")
        else:
            print(f"  {exchange}: no data")

    missing = {"BINANCE", "BYBIT", "OKX", "GATEIO"} - set(prices)
    if missing:
        raise RuntimeError(f"No WebSocket data from: {', '.join(sorted(missing))}")


async def main() -> None:
    await check_funding_rates()
    await check_websockets()
    print("\nHealth check passed")


if __name__ == "__main__":
    asyncio.run(main())
