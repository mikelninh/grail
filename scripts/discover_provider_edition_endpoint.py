from __future__ import annotations

import html as html_lib
import json
import re
import urllib.parse
import urllib.request

PAGE = "https://vevealpha.com/c/marvel-disney-what-if-goofy-became-spider-man-common"


def get(url: str, timeout: float = 20.0) -> str:
    req = urllib.request.Request(url, headers={"User-Agent":"GRAIL/0.9 evidence-research (+https://github.com/mikelninh/grail)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def around(text: str, needle: str, radius: int = 900) -> list[str]:
    low=text.lower(); target=needle.lower(); out=[]; start=0
    while len(out)<8:
        pos=low.find(target,start)
        if pos<0: break
        out.append(re.sub(r"\s+"," ",text[max(0,pos-radius):pos+radius]))
        start=pos+len(target)
    return out


def main() -> int:
    page=get(PAGE)
    scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)["\']',page,re.I)
    candidates=set();contexts=[];supabase_hosts=set();rpc_contexts=[]
    for raw in scripts[:40]:
        url=urllib.parse.urljoin(PAGE,html_lib.unescape(raw))
        if urllib.parse.urlparse(url).hostname not in {"vevealpha.com","www.vevealpha.com"}: continue
        try: js=get(url)
        except Exception: continue
        for host in re.findall(r'https://[a-z0-9-]+\.supabase\.co',js,re.I): supabase_hosts.add(host)
        if "find_edition_v2" in js: rpc_contexts.extend(around(js,"find_edition_v2",1400))
        low=js.lower()
        if any(term in low for term in ("edition","holder","collectscan","token_id","tokenid")):
            for pat in (r'["\']([^"\']*/api/[^"\']+)["\']',r'["\']([^"\']*(?:edition|holder|ownership)[^"\']*)["\']'):
                for m in re.finditer(pat,js,re.I):
                    value=m.group(1)
                    if len(value)<300: candidates.add(value)
            for term in ("find_edition_v2","get_holders","holder_stats","edition_number"):
                contexts.extend(around(js,term,350)[:3])
    out={"page":PAGE,"script_count":len(scripts),"supabase_hosts":sorted(supabase_hosts),"rpc_find_edition_v2_contexts":rpc_contexts[:8],"candidate_strings":sorted(candidates)[:120],"contexts":contexts[:24]}
    print(json.dumps(out,indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
