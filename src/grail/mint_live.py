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


_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12}
_COINGECKO_OMI_URL = "https://api.coingecko.com/api/v3/simple/price?ids=ecomi&vs_currencies=usd"


@dataclass(frozen=True)
class EditionListing:
    collectible: str
    mint: int
    marketplace: str
    ask_usd: float  # USD approximation shown when the listing event was recorded.
    ask_omi: int | None
    source_url: str
    observed_at: str
    listed_date: str | None = None
    age_days: int | None = None


@dataclass(frozen=True)
class MintCandidate:
    collectible: str
    mint: int
    ask_usd: float  # Repriced at current OMI/USD when available.
    ask_omi: int | None
    omi_usd: float | None
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
    req = urllib.request.Request(url, headers={"User-Agent": "GRAIL/0.4 collector-intelligence (+https://github.com/mikelninh/grail)"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def fetch_omi_usd(timeout: float = 15.0) -> float:
    """Fetch one current OMI/USD spot observation for repricing OMI-denominated asks."""
    req = urllib.request.Request(_COINGECKO_OMI_URL, headers={"User-Agent": "GRAIL/0.4 collector-intelligence"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    price = float(payload["ecomi"]["usd"])
    if not (0 < price < 1):
        raise ValueError(f"implausible OMI/USD price: {price}")
    return price


def _parse_event_date(day: str, month: str, observed_at: str) -> tuple[str | None, int | None]:
    try:
        observed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        candidate = datetime(observed.year, _MONTHS[month.lower()], int(day), tzinfo=timezone.utc)
        if candidate > observed and (candidate - observed).days > 14:
            candidate = candidate.replace(year=observed.year - 1)
        age = max(0, (observed.date() - candidate.date()).days)
        return candidate.date().isoformat(), age
    except (ValueError, KeyError):
        return None, None


def parse_latest_stackr_listings(html: str, collectible: str, source_url: str, observed_at: str | None = None) -> list[EditionListing]:
    """Parse latest provider-reported StackR event per mint from the public live-market section."""
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
    # VeVe Alpha emits newest events first. Repricing/relisting the same edition can create
    # several rows, so retain only the first (latest) event for each mint.
    seen_mints: set[int] = set()
    rows: list[EditionListing] = []
    for match in pattern.finditer(text):
        day, month = match.group(1), match.group(2)
        mint = int(match.group(3).replace(",", ""))
        if mint in seen_mints:
            continue
        seen_mints.add(mint)
        omi = int(match.group(4).replace(",", ""))
        historical_usd = float(match.group(5).replace(",", ""))
        listed_date, age_days = _parse_event_date(day, month, now) if day and month else (None, None)
        rows.append(EditionListing(collectible, mint, "StackR", historical_usd, omi, source_url, now, listed_date, age_days))
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


def score_mint_listing(
    listing: EditionListing,
    market: MarketObservation,
    collectible: Collectible,
    omi_usd: float | None = None,
) -> MintCandidate:
    floor = market.stackr_floor_usd
    current_ask = listing.ask_usd
    pricing_verified = False
    if listing.ask_omi is not None and omi_usd is not None:
        current_ask = listing.ask_omi * omi_usd
        pricing_verified = True

    premium = 0.0 if floor <= 0 else (current_ask - floor) / floor
    price_score = max(0.0, min(100.0, 55.0 - premium * 90.0))
    mscore, signals = mint_score(listing.mint, collectible)

    scarcity = 50.0
    if collectible.total_editions:
        scarcity = max(20.0, min(95.0, 100 - collectible.total_editions / 20000.0 * 70.0))
    listing_activity = min(100.0, 20.0 + (market.listings_30d or 0) * 1.2)

    confidence = 58.0 + (7 if collectible.total_editions else 0) + (7 if signals else 0) + (5 if market.listings_30d is not None else 0)
    confidence += 8 if pricing_verified else 0
    confidence += 3 if listing.age_days is not None else 0
    confidence = min(88.0, confidence)

    reasons = [signal.reason for signal in signals[:4]]
    if pricing_verified and listing.ask_omi is not None:
        reasons.insert(0, f"repriced {listing.ask_omi:,} OMI at current OMI/USD {omi_usd:.8f}")
    else:
        reasons.insert(0, "current OMI/USD unavailable; USD ask is not safe for execution")

    if premium <= -0.10:
        reasons.insert(0, f"current ask is {-premium:.0%} below daily StackR floor snapshot — verify live floor")
    elif premium >= 0.20:
        reasons.insert(0, f"current ask is {premium:.0%} above daily StackR floor snapshot")
    else:
        reasons.insert(0, f"current ask is {premium:+.0%} vs daily StackR floor snapshot")
    if listing.age_days is not None:
        reasons.insert(0, f"latest provider-reported event for this mint is {listing.age_days}d old")

    total = (price_score * 0.38 + mscore * 0.40 + scarcity * 0.12 + listing_activity * 0.10)
    total *= 0.78 + 0.22 * confidence / 100.0

    if not pricing_verified:
        total = min(total, 35.0)
        actionability = "pricing-unverified"
    elif premium > 2.0:
        total = min(total, 20.0)
        actionability = "reject-price"
    elif premium > 0.5:
        total = min(total, 45.0)
        actionability = "reject-price"
    elif premium <= 0.20:
        actionability = "verify-now"
    else:
        actionability = "watch"

    return MintCandidate(
        collectible=collectible.name,
        mint=listing.mint,
        ask_usd=round(current_ask, 2),
        ask_omi=listing.ask_omi,
        omi_usd=omi_usd,
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
    try:
        omi_usd = fetch_omi_usd()
    except Exception as exc:
        omi_usd = None
        errors.append({"url": _COINGECKO_OMI_URL, "error": f"{type(exc).__name__}: {exc}"})

    for item in payload["collectibles"]:
        url = str(item["url"])
        try:
            html = fetch_html(url)
            market = parse_vevealpha_html(html, url)
            collectible = _collectible_from_watch(item, market)
            for listing in parse_latest_stackr_listings(html, market.collectible, url, market.observed_at):
                candidates.append(score_mint_listing(listing, market, collectible, omi_usd=omi_usd))
        except Exception as exc:
            errors.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})

    rank = {"verify-now": 4, "watch": 3, "pricing-unverified": 2, "reject-price": 1}
    candidates.sort(key=lambda c: (rank[c.actionability], c.opportunity_score, c.mint_score), reverse=True)
    return candidates, errors


def write_results(path: str | Path, candidates: list[MintCandidate], errors: list[dict[str, str]]) -> None:
    Path(path).write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "read-only mint intelligence; provider-reported listings and daily floor snapshots must be verified live before acting",
        "candidates": [asdict(c) for c in candidates],
        "errors": errors,
    }, indent=2, sort_keys=True), encoding="utf-8")
