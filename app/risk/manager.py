# app/risk/manager.py
from dataclasses import dataclass
from typing import Optional


@dataclass
class RiskLimits:
    max_position_size: float = 10.0  # макс SOL в позиции (10 SOL ~$500)
    max_exposure_usd: float = 500.0  # макс $500
    max_drawdown_pct: float = 2.0  # макс просадка 2%
    min_spread_for_entry: float = 0.50  # мин $0.50 спред для входа (SOL дешевле)
    max_daily_trades: int = 10


class RiskManager:

    def __init__(self, limits: RiskLimits):
        self.limits = limits
        self.position: Optional[dict] = None
        self.daily_trades = 0
        self.total_pnl = 0.0

    def can_enter(self, spread: float, price: float, side: str) -> tuple[bool, str]:
        if abs(spread) < self.limits.min_spread_for_entry:
            return False, f"Spread too small: ${abs(spread):.2f} < ${self.limits.min_spread_for_entry}"

        if self.daily_trades >= self.limits.max_daily_trades:
            return False, f"Daily trade limit reached: {self.daily_trades}"

        if self.position is not None:
            return False, "Position already open"

        position_size = self._calculate_position_size(price)
        exposure = position_size * price

        if exposure > self.limits.max_exposure_usd:
            return False, f"Exposure too high: ${exposure:.0f} > ${self.limits.max_exposure_usd}"

        return True, "OK"

    def can_exit(self, current_price: float) -> tuple[bool, str]:
        if self.position is None:
            return False, "No position"

        entry_price = self.position["entry_price"]
        side = self.position["side"]

        if side == "long":
            pnl_pct = (current_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - current_price) / entry_price * 100

        if pnl_pct < -self.limits.max_drawdown_pct:
            return True, f"Stop loss: {pnl_pct:.2f}%"

        return False, f"P&L: {pnl_pct:+.2f}%"

    def enter_position(self, price: float, side: str, spread: float):
        size = self._calculate_position_size(price)

        self.position = {
            "side": side,
            "entry_price": price,
            "size": size,
            "spread_at_entry": spread,
            "entry_time": __import__('time').time()
        }
        self.daily_trades += 1

        return self.position

    def exit_position(self, exit_price: float):
        if self.position is None:
            return None

        entry = self.position
        side = entry["side"]

        if side == "long":
            pnl = (exit_price - entry["entry_price"]) * entry["size"]
        else:
            pnl = (entry["entry_price"] - exit_price) * entry["size"]

        self.total_pnl += pnl
        result = {
            "pnl": pnl,
            "entry": entry,
            "exit_price": exit_price,
            "total_pnl": self.total_pnl
        }

        self.position = None
        return result

    def _calculate_position_size(self, price: float) -> float:
        return min(
            self.limits.max_exposure_usd / price,
            self.limits.max_position_size
        )

    def get_status(self) -> dict:
        return {
            "position": self.position,
            "daily_trades": self.daily_trades,
            "total_pnl": self.total_pnl,
            "limits": {
                "max_position": self.limits.max_position_size,
                "max_exposure": self.limits.max_exposure_usd,
                "min_spread": self.limits.min_spread_for_entry,
                "max_trades": self.limits.max_daily_trades
            }
        }