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


def main() -> int:
    page = get(PAGE)
    scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', page, re.I)
    candidates = set()
    edition_context = []
    for raw in scripts[:40]:
        url = urllib.parse.urljoin(PAGE, html_lib.unescape(raw))
        if urllib.parse.urlparse(url).hostname not in {"vevealpha.com", "www.vevealpha.com"}:
            continue
        try:
            js = get(url)
        except Exception:
            continue
        low = js.lower()
        if any(term in low for term in ("edition", "holder", "collectscan", "token_id", "tokenid")):
            for pat in (r'["\']([^"\']*/api/[^"\']+)["\']', r'["\']([^"\']*(?:edition|holder|ownership)[^"\']*)["\']'):
                for m in re.finditer(pat, js, re.I):
                    value=m.group(1)
                    if len(value)<300:
                        candidates.add(value)
            for term in ("edition", "holder", "tokenid", "token_id"):
                pos=low.find(term)
                if pos>=0:
                    edition_context.append(re.sub(r"\s+"," ",js[max(0,pos-180):pos+260])[:440])
    out={"page":PAGE,"script_count":len(scripts),"candidate_strings":sorted(candidates)[:100],"contexts":edition_context[:20]}
    print(json.dumps(out,indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
