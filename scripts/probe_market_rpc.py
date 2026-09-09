from __future__ import annotations

import json

from grail.provider_edition import _rpc, discover_public_supabase_config

PAGE="https://vevealpha.com/listings"


def call(kind: str | None):
    config=discover_public_supabase_config(PAGE)
    args={
        "p_source": None,
        "p_rarity": None,
        "p_search": None,
        "p_collectible_id": None,
        "p_top200": False,
        "p_mint_exact": None,
        "p_mint_from": None,
        "p_mint_to": None,
        "p_before": None,
        "p_limit": 150,
        "p_min_pct": None,
        "p_kind": kind,
        "p_max_usd_per_mcp": None,
    }
    return _rpc(config,"get_listings_feed_enriched_v2",args,30)


def summarise(raw):
    items=raw if isinstance(raw,list) else raw.get("items",[]) if isinstance(raw,dict) else []
    return {
        "type":type(raw).__name__,
        "top_keys":sorted(raw.keys()) if isinstance(raw,dict) else None,
        "count":len(items),
        "sample":items[:5],
        "item_keys":sorted({k for x in items[:20] if isinstance(x,dict) for k in x.keys()}),
    }


def main() -> int:
    out={}
    for kind in (None,"comic","collectible"):
        try: out[str(kind or "all")]=summarise(call(kind))
        except Exception as exc: out[str(kind or "all")]={"error":f"{type(exc).__name__}: {exc}"}
    print(json.dumps(out,indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
