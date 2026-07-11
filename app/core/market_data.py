# app/core/market_data.py
import time
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass(slots=True, frozen=True)
class OrderBookLevel:
    price: float
    size: float

    def is_valid(self) -> bool:
        return self.price > 0 and self.size > 0


@dataclass(slots=True)
class OrderBookSnapshot:
    exchange: str
    symbol: str
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    timestamp: float = field(default_factory=time.time)

    @property
    def best_bid(self) -> float:
        return self.bids[0].price if self.bids else 0.0

    @property
    def best_ask(self) -> float:
        return self.asks[0].price if self.asks else 0.0

    @property
    def best_bid_size(self) -> float:
        return self.bids[0].size if self.bids else 0.0

    @property
    def best_ask_size(self) -> float:
        return self.asks[0].size if self.asks else 0.0

    def is_valid(self) -> bool:
        if not self.bids or not self.asks:
            return False
        if any(not level.is_valid() for level in self.bids + self.asks):
            return False
        return self.best_ask >= self.best_bid


@dataclass(slots=True)
class MarketSnapshot:
    exchange: str
    symbol: str
    bid_price: float
    ask_price: float
    bid_size: float = 0.0
    ask_size: float = 0.0
    last_price: float | None = None
    timestamp: float = field(default_factory=time.time)

    @property
    def price(self) -> float:
        if self.last_price is not None:
            return self.last_price
        return (self.bid_price + self.ask_price) / 2

    @property
    def mid_price(self) -> float:
        return (self.bid_price + self.ask_price) / 2

    @property
    def spread(self) -> float:
        return self.ask_price - self.bid_price

    def is_valid(self) -> bool:
        return self.bid_price > 0 and self.ask_price > 0 and self.ask_price >= self.bid_price

    def __repr__(self):
        return f"{self.exchange}:{self.symbol} bid={self.bid_price:.2f} ask={self.ask_price:.2f}"


class PriceTick(MarketSnapshot):
    """Backward-compatible wrapper for older tests and simple last-price feeds."""

    def __init__(self, exchange: str, symbol: str, price: float):
        super().__init__(
            exchange=exchange,
            symbol=symbol,
            bid_price=price,
            ask_price=price,
            bid_size=0.0,
            ask_size=0.0,
            last_price=price,
        )


class MarketDataState:
    def __init__(self, throttle_ms: float = 100):
        self._snapshots: Dict[str, Dict[str, MarketSnapshot]] = {}
        self._order_books: Dict[str, Dict[str, OrderBookSnapshot]] = {}
        self._last_update: Dict[str, float] = {}
        self._throttle_seconds = throttle_ms / 1000

    def update(self, snapshot: MarketSnapshot) -> bool:
        if not snapshot.is_valid():
            return False

        key = f"{snapshot.exchange}:{snapshot.symbol}"
        now = time.time()
        last = self._last_update.get(key, 0)
        if now - last < self._throttle_seconds:
            return False

        if snapshot.symbol not in self._snapshots:
            self._snapshots[snapshot.symbol] = {}
        self._snapshots[snapshot.symbol][snapshot.exchange] = snapshot
        self._last_update[key] = now
        return True

    def update_order_book(self, order_book: OrderBookSnapshot) -> bool:
        if not order_book.is_valid():
            return False

        if order_book.symbol not in self._order_books:
            self._order_books[order_book.symbol] = {}
        self._order_books[order_book.symbol][order_book.exchange] = order_book

        self.update(
            MarketSnapshot(
                exchange=order_book.exchange,
                symbol=order_book.symbol,
                bid_price=order_book.best_bid,
                ask_price=order_book.best_ask,
                bid_size=order_book.best_bid_size,
                ask_size=order_book.best_ask_size,
                last_price=(order_book.best_bid + order_book.best_ask) / 2,
                timestamp=order_book.timestamp,
            )
        )
        return True

    def get_latest(self, symbol: str, exchange: str) -> Optional[MarketSnapshot]:
        return self._snapshots.get(symbol, {}).get(exchange)

    def get_symbols(self) -> list[str]:
        return sorted(self._snapshots.keys())

    def get_all_for_symbol(
        self,
        symbol: str,
        max_age_seconds: float | None = None,
    ) -> Dict[str, MarketSnapshot]:
        snapshots = self._snapshots.get(symbol, {}).copy()
        if max_age_seconds is None:
            return snapshots

        now = time.time()
        return {
            exchange: snapshot
            for exchange, snapshot in snapshots.items()
            if now - snapshot.timestamp <= max_age_seconds
        }

    def get_order_book(self, symbol: str, exchange: str) -> Optional[OrderBookSnapshot]:
        return self._order_books.get(symbol, {}).get(exchange)

    def get_order_books_for_symbol(
        self,
        symbol: str,
        max_age_seconds: float | None = None,
    ) -> Dict[str, OrderBookSnapshot]:
        order_books = self._order_books.get(symbol, {}).copy()
        if max_age_seconds is None:
            return order_books

        now = time.time()
        return {
            exchange: order_book
            for exchange, order_book in order_books.items()
            if now - order_book.timestamp <= max_age_seconds
        }

    def get_spread(self, symbol: str, exchange1: str = "BINANCE", exchange2: str = "BYBIT") -> Optional[float]:
        snapshots = self.get_all_for_symbol(symbol)
        ex1 = snapshots.get(exchange1)
        ex2 = snapshots.get(exchange2)
        if ex1 is None or ex2 is None:
            return None
        return ex2.price - ex1.price

    def get_best_spread(self, symbol: str, max_age_seconds: float | None = None) -> Optional[dict]:
        snapshots = self.get_all_for_symbol(symbol, max_age_seconds=max_age_seconds)
        if len(snapshots) < 2:
            return None

        cheapest_ask = min(snapshots.values(), key=lambda item: item.ask_price)
        highest_bid = max(snapshots.values(), key=lambda item: item.bid_price)
        if cheapest_ask.exchange == highest_bid.exchange:
            return None

        spread = highest_bid.bid_price - cheapest_ask.ask_price
        return {
            "spread": spread,
            "spread_pct": spread / cheapest_ask.ask_price * 100,
            "buy_on": cheapest_ask.exchange,
            "sell_on": highest_bid.exchange,
            "pair": (cheapest_ask.exchange, highest_bid.exchange),
            "buy_price": cheapest_ask.ask_price,
            "sell_price": highest_bid.bid_price,
        }

    def get_estimated_opportunity(
        self,
        symbol: str,
        budget_usd: float,
        taker_fee_rate: float,
        max_age_seconds: float,
    ) -> Optional[dict]:
        from app.analytics.opportunities import OpportunityAnalyzer

        analyzer = OpportunityAnalyzer(
            budget_usd=budget_usd,
            taker_fee_rate=taker_fee_rate,
            max_age_seconds=max_age_seconds,
        )
        return analyzer.find_best(symbol, self.get_all_for_symbol(symbol))
