from __future__ import annotations

import html as html_lib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .mint_live import _MONTHS, fetch_html


@dataclass(frozen=True)
class SaleEvent:
    collectible_id: str
    collectible: str
    mint: int
    marketplace: str
    price_usd: float | None
    price_omi: int | None
    seller: str | None
    buyer: str | None
    sold_date: str | None
    source_url: str
    observed_at: str


def _date(day: str | None, month: str | None, observed_at: str) -> str | None:
    if not day or not month:
        return None
    try:
        observed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
        candidate = datetime(observed.year, _MONTHS[month.lower()], int(day), tzinfo=timezone.utc)
        if candidate.date() > observed.date() and (candidate.date() - observed.date()).days > 14:
            candidate = candidate.replace(year=observed.year - 1)
        return candidate.date().isoformat()
    except (ValueError, KeyError):
        return None


def _participant(token: str | None) -> str | None:
    if not token:
        return None
    token = token.strip()
    if token in {"—", "-"}:
        return None
    return token


def parse_recent_sales_html(html: str, *, collectible_id: str, collectible: str, source_url: str, observed_at: str | None = None) -> list[SaleEvent]:
    """Parse provider-rendered Recent sales rows.

    VeVe Alpha rows can contain either USD or OMI, and participant columns vary by source.
    The parser therefore anchors on date + edition + marketplace + terminal price rather than
    assuming a fixed table-column count.
    """
    observed_at = observed_at or datetime.now(timezone.utc).isoformat()
    text = re.sub(r"<[^>]+>", " ", html_lib.unescape(html))
    text = re.sub(r"\s+", " ", text)
    start = text.lower().find("recent sales")
    if start < 0:
        return []
    text = text[start + len("recent sales"):]
    ends = [x for marker in ("never miss a deal", "holders", "← back", "about this data") if (x := text.lower().find(marker)) >= 0]
    if ends:
        text = text[:min(ends)]

    # Split at each dated edition row while retaining the date header.
    header = re.compile(r"(?=(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)(?:,\s*\d{1,2}:\d{2})?\s*(?:·|\u00b7)?\s*#\s*([0-9][0-9,]*)\s+(VEVE|STACKR)\b)", re.I)
    matches = list(header.finditer(text))
    rows: list[SaleEvent] = []
    seen: set[tuple[int, str | None, str]] = set()
    for idx, match in enumerate(matches):
        chunk = text[match.start(): matches[idx + 1].start() if idx + 1 < len(matches) else len(text)]
        day, month, mint_raw, market = match.group(1), match.group(2), match.group(3), match.group(4).upper()
        mint = int(mint_raw.replace(",", ""))

        omi_matches = list(re.finditer(r"([0-9][0-9,]*)\s*OMI\b", chunk, re.I))
        usd_matches = list(re.finditer(r"\$\s*([0-9][0-9,]*(?:\.[0-9]+)?)", chunk))
        price_omi = int(omi_matches[-1].group(1).replace(",", "")) if omi_matches else None
        price_usd = float(usd_matches[-1].group(1).replace(",", "")) if usd_matches else None
        if price_omi is None and price_usd is None:
            continue

        # Participant tokens are handles or truncated/full EVM addresses between market and price.
        middle = chunk[match.end() - match.start():]
        first_price_positions = [m.start() for m in list(re.finditer(r"(?:\$\s*[0-9]|[0-9][0-9,]*\s*OMI)", middle, re.I))]
        if first_price_positions:
            middle = middle[:first_price_positions[0]]
        participants = re.findall(r"@[A-Za-z0-9_.-]{2,40}|0x[a-fA-F0-9]{4,64}(?:…[a-fA-F0-9]{2,16})?", middle)
        seller = _participant(participants[0]) if len(participants) >= 2 else None
        buyer = _participant(participants[1]) if len(participants) >= 2 else (_participant(participants[0]) if len(participants) == 1 else None)
        sold_date = _date(day, month, observed_at)
        key = (mint, sold_date, market)
        if key in seen:
            continue
        seen.add(key)
        rows.append(SaleEvent(collectible_id, collectible, mint, market, price_usd, price_omi, seller, buyer, sold_date, source_url, observed_at))
    return rows


def scan_sales_watchlist(path: str | Path, max_workers: int = 8) -> tuple[list[SaleEvent], list[dict[str, str]]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    sales: list[SaleEvent] = []
    errors: list[dict[str, str]] = []

    def scan(item: dict):
        url = str(item["url"])
        try:
            html = fetch_html(url)
            # Product name is available in page title/structured data, but watchlist note is a stable fallback.
            name_match = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', html, re.I)
            name = html_lib.unescape(name_match.group(1)).strip() if name_match else str(item.get("note") or item["id"])
            now = datetime.now(timezone.utc).isoformat()
            return parse_recent_sales_html(html, collectible_id=str(item["id"]), collectible=name, source_url=url, observed_at=now), None
        except Exception as exc:
            return [], {"url": url, "error": f"{type(exc).__name__}: {exc}"}

    with ThreadPoolExecutor(max_workers=max(1, min(max_workers, 12))) as pool:
        futures = [pool.submit(scan, item) for item in payload["collectibles"]]
        for f in as_completed(futures):
            found, err = f.result()
            sales.extend(found)
            if err:
                errors.append(err)
    sales.sort(key=lambda s: (s.sold_date or "", s.collectible_id, s.mint), reverse=True)
    return sales, errors


def write_sales(path: str | Path, sales: list[SaleEvent], errors: list[dict[str, str]]) -> None:
    Path(path).write_text(json.dumps({"generated_at": datetime.now(timezone.utc).isoformat(), "sales": [asdict(s) for s in sales], "errors": errors}, indent=2), encoding="utf-8")
