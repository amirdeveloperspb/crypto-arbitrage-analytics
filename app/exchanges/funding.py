# app/exchanges/funding.py
import asyncio
import aiohttp
import certifi
import ssl
import time


class FundingRateFetcher:
    """
    Получает funding rate с бирж.
    """

    def __init__(self):
        self.rates = {}  # {"BINANCE": {"SOLUSDT": 0.0001}, ...}
        self._last_update = 0
        self._ssl_context = ssl.create_default_context(cafile=certifi.where())

    def _connector(self):
        return aiohttp.TCPConnector(ssl=self._ssl_context)

    async def fetch_binance(self):
        """Binance funding rate."""
        url = "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=SOLUSDT"
        try:
            async with aiohttp.ClientSession(connector=self._connector()) as session:
                async with session.get(url) as resp:
                    data = await resp.json()
                    return {
                        "rate": float(data.get("lastFundingRate", 0)),
                        "next_time": data.get("nextFundingTime", 0)
                    }
        except Exception as e:
            print(f"[FUNDING] Binance error: {e}")
            return None

    async def fetch_bybit(self):
        """Bybit funding rate."""
        url = "https://api.bybit.com/v5/market/tickers?category=linear&symbol=SOLUSDT"
        try:
            async with aiohttp.ClientSession(connector=self._connector()) as session:
                async with session.get(url) as resp:
                    data = await resp.json()
                    result = data.get("result", {}).get("list", [{}])[0]
                    return {
                        "rate": float(result.get("fundingRate", 0)),
                        "next_time": int(result.get("nextFundingTime", 0))
                    }
        except Exception as e:
            print(f"[FUNDING] Bybit error: {e}")
            return None

    async def fetch_okx(self):
        """OKX funding rate."""
        url = "https://www.okx.com/api/v5/public/funding-rate?instId=SOL-USDT-SWAP"
        try:
            async with aiohttp.ClientSession(connector=self._connector()) as session:
                async with session.get(url) as resp:
                    data = await resp.json()
                    result = data.get("data", [{}])[0]
                    return {
                        "rate": float(result.get("fundingRate", 0)),
                        "next_time": int(result.get("fundingTime", 0))
                    }
        except Exception as e:
            print(f"[FUNDING] OKX error: {e}")
            return None

    async def update_all(self):
        """Обновить все funding rates."""
        results = await asyncio.gather(
            self.fetch_binance(),
            self.fetch_bybit(),
            self.fetch_okx(),
            return_exceptions=True
        )

        exchanges = ["BINANCE", "BYBIT", "OKX"]
        for ex, result in zip(exchanges, results):
            if isinstance(result, Exception):
                continue
            if result:
                self.rates[ex] = result

        self._last_update = time.time()

    def get_best_opportunity(self):
        """
        Найти лучшую пару для фандинг арбитража.
        Возвращает: (buy_exchange, sell_exchange, profit_rate)
        """
        if len(self.rates) < 2:
            return None

        exchanges = list(self.rates.keys())
        best = None
        best_profit = 0

        for i in range(len(exchanges)):
            for j in range(i + 1, len(exchanges)):
                ex1, ex2 = exchanges[i], exchanges[j]
                rate1 = self.rates[ex1]["rate"]
                rate2 = self.rates[ex2]["rate"]

                # Упрощенная модель:
                # long получает funding, если rate отрицательный; short получает, если rate положительный.
                # Поэтому для long ex2 + short ex1 ожидаемая разница: rate1 - rate2.
                profit1 = rate1 - rate2
                profit2 = rate2 - rate1

                if profit1 > best_profit:
                    best_profit = profit1
                    best = {
                        "short_on": ex1,
                        "long_on": ex2,
                        "profit_rate": profit1,
                        "rates": {ex1: rate1, ex2: rate2}
                    }

                if profit2 > best_profit:
                    best_profit = profit2
                    best = {
                        "short_on": ex2,
                        "long_on": ex1,
                        "profit_rate": profit2,
                        "rates": {ex1: rate1, ex2: rate2}
                    }

        return best if best_profit > 0.0001 else None  # минимум 0.01%

    def __str__(self):
        lines = ["Funding Rates:"]
        for ex, data in self.rates.items():
            rate = data["rate"] * 100  # в процентах
            lines.append(f"  {ex}: {rate:+.4f}%")

        opp = self.get_best_opportunity()
        if opp:
            lines.append(f"\nBest: Short {opp['short_on']} + Long {opp['long_on']}")
            lines.append(f"Profit: {opp['profit_rate'] * 100:+.4f}% per 8h")

        return "\n".join(lines)
