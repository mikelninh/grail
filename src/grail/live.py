from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return " ".join(self.parts)


@dataclass(frozen=True)
class MarketObservation:
    source: str
    source_url: str
    collectible: str
    rarity: str | None
    edition_size: int | None
    veve_floor_usd: float
    stackr_floor_usd: float
    listings_30d: int | None
    observed_at: str

    @property
    def cheaper_market(self) -> str:
        return "StackR" if self.stackr_floor_usd <= self.veve_floor_usd else "VeVe"

    @property
    def cheaper_floor_usd(self) -> float:
        return min(self.stackr_floor_usd, self.veve_floor_usd)

    @property
    def expensive_floor_usd(self) -> float:
        return max(self.stackr_floor_usd, self.veve_floor_usd)

    @property
    def nominal_gap_pct(self) -> float:
        high = self.expensive_floor_usd
        if high <= 0:
            return 0.0
        return round((high - self.cheaper_floor_usd) / high * 100, 2)


@dataclass(frozen=True)
class LiveCandidate:
    collectible: str
    cheaper_market: str
    cheap_floor_usd: float
    expensive_floor_usd: float
    nominal_gap_pct: float
    confidence: float
    activity_score: float
    opportunity_score: float
    source_url: str
    observed_at: str
    warnings: tuple[str, ...]


def _normalise_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return re.sub(r"\s+", " ", parser.text())


def _money_after(label: str, text: str) -> float:
    match = re.search(re.escape(label) + r"\s*\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)", text, re.I)
    if not match:
        raise ValueError(f"missing field: {label}")
    return float(match.group(1).replace(",", ""))


def _int_after(label: str, text: str) -> int | None:
    match = re.search(re.escape(label) + r"\s*([0-9][0-9,]*)", text, re.I)
    return int(match.group(1).replace(",", "")) if match else None


def parse_vevealpha_html(html: str, source_url: str, observed_at: str | None = None) -> MarketObservation:
    text = _normalise_text(html)
    # VeVe Alpha pages are server-rendered. The title precedes the marketplace labels.
    title_match = re.search(r"(?:Floor Price, Sales History & Market Data \| VeVe Alpha \| Veve Alpha\s*)?#\s*([^#]+?)\s+(?:VeVe gem floor|COMMON|UNCOMMON|RARE|ULTRA_RARE|SECRET_RARE)", text, re.I)
    if not title_match:
        # Fallback for pages where the heading is emitted without a literal '#'.
        title_match = re.search(r"VeVe Alpha\s+(.+?)\s+(?:COMMON|UNCOMMON|RARE|ULTRA_RARE|SECRET_RARE)\s+(?:COLLECTIBLE|COMIC)", text, re.I)
    collectible = title_match.group(1).strip() if title_match else source_url.rstrip("/").split("/")[-1]

    rarity_match = re.search(r"\b(COMMON|UNCOMMON|RARE|ULTRA_RARE|SECRET_RARE)\b", text)
    rarity = rarity_match.group(1) if rarity_match else None
    editions_match = re.search(r"\b([0-9][0-9,]*)\s+editions\b", text, re.I)
    edition_size = int(editions_match.group(1).replace(",", "")) if editions_match else None

    return MarketObservation(
        source="VeVe Alpha",
        source_url=source_url,
        collectible=collectible,
        rarity=rarity,
        edition_size=edition_size,
        veve_floor_usd=_money_after("VeVe gem floor", text),
        stackr_floor_usd=_money_after("StackR floor", text),
        listings_30d=_int_after("Listings 30d", text),
        observed_at=observed_at or datetime.now(timezone.utc).isoformat(),
    )


def fetch_vevealpha(url: str, timeout: float = 20.0) -> MarketObservation:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "GRAIL/0.2 collector-intelligence (+https://github.com/mikelninh/grail)"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        html = response.read().decode("utf-8", errors="replace")
    return parse_vevealpha_html(html, url)


def rank_observation(obs: MarketObservation) -> LiveCandidate:
    warnings: list[str] = [
        "floor gap is not executable arbitrage until fees, depth, custody and transfer constraints are verified"
    ]
    gap = obs.nominal_gap_pct

    # Activity is intentionally conservative: listings are supply/activity evidence, not realised sales.
    listings = obs.listings_30d or 0
    activity = min(100.0, 20.0 + listings * 1.5)
    if listings < 5:
        warnings.append("very low 30d listing activity")

    evidence_points = 3  # two floors + named source
    evidence_points += 1 if obs.edition_size else 0
    evidence_points += 1 if obs.listings_30d is not None else 0
    confidence = min(90.0, 42.0 + evidence_points * 9.0)

    # V0.2 ranks cross-market asymmetry, but avoids equating a huge spread with liquidity.
    gap_score = min(100.0, gap * 1.65)
    scarcity = 50.0
    if obs.edition_size:
        scarcity = max(20.0, min(95.0, 100 - (obs.edition_size / 20000.0) * 70.0))
    score = gap_score * 0.62 + activity * 0.23 + scarcity * 0.15
    score *= 0.72 + 0.28 * confidence / 100.0

    return LiveCandidate(
        collectible=obs.collectible,
        cheaper_market=obs.cheaper_market,
        cheap_floor_usd=round(obs.cheaper_floor_usd, 2),
        expensive_floor_usd=round(obs.expensive_floor_usd, 2),
        nominal_gap_pct=gap,
        confidence=round(confidence, 2),
        activity_score=round(activity, 2),
        opportunity_score=round(min(100.0, score), 2),
        source_url=obs.source_url,
        observed_at=obs.observed_at,
        warnings=tuple(warnings),
    )


def scan_urls(urls: Iterable[str]) -> tuple[list[LiveCandidate], list[dict[str, str]]]:
    candidates: list[LiveCandidate] = []
    errors: list[dict[str, str]] = []
    for url in urls:
        try:
            candidates.append(rank_observation(fetch_vevealpha(url)))
        except Exception as exc:  # A single provider failure must not kill a watchlist scan.
            errors.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})
    candidates.sort(key=lambda x: x.opportunity_score, reverse=True)
    return candidates, errors


def load_watchlist(path: str | Path) -> list[str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return [str(item["url"]) for item in payload["collectibles"]]


def write_scan(path: str | Path, candidates: list[LiveCandidate], errors: list[dict[str, str]]) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "read-only intelligence; not financial advice",
        "candidates": [asdict(c) for c in candidates],
        "errors": errors,
    }
    Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
