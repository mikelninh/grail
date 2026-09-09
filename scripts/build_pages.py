from __future__ import annotations

import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from api.opportunities import build_payload  # noqa: E402
from grail.inventory import annotate_payload, update_inventory_state  # noqa: E402
from grail.premium_model import build_premium_model  # noqa: E402
from grail.sales import scan_sales_watchlist  # noqa: E402


def _node(nodes: dict, node_id: str, kind: str, label: str, **attrs) -> None:
    nodes.setdefault(node_id, {"id": node_id, "kind": kind, "label": label, **attrs})


def _watch_meta() -> tuple[dict[str, dict], dict[str, dict]]:
    raw = json.loads((ROOT / "data" / "watchlist.json").read_text(encoding="utf-8"))
    return ({str(x["url"]): x for x in raw["collectibles"]}, {str(x["id"]): x for x in raw["collectibles"]})


def _sale_aware(payload: dict, sales: list) -> None:
    sale_index: dict[tuple[str, int], list] = defaultdict(list)
    for sale in sales:
        sale_index[(sale.source_url, sale.mint)].append(sale)

    for row in payload.get("candidates", []):
        matches = sale_index.get((row["source_url"], int(row["mint"])), [])
        listing_date = row.get("listed_date")
        later = [s for s in matches if s.sold_date and listing_date and s.sold_date >= listing_date]
        if not later:
            row["availability_status"] = "provider-current-unverified"
            continue
        latest = max(later, key=lambda s: s.sold_date or "")
        row["availability_status"] = "sold-after-listing"
        row["last_sale"] = {
            "date": latest.sold_date, "marketplace": latest.marketplace,
            "price_usd": latest.price_usd, "price_omi": latest.price_omi,
            "seller": latest.seller, "buyer": latest.buyer,
        }
        if row.get("signal_class") in {"GRAIL", "EDGE", "WATCH"}:
            row["signal_class"] = "HISTORY"
            row["why"] = "A realised sale on/after the recorded listing date closes this opportunity. Kept as historical evidence."

    _resort(payload)


def _resort(payload: dict) -> None:
    order = {"GRAIL": 7, "EDGE": 6, "WATCH": 5, "MARKET": 4, "HISTORY": 3, "UNVERIFIED": 2, "REJECT": 1}
    payload["candidates"].sort(key=lambda r: (order.get(r.get("signal_class"), 0), r.get("opportunity_score", 0), r.get("mint_score", 0)), reverse=True)
    payload["counts"] = {key: sum(1 for r in payload["candidates"] if r.get("signal_class") == key) for key in order}


def build_graph(payload: dict, sales: list, premium_stats: dict, inventory: dict) -> dict:
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    seen_edges: set[tuple[str, str, str]] = set()

    def edge(source: str, relation: str, target: str, evidence: str, observed_at: str | None = None) -> None:
        key = (source, relation, target)
        if key in seen_edges:
            return
        seen_edges.add(key)
        edges.append({"source": source, "relation": relation, "target": target, "evidence": evidence, "observed_at": observed_at})

    source_to_slug: dict[str, str] = {}
    for row in payload.get("candidates", []):
        slug = row["source_url"].rstrip("/").split("/")[-1]
        source_to_slug[row["source_url"]] = slug
        collectible_id = f"collectible:{slug}"
        mint_id = f"mint:{slug}:{row['mint']}"
        market_id = "marketplace:stackr"
        category = row.get("category") or "Unknown"
        category_id = f"universe:{category.lower().replace(' ', '-').replace('×', 'x')}"
        _node(nodes, category_id, "universe", category)
        _node(nodes, collectible_id, "collectible", row["collectible"], image_url=row.get("image_url"), veve_url=row.get("veve_url"), stackr_url=row.get("stackr_url"))
        _node(nodes, mint_id, "mint", f"#{row['mint']}", mint=row["mint"], mint_score=row.get("mint_score", 0), signal_class=row.get("signal_class"), live_status=row.get("live_status"), availability_status=row.get("availability_status"))
        _node(nodes, market_id, "marketplace", "StackR")
        edge(collectible_id, "belongs_to", category_id, row["source_url"], row.get("observed_at"))
        edge(collectible_id, "has_mint", mint_id, row["source_url"], row.get("observed_at"))
        edge(mint_id, "listed_on", market_id, row.get("stackr_url") or row["source_url"], row.get("observed_at"))
        price_id = f"price:{slug}:{row['mint']}:{row.get('ask_omi') or 0}"
        _node(nodes, price_id, "price_observation", f"${row.get('ask_usd', 0):.2f}", ask_usd=row.get("ask_usd"), ask_omi=row.get("ask_omi"), floor_usd=row.get("floor_usd"), premium_to_floor_pct=row.get("premium_to_floor_pct"))
        edge(mint_id, "priced_at", price_id, row["source_url"], row.get("observed_at"))
        for reason in row.get("reasons", []):
            low = reason.lower()
            if any(token in low for token in ("low edition", "top ~1%", "first-appearance", "release year", "earth-616", "order 66", "501st", "identity", "palindromic", "sequential", "repeating", "lucky-8")):
                signal_id = "signal:" + "-".join(c for c in low if c.isalnum() or c in " -_").replace(" ", "-")[:90]
                _node(nodes, signal_id, "semantic_signal", reason)
                edge(mint_id, "matches_signal", signal_id, row["source_url"], row.get("observed_at"))

    for i, sale in enumerate(sales):
        slug = source_to_slug.get(sale.source_url, sale.source_url.rstrip("/").split("/")[-1])
        collectible_id = f"collectible:{slug}"
        mint_id = f"mint:{slug}:{sale.mint}"
        sale_id = f"sale:{slug}:{sale.mint}:{sale.sold_date or i}:{sale.marketplace.lower()}"
        _node(nodes, collectible_id, "collectible", sale.collectible)
        _node(nodes, mint_id, "mint", f"#{sale.mint}", mint=sale.mint)
        _node(nodes, sale_id, "sale", f"{sale.marketplace} sale #{sale.mint}", price_usd=sale.price_usd, price_omi=sale.price_omi, sold_date=sale.sold_date)
        edge(collectible_id, "has_mint", mint_id, sale.source_url, sale.observed_at)
        edge(mint_id, "sold_in", sale_id, sale.source_url, sale.observed_at)
        if sale.seller:
            seller_id = f"collector:{sale.seller.lower()}"
            _node(nodes, seller_id, "collector", sale.seller)
            edge(sale_id, "sold_by", seller_id, sale.source_url, sale.observed_at)
        if sale.buyer:
            buyer_id = f"collector:{sale.buyer.lower()}"
            _node(nodes, buyer_id, "collector", sale.buyer)
            edge(sale_id, "bought_by", buyer_id, sale.source_url, sale.observed_at)
            edge(mint_id, "last_observed_buyer", buyer_id, sale.source_url, sale.observed_at)

    for signal_kind, stat in premium_stats.items():
        node_id = f"premium:{signal_kind}"
        attrs = {k: v for k, v in stat.items() if k != "kind"}
        _node(nodes, node_id, "realised_premium_evidence", signal_kind, **attrs)

    return {
        "generated_at": payload.get("generated_at"), "nodes": list(nodes.values()), "edges": edges,
        "stats": {"nodes": len(nodes), "edges": len(edges), "sales": len(sales), "premium_signal_types": len(premium_stats), "inventory": inventory.get("counts", {})},
        "premium_stats": premium_stats,
        "note": "Evidence graph. Historical buyers are not current owners. Provider-chain and exact-token owner evidence are tracked separately; exact-token conflicts are surfaced. Private friend/user overlays remain browser-local.",
    }


def main() -> int:
    site = ROOT / "site"
    if site.exists(): shutil.rmtree(site)
    (site / "data").mkdir(parents=True)

    payload = build_payload(limit=250)
    sales, sale_errors = scan_sales_watchlist(ROOT / "data" / "watchlist.json", max_workers=10)
    _sale_aware(payload, sales)

    previous_inventory = None
    inventory_path = ROOT / "data" / "inventory_state.json"
    if inventory_path.exists():
        previous_inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    inventory = update_inventory_state(previous_inventory, payload, sales)
    annotate_payload(payload, inventory)
    _resort(payload)
    (ROOT / "data" / "inventory_state.next.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")

    _, watch_by_id = _watch_meta()
    premiums = build_premium_model(sales, watch_by_id, min_samples=10)
    graph = build_graph(payload, sales, premiums, inventory)

    (site / "data" / "opportunities.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (site / "data" / "sales.json").write_text(json.dumps({"sales": [s.__dict__ for s in sales], "errors": sale_errors, "premium_stats": premiums}, indent=2), encoding="utf-8")
    (site / "data" / "inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    (site / "data" / "graph.json").write_text(json.dumps(graph, indent=2), encoding="utf-8")

    for name in ("index.html", "styles.css", "app.js", "ownership-proof.js"):
        shutil.copy2(ROOT / "dashboard" / name, site / name)
    with (site / "styles.css").open("a", encoding="utf-8") as out:
        out.write("\n")
        out.write((ROOT / "dashboard" / "pages-polish.css").read_text(encoding="utf-8"))
    (site / ".nojekyll").write_text("", encoding="utf-8")

    errors = list(payload.get("errors", [])) + sale_errors
    print(json.dumps({"candidates": len(payload.get("candidates", [])), "counts": payload.get("counts", {}), "sales": len(sales), "premium_signal_types": len(premiums), "inventory": inventory.get("counts", {}), "graph": graph["stats"], "errors": errors}, indent=2))
    return 0


if __name__ == "__main__": raise SystemExit(main())
