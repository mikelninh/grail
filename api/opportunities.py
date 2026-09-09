from __future__ import annotations

import json
import sys
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from grail.mint_live import scan_watchlist  # noqa: E402
from grail.universe_scan import scan_universe_selection  # noqa: E402


_GENERIC_LOW_MINT_MARKERS = ("low edition #", "top ~1% low edition")
_STRONG_THESIS_MARKERS = (
    "first-appearance year",
    "matches release year",
    "earth-616",
    "order 66",
    "501st",
    "spider-man 2099 character identity",
    "first appeared",
    "debut",
)


def _reason_text(candidate: dict) -> str:
    return " | ".join(str(x).lower() for x in candidate.get("reasons", ()))


def _has_generic_low_mint(candidate: dict) -> bool:
    text=_reason_text(candidate)
    return any(marker in text for marker in _GENERIC_LOW_MINT_MARKERS)


def _has_strong_thesis(candidate: dict) -> bool:
    text=_reason_text(candidate)
    return any(marker in text for marker in _STRONG_THESIS_MARKERS)


def _has_thesis_mint(candidate: dict) -> bool:
    return _has_generic_low_mint(candidate) or _has_strong_thesis(candidate)


def _signal_class(candidate: dict) -> str:
    action = candidate["actionability"]
    mint = float(candidate["mint_score"])
    score = float(candidate["opportunity_score"])
    premium = float(candidate["premium_to_floor_pct"])
    if action == "reject-price": return "REJECT"
    if action == "pricing-unverified": return "UNVERIFIED"

    sane = action == "verify-now" and premium <= 20 and score >= 42
    broad = candidate.get("discovery_source") == "universe"

    # Curated assets retain the established behavior because their low-mint semantics were
    # explicitly chosen and reviewed. Broad discovery is intentionally stricter: a generic
    # low edition from an unknown asset is not enough to earn our rarest label.
    if not broad:
        if _has_thesis_mint(candidate) and mint >= 72 and sane:
            return "GRAIL"
    else:
        strong_semantic = _has_strong_thesis(candidate)
        provider_grail = bool(candidate.get("provider_grail"))
        provider_alpha = bool(candidate.get("provider_alpha"))
        provider_fa = candidate.get("catalog_is_fa") is True
        if strong_semantic and mint >= 78 and sane and score >= 48:
            return "GRAIL"
        if provider_grail and mint >= 84 and sane and score >= 52:
            return "GRAIL"
        if provider_grail and provider_alpha and provider_fa and mint >= 75 and sane and score >= 50:
            return "GRAIL"

    if action == "verify-now" and premium <= -15 and score >= 42:
        return "EDGE"
    if mint >= 35:
        return "WATCH"
    return "MARKET"


def _why(candidate: dict) -> str:
    signal = candidate["signal_class"]
    if signal == "GRAIL": return "Thesis-grade mint significance plus sane price positioning. Verify live inventory, owner and recent realised sales before acting."
    if signal == "EDGE": return "Price dislocation versus the latest daily StackR floor snapshot. Useful lead, not proof of a grail."
    if signal == "WATCH": return "The mint has a collector pattern, but not enough historical/IP significance or economic evidence to call it a grail."
    if signal == "REJECT": return "Interesting mint or listing, but the price fails GRAIL's margin-of-safety guardrail."
    if signal == "UNVERIFIED": return "Current OMI pricing could not be verified, so this candidate is not actionable."
    return "Normal market listing. Kept for context and baseline comparison."


def _universe_meta() -> tuple[dict[str,dict], dict]:
    path = ROOT / "data" / "universe_catalog.next.json"
    if not path.exists(): path = ROOT / "data" / "universe_catalog.json"
    if not path.exists(): return {}, {"assets":0,"comics":0,"collectibles":0}
    try:
        payload=json.loads(path.read_text(encoding="utf-8"))
        by_url={str(x.get("source_url")):x for x in payload.get("assets",[]) if x.get("source_url")}
        return by_url,payload.get("counts",{})
    except Exception:
        return {}, {"assets":0,"comics":0,"collectibles":0}


def _scan_all() -> tuple[list, list[dict]]:
    curated,errors=scan_watchlist(ROOT / "data" / "watchlist.json", max_workers=10)
    selection=ROOT / "data" / "universe_deep_scan.next.json"
    if not selection.exists(): selection=ROOT / "data" / "universe_deep_scan.json"
    broad=[]
    if selection.exists():
        found,broad_errors=scan_universe_selection(selection,max_workers=18)
        broad=found; errors.extend(broad_errors)
    dedup={}
    for c in [*broad,*curated]:
        key=(c.source_url,c.mint)
        prev=dedup.get(key)
        if prev is None or (c.mint_score,c.confidence) >= (prev.mint_score,prev.confidence): dedup[key]=c
    return list(dedup.values()),errors


def build_payload(limit: int = 120) -> dict:
    candidates, errors = _scan_all()
    universe_by_url,universe_counts=_universe_meta()
    rows=[]
    for c in candidates:
        row=asdict(c)
        meta=universe_by_url.get(row["source_url"],{})
        row["asset_kind"]=meta.get("kind") or ("comic" if row.get("category")=="Comics" else "collectible")
        row["catalog_mcap"]=meta.get("mcap")
        row["catalog_floor_usd"]=meta.get("floor_usd")
        row["catalog_supply"]=meta.get("supply")
        row["catalog_holders"]=meta.get("holders")
        row["catalog_sales30"]=meta.get("sales30")
        row["catalog_grade"]=meta.get("grade")
        row["catalog_is_fa"]=meta.get("is_fa")
        row["provider_grail"]=bool(meta.get("provider_grail"))
        row["provider_alpha"]=bool(meta.get("provider_alpha"))
        row["provider_alpha_why"]=meta.get("alpha_why") or []
        row["catalog_floor_vs_sales_pct"]=meta.get("floor_vs_sales_pct")
        row["discovery_source"]="universe" if meta else "curated"
        row["signal_class"]=_signal_class(row)
        row["why"]=_why(row)
        row["owner_status"]="unresolved"; row["owner"]=None
        rows.append(row)

    order={"GRAIL":5,"EDGE":4,"WATCH":3,"MARKET":2,"UNVERIFIED":1,"REJECT":0}
    rows.sort(key=lambda r:(order[r["signal_class"]],r["opportunity_score"],r["mint_score"]),reverse=True)
    rows=rows[:limit]
    spot=next((r.get("omi_usd") for r in rows if r.get("omi_usd")),None)
    return {
        "generated_at":rows[0]["observed_at"] if rows else None,
        "omi_usd":spot,
        "counts":{key:sum(1 for r in rows if r["signal_class"]==key) for key in order},
        "universe":universe_counts,
        "deep_scan":{"candidate_rows":len(candidates),"universe_rows":sum(r.get("discovery_source")=="universe" for r in rows)},
        "candidates":rows,
        "errors":errors,
        "disclaimer":"Collector intelligence, not financial advice. Always verify live listing, owner, fees and market depth before acting.",
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query=parse_qs(urlparse(self.path).query)
        try: limit=max(1,min(500,int(query.get("limit",[120])[0])))
        except ValueError: limit=120
        try:
            payload=build_payload(limit=limit); body=json.dumps(payload,separators=(",",":")).encode("utf-8"); self.send_response(200); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Cache-Control","s-maxage=300, stale-while-revalidate=1800")
        except Exception as exc:
            body=json.dumps({"error":f"{type(exc).__name__}: {exc}"}).encode("utf-8"); self.send_response(500); self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
