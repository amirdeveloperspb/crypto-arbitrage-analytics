import math


class OpportunityQualityModel:
    """Fast explainable quality model.

    This is intentionally dependency-free and deterministic. It uses the same
    feature shape that a later trained model can consume, but it stays honest:
    the current output is a fast analytical score, not a trained neural net.
    """

    MODEL_NAME = "fast_explainable_quality_v2"

    def predict_quality(self, opportunity: dict | None) -> dict:
        if not opportunity:
            return {
                "quality": "no_signal",
                "probability": 0.0,
                "confidence": 0.0,
                "recommendation": "wait_for_data",
                "model": self.MODEL_NAME,
                "risk_factors": ["not enough fresh market data"],
            }

        features = self.extract_features(opportunity)
        probability = self._probability(features)
        confidence = self._confidence(features)
        risk_factors = self._risk_factors(features)

        if probability >= 0.66 and confidence >= 0.55 and features["net_profit_usd"] > 0:
            quality = "strong"
            recommendation = "show_to_user"
        elif probability >= 0.52 and features["net_profit_usd"] > 0:
            quality = "watch"
            recommendation = "watch"
        else:
            quality = "weak"
            recommendation = "ignore"

        return {
            "quality": quality,
            "probability": round(probability, 3),
            "confidence": round(confidence, 3),
            "recommendation": recommendation,
            "model": self.MODEL_NAME,
            "features": features,
            "risk_factors": risk_factors,
        }

    def extract_features(self, opportunity: dict) -> dict:
        buy_size = self._float(opportunity.get("buy_size"))
        sell_size = self._float(opportunity.get("sell_size"))
        visible_size = min(buy_size, sell_size) if buy_size and sell_size else 0.0
        gross_profit = self._float(opportunity.get("gross_profit_usd"))
        fees = self._float(opportunity.get("estimated_fees_usd"))
        net_profit = self._float(opportunity.get("estimated_net_profit_usd"))
        spread_pct = self._float(opportunity.get("spread_pct"))
        score = self._float(opportunity.get("score"))
        fee_drag = fees / max(abs(gross_profit), 1.0)
        profit_after_fee_ratio = net_profit / max(abs(gross_profit), 1.0)

        return {
            "score": score,
            "spread_pct": spread_pct,
            "net_profit_usd": net_profit,
            "gross_profit_usd": gross_profit,
            "fee_drag": round(fee_drag, 4),
            "profit_after_fee_ratio": round(profit_after_fee_ratio, 4),
            "visible_size": visible_size,
            "buy_size": buy_size,
            "sell_size": sell_size,
            "is_positive_after_fees": bool(opportunity.get("is_positive_after_fees", net_profit > 0)),
        }

    def _probability(self, features: dict) -> float:
        raw = (
            features["score"] / 100 * 2.1
            + min(max(features["spread_pct"], -1.5), 1.5) * 0.55
            + min(max(features["net_profit_usd"], -25), 25) / 25 * 0.9
            + min(features["visible_size"], 25) / 25 * 0.35
            - min(features["fee_drag"], 2.0) * 0.45
            - 1.25
        )
        return 1 / (1 + math.exp(-raw))

    def _confidence(self, features: dict) -> float:
        size_component = min(features["visible_size"], 25) / 25
        score_component = features["score"] / 100
        fee_component = max(0.0, 1 - min(features["fee_drag"], 1.5) / 1.5)
        return max(0.0, min(1.0, 0.2 + score_component * 0.45 + size_component * 0.25 + fee_component * 0.1))

    def _risk_factors(self, features: dict) -> list[str]:
        risks = []
        if not features["is_positive_after_fees"]:
            risks.append("net result is not positive after fees")
        if features["fee_drag"] > 0.55:
            risks.append("fees consume a large part of gross spread")
        if features["visible_size"] <= 0:
            risks.append("visible liquidity size is unknown")
        elif features["visible_size"] < 2:
            risks.append("visible liquidity is small")
        if features["spread_pct"] < 0.05:
            risks.append("spread is too narrow")
        return risks or ["no major top-of-book risk detected"]

    @staticmethod
    def _float(value) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0
