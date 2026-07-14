import time
from dataclasses import dataclass
from typing import Iterable, Mapping

from app.core.market_data import OrderBookLevel, OrderBookSnapshot


@dataclass(frozen=True)
class FillResult:
    requested_size: float
    filled_size: float
    notional: float
    average_price: float
    slippage_pct: float
    fully_filled: bool
    levels_used: int
    consumed_levels: list[dict]


class ExecutionQualityAnalyzer:
    def __init__(
        self,
        taker_fee_rate: float,
        max_age_seconds: float,
        min_net_profit_usd: float = 0.0,
        min_fill_ratio: float = 1.0,
        max_snapshot_skew_seconds: float | None = None,
    ):
        self.taker_fee_rate = taker_fee_rate
        self.max_age_seconds = max_age_seconds
        self.min_net_profit_usd = min_net_profit_usd
        self.min_fill_ratio = min_fill_ratio
        self.max_snapshot_skew_seconds = (
            max_snapshot_skew_seconds
            if max_snapshot_skew_seconds is not None
            else max_age_seconds
        )

    def simulate_buy(self, asks: Iterable[OrderBookLevel], size: float) -> FillResult:
        levels = sorted(asks, key=lambda item: item.price)
        return self._consume_levels(levels, size, reference_price=levels[0].price if levels else 0.0)

    def simulate_sell(self, bids: Iterable[OrderBookLevel], size: float) -> FillResult:
        levels = sorted(bids, key=lambda item: item.price, reverse=True)
        return self._consume_levels(levels, size, reference_price=levels[0].price if levels else 0.0)

    def find_best_executable(
        self,
        symbol: str,
        order_books: Mapping[str, OrderBookSnapshot],
        target_size: float,
    ) -> dict | None:
        fresh = self._fresh_books(order_books)
        if len(fresh) < 2 or target_size <= 0:
            return None

        best_result = None
        for buy_exchange, buy_book in fresh.items():
            for sell_exchange, sell_book in fresh.items():
                if buy_exchange == sell_exchange:
                    continue

                result = self.evaluate_route(
                    symbol=symbol,
                    buy_book=buy_book,
                    sell_book=sell_book,
                    target_size=target_size,
                )
                if result is None:
                    continue
                if best_result is None or result["estimated_net_profit_usd"] > best_result["estimated_net_profit_usd"]:
                    best_result = result

        return best_result

    def evaluate_route(
        self,
        symbol: str,
        buy_book: OrderBookSnapshot,
        sell_book: OrderBookSnapshot,
        target_size: float,
    ) -> dict | None:
        buy_fill = self.simulate_buy(buy_book.asks, target_size)
        sell_fill = self.simulate_sell(sell_book.bids, target_size)
        snapshot_skew_seconds = abs(buy_book.timestamp - sell_book.timestamp)
        if snapshot_skew_seconds > self.max_snapshot_skew_seconds:
            return None

        executable_size = min(buy_fill.filled_size, sell_fill.filled_size)
        if executable_size <= 0:
            return None

        fill_ratio = executable_size / target_size
        if fill_ratio < self.min_fill_ratio:
            return None

        if executable_size != target_size:
            buy_fill = self.simulate_buy(buy_book.asks, executable_size)
            sell_fill = self.simulate_sell(sell_book.bids, executable_size)

        buy_notional = buy_fill.notional
        sell_notional = sell_fill.notional
        gross_profit = sell_notional - buy_notional
        estimated_fees = buy_notional * self.taker_fee_rate + sell_notional * self.taker_fee_rate
        net_profit = gross_profit - estimated_fees
        raw_spread = sell_book.best_bid - buy_book.best_ask
        raw_spread_pct = raw_spread / buy_book.best_ask * 100
        executable_spread = sell_fill.average_price - buy_fill.average_price
        executable_spread_pct = executable_spread / buy_fill.average_price * 100
        max_profitable_size = self._find_max_profitable_size(buy_book, sell_book, target_size)
        data_age_seconds = {
            buy_book.exchange: time.time() - buy_book.timestamp,
            sell_book.exchange: time.time() - sell_book.timestamp,
        }
        sync_quality = self._sync_quality(snapshot_skew_seconds)
        score_details = self._score(
            net_profit=net_profit,
            executable_spread_pct=executable_spread_pct,
            buy_fill=buy_fill,
            sell_fill=sell_fill,
            fill_ratio=fill_ratio,
        )

        return {
            "symbol": symbol,
            "buy_on": buy_book.exchange,
            "sell_on": sell_book.exchange,
            "target_size": target_size,
            "executable_size": executable_size,
            "fill_ratio": fill_ratio,
            "raw_buy_price": buy_book.best_ask,
            "raw_sell_price": sell_book.best_bid,
            "raw_spread": raw_spread,
            "raw_spread_pct": raw_spread_pct,
            "average_buy_price": buy_fill.average_price,
            "average_sell_price": sell_fill.average_price,
            "executable_spread": executable_spread,
            "executable_spread_pct": executable_spread_pct,
            "buy_notional_usd": buy_notional,
            "sell_notional_usd": sell_notional,
            "gross_profit_usd": gross_profit,
            "estimated_fees_usd": estimated_fees,
            "estimated_net_profit_usd": net_profit,
            "is_positive_after_fees": net_profit > self.min_net_profit_usd,
            "buy_slippage_pct": buy_fill.slippage_pct,
            "sell_slippage_pct": sell_fill.slippage_pct,
            "combined_slippage_pct": buy_fill.slippage_pct + sell_fill.slippage_pct,
            "buy_levels_used": buy_fill.levels_used,
            "sell_levels_used": sell_fill.levels_used,
            "buy_fills": buy_fill.consumed_levels,
            "sell_fills": sell_fill.consumed_levels,
            "max_profitable_size": max_profitable_size,
            "score": score_details["score"],
            "score_reasons": score_details["reasons"],
            "data_age_seconds": data_age_seconds,
            "snapshot_skew_seconds": snapshot_skew_seconds,
            "snapshot_skew_ms": round(snapshot_skew_seconds * 1000, 3),
            "sync_quality": sync_quality,
            "limitations": [
                "uses REST order-book snapshots, not guaranteed atomic cross-exchange state",
                "does not include withdrawal/deposit fees",
                "does not include transfer time or exchange maintenance status",
            ],
        }

    def _consume_levels(
        self,
        levels: list[OrderBookLevel],
        size: float,
        reference_price: float,
    ) -> FillResult:
        remaining = size
        filled = 0.0
        notional = 0.0
        levels_used = 0
        consumed_levels = []

        for level in levels:
            if remaining <= 0:
                break
            quantity = min(remaining, level.size)
            filled += quantity
            notional += quantity * level.price
            remaining -= quantity
            levels_used += 1
            consumed_levels.append({
                "price": level.price,
                "available_size": level.size,
                "filled_size": quantity,
                "notional": quantity * level.price,
                "fill_pct": quantity / level.size * 100,
            })

        average_price = notional / filled if filled else 0.0
        slippage_pct = abs(average_price - reference_price) / reference_price * 100 if reference_price else 0.0
        return FillResult(
            requested_size=size,
            filled_size=filled,
            notional=notional,
            average_price=average_price,
            slippage_pct=slippage_pct,
            fully_filled=filled >= size,
            levels_used=levels_used,
            consumed_levels=consumed_levels,
        )

    def _fresh_books(self, order_books: Mapping[str, OrderBookSnapshot]) -> dict[str, OrderBookSnapshot]:
        now = time.time()
        return {
            exchange: order_book
            for exchange, order_book in order_books.items()
            if now - order_book.timestamp <= self.max_age_seconds
        }

    def _sync_quality(self, snapshot_skew_seconds: float) -> str:
        if snapshot_skew_seconds <= 0.25:
            return "fresh"
        if snapshot_skew_seconds <= min(1.0, self.max_snapshot_skew_seconds):
            return "acceptable"
        return "weak"

    def _find_max_profitable_size(
        self,
        buy_book: OrderBookSnapshot,
        sell_book: OrderBookSnapshot,
        target_size: float,
    ) -> float:
        candidate_sizes = sorted({
            round(level.size, 10)
            for level in buy_book.asks
        } | {
            round(level.size, 10)
            for level in sell_book.bids
        } | {
            round(target_size * ratio, 10)
            for ratio in (0.25, 0.5, 0.75, 1.0)
        })

        cumulative_sizes = []
        total = 0.0
        for level in sorted(buy_book.asks, key=lambda item: item.price):
            total += level.size
            cumulative_sizes.append(round(total, 10))
        total = 0.0
        for level in sorted(sell_book.bids, key=lambda item: item.price, reverse=True):
            total += level.size
            cumulative_sizes.append(round(total, 10))

        max_size = 0.0
        for size in sorted(set(candidate_sizes + cumulative_sizes)):
            if size <= 0 or size > target_size:
                continue
            route = self.evaluate_route_without_max_size(buy_book, sell_book, size)
            if route and route["estimated_net_profit_usd"] > self.min_net_profit_usd:
                max_size = size
        return max_size

    def evaluate_route_without_max_size(
        self,
        buy_book: OrderBookSnapshot,
        sell_book: OrderBookSnapshot,
        target_size: float,
    ) -> dict | None:
        buy_fill = self.simulate_buy(buy_book.asks, target_size)
        sell_fill = self.simulate_sell(sell_book.bids, target_size)
        if not buy_fill.fully_filled or not sell_fill.fully_filled:
            return None
        gross_profit = sell_fill.notional - buy_fill.notional
        fees = buy_fill.notional * self.taker_fee_rate + sell_fill.notional * self.taker_fee_rate
        return {"estimated_net_profit_usd": gross_profit - fees}

    def _score(
        self,
        net_profit: float,
        executable_spread_pct: float,
        buy_fill: FillResult,
        sell_fill: FillResult,
        fill_ratio: float,
    ) -> dict:
        score = 0
        reasons = []

        if net_profit > self.min_net_profit_usd:
            score += 35
            reasons.append("net profit remains positive after fees and depth simulation")
        else:
            reasons.append("net profit is not positive after fees and depth simulation")

        if executable_spread_pct > 0:
            score += min(20, executable_spread_pct * 120)
            reasons.append("VWAP sell price is above VWAP buy price")

        if fill_ratio >= 1:
            score += 20
            reasons.append("target size is fully executable on visible levels")
        else:
            reasons.append("target size is not fully executable on visible levels")

        slippage = buy_fill.slippage_pct + sell_fill.slippage_pct
        if slippage < 0.05:
            score += 15
            reasons.append("combined slippage is low")
        elif slippage < 0.2:
            score += 8
            reasons.append("combined slippage is moderate")
        else:
            reasons.append("combined slippage is high")

        if buy_fill.levels_used <= 3 and sell_fill.levels_used <= 3:
            score += 10
            reasons.append("execution uses only a few order-book levels")

        return {"score": round(min(100, score), 1), "reasons": reasons}
