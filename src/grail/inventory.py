from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable


def key_of(row: dict[str, Any]) -> str:
    return f"{row.get('source_url')}|{int(row.get('mint', 0))}"


def update_inventory_state(previous: dict[str, Any] | None, payload: dict[str, Any], sales: Iterable[Any], *, now: str | None = None, stale_after_misses: int = 2) -> dict[str, Any]:
    """Track listing presence conservatively across hourly observations.

    `live` means present in the provider's current listing section in this scan.
    A missing row becomes `not-seen` first; only repeated misses become `stale`.
    `sold` requires an observed realised sale for the exact collectible + edition.
    """
    now = now or datetime.now(timezone.utc).isoformat()
    state = dict(previous or {})
    items = {x["key"]: dict(x) for x in state.get("items", []) if x.get("key")}

    sale_rows = []
    for sale in sales:
        sale_rows.append(dict(sale) if isinstance(sale, dict) else dict(vars(sale)))
    sold_keys = {(s.get("source_url"), int(s.get("mint", -1))): s for s in sale_rows if s.get("sold_date")}

    seen = set()
    for row in payload.get("candidates", []):
        key = key_of(row)
        seen.add(key)
        item = items.get(key) or {
            "key": key,
            "source_url": row.get("source_url"),
            "collectible": row.get("collectible"),
            "mint": int(row.get("mint", 0)),
            "first_seen": now,
            "misses": 0,
            "status": "live",
        }
        item.update({
            "last_seen": now,
            "status": "live",
            "misses": 0,
            "ask_usd": row.get("ask_usd"),
            "ask_omi": row.get("ask_omi"),
            "floor_usd": row.get("floor_usd"),
            "signal_class": row.get("signal_class"),
            "stackr_url": row.get("stackr_url"),
            "veve_url": row.get("veve_url"),
        })
        sale = sold_keys.get((row.get("source_url"), int(row.get("mint", 0))))
        if row.get("availability_status") == "sold-after-listing" and sale:
            item["status"] = "sold"
            item["sold_at"] = sale.get("sold_date")
            item["sale"] = sale
        items[key] = item

    for key, item in items.items():
        if key in seen or item.get("status") == "sold":
            continue
        sale = sold_keys.get((item.get("source_url"), int(item.get("mint", -1))))
        if sale:
            item["status"] = "sold"
            item["sold_at"] = sale.get("sold_date")
            item["sale"] = sale
            continue
        misses = int(item.get("misses", 0)) + 1
        item["misses"] = misses
        item["status"] = "stale" if misses >= stale_after_misses else "not-seen"
        item.setdefault("disappeared_at", now)

    ordered = sorted(items.values(), key=lambda x: (x.get("status") != "live", x.get("collectible") or "", x.get("mint") or 0))
    counts = {status: sum(1 for x in ordered if x.get("status") == status) for status in ("live", "not-seen", "stale", "sold")}
    return {"version": 1, "updated_at": now, "items": ordered, "counts": counts}


def annotate_payload(payload: dict[str, Any], inventory: dict[str, Any]) -> None:
    idx = {x["key"]: x for x in inventory.get("items", []) if x.get("key")}
    for row in payload.get("candidates", []):
        item = idx.get(key_of(row))
        if not item:
            row["live_status"] = "untracked"
            continue
        row["live_status"] = item.get("status")
        row["first_seen"] = item.get("first_seen")
        row["last_seen"] = item.get("last_seen")
        row["disappeared_at"] = item.get("disappeared_at")
        if item.get("status") == "sold" and row.get("signal_class") in {"GRAIL", "EDGE", "WATCH"}:
            row["signal_class"] = "HISTORY"
            row["why"] = "Observed realised sale closes this listing signal; retained as history, never actionable."
