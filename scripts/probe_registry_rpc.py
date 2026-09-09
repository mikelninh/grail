from __future__ import annotations

import json

from grail.provider_edition import _rpc, discover_public_supabase_config

PAGE="https://vevealpha.com/analytics/collectibles"


def call(offset: int, kind: str | None = None):
    config=discover_public_supabase_config(PAGE)
    args={
        "p_sort":"mcap",
        "p_search":None,
        "p_limit":50,
        "p_offset":offset,
        "p_grade":None,
        "p_kind":kind,
        "p_edition":None,
        "p_incl_store":None,
        "p_rarity":None,
        "p_ids":None,
        "p_alpha":None,
        "p_supply_max":None,
    }
    return _rpc(config,"get_collectibles_registry_v6",args,30)


def summarise(raw):
    items=raw if isinstance(raw,list) else raw.get("items",[]) if isinstance(raw,dict) else []
    return {
        "type":type(raw).__name__,
        "top_keys":sorted(raw.keys()) if isinstance(raw,dict) else None,
        "count":len(items),
        "sample":items[:3],
        "item_keys":sorted({k for x in items[:20] if isinstance(x,dict) for k in x.keys()}),
    }


def main() -> int:
    out={}
    for label,offset,kind in (("all0",0,None),("all50",50,None),("comic0",0,"comic"),("collectible0",0,"collectible")):
        try: out[label]=summarise(call(offset,kind))
        except Exception as exc: out[label]={"error":f"{type(exc).__name__}: {exc}"}
    print(json.dumps(out,indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
