from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from grail.ownership import load_mappings  # noqa: E402
from grail.ownership_discovery import discover_mapping  # noqa: E402


GOLDEN = [
    {
        "source_url": "https://vevealpha.com/c/marvel-disney-what-if-goofy-became-spider-man-common",
        "mint": 851,
        "expected_name": "Goofy Became Spider-Man #1",
        "label": "Goofy Spider-Man #851",
    }
]


def main() -> int:
    registry = ROOT / "data" / "token_mappings.json"
    existing = load_mappings(registry)
    by_key = {(x.source_url, x.mint): x for x in existing}
    site = ROOT / "site" / "data" / "opportunities.json"
    opportunities = json.loads(site.read_text(encoding="utf-8")) if site.exists() else {"candidates": []}

    targets = list(GOLDEN)
    # Spider-Man #777 can refer to more than one Spider-Man asset. Only attempt rows actually
    # observed by GRAIL; ambiguity is reported rather than silently choosing a collectible.
    spider_rows = [r for r in opportunities.get("candidates", []) if int(r.get("mint", -1)) == 777 and "spider-man" in str(r.get("collectible", "")).lower()]
    for r in spider_rows:
        targets.append({"source_url": r["source_url"], "mint": 777, "expected_name": r["collectible"], "label": f"{r['collectible']} #777"})

    results = []
    added = []
    for t in targets:
        key = (t["source_url"], t["mint"])
        if key in by_key:
            results.append({**t, "status": "already-mapped", "mapping": asdict(by_key[key])})
            continue
        try:
            mapping, proof = discover_mapping(source_url=t["source_url"], mint=t["mint"], expected_name=t["expected_name"], max_pages=120)
            row = {**t, "proof": asdict(proof)}
            if mapping:
                by_key[key] = mapping
                added.append(mapping)
                row["status"] = "resolved"
                row["mapping"] = asdict(mapping)
            else:
                row["status"] = proof.status
            results.append(row)
        except Exception as exc:
            results.append({**t, "status": "error", "error": f"{type(exc).__name__}: {exc}"})

    out = {"version": 1, "targets": results, "resolved_total": len(by_key), "added": len(added)}
    (ROOT / "site" / "data" / "mapping_discovery.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    next_registry = {"version": 1, "mappings": [asdict(x) for x in by_key.values()]}
    (ROOT / "data" / "token_mappings.next.json").write_text(json.dumps(next_registry, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__": raise SystemExit(main())
