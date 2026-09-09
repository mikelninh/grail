from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from grail.provider_edition import lookup_edition  # noqa: E402


def main() -> int:
    targets = json.loads((ROOT / "data" / "provider_owner_targets.json").read_text(encoding="utf-8")).get("targets", [])
    opp_path = ROOT / "site" / "data" / "opportunities.json"
    graph_path = ROOT / "site" / "data" / "graph.json"
    payload = json.loads(opp_path.read_text(encoding="utf-8"))
    graph = json.loads(graph_path.read_text(encoding="utf-8"))

    rows = {(r.get("source_url"), int(r.get("mint", 0))): r for r in payload.get("candidates", [])}
    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    edges = list(graph.get("edges", []))
    seen = {(e.get("source"), e.get("relation"), e.get("target")) for e in edges}
    results, errors = [], []

    def add_node(node_id: str, kind: str, label: str, **attrs) -> None:
        nodes.setdefault(node_id, {"id": node_id, "kind": kind, "label": label, **attrs})

    def add_edge(source_id: str, relation: str, target_id: str, evidence: str, **attrs) -> None:
        key = (source_id, relation, target_id)
        if key in seen:
            return
        seen.add(key)
        edges.append({"source": source_id, "relation": relation, "target": target_id, "evidence": evidence, **attrs})

    for target in targets:
        source_url = str(target["source_url"])
        mint = int(target["mint"])
        try:
            result = lookup_edition(source_url, mint, timeout=20)
            public = asdict(result)
            public.pop("raw", None)
            public["source_url"] = source_url
            public["label"] = target.get("label")
            public["verification_level"] = "provider-chain" if result.owner else "provider-seen"
            results.append(public)

            row = rows.get((source_url, mint))
            if row is not None:
                row["provider_chain_seen"] = bool(result.raw.get("onchain_found") or result.owner)
                row["provider_chain_coverage_pct"] = result.raw.get("onchain_coverage_pct")
                row["provider_owner_evidence_url"] = result.evidence_url
                if result.owner:
                    row["owner"] = result.owner
                    row["owner_status"] = "verified-chain"
                    row["owner_evidence_level"] = "provider-chain"
                    row["owner_source"] = "vevealpha-find_edition_v2"
                if result.token_id:
                    row["collect_token_id"] = result.token_id
                    row["owner_evidence_level"] = "provider-token"

            slug = source_url.rstrip("/").split("/")[-1]
            mint_id = f"mint:{slug}:{mint}"
            add_node(mint_id, "mint", f"#{mint}", mint=mint)
            provider_fact_id = f"provider-edition:{slug}:{mint}"
            add_node(provider_fact_id, "provider_chain_fact", f"{target.get('label') or mint} provider chain lookup",
                     collectible_id=result.collectible_id, edition=mint, owner=result.owner,
                     token_id=result.token_id, coverage_pct=result.raw.get("onchain_coverage_pct"))
            add_edge(mint_id, "verified_by_provider_chain", provider_fact_id, result.evidence_url,
                     verification_level=public["verification_level"])
            if result.owner:
                wallet_id = f"wallet:{result.owner.lower()}"
                add_node(wallet_id, "wallet", result.owner)
                add_edge(mint_id, "owned_by", wallet_id, result.evidence_url,
                         verification_level="provider-chain", provider_source="find_edition_v2")
        except Exception as exc:
            errors.append({"source_url": source_url, "mint": mint, "label": target.get("label"), "error": f"{type(exc).__name__}: {exc}"})

    graph["nodes"] = list(nodes.values())
    graph["edges"] = edges
    graph.setdefault("stats", {})["provider_chain_owners"] = sum(1 for r in results if r.get("owner"))
    graph["provider_ownership_errors"] = errors
    opp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    graph_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    out = {"version": 1, "resolutions": results, "errors": errors,
           "rules": ["Provider-chain ownership is edition-level evidence from public find_edition_v2.",
                     "Exact token verification remains a stricter level and is never inferred."]}
    (ROOT / "site" / "data" / "provider_ownership.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({"resolved": len(results), "owners": sum(1 for r in results if r.get("owner")), "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
