class OpportunityQualityModel:
    """ML-ready baseline.

    Сейчас это прозрачная эвристика без внешних зависимостей. Когда накопим
    историю в SQLite, этот класс можно заменить на модель sklearn, обученную
    на тех же features.
    """

    def predict_quality(self, opportunity: dict | None) -> dict:
        if not opportunity:
            return {
                "quality": "no_signal",
                "probability": 0.0,
                "model": "heuristic_baseline",
            }

        score = float(opportunity.get("score", 0))
        net_profit = float(opportunity.get("estimated_net_profit_usd", 0))

        if score >= 70 and net_profit > 0:
            quality = "strong"
        elif score >= 45 and net_profit > 0:
            quality = "watch"
        else:
            quality = "weak"

        return {
            "quality": quality,
            "probability": round(score / 100, 3),
            "model": "heuristic_baseline",
            "features": {
                "score": score,
                "net_profit_usd": net_profit,
                "spread_pct": opportunity.get("spread_pct"),
                "buy_size": opportunity.get("buy_size"),
                "sell_size": opportunity.get("sell_size"),
            },
        }
