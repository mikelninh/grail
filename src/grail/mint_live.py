from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .live import MarketObservation, parse_vevealpha_html
from .mint import mint_score
from .models import Collectible


_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


@dataclass(frozen=True)
class EditionListing:
    collectible: str
    mint: int
    marketplace: str
    ask_usd: float
    ask_omi: int | None
    source_url: str
    observed_at: str
    listed_date: str | None = None
    age_days: int | None = None


@dataclass(frozen=True)
class MintCandidate:
    collectible: str
    mint: int
    ask_usd: float
    floor_usd: float
    premium_to_floor_pct: float
    mint_score: float
    opportunity_score: float
    confidence: float
    reasons: tuple[str, ...]
    source_url: str
    observed_at: str
    listed_date: str | None
    age_days: int | None
    actionability: str


def fetch_html(url: str, timeout: float = 20.0) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "GRAIL/0.3 mint-sniper (+https://github.com/mikelninh/grail)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def _parse_event_date(day: str, month: str, observed_at: str) -> tuple[str | None, int | None]:
    try:
        observed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        candidate = datetime(observed.year, _MONTHS[month.lower()], int(day), tzinfo=timezone.utc)
        # Handle year-boundary pages such as a late-December event observed in early January.
        if candidate > observed and (candidate - observed).days > 14:
            candidate = candidate.replace(year=observed.year - 1)
        age = max(0, (observed.date() - candidate.date()).days)
        return candidate.date().isoformat(), age
    except (ValueError, KeyError):
        return None, None


def parse_latest_stackr_listings(html: str, collectible: str, source_url: str, observed_at: str | None = None) -> list[EditionListing]:
    """Parse StackR listing *events* from VeVe Alpha's public latest-listings section.

    These rows are not assumed to still be active inventory. Freshness is captured so downstream
    ranking can distinguish a recent verify-now candidate from stale historical signal.
    """
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    start = text.find("Latest listings")
    if start >= 0:
        text = text[start:]
    end_markers = [m for marker in ("Recent sales", "Never miss a deal", "← Back to all collectibles") if (m := text.find(marker)) >= 0]
    if end_markers:
        text = text[: min(end_markers)]

    pattern = re.compile(
        r"(?:(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\s*(?:·|\u00b7)?\s*)?"
        r"#\s*([0-9][0-9,]*)\s*STACKR\s*([0-9][0-9,]*)\s*OMI\s*(?:·|\u00b7)?\s*(?:≈|~)?\s*\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)",
        re.I,
    )
    now = observed_at or datetime.now(timezone.utc).isoformat()
    seen: set[tuple[int, int, str | None]] = set()
    rows: list[EditionListing] = []
    for match in pattern.finditer(text):
        day, month = match.group(1), match.group(2)
        mint = int(match.group(3).replace(",", ""))
        omi = int(match.group(4).replace(",", ""))
        usd = float(match.group(5).replace(",", ""))
        listed_date, age_days = _parse_event_date(day, month, now) if day and month else (None, None)
        key = (mint, omi, listed_date)
        if key in seen:
            continue
        seen.add(key)
        rows.append(EditionListing(collectible, mint, "StackR", usd, omi, source_url, now, listed_date, age_days))
    return rows


def _collectible_from_watch(item: dict, market: MarketObservation) -> Collectible:
    semantic_numbers = tuple(int(x) for x in item.get("semantic_numbers", []))
    labels = {int(k): str(v) for k, v in item.get("semantic_labels", {}).items()}
    return Collectible(
        id=item.get("id", item["url"].rstrip("/").split("/")[-1]),
        name=market.collectible,
        brand=str(item.get("brand", "Unknown")),
        character=item.get("character"),
        rarity=market.rarity,
        total_editions=market.edition_size,
        first_appearance_year=item.get("first_appearance_year"),
        semantic_numbers=semantic_numbers,
        semantic_labels=labels,
    )


def score_mint_listing(listing: EditionListing, market: MarketObservation, collectible: Collectible) -> MintCandidate:
    floor = market.stackr_floor_usd
    premium = 0.0 if floor <= 0 else (listing.ask_usd - floor) / floor
    price_score = max(0.0, min(100.0, 55.0 - premium * 90.0))
    mscore, signals = mint_score(listing.mint, collectible)

    scarcity = 50.0
    if collectible.total_editions:
        scarcity = max(20.0, min(95.0, 100 - collectible.total_editions / 20000.0 * 70.0))

    listing_activity = min(100.0, 20.0 + (market.listings_30d or 0) * 1.2)
    confidence = 63.0
    confidence += 7 if collectible.total_editions else 0
    confidence += 7 if signals else 0
    confidence += 5 if market.listings_30d is not None else 0
    confidence += 5 if listing.age_days is not None and listing.age_days <= 1 else 0
    confidence = min(87.0, confidence)

    reasons = [signal.reason for signal in signals[:4]]
    if premium <= -0.10:
        reasons.insert(0, f"listing event ask is {-premium:.0%} below current StackR floor")
    elif premium >= 0.20:
        reasons.insert(0, f"listing event ask is {premium:.0%} above current StackR floor")
    else:
        reasons.insert(0, f"listing event ask is {premium:+.0%} vs current StackR floor")

    if listing.age_days is not None:
        reasons.insert(0, f"listing event is {listing.age_days}d old")

    total = price_score * 0.38 + mscore * 0.40 + scarcity * 0.12 + listing_activity * 0.10
    total *= 0.78 + 0.22 * confidence / 100.0

    # Hard guardrails: semantics must never rescue absurd price positioning.
    if premium > 2.0:
        total = min(total, 20.0)
    elif premium > 0.5:
        total = min(total, 45.0)

    if listing.age_days is None:
        actionability = "historical-signal"
        total = min(total, 50.0)
    elif listing.age_days <= 1:
        actionability = "verify-now"
    elif listing.age_days <= 3:
        actionability = "recent-signal"
        total = min(total, 62.0)
    else:
        actionability = "historical-signal"
        total = min(total, 45.0)

    return MintCandidate(
        collectible=collectible.name,
        mint=listing.mint,
        ask_usd=round(listing.ask_usd, 2),
        floor_usd=round(floor, 2),
        premium_to_floor_pct=round(premium * 100, 2),
        mint_score=round(mscore, 2),
        opportunity_score=round(max(0.0, min(100.0, total)), 2),
        confidence=round(confidence, 2),
        reasons=tuple(reasons),
        source_url=listing.source_url,
        observed_at=listing.observed_at,
        listed_date=listing.listed_date,
        age_days=listing.age_days,
        actionability=actionability,
    )


def scan_watchlist(path: str | Path) -> tuple[list[MintCandidate], list[dict[str, str]]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    candidates: list[MintCandidate] = []
    errors: list[dict[str, str]] = []
    for item in payload["collectibles"]:
        url = str(item["url"])
        try:
            html = fetch_html(url)
            market = parse_vevealpha_html(html, url)
            collectible = _collectible_from_watch(item, market)
            listings = parse_latest_stackr_listings(html, market.collectible, url, market.observed_at)
            for listing in listings:
                candidates.append(score_mint_listing(listing, market, collectible))
        except Exception as exc:
            errors.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})
    rank = {"verify-now": 2, "recent-signal": 1, "historical-signal": 0}
    candidates.sort(key=lambda c: (rank[c.actionability], c.opportunity_score, c.mint_score), reverse=True)
    return candidates, errors


def write_results(path: str | Path, candidates: list[MintCandidate], errors: list[dict[str, str]]) -> None:
    Path(path).write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "mode": "read-only mint intelligence; listing rows are events and must be verified before acting",
                "candidates": [asdict(c) for c in candidates],
                "errors": errors,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
