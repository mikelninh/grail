from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .provider_edition import _rpc, discover_public_supabase_config

SEARCH_URL = "https://vevealpha.com/api/collectibles/search"
REGISTRY_PAGE = "https://vevealpha.com/analytics/collectibles"
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
    brand: str | None = None
    grade: str | None = None
    era: str | None = None
    supply: int | None = None
    holders: int | None = None
    sales30: int | None = None
    vol30: float | None = None
    active_pct: float | None = None
    rating: float | None = None
    is_fa: bool | None = None
    is_fe: bool | None = None
    provider_alpha: bool = False
    alpha_why: tuple[str, ...] = ()
    sale_median_30d: float | None = None
    floor_vs_sales_pct: float | None = None

    @property
    def is_comic(self) -> bool:
        return self.kind == "comic"


def _num(value, cast=float):
    if value in (None, ""): return None
    try: return cast(float(value))
    except (TypeError, ValueError): return None


def normalise_item(item: dict) -> UniverseAsset:
    collectible_id = str(item.get("collectible_id") or "").strip()
    slug = str(item.get("slug") or "").strip()
    name = str(item.get("collectible_name") or item.get("name") or "").strip()
    if not collectible_id or not slug or not name:
        raise ValueError("catalog item missing collectible_id, slug or name")
    is_comic = bool(item.get("is_comic")) or str(item.get("element_type") or "") == "COMIC_COVER"
    return UniverseAsset(
        collectible_id=collectible_id,
        name=name,
        slug=slug,
        source_url=f"https://vevealpha.com/c/{slug}",
        image_url=str(item.get("image_url")) if item.get("image_url") else None,
        rarity=str(item.get("rarity")) if item.get("rarity") else None,
        kind="comic" if is_comic else "collectible",
        floor_usd=_num(item.get("floor_usd")),
        floor_omi=_num(item.get("floor_omi"), int),
        mcap=_num(item.get("mcap")),
        is_top200=bool(item.get("is_top200_veve")),
        provider_grail=bool(item.get("is_grail")),
        brand=str(item.get("brand")) if item.get("brand") else None,
        grade=str(item.get("grade")) if item.get("grade") else None,
        era=str(item.get("era")) if item.get("era") else None,
        supply=_num(item.get("supply"), int),
        holders=_num(item.get("holders"), int),
        sales30=_num(item.get("sales30"), int),
        vol30=_num(item.get("vol30")),
        active_pct=_num(item.get("active_pct")),
        rating=_num(item.get("rating")),
        is_fa=item.get("is_fa") if isinstance(item.get("is_fa"), bool) else None,
        is_fe=item.get("is_fe") if isinstance(item.get("is_fe"), bool) else None,
        provider_alpha=bool(item.get("is_alpha")),
        alpha_why=tuple(str(x) for x in item.get("alpha_why", []) if x),
        sale_median_30d=_num(item.get("sale_median_30d")),
        floor_vs_sales_pct=_num(item.get("floor_vs_sales_pct")),
    )


def _fetch_search(query: str, limit: int = 40, timeout: float = 20.0) -> list[dict]:
    url = SEARCH_URL + "?" + urllib.parse.urlencode({"q": query, "limit": min(40, max(1, limit))})
    req = urllib.request.Request(url, headers={"User-Agent":"GRAIL/0.8 universe-discovery (+https://github.com/mikelninh/grail)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = json.loads(r.read().decode("utf-8"))
    if isinstance(raw, list): return [x for x in raw if isinstance(x, dict)]
    if isinstance(raw, dict): return [x for x in raw.get("items", []) if isinstance(x, dict)]
    return []


def _fetch_registry_preview(timeout: float = 25.0) -> list[dict]:
    config=discover_public_supabase_config(REGISTRY_PAGE)
    raw=_rpc(config,"get_collectibles_registry_v6",{
        "p_sort":"mcap","p_search":None,"p_limit":50,"p_offset":0,"p_grade":None,
        "p_kind":None,"p_edition":None,"p_incl_store":None,"p_rarity":None,
        "p_ids":None,"p_alpha":None,"p_supply_max":None,
    },timeout)
    if isinstance(raw,dict): return [x for x in raw.get("items",[]) if isinstance(x,dict)]
    if isinstance(raw,list): return [x for x in raw if isinstance(x,dict)]
    return []


def _overlay(base: UniverseAsset, rich: UniverseAsset) -> UniverseAsset:
    fields={}
    for name in (
        "brand","grade","era","supply","holders","sales30","vol30","active_pct","rating",
        "is_fa","is_fe","sale_median_30d","floor_vs_sales_pct",
    ):
        value=getattr(rich,name)
        if value is not None: fields[name]=value
    if rich.floor_usd is not None: fields["floor_usd"]=rich.floor_usd
    if rich.mcap is not None: fields["mcap"]=rich.mcap
    fields["provider_grail"]=base.provider_grail or rich.provider_grail
    fields["provider_alpha"]=rich.provider_alpha
    if rich.alpha_why: fields["alpha_why"]=rich.alpha_why
    return replace(base,**fields)


def discover_catalog(queries: Iterable[str] = DEFAULT_QUERIES, timeout: float = 20.0) -> tuple[list[UniverseAsset], list[dict[str,str]]]:
    assets: dict[str, UniverseAsset] = {}
    errors: list[dict[str,str]] = []
    for query in queries:
        try:
            for raw in _fetch_search(str(query), timeout=timeout):
                try: asset = normalise_item(raw)
                except Exception as exc:
                    errors.append({"query":str(query),"error":f"normalise: {type(exc).__name__}: {exc}"}); continue
                assets[asset.collectible_id] = asset
        except Exception as exc:
            errors.append({"query":str(query),"error":f"{type(exc).__name__}: {exc}"})
    try:
        for raw in _fetch_registry_preview():
            try: rich=normalise_item(raw)
            except Exception: continue
            if rich.collectible_id in assets: assets[rich.collectible_id]=_overlay(assets[rich.collectible_id],rich)
            else: assets[rich.collectible_id]=rich
    except Exception as exc:
        errors.append({"query":"registry-preview","error":f"{type(exc).__name__}: {exc}"})
    rows = sorted(assets.values(), key=lambda a: (triage_score(a), a.name), reverse=True)
    return rows, errors


def _issue_number(name: str) -> int | None:
    m = re.search(r"#\s*([0-9]{1,4})\b", name)
    return int(m.group(1)) if m else None


def triage_score(asset: UniverseAsset) -> float:
    """Cheap market score used only to select deeper inspection; never a GRAIL verdict."""
    score = 0.0
    if asset.provider_grail: score += 30
    if asset.provider_alpha: score += 12
    if asset.is_top200: score += 15
    if asset.is_fa: score += 8
    if asset.is_comic:
        score += 8
        issue = _issue_number(asset.name)
        if issue == 1: score += 10
        elif issue in {4, 5, 15, 27, 181, 252, 300, 361}: score += 4
    rarity = (asset.rarity or "").upper()
    score += {"SECRET_RARE":12,"ULTRA_RARE":8,"RARE":4,"UNCOMMON":2}.get(rarity, 0)
    if asset.grade in {"A+","A"}: score += 5
    if asset.sales30 is not None:
        if asset.sales30 >= 50: score += 10
        elif asset.sales30 >= 10: score += 7
        elif asset.sales30 >= 3: score += 4
    if asset.floor_vs_sales_pct is not None and asset.floor_vs_sales_pct <= -10:
        score += min(15, abs(asset.floor_vs_sales_pct)/4)
    if asset.mcap:
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
        if len(selected) >= limit: break
    return sorted(selected.values(), key=triage_score, reverse=True)[:limit]


def write_catalog(path: str | Path, assets: list[UniverseAsset], errors: list[dict[str,str]]) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "VeVe Alpha public search + public registry preview",
        "counts": {"assets":len(assets),"comics":sum(a.is_comic for a in assets),"collectibles":sum(not a.is_comic for a in assets)},
        "rich_market_rows":sum(a.sales30 is not None or a.grade is not None for a in assets),
        "assets": [asdict(a) | {"triage_score":triage_score(a)} for a in assets],
        "errors": errors,
    }
    Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
