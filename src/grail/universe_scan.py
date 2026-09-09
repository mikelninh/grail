from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .mint_live import MintCandidate, _scan_item, fetch_omi_usd


def scan_universe_selection(path: str | Path, max_workers: int = 18) -> tuple[list[MintCandidate], list[dict[str,str]]]:
    payload=json.loads(Path(path).read_text(encoding="utf-8"))
    items=list(payload.get("assets",[]))
    candidates: list[MintCandidate]=[]
    errors: list[dict[str,str]]=[]
    try:
        omi_usd=fetch_omi_usd()
    except Exception as exc:
        omi_usd=None
        errors.append({"url":"OMI/USD","error":f"{type(exc).__name__}: {exc}"})
    if not items:
        return [], errors
    workers=max(1,min(max_workers,len(items)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(_scan_item,item,omi_usd) for item in items]
        for future in as_completed(futures):
            found,error=future.result()
            candidates.extend(found)
            if error: errors.append(error)
    rank={"verify-now":4,"watch":3,"pricing-unverified":2,"reject-price":1}
    candidates.sort(key=lambda c:(rank[c.actionability],c.opportunity_score,c.mint_score),reverse=True)
    return candidates,errors
