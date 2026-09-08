from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    collectible_id: str
    quantity: int
    floor_usd: float
    median_sale_usd: float | None
    sales_30d: int


@dataclass(frozen=True)
class PortfolioValuation:
    floor_value: float
    fair_value: float
    liquidation_value: float
    liquidity_haircut_pct: float


def value_portfolio(positions: list[Position]) -> PortfolioValuation:
    floor_value = sum(p.quantity * p.floor_usd for p in positions)
    fair_value = sum(p.quantity * (p.median_sale_usd or p.floor_usd) for p in positions)
    liquidation = 0.0
    for p in positions:
        haircut = 0.10 if p.sales_30d >= 20 else 0.20 if p.sales_30d >= 5 else 0.35
        base = min(p.floor_usd, p.median_sale_usd or p.floor_usd)
        liquidation += p.quantity * base * (1 - haircut)
    haircut_pct = 0.0 if fair_value <= 0 else (1 - liquidation / fair_value) * 100
    return PortfolioValuation(round(floor_value, 2), round(fair_value, 2), round(liquidation, 2), round(haircut_pct, 2))
