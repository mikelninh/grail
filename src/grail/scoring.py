from .mint import mint_score
from .models import Collectible, Listing, OpportunityScore, median


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def score_listing(listing: Listing, collectible: Collectible) -> OpportunityScore:
    """Evidence-first opportunity score; never interprets the result as financial advice."""
    reasons: list[str] = []
    reference = median(listing.recent_sales_usd) or listing.market_floor_usd
    discount = 0.0 if reference <= 0 else (reference - listing.ask_usd) / reference
    price = _clamp(50 + discount * 180)
    if discount >= 0.10:
        reasons.append(f"ask is {discount:.0%} below recent reference")
    elif discount <= -0.20:
        reasons.append(f"ask is {-discount:.0%} above recent reference")

    mint, signals = mint_score(listing.mint, collectible)
    reasons.extend(signal.reason for signal in signals[:3])

    velocity = min(1.0, listing.sales_30d / 30.0)
    supply_pressure = min(1.0, listing.active_listings / max(1, listing.sales_30d + 1))
    liquidity = _clamp(25 + 75 * velocity - 30 * supply_pressure)
    if listing.sales_30d >= 10:
        reasons.append(f"{listing.sales_30d} sales in 30d")

    scarcity = 50.0
    if collectible.total_editions:
        scarcity = _clamp(100 - (collectible.total_editions / 20000) * 70, 20, 95)
        if collectible.total_editions <= 1000:
            reasons.append(f"scarce supply: {collectible.total_editions} editions")

    evidence_points = 0
    evidence_points += 2 if listing.recent_sales_usd else 0
    evidence_points += 1 if listing.market_floor_usd > 0 else 0
    evidence_points += 1 if listing.sales_30d > 0 else 0
    evidence_points += 1 if collectible.total_editions else 0
    evidence_points += 1 if signals else 0
    confidence = _clamp(25 + evidence_points * 12.5)

    total = price * 0.34 + mint * 0.31 + liquidity * 0.20 + scarcity * 0.15
    total *= 0.70 + 0.30 * (confidence / 100)

    return OpportunityScore(listing.id, round(_clamp(total), 2), round(price, 2), round(mint, 2), round(liquidity, 2), round(scarcity, 2), round(confidence, 2), tuple(reasons))
