from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))

from grail.universe import discover_catalog, select_for_deep_scan, write_catalog


def main() -> int:
    out=ROOT/"data"/"universe_catalog.next.json"
    assets,errors=discover_catalog()
    if len(assets)<250 or sum(a.is_comic for a in assets)<100:
        fallback=ROOT/"data"/"universe_catalog.json"
        if fallback.exists():
            cached=json.loads(fallback.read_text(encoding="utf-8"))
            if cached.get("counts",{}).get("assets",0)>=250 and cached.get("counts",{}).get("comics",0)>=100:
                out.write_text(json.dumps(cached,indent=2),encoding="utf-8")
                print(json.dumps({"status":"cached-fallback","counts":cached.get("counts",{}),"live_errors":errors},indent=2))
                return 0
        raise RuntimeError(f"universe discovery below safety threshold: assets={len(assets)}, comics={sum(a.is_comic for a in assets)}")
    write_catalog(out,assets,errors)
    selected=select_for_deep_scan(assets,limit=120,min_comics=55)
    selection={
        "assets":[{
            "id":a.collectible_id,
            "url":a.source_url,
            "category":"Comics" if a.is_comic else "Collectibles",
            "brand":"Unknown",
            "character":None,
            "asset_kind":a.kind,
            "provider_grail":a.provider_grail,
            "catalog_floor_usd":a.floor_usd,
            "catalog_mcap":a.mcap,
            "image_url":a.image_url,
            "rarity":a.rarity,
        } for a in selected]
    }
    (ROOT/"data"/"universe_deep_scan.next.json").write_text(json.dumps(selection,indent=2),encoding="utf-8")
    print(json.dumps({"status":"live","assets":len(assets),"comics":sum(a.is_comic for a in assets),"deep_scan":len(selected),"deep_comics":sum(a.is_comic for a in selected),"errors":len(errors)},indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
