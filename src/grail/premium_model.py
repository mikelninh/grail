from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import Any, Iterable

from .mint import analyse_mint
from .models import Collectible


@dataclass(frozen=True)
class PremiumEvidence:
    kind: str
    sample_size: int
    median_premium_pct: float
    q25_pct: float
    q75_pct: float
    confidence: str
    usable_for_value: bool


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo, hi = int(pos), min(len(xs) - 1, int(pos) + 1)
    frac = pos - lo
    return xs[lo] * (1 - frac) + xs[hi] * frac


def build_premium_model(sales: Iterable[Any], watch_by_id: dict[str, dict[str, Any]], *, min_samples: int = 10) -> dict[str, dict[str, Any]]:
    rows = [dict(s) if isinstance(s, dict) else dict(vars(s)) for s in sales]
    by_collectible: dict[str, list[float]] = defaultdict(list)
    for s in rows:
        if s.get("price_usd") and float(s["price_usd"]) > 0:
            by_collectible[str(s.get("collectible_id"))].append(float(s["price_usd"]))

    buckets: dict[str, list[float]] = defaultdict(list)
    examples: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for s in rows:
        price = s.get("price_usd")
        cid = str(s.get("collectible_id"))
        if not price or float(price) <= 0 or len(by_collectible.get(cid, [])) < 5:
            continue
        baseline = statistics.median(by_collectible[cid])
        if baseline <= 0:
            continue
        meta = watch_by_id.get(cid, {})
        collectible = Collectible(
            id=cid,
            name=str(s.get("collectible") or meta.get("note") or cid),
            brand=str(meta.get("brand", "Unknown")),
            character=meta.get("character"),
            first_appearance_year=meta.get("first_appearance_year"),
            release_year=meta.get("release_year"),
            semantic_numbers=tuple(int(x) for x in meta.get("semantic_numbers", [])),
            semantic_labels={int(k): str(v) for k, v in meta.get("semantic_labels", {}).items()},
        )
        premium = (float(price) / baseline - 1.0) * 100.0
        for sig in analyse_mint(int(s.get("mint", 0)), collectible):
            buckets[sig.kind].append(premium)
            if len(examples[sig.kind]) < 12:
                examples[sig.kind].append({
                    "collectible": s.get("collectible"), "mint": s.get("mint"), "price_usd": price,
                    "premium_pct": round(premium, 2), "reason": sig.reason, "source_url": s.get("source_url"),
                })

    model: dict[str, dict[str, Any]] = {}
    for kind, vals in buckets.items():
        n = len(vals)
        confidence = "high" if n >= 50 else "medium" if n >= 20 else "directional" if n >= 5 else "insufficient"
        evidence = PremiumEvidence(
            kind=kind,
            sample_size=n,
            median_premium_pct=round(statistics.median(vals), 2),
            q25_pct=round(_quantile(vals, .25), 2),
            q75_pct=round(_quantile(vals, .75), 2),
            confidence=confidence,
            usable_for_value=n >= min_samples,
        )
        model[kind] = {**asdict(evidence), "examples": examples[kind]}
    return model


def conservative_premium_pct(signal_kinds: Iterable[str], model: dict[str, dict[str, Any]], *, cap_pct: float = 100.0) -> float:
    """Use only evidenced positive medians; take strongest, not additive folklore."""
    eligible = [float(model[k]["median_premium_pct"]) for k in signal_kinds if k in model and model[k].get("usable_for_value") and float(model[k].get("median_premium_pct", 0)) > 0]
    return round(min(cap_pct, max(eligible, default=0.0)), 2)
