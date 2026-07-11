import time
from dataclasses import dataclass
from typing import Mapping

from app.core.market_data import MarketSnapshot


@dataclass(frozen=True)
class OpportunityAnalyzer:
    budget_usd: float
    taker_fee_rate: float
    max_age_seconds: float
    min_net_profit_usd: float = 0.0

    def find_best(self, symbol: str, snapshots: Mapping[str, MarketSnapshot]) -> dict | None:
        fresh = self._fresh_snapshots(snapshots)
        if len(fresh) < 2:
            return None

        buy_snapshot = min(fresh.values(), key=lambda item: item.ask_price)
        sell_snapshot = max(fresh.values(), key=lambda item: item.bid_price)
        if buy_snapshot.exchange == sell_snapshot.exchange:
            return None

        quantity = self.budget_usd / buy_snapshot.ask_price
        gross_profit = (sell_snapshot.bid_price - buy_snapshot.ask_price) * quantity
        estimated_fees = (
            self.budget_usd * self.taker_fee_rate
            + quantity * sell_snapshot.bid_price * self.taker_fee_rate
        )
        net_profit = gross_profit - estimated_fees
        spread = sell_snapshot.bid_price - buy_snapshot.ask_price
        spread_pct = spread / buy_snapshot.ask_price * 100
        score_details = self._score(
            spread_pct=spread_pct,
            net_profit=net_profit,
            buy_snapshot=buy_snapshot,
            sell_snapshot=sell_snapshot,
        )

        return {
            "symbol": symbol,
            "buy_on": buy_snapshot.exchange,
            "sell_on": sell_snapshot.exchange,
            "buy_price": buy_snapshot.ask_price,
            "sell_price": sell_snapshot.bid_price,
            "buy_size": buy_snapshot.ask_size,
            "sell_size": sell_snapshot.bid_size,
            "spread": spread,
            "spread_pct": spread_pct,
            "budget_usd": self.budget_usd,
            "quantity": quantity,
            "gross_profit_usd": gross_profit,
            "estimated_fees_usd": estimated_fees,
            "estimated_net_profit_usd": net_profit,
            "is_positive_after_fees": net_profit > self.min_net_profit_usd,
            "score": score_details["score"],
            "score_reasons": score_details["reasons"],
            "data_age_seconds": {
                buy_snapshot.exchange: time.time() - buy_snapshot.timestamp,
                sell_snapshot.exchange: time.time() - sell_snapshot.timestamp,
            },
            "limitations": [
                "uses top-of-book bid/ask only",
                "does not simulate full order-book depth",
                "does not include slippage",
                "does not include withdrawal/deposit fees",
            ],
        }

    def _fresh_snapshots(self, snapshots: Mapping[str, MarketSnapshot]) -> dict[str, MarketSnapshot]:
        now = time.time()
        return {
            exchange: snapshot
            for exchange, snapshot in snapshots.items()
            if now - snapshot.timestamp <= self.max_age_seconds
        }

    def _score(
        self,
        spread_pct: float,
        net_profit: float,
        buy_snapshot: MarketSnapshot,
        sell_snapshot: MarketSnapshot,
    ) -> dict:
        score = 0
        reasons = []

        if net_profit > 0:
            score += 35
            reasons.append("net profit is positive after estimated taker fees")
        else:
            reasons.append("net profit is not positive after estimated taker fees")

        if spread_pct > 0:
            score += min(20, spread_pct * 250)
            reasons.append("best bid is above best ask across exchanges")

        now = time.time()
        max_age = max(now - buy_snapshot.timestamp, now - sell_snapshot.timestamp)
        if max_age <= self.max_age_seconds / 2:
            score += 15
            reasons.append("both market snapshots are very fresh")
        elif max_age <= self.max_age_seconds:
            score += 8
            reasons.append("market snapshots are fresh enough")

        min_size = min(buy_snapshot.ask_size, sell_snapshot.bid_size)
        if min_size > 0:
            score += min(20, min_size * 2)
            reasons.append("top-of-book size is available")
        else:
            reasons.append("top-of-book size is unknown on at least one exchange")

        if buy_snapshot.exchange != sell_snapshot.exchange:
            score += 10
            reasons.append("route uses two different exchanges")

        return {
            "score": round(min(100, score), 1),
            "reasons": reasons,
        }


def summarize_prices(symbol: str, snapshots: Mapping[str, MarketSnapshot], max_age_seconds: float) -> dict:
    now = time.time()
    return {
        "symbol": symbol,
        "prices": {
            exchange: {
                "bid_price": snapshot.bid_price,
                "ask_price": snapshot.ask_price,
                "bid_size": snapshot.bid_size,
                "ask_size": snapshot.ask_size,
                "last_price": snapshot.last_price,
                "mid_price": snapshot.mid_price,
                "age_seconds": now - snapshot.timestamp,
                "fresh": now - snapshot.timestamp <= max_age_seconds,
            }
            for exchange, snapshot in sorted(snapshots.items())
        },
    }
