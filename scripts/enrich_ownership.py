from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from grail.ownership import public_resolution, resolve_registry  # noqa: E402


def _address(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("hash") or value.get("address")
    return value if isinstance(value, str) else None


def main() -> int:
    graph_path = ROOT / "site" / "data" / "graph.json"
    opportunities_path = ROOT / "site" / "data" / "opportunities.json"
    registry = ROOT / "data" / "token_mappings.json"

    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    payload = json.loads(opportunities_path.read_text(encoding="utf-8"))
    resolutions, errors = resolve_registry(registry)

    nodes = {n["id"]: n for n in graph.get("nodes", [])}
    edges = list(graph.get("edges", []))
    seen = {(e.get("source"), e.get("relation"), e.get("target")) for e in edges}
    conflicts: list[dict[str, Any]] = []

    def node(node_id: str, kind: str, label: str, **attrs) -> None:
        nodes.setdefault(node_id, {"id": node_id, "kind": kind, "label": label, **attrs})

    def edge(source: str, relation: str, target: str, evidence: str, observed_at: str | None = None) -> None:
        key = (source, relation, target)
        if key in seen:
            return
        seen.add(key)
        edges.append({"source": source, "relation": relation, "target": target, "evidence": evidence, "observed_at": observed_at})

    index = {(r.get("source_url"), int(r.get("mint", 0))): r for r in payload.get("candidates", [])}
    for resolution in resolutions:
        row = index.get((resolution.source_url, resolution.mint))
        slug = resolution.source_url.rstrip("/").split("/")[-1]
        mint_id = f"mint:{slug}:{resolution.mint}"
        token_id = f"collect-token:{resolution.contract.lower()}:{resolution.token_id}"
        collectscan_url = f"https://collectscan.com/token/{resolution.contract}/instance/{resolution.token_id}"
        node(token_id, "collect_token", f"Collect #{resolution.token_id}", contract=resolution.contract, token_id=resolution.token_id, collectscan_url=collectscan_url, token_name=resolution.token_name)
        node(mint_id, "mint", f"#{resolution.mint}", mint=resolution.mint)
        edge(mint_id, "mapped_to_token", token_id, resolution.evidence_url)

        if row is not None:
            provider_owner = row.get("owner") if row.get("owner_evidence_level") == "provider-chain" else row.get("provider_owner")
            if provider_owner:
                row["provider_owner"] = provider_owner
                row["provider_owner_evidence_url"] = row.get("provider_owner_evidence_url") or row.get("source_url")
            if provider_owner and resolution.owner and str(provider_owner).lower() != str(resolution.owner).lower():
                conflict = {
                    "source_url": resolution.source_url,
                    "mint": resolution.mint,
                    "provider_owner": provider_owner,
                    "exact_token_owner": resolution.owner,
                    "preferred_source": "collectscan-exact-token",
                    "reason": "provider edition owner differs from independently resolved exact Collect token owner",
                }
                conflicts.append(conflict)
                row["owner_source_conflict"] = True
                row["owner_conflict"] = conflict
            else:
                row["owner_source_conflict"] = False

            row["chain_mapping_status"] = "verified" if resolution.verified else "mapped-unresolved-owner"
            row["collect_contract"] = resolution.contract
            row["collect_token_id"] = resolution.token_id
            row["collectscan_url"] = collectscan_url
            row["owner_status"] = "verified-chain" if resolution.verified else "unresolved"
            row["owner"] = resolution.owner if resolution.verified else None
            if resolution.verified:
                row["owner_evidence_level"] = "exact-token"
                row["owner_source"] = "collectscan-exact-token"

        if resolution.owner:
            owner_id = f"wallet:{resolution.owner.lower()}"
            node(owner_id, "wallet", resolution.owner)
            edge(token_id, "owned_by", owner_id, collectscan_url)

        for idx, transfer in enumerate(resolution.transfers):
            tx_hash = transfer.get("transaction_hash") or transfer.get("tx_hash") or transfer.get("hash")
            transfer_id = f"transfer:{resolution.contract.lower()}:{resolution.token_id}:{tx_hash or idx}"
            node(transfer_id, "transfer", str(tx_hash or f"transfer {idx+1}"), block_number=transfer.get("block_number"), timestamp=transfer.get("timestamp"))
            edge(token_id, "transferred_in", transfer_id, collectscan_url)
            sender = _address(transfer.get("from"))
            receiver = _address(transfer.get("to"))
            if sender:
                sid = f"wallet:{sender.lower()}"
                node(sid, "wallet", sender)
                edge(transfer_id, "transferred_from", sid, collectscan_url)
            if receiver:
                rid = f"wallet:{receiver.lower()}"
                node(rid, "wallet", receiver)
                edge(transfer_id, "transferred_to", rid, collectscan_url)

    graph["nodes"] = list(nodes.values())
    graph["edges"] = edges
    graph.setdefault("stats", {})["verified_chain_owners"] = sum(1 for r in resolutions if r.verified)
    graph["stats"]["token_mappings"] = len(resolutions)
    graph["stats"]["owner_source_conflicts"] = len(conflicts)
    graph["ownership_errors"] = errors
    graph["owner_source_conflicts"] = conflicts

    graph_path.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    opportunities_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    (ROOT / "site" / "data" / "ownership.json").write_text(json.dumps({
        "resolutions": [public_resolution(r) for r in resolutions],
        "conflicts": conflicts,
        "errors": errors,
        "rules": [
            "No VeVe edition-to-token inference.",
            "Only evidence-registered exact mappings can produce exact-token current-owner edges.",
            "When provider-chain and exact-token owners disagree, exact-token evidence is preferred and the conflict is surfaced.",
        ],
    }, indent=2), encoding="utf-8")

    print(json.dumps({"mappings": len(resolutions), "verified_owners": sum(1 for r in resolutions if r.verified), "owner_source_conflicts": len(conflicts), "errors": errors}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
