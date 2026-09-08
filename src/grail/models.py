from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class Collectible:
    id: str
    name: str
    brand: str
    character: str | None = None
    rarity: str | None = None
    total_editions: int | None = None
    release_year: int | None = None
    first_appearance_year: int | None = None
    semantic_numbers: tuple[int, ...] = ()
    semantic_labels: dict[int, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Listing:
    id: str
    collectible_id: str
    marketplace: str
    mint: int
    ask_usd: float
    market_floor_usd: float
    recent_sales_usd: tuple[float, ...] = ()
    sales_30d: int = 0
    active_listings: int = 0
    listed_at_epoch: int | None = None


@dataclass(frozen=True)
class MintSignal:
    kind: str
    score: float
    reason: str


@dataclass(frozen=True)
class OpportunityScore:
    listing_id: str
    total: float
    price: float
    mint: float
    liquidity: float
    scarcity: float
    confidence: float
    reasons: tuple[str, ...]


def median(values: Iterable[float]) -> float | None:
    ordered = sorted(float(v) for v in values)
    if not ordered:
        return None
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2
