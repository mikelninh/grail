from __future__ import annotations

import json
import re
import urllib.parse

from grail.provider_edition import _get

PAGES = [
    "https://vevealpha.com/",
    "https://vevealpha.com/listings",
    "https://vevealpha.com/sales",
    "https://vevealpha.com/arbitrage",
    "https://vevealpha.com/c/marvel-comics-common",
]


def around(text: str, needle: str, radius: int = 700) -> list[str]:
    low=text.lower(); target=needle.lower(); out=[]; start=0
    while len(out)<10:
        pos=low.find(target,start)
        if pos<0: break
        out.append(re.sub(r"\s+"," ",text[max(0,pos-radius):pos+radius]))
        start=pos+len(target)
    return out


def main() -> int:
    scripts=set(); direct_links=set(); page_results=[]
    for page in PAGES:
        try: html=_get(page)
        except Exception as exc:
            page_results.append({"page":page,"error":f"{type(exc).__name__}: {exc}"}); continue
        direct_links.update(re.findall(r'href=["\'](?:https?://vevealpha\.com)?(/c/[^"\'?#]+)',html,re.I))
        for raw in re.findall(r'<script[^>]+src=["\']([^"\']+)["\']',html,re.I):
            scripts.add(urllib.parse.urljoin(page,raw))
        page_results.append({"page":page,"bytes":len(html),"c_links":len(set(re.findall(r'/c/[a-z0-9][a-z0-9-]+',html,re.I)))})

    tables=set(); rpcs=set(); contexts=[]; all_c_links=set(direct_links)
    for url in list(scripts)[:100]:
        try: js=_get(url)
        except Exception: continue
        all_c_links.update(re.findall(r'["\'](/c/[a-z0-9][a-z0-9-]+)["\']',js,re.I))
        for m in re.finditer(r'\.from\(["\']([^"\']+)["\']\)',js):
            tables.add(m.group(1)); contexts.extend(around(js,m.group(0),350)[:1])
        for m in re.finditer(r'\.rpc\(["\']([^"\']+)["\']',js):
            rpcs.add(m.group(1)); contexts.extend(around(js,m.group(1),500)[:1])
        for needle in ("collectible_type","collectibles","screener","catalog","rarity","edition_size","is_comic","comic"):
            if needle in js.lower(): contexts.extend(around(js,needle,300)[:2])

    print(json.dumps({
        "pages":page_results,
        "scripts":len(scripts),
        "tables":sorted(tables),
        "rpcs":sorted(rpcs),
        "c_links_count":len(all_c_links),
        "c_links_sample":sorted(all_c_links)[:100],
        "contexts":contexts[:80],
    },indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
