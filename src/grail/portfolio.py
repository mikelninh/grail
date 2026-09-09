from dataclasses import dataclass
from collections import defaultdict


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


@dataclass(frozen=True)
class EditionPosition:
    key: str
    collectible: str
    mint: int
    universe: str
    floor_usd: float
    recent_median_usd: float | None
    sales_30d: int
    evidenced_premium_pct: float = 0.0


@dataclass(frozen=True)
class PortfolioIntelligence:
    floor_value: float
    fair_value: float
    liquidation_value: float
    liquidity_haircut_pct: float
    weighted_sales_30d: float
    concentration: tuple[tuple[str, float], ...]
    best_hold_keys: tuple[str, ...]
    easiest_exit_keys: tuple[str, ...]


def _haircut(sales_30d: int) -> float:
    if sales_30d >= 30:
        return 0.08
    if sales_30d >= 10:
        return 0.15
    if sales_30d >= 3:
        return 0.25
    return 0.40


def value_editions(positions: list[EditionPosition]) -> PortfolioIntelligence:
    """Edition-aware valuation using only evidenced mint premiums.

    Fair value never uses an unevidenced premium. Liquidation value is based on the lower of
    floor/recent median, then receives a liquidity haircut.
    """
    if not positions:
        return PortfolioIntelligence(0, 0, 0, 0, 0, (), (), ())

    floor_value = sum(max(0.0, p.floor_usd) for p in positions)
    fair_values: dict[str, float] = {}
    liquidation_values: dict[str, float] = {}
    universe_values: dict[str, float] = defaultdict(float)

    for p in positions:
        reference = p.recent_median_usd if p.recent_median_usd and p.recent_median_usd > 0 else p.floor_usd
        base_fair = max(p.floor_usd, reference)
        premium = max(0.0, min(100.0, p.evidenced_premium_pct)) / 100.0
        fair = base_fair * (1.0 + premium)
        fair_values[p.key] = fair
        liq_base = min(p.floor_usd, reference) if p.floor_usd > 0 and reference > 0 else max(p.floor_usd, reference)
        liquidation_values[p.key] = max(0.0, liq_base * (1.0 - _haircut(p.sales_30d)))
        universe_values[p.universe or "Unknown"] += fair

    fair_value = sum(fair_values.values())
    liquidation = sum(liquidation_values.values())
    concentration = tuple(sorted(((u, round(v / fair_value * 100.0, 2)) for u, v in universe_values.items()), key=lambda x: x[1], reverse=True)) if fair_value else ()
    haircut_pct = 0.0 if fair_value <= 0 else (1 - liquidation / fair_value) * 100.0
    weighted_sales = sum(p.sales_30d * fair_values[p.key] for p in positions) / fair_value if fair_value else 0.0

    best_hold = tuple(p.key for p in sorted(positions, key=lambda p: (p.evidenced_premium_pct, p.sales_30d), reverse=True)[:5])
    easiest_exit = tuple(p.key for p in sorted(positions, key=lambda p: (p.sales_30d, -_haircut(p.sales_30d)), reverse=True)[:5])
    return PortfolioIntelligence(
        round(floor_value, 2), round(fair_value, 2), round(liquidation, 2), round(haircut_pct, 2),
        round(weighted_sales, 2), concentration, best_hold, easiest_exit,
    )
