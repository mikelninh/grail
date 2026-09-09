from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

from grail.provider_edition import _get

PAGES = [
    "https://vevealpha.com/",
    "https://vevealpha.com/listings",
    "https://vevealpha.com/sales",
    "https://vevealpha.com/arbitrage",
    "https://vevealpha.com/analytics/collectibles",
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


def get_json(url: str) -> object:
    req=urllib.request.Request(url,headers={"User-Agent":"GRAIL/0.8 universe-discovery (+https://github.com/mikelninh/grail)"})
    with urllib.request.urlopen(req,timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> int:
    scripts=set(); direct_links=set(); page_results=[]
    for page in PAGES:
        try: html=_get(page)
        except Exception as exc:
            page_results.append({"page":page,"error":f"{type(exc).__name__}: {exc}"}); continue
        direct_links.update(re.findall(r'href=["\'](?:https?://vevealpha\.com)?(/c/[^"\'?#]+)',html,re.I))
        for raw in re.findall(r'<script[^>]+src=["\']([^"\']+)["\']',html,re.I): scripts.add(urllib.parse.urljoin(page,raw))
        page_results.append({"page":page,"bytes":len(html),"c_links":len(set(re.findall(r'/c/[a-z0-9][a-z0-9-]+',html,re.I)))})

    tables=set(); rpcs=set(); contexts=[]; all_c_links=set(direct_links)
    for url in list(scripts)[:120]:
        try: js=_get(url)
        except Exception: continue
        all_c_links.update(re.findall(r'["\'](/c/[a-z0-9][a-z0-9-]+)["\']',js,re.I))
        for m in re.finditer(r'\.from\(["\']([^"\']+)["\']\)',js): tables.add(m.group(1))
        for m in re.finditer(r'\.rpc\(["\']([^"\']+)["\']',js): rpcs.add(m.group(1))
        for needle in ("/api/collectibles/search","analytics/collectibles","is_comic","element_type"):
            if needle.lower() in js.lower(): contexts.extend(around(js,needle,450)[:3])

    search_results=[]; search_items={}
    for q in list("abcdefghijklmnopqrstuvwxyz0123456789") + ["spider","batman","star wars","marvel","disney"]:
        try:
            url="https://vevealpha.com/api/collectibles/search?"+urllib.parse.urlencode({"q":q,"limit":100})
            raw=get_json(url)
            items=raw if isinstance(raw,list) else raw.get("items",[]) if isinstance(raw,dict) else []
            for item in items:
                if isinstance(item,dict):
                    key=str(item.get("collectible_id") or item.get("slug") or item.get("collectible_name") or "")
                    if key: search_items[key]=item
            search_results.append({"q":q,"count":len(items)})
        except Exception as exc:
            search_results.append({"q":q,"error":f"{type(exc).__name__}: {exc}"})

    comics=sum(1 for x in search_items.values() if x.get("is_comic") or x.get("element_type")=="COMIC_COVER")
    print(json.dumps({
        "pages":page_results,"scripts":len(scripts),"tables":sorted(tables),"rpcs":sorted(rpcs),
        "c_links_count":len(all_c_links),"c_links_sample":sorted(all_c_links)[:50],
        "search_probes":search_results,"search_unique":len(search_items),"search_comics":comics,
        "search_sample":list(search_items.values())[:30],"contexts":contexts[:30],
    },indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
