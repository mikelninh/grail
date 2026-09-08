from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from api.opportunities import build_payload  # noqa: E402


def _node(nodes: dict, node_id: str, kind: str, label: str, **attrs) -> None:
    nodes.setdefault(node_id, {"id": node_id, "kind": kind, "label": label, **attrs})


def build_graph(payload: dict) -> dict:
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    seen_edges: set[tuple[str, str, str]] = set()

    def edge(source: str, relation: str, target: str, evidence: str, observed_at: str | None = None) -> None:
        key = (source, relation, target)
        if key in seen_edges:
            return
        seen_edges.add(key)
        edges.append({"source": source, "relation": relation, "target": target, "evidence": evidence, "observed_at": observed_at})

    for row in payload.get("candidates", []):
        slug = row["source_url"].rstrip("/").split("/")[-1]
        collectible_id = f"collectible:{slug}"
        mint_id = f"mint:{slug}:{row['mint']}"
        market_id = "marketplace:stackr"
        category = row.get("category") or "Unknown"
        category_id = f"universe:{category.lower().replace(' ', '-').replace('×', 'x')}"
        _node(nodes, category_id, "universe", category)
        _node(nodes, collectible_id, "collectible", row["collectible"], image_url=row.get("image_url"), veve_url=row.get("veve_url"), stackr_url=row.get("stackr_url"))
        _node(nodes, mint_id, "mint", f"#{row['mint']}", mint=row["mint"], mint_score=row.get("mint_score", 0), signal_class=row.get("signal_class"))
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
        owner = row.get("owner")
        if owner:
            owner_id = f"owner:{owner.lower()}"
            _node(nodes, owner_id, "owner", owner)
            edge(mint_id, "owned_by", owner_id, row.get("stackr_url") or row["source_url"], row.get("observed_at"))
    return {"generated_at": payload.get("generated_at"), "nodes": list(nodes.values()), "edges": edges, "stats": {"nodes": len(nodes), "edges": len(edges)}, "note": "Public evidence graph. Private user/friend ownership is merged locally in each browser and is never published by default."}


def main() -> int:
    site = ROOT / "site"
    if site.exists():
        shutil.rmtree(site)
    (site / "data").mkdir(parents=True)
    payload = build_payload(limit=250)
    graph = build_graph(payload)
    (site / "data" / "opportunities.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (site / "data" / "graph.json").write_text(json.dumps(graph, indent=2), encoding="utf-8")
    for name in ("index.html", "styles.css", "app.js"):
        shutil.copy2(ROOT / "dashboard" / name, site / name)
    with (site / "styles.css").open("a", encoding="utf-8") as out:
        out.write("\n")
        out.write((ROOT / "dashboard" / "pages-polish.css").read_text(encoding="utf-8"))
    (site / ".nojekyll").write_text("", encoding="utf-8")
    print(json.dumps({"candidates": len(payload.get("candidates", [])), "counts": payload.get("counts", {}), "graph": graph["stats"], "errors": payload.get("errors", [])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
