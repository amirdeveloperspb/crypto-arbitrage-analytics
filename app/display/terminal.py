# app/display/terminal.py
import asyncio
import time


class DisplayEngine:

    def __init__(self, state, symbol: str = "SOLUSDT", max_price_age_seconds: float = 2.0, throttle_ms: float = 500):
        self.state = state
        self.symbol = symbol
        self.max_price_age_seconds = max_price_age_seconds
        self.throttle_seconds = throttle_ms / 1000
        self.running = False
        self._last_lines = 0

    async def start(self):
        self.running = True
        last_update = 0

        while self.running:
            now = time.time()

            if now - last_update >= self.throttle_seconds:
                self._render()
                last_update = now

            await asyncio.sleep(0.1)

    def _render(self):
        if self._last_lines > 0:
            print(f"\033[{self._last_lines}A", end="")
            print("\033[J", end="")

        lines = []
        lines.append("=" * 50)
        lines.append(f"  {self.symbol} ANALYTICS — 3 EXCHANGES  |  " + time.strftime("%H:%M:%S"))
        lines.append("=" * 50)

        binance = self.state.get_latest(self.symbol, "BINANCE")
        bybit = self.state.get_latest(self.symbol, "BYBIT")
        okx = self.state.get_latest(self.symbol, "OKX")

        bp = f"${binance.price:.2f}" if binance else "WAITING"
        by = f"${bybit.price:.2f}" if bybit else "WAITING"
        op = f"${okx.price:.2f}" if okx else "WAITING"

        lines.append(f"\n  BINANCE  {bp:>15}")
        lines.append(f"  BYBIT    {by:>15}")
        lines.append(f"  OKX      {op:>15}")

        # Лучший спред
        best = self.state.get_best_spread(self.symbol, max_age_seconds=self.max_price_age_seconds)
        if best:
            sp = f"${best['spread']:+.2f}"
            color = "\033[92m" if best['spread'] > 0 else "\033[91m"
            lines.append(f"\n  BEST SPREAD  {color}{sp:>11}\033[0m")
            lines.append(f"  {best['buy_on']} → {best['sell_on']}")
        else:
            lines.append(f"\n  BEST SPREAD  {'WAITING':>11}")

        lines.append("\n" + "-" * 50)

        ba = "LIVE" if binance and time.time() - binance.timestamp < 2 else "STALE"
        bya = "LIVE" if bybit and time.time() - bybit.timestamp < 2 else "STALE"
        oa = "LIVE" if okx and time.time() - okx.timestamp < 2 else "STALE"
        lines.append(f"  B:{ba}  BY:{bya}  O:{oa}")
        lines.append("=" * 50)

        output = "\n".join(lines)
        print(output, end="", flush=True)

        self._last_lines = len(lines)

    def stop(self):
        self.running = False
