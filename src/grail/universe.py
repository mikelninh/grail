from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

SEARCH_URL = "https://vevealpha.com/api/collectibles/search"
DEFAULT_QUERIES = tuple("abcdefghijklmnopqrstuvwxyz0123456789") + (
    "spider", "batman", "superman", "star wars", "marvel", "disney",
    "x-men", "avengers", "fantastic four", "iron man", "yoda", "comic",
)

@dataclass(frozen=True)
class UniverseAsset:
    collectible_id: str
    name: str
    slug: str
    source_url: str
    image_url: str | None
    rarity: str | None
    kind: str
    floor_usd: float | None
    floor_omi: int | None
    mcap: float | None
    is_top200: bool
    provider_grail: bool

    @property
    def is_comic(self) -> bool:
        return self.kind == "comic"


def normalise_item(item: dict) -> UniverseAsset:
    collectible_id = str(item.get("collectible_id") or "").strip()
    slug = str(item.get("slug") or "").strip()
    name = str(item.get("collectible_name") or item.get("name") or "").strip()
    if not collectible_id or not slug or not name:
        raise ValueError("catalog item missing collectible_id, slug or name")
    is_comic = bool(item.get("is_comic")) or str(item.get("element_type") or "") == "COMIC_COVER"
    floor_usd = item.get("floor_usd")
    floor_omi = item.get("floor_omi")
    mcap = item.get("mcap")
    return UniverseAsset(
        collectible_id=collectible_id,
        name=name,
        slug=slug,
        source_url=f"https://vevealpha.com/c/{slug}",
        image_url=str(item.get("image_url")) if item.get("image_url") else None,
        rarity=str(item.get("rarity")) if item.get("rarity") else None,
        kind="comic" if is_comic else "collectible",
        floor_usd=float(floor_usd) if floor_usd not in (None, "") else None,
        floor_omi=int(float(floor_omi)) if floor_omi not in (None, "") else None,
        mcap=float(mcap) if mcap not in (None, "") else None,
        is_top200=bool(item.get("is_top200_veve")),
        provider_grail=bool(item.get("is_grail")),
    )


def _fetch_search(query: str, limit: int = 40, timeout: float = 20.0) -> list[dict]:
    url = SEARCH_URL + "?" + urllib.parse.urlencode({"q": query, "limit": min(40, max(1, limit))})
    req = urllib.request.Request(url, headers={"User-Agent":"GRAIL/0.8 universe-discovery (+https://github.com/mikelninh/grail)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = json.loads(r.read().decode("utf-8"))
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, dict):
        return [x for x in raw.get("items", []) if isinstance(x, dict)]
    return []


def discover_catalog(queries: Iterable[str] = DEFAULT_QUERIES, timeout: float = 20.0) -> tuple[list[UniverseAsset], list[dict[str,str]]]:
    assets: dict[str, UniverseAsset] = {}
    errors: list[dict[str,str]] = []
    for query in queries:
        try:
            for raw in _fetch_search(str(query), timeout=timeout):
                try:
                    asset = normalise_item(raw)
                except Exception as exc:
                    errors.append({"query":str(query),"error":f"normalise: {type(exc).__name__}: {exc}"})
                    continue
                assets[asset.collectible_id] = asset
        except Exception as exc:
            errors.append({"query":str(query),"error":f"{type(exc).__name__}: {exc}"})
    rows = sorted(assets.values(), key=lambda a: (triage_score(a), a.name), reverse=True)
    return rows, errors


def _issue_number(name: str) -> int | None:
    m = re.search(r"#\s*([0-9]{1,4})\b", name)
    return int(m.group(1)) if m else None


def triage_score(asset: UniverseAsset) -> float:
    """Cheap catalog-only score. It chooses what deserves deeper inspection; it is never a GRAIL verdict."""
    score = 0.0
    if asset.provider_grail:
        score += 30
    if asset.is_top200:
        score += 15
    if asset.is_comic:
        score += 8
        issue = _issue_number(asset.name)
        if issue == 1:
            score += 10
        elif issue in {4, 5, 15, 27, 181, 252, 300, 361}:
            score += 4  # title-level attention only; not a historical-key claim
    rarity = (asset.rarity or "").upper()
    score += {"SECRET_RARE":12,"ULTRA_RARE":8,"RARE":4,"UNCOMMON":2}.get(rarity, 0)
    if asset.mcap:
        # enough market significance to justify deep inspection, without automatically favouring only whales
        if asset.mcap >= 1_000_000: score += 10
        elif asset.mcap >= 250_000: score += 7
        elif asset.mcap >= 50_000: score += 4
    if asset.floor_usd is not None:
        if 1 <= asset.floor_usd <= 500: score += 6
        elif asset.floor_usd <= 2_500: score += 3
    return round(score, 2)


def select_for_deep_scan(assets: Iterable[UniverseAsset], limit: int = 120, min_comics: int = 50) -> list[UniverseAsset]:
    rows = sorted(assets, key=triage_score, reverse=True)
    comics = [a for a in rows if a.is_comic][:min_comics]
    selected: dict[str,UniverseAsset] = {a.collectible_id:a for a in comics}
    for asset in rows:
        selected.setdefault(asset.collectible_id, asset)
        if len(selected) >= limit:
            break
    return sorted(selected.values(), key=triage_score, reverse=True)[:limit]


def write_catalog(path: str | Path, assets: list[UniverseAsset], errors: list[dict[str,str]]) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "VeVe Alpha public collectible search",
        "counts": {"assets":len(assets),"comics":sum(a.is_comic for a in assets),"collectibles":sum(not a.is_comic for a in assets)},
        "assets": [asdict(a) | {"triage_score":triage_score(a)} for a in assets],
        "errors": errors,
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
