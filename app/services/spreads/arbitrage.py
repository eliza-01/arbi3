from app.services.spreads.calculator import SpreadResult


def select_best_arbitrage(spreads: list[SpreadResult]) -> SpreadResult | None:
    if not spreads:
        return None
    return max(spreads, key=lambda item: item.delta_pct)
