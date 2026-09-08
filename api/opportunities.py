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


_THESIS_MINT_MARKERS = (
    "low edition #",
    "top ~1% low edition",
    "first-appearance year",
    "matches release year",
    "Earth-616",
    "Order 66",
    "501st",
    "Spider-Man 2099 character identity",
    "first appeared",
    "debut",
)


def _has_thesis_mint(candidate: dict) -> bool:
    """True only for mint reasons strong enough to support a GRAIL thesis.

    Generic palindromes/sequences are intentionally excluded. Pretty number != grail.
    """
    reasons = " | ".join(str(x) for x in candidate.get("reasons", ()))
    return any(marker.lower() in reasons.lower() for marker in _THESIS_MINT_MARKERS)


def _signal_class(candidate: dict) -> str:
    action = candidate["actionability"]
    mint = float(candidate["mint_score"])
    score = float(candidate["opportunity_score"])
    premium = float(candidate["premium_to_floor_pct"])

    if action == "reject-price":
        return "REJECT"
    if action == "pricing-unverified":
        return "UNVERIFIED"
    # GRAIL is deliberately rare: thesis-grade mint significance + sane economics.
    if _has_thesis_mint(candidate) and mint >= 72 and action == "verify-now" and premium <= 20 and score >= 42:
        return "GRAIL"
    if action == "verify-now" and premium <= -15 and score >= 42:
        return "EDGE"
    if mint >= 35:
        return "WATCH"
    return "MARKET"


def _why(candidate: dict) -> str:
    signal = candidate["signal_class"]
    if signal == "GRAIL":
        return "Thesis-grade mint significance plus sane price positioning. Verify live inventory, owner and recent realised sales before acting."
    if signal == "EDGE":
        return "Price dislocation versus the latest daily StackR floor snapshot. Useful lead, not proof of a grail."
    if signal == "WATCH":
        return "The mint has a collector pattern, but not enough historical/IP significance or economic evidence to call it a grail."
    if signal == "REJECT":
        return "Interesting mint or listing, but the price fails GRAIL's margin-of-safety guardrail."
    if signal == "UNVERIFIED":
        return "Current OMI pricing could not be verified, so this candidate is not actionable."
    return "Normal market listing. Kept for context and baseline comparison."


def build_payload(limit: int = 120) -> dict:
    candidates, errors = scan_watchlist(ROOT / "data" / "watchlist.json", max_workers=10)
    rows = []
    for c in candidates[:limit]:
        row = asdict(c)
        row["signal_class"] = _signal_class(row)
        row["why"] = _why(row)
        row["owner_status"] = "unresolved"
        row["owner"] = None
        rows.append(row)

    order = {"GRAIL": 5, "EDGE": 4, "WATCH": 3, "MARKET": 2, "UNVERIFIED": 1, "REJECT": 0}
    rows.sort(key=lambda r: (order[r["signal_class"]], r["opportunity_score"], r["mint_score"]), reverse=True)
    spot = next((r.get("omi_usd") for r in rows if r.get("omi_usd")), None)
    return {
        "generated_at": rows[0]["observed_at"] if rows else None,
        "omi_usd": spot,
        "counts": {key: sum(1 for r in rows if r["signal_class"] == key) for key in order},
        "candidates": rows,
        "errors": errors,
        "disclaimer": "Collector intelligence, not financial advice. Always verify live listing, owner, fees and market depth before acting.",
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        try:
            limit = max(1, min(250, int(query.get("limit", [120])[0])))
        except ValueError:
            limit = 120
        try:
            payload = build_payload(limit=limit)
            body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "s-maxage=300, stale-while-revalidate=1800")
        except Exception as exc:
            body = json.dumps({"error": f"{type(exc).__name__}: {exc}"}).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
