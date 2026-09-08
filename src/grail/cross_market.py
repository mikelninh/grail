from dataclasses import dataclass


@dataclass(frozen=True)
class MarketQuote:
    marketplace: str
    price_native: float
    native_symbol: str
    price_usd: float
    fee_pct: float = 0.0


@dataclass(frozen=True)
class MarketDiscrepancy:
    cheaper_market: str
    expensive_market: str
    effective_gap_pct: float
    cheaper_effective_usd: float
    expensive_effective_usd: float


def compare_quotes(a: MarketQuote, b: MarketQuote) -> MarketDiscrepancy:
    a_effective = a.price_usd * (1 + a.fee_pct / 100)
    b_effective = b.price_usd * (1 + b.fee_pct / 100)
    cheap, expensive = (a, b) if a_effective <= b_effective else (b, a)
    cheap_eff, exp_eff = sorted((a_effective, b_effective))
    gap = 0.0 if exp_eff == 0 else (exp_eff - cheap_eff) / exp_eff * 100
    return MarketDiscrepancy(cheap.marketplace, expensive.marketplace, round(gap, 2), round(cheap_eff, 2), round(exp_eff, 2))
