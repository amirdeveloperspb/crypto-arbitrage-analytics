# Order-Book Execution Algorithm

This is the main algorithmic feature of the project.

The goal is to show the difference between a raw arbitrage spread and a more realistic executable result.

## Why Raw Spread Is Not Enough

Raw top-of-book spread:

```text
raw_spread = best_bid_on_sell_exchange - best_ask_on_buy_exchange
```

This is useful, but incomplete. If we want to buy or sell more than the first level can fill, we must walk deeper order-book levels.

## Core Idea

For a target size, for example `10 SOL`:

1. Buy `10 SOL` by consuming ask levels from the cheapest exchange.
2. Sell `10 SOL` by consuming bid levels from the most expensive exchange.
3. Compute VWAP buy price and VWAP sell price.
4. Subtract taker fees on both sides.
5. Report realistic net result, slippage, fill ratio, and score.

## Manual Example

Target size:

```text
10 SOL
```

Buy-side asks:

```text
5 SOL @ $100
5 SOL @ $101
```

Buy notional:

```text
5 * 100 + 5 * 101 = 1005
```

Average buy price:

```text
1005 / 10 = $100.50
```

Sell-side bids:

```text
4 SOL @ $103
6 SOL @ $102
```

Sell notional:

```text
4 * 103 + 6 * 102 = 1024
```

Average sell price:

```text
1024 / 10 = $102.40
```

Gross profit:

```text
1024 - 1005 = $19
```

If taker fee is `0.1%`:

```text
buy fee = 1005 * 0.001 = $1.005
sell fee = 1024 * 0.001 = $1.024
total fees = $2.029
```

Net profit:

```text
19 - 2.029 = $16.971
```

This is much more realistic than simply comparing the best ask and best bid.

## Slippage

Buy slippage compares average buy price against best ask:

```text
buy_slippage_pct = abs(avg_buy_price - best_ask) / best_ask * 100
```

Sell slippage compares average sell price against best bid:

```text
sell_slippage_pct = abs(avg_sell_price - best_bid) / best_bid * 100
```

High slippage means the opportunity may disappear when size increases.

## Maximum Profitable Size

The analyzer tries candidate sizes from visible order-book levels and finds the largest size where:

```text
net_profit_after_fees > 0
```

This is not a perfect optimizer, but it is transparent, fast, and explainable.

## Signal Score

Score is based on:

- net profit after fees;
- positive VWAP spread;
- full target-size fill;
- low slippage;
- number of order-book levels used.

The score is explainable through `score_reasons`.

## Current Limitations

- Live order books are REST snapshots, not atomic synchronized exchange states.
- The model does not include withdrawal fees.
- The model does not include transfer time between exchanges.
- The model does not check whether deposits/withdrawals are currently enabled.
- The model uses visible levels only.

These limitations should be said openly during defense.

## Defense Questions

Q: Why not just compare last prices?

A: Last price is a historical trade. It does not guarantee that we can buy or sell at that price now.

Q: Why use ask for buying and bid for selling?

A: To buy immediately, we consume asks. To sell immediately, we consume bids.

Q: What is VWAP?

A: Volume-weighted average price. It is the average execution price after consuming multiple order-book levels.

Q: What is slippage?

A: The difference between expected top price and actual average execution price after consuming depth.

Q: Is this guaranteed profit?

A: No. It is an analytical execution estimate. Real trading also depends on transfer time, exchange limits, withdrawal fees, and rapidly changing markets.
