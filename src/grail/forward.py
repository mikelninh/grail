from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timezone
from typing import Any, Iterable


TRACKED_SIGNALS = {"GRAIL", "EDGE"}
CHECKPOINT_HOURS = (1, 24, 168, 720)


def _iso_day(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None


def _iso_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _key(row: dict[str, Any]) -> str:
    return f"{row.get('source_url')}|{int(row.get('mint', 0))}"


def _sale_dict(sale: Any) -> dict[str, Any]:
    if isinstance(sale, dict):
        return dict(sale)
    try:
        return asdict(sale)
    except TypeError:
        return dict(vars(sale))


def _eligible_sale(alert: dict[str, Any], sale: dict[str, Any]) -> bool:
    if sale.get("source_url") != alert.get("source_url"):
        return False
    if int(sale.get("mint", -1)) != int(alert.get("mint", -2)):
        return False
    sold = _iso_day(sale.get("sold_date"))
    first_seen = _iso_day(alert.get("first_seen"))
    listing = _iso_day(alert.get("listed_date"))
    threshold = listing or first_seen
    if sold is None or threshold is None:
        return False
    return sold >= threshold


def _return_proxy(alert: dict[str, Any], sale: dict[str, Any]) -> float | None:
    ask_omi, sale_omi = alert.get("ask_omi"), sale.get("price_omi")
    if ask_omi and sale_omi and float(ask_omi) > 0:
        return round((float(sale_omi) / float(ask_omi) - 1.0) * 100.0, 2)
    ask_usd, sale_usd = alert.get("ask_usd"), sale.get("price_usd")
    if ask_usd and sale_usd and float(ask_usd) > 0:
        return round((float(sale_usd) / float(ask_usd) - 1.0) * 100.0, 2)
    return None


def _baseline_rows(payload: dict[str, Any], source_url: str, exclude_key: str) -> dict[str, dict[str, Any]]:
    rows = [
        r for r in payload.get("candidates", [])
        if r.get("source_url") == source_url
        and _key(r) != exclude_key
        and r.get("signal_class") not in {"HISTORY", "REJECT", "UNVERIFIED"}
        and r.get("live_status") in {None, "live"}
        and r.get("ask_usd") is not None
    ]
    if not rows:
        return {}
    cheapest = min(rows, key=lambda r: (float(r.get("ask_usd") or 1e18), int(r.get("mint") or 0)))
    deepest = min(rows, key=lambda r: (float(r.get("premium_to_floor_pct") or 0), float(r.get("ask_usd") or 1e18)))
    control = sorted(rows, key=lambda r: int(r.get("mint") or 0))[len(rows) // 2]

    def snap(r: dict[str, Any]) -> dict[str, Any]:
        return {"mint": int(r.get("mint", 0)), "ask_usd": r.get("ask_usd"), "ask_omi": r.get("ask_omi"), "premium_to_floor_pct": r.get("premium_to_floor_pct"), "signal_class": r.get("signal_class")}
    return {"cheapest": snap(cheapest), "deepest_discount": snap(deepest), "control": snap(control)}


def _capture_checkpoints(alert: dict[str, Any], current: dict[str, Any] | None, now: str) -> None:
    first = _iso_dt(alert.get("first_seen"))
    current_dt = _iso_dt(now)
    if not first or not current_dt:
        return
    elapsed = (current_dt - first).total_seconds() / 3600.0
    checkpoints = alert.setdefault("checkpoints", {})
    for hours in CHECKPOINT_HOURS:
        key = f"{hours}h"
        if key in checkpoints or elapsed < hours:
            continue
        checkpoints[key] = {
            "observed_at": now,
            "hours_target": hours,
            "live_status": current.get("live_status") if current else "not-observed",
            "ask_usd": current.get("ask_usd") if current else None,
            "ask_omi": current.get("ask_omi") if current else None,
            "floor_usd": current.get("floor_usd") if current else None,
            "premium_to_floor_pct": current.get("premium_to_floor_pct") if current else None,
        }


def update_forward_state(previous: dict[str, Any] | None, payload: dict[str, Any], sales: Iterable[Any], *, now: str | None = None) -> dict[str, Any]:
    """Update the evidence ledger without inventing execution or sales.

    New cohorts require a row observed live. Outcomes resolve only from an exact-mint realised
    sale. Time checkpoints record later market observations but are not treated as realised P&L.
    """
    now = now or datetime.now(timezone.utc).isoformat()
    state = dict(previous or {})
    alerts = {a["key"]: dict(a) for a in state.get("alerts", []) if a.get("key")}
    sale_rows = [_sale_dict(s) for s in sales]
    current_index = {_key(r): r for r in payload.get("candidates", [])}

    for row in payload.get("candidates", []):
        if row.get("signal_class") not in TRACKED_SIGNALS:
            continue
        if row.get("availability_status") == "sold-after-listing" or row.get("live_status") not in {None, "live"}:
            continue
        key = _key(row)
        alert = alerts.get(key)
        if alert is None:
            alert = {
                "key": key, "source_url": row.get("source_url"), "collectible": row.get("collectible"), "mint": int(row.get("mint", 0)),
                "signal_class": row.get("signal_class"), "first_seen": now, "listed_date": row.get("listed_date"),
                "ask_usd": row.get("ask_usd"), "ask_omi": row.get("ask_omi"), "floor_usd": row.get("floor_usd"),
                "premium_to_floor_pct": row.get("premium_to_floor_pct"), "mint_score": row.get("mint_score"),
                "opportunity_score": row.get("opportunity_score"), "confidence": row.get("confidence"),
                "stackr_url": row.get("stackr_url"), "veve_url": row.get("veve_url"),
                "baselines": _baseline_rows(payload, str(row.get("source_url")), key), "status": "open", "resolved_sale": None, "checkpoints": {},
            }
        alert["last_seen"] = now
        alert["latest_ask_usd"] = row.get("ask_usd")
        alert["latest_floor_usd"] = row.get("floor_usd")
        alerts[key] = alert

    for alert in alerts.values():
        current = current_index.get(alert["key"])
        _capture_checkpoints(alert, current, now)
        if alert.get("status") != "sold":
            matches = [s for s in sale_rows if _eligible_sale(alert, s)]
            if matches:
                latest = max(matches, key=lambda s: s.get("sold_date") or "")
                alert["status"] = "sold"
                alert["resolved_sale"] = latest
                alert["return_proxy_pct"] = _return_proxy(alert, latest)
                first = _iso_day(alert.get("first_seen")); sold = _iso_day(latest.get("sold_date"))
                alert["days_to_observed_sale"] = (sold - first).days if first and sold else None

        baseline_outcomes = alert.setdefault("baseline_outcomes", {})
        for name, baseline in alert.get("baselines", {}).items():
            if name in baseline_outcomes:
                continue
            pseudo = {"source_url": alert.get("source_url"), "mint": baseline.get("mint"), "first_seen": alert.get("first_seen"), "listed_date": alert.get("listed_date"), "ask_omi": baseline.get("ask_omi"), "ask_usd": baseline.get("ask_usd")}
            matches = [s for s in sale_rows if _eligible_sale(pseudo, s)]
            if matches:
                latest = max(matches, key=lambda s: s.get("sold_date") or "")
                baseline_outcomes[name] = {"status": "sold", "sale": latest, "return_proxy_pct": _return_proxy(pseudo, latest)}

    ordered = sorted(alerts.values(), key=lambda a: (a.get("first_seen") or "", a.get("key") or ""))
    summary = summarize_forward_state({"alerts": ordered})
    return {"version": 2, "updated_at": now, "alerts": ordered, "summary": summary}


def summarize_forward_state(state: dict[str, Any]) -> dict[str, Any]:
    alerts = list(state.get("alerts", [])); tracked = len(alerts)
    sold = [a for a in alerts if a.get("status") == "sold"]
    grails = [a for a in alerts if a.get("signal_class") == "GRAIL"]; edges = [a for a in alerts if a.get("signal_class") == "EDGE"]

    def hit_rate(rows: list[dict[str, Any]]) -> float | None:
        return None if not rows else round(sum(1 for r in rows if r.get("status") == "sold") / len(rows) * 100.0, 2)

    returns = [float(a["return_proxy_pct"]) for a in sold if a.get("return_proxy_pct") is not None]
    days = [int(a["days_to_observed_sale"]) for a in sold if a.get("days_to_observed_sale") is not None]
    baseline_rates: dict[str, float | None] = {}
    for name in ("cheapest", "deepest_discount", "control"):
        eligible = [a for a in alerts if name in a.get("baselines", {})]
        if not eligible: baseline_rates[name] = None
        else:
            wins = sum(1 for a in eligible if a.get("baseline_outcomes", {}).get(name, {}).get("status") == "sold")
            baseline_rates[name] = round(wins / len(eligible) * 100.0, 2)
    checkpoint_counts = {f"{h}h": sum(1 for a in alerts if f"{h}h" in a.get("checkpoints", {})) for h in CHECKPOINT_HOURS}
    return {
        "tracked_alerts": tracked, "resolved_sales": len(sold), "overall_sell_through_pct": hit_rate(alerts),
        "grail_sell_through_pct": hit_rate(grails), "edge_sell_through_pct": hit_rate(edges),
        "median_return_proxy_pct": round(sorted(returns)[len(returns)//2],2) if returns else None,
        "median_days_to_observed_sale": sorted(days)[len(days)//2] if days else None,
        "baseline_sell_through_pct": baseline_rates, "checkpoint_counts": checkpoint_counts,
        "status": "collecting" if tracked < 20 or len(sold) < 5 else "directional" if tracked < 100 or len(sold) < 25 else "evidence-building",
    }
