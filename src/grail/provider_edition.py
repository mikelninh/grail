from __future__ import annotations

import base64
import html as html_lib
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PublicSupabaseConfig:
    url: str
    anon_key: str


@dataclass(frozen=True)
class EditionLookup:
    collectible_id: str
    edition: int
    name: str | None
    owner: str | None
    token_id: str | None
    raw: dict[str, Any]
    evidence_url: str


def _get(url: str, timeout: float = 20.0) -> str:
    req=urllib.request.Request(url,headers={"User-Agent":"GRAIL/0.9 collector-intelligence (+https://github.com/mikelninh/grail)"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return r.read().decode("utf-8",errors="replace")


def _jwt_payload(token: str) -> dict[str, Any] | None:
    try:
        part=token.split(".")[1]; part += "="*((4-len(part)%4)%4)
        return json.loads(base64.urlsafe_b64decode(part.encode()).decode())
    except Exception:
        return None


def discover_public_supabase_config(page_url: str, timeout: float = 20.0) -> PublicSupabaseConfig:
    """Read the same public client config shipped to every browser; never use service-role credentials."""
    page=_get(page_url,timeout)
    scripts=re.findall(r'<script[^>]+src=["\']([^"\']+)["\']',page,re.I)
    hosts=[]; keys=[]
    for raw in scripts[:40]:
        url=urllib.parse.urljoin(page_url,html_lib.unescape(raw))
        if urllib.parse.urlparse(url).hostname not in {"vevealpha.com","www.vevealpha.com"}: continue
        try: js=_get(url,timeout)
        except Exception: continue
        hosts.extend(re.findall(r'https://[a-z0-9-]+\.supabase\.co',js,re.I))
        keys.extend(re.findall(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+',js))
        keys.extend(re.findall(r'sb_publishable_[A-Za-z0-9_-]+',js))
    host=next(iter(dict.fromkeys(hosts)),None)
    anon=None
    for key in dict.fromkeys(keys):
        if key.startswith("sb_publishable_"):
            anon=key; break
        payload=_jwt_payload(key)
        if payload and payload.get("role")=="anon":
            anon=key; break
    if not host or not anon:
        raise RuntimeError("public Supabase browser config not discoverable")
    return PublicSupabaseConfig(host,anon)


def extract_collectible_id(page_url: str, timeout: float = 20.0) -> str:
    html=_get(page_url,timeout)
    patterns=(
        r'"collectible_id"\s*:\s*"([0-9a-fA-F-]{36})"',
        r'collectible_id\\?"\s*:\s*\\?"([0-9a-fA-F-]{36})',
        r'"id"\s*:\s*"([0-9a-fA-F-]{36})"\s*,\s*"slug"',
    )
    for pat in patterns:
        m=re.search(pat,html,re.I)
        if m: return m.group(1)
    # Fall back to product UUID exposed by the direct VeVe / StackR URLs.
    hrefs=re.findall(r'href=["\']([^"\']+)["\']',html_lib.unescape(html),re.I)
    for href in hrefs:
        m=re.search(r'/([0-9a-fA-F-]{36})(?:[/?#]|$)',href)
        if m: return m.group(1)
    raise RuntimeError("provider collectible_id not discoverable")


def _rpc(config: PublicSupabaseConfig, function: str, args: dict[str, Any], timeout: float = 20.0) -> Any:
    url=f"{config.url}/rest/v1/rpc/{function}"
    body=json.dumps(args).encode()
    req=urllib.request.Request(url,data=body,method="POST",headers={"apikey":config.anon_key,"Authorization":f"Bearer {config.anon_key}","Content-Type":"application/json","User-Agent":"GRAIL/0.9 collector-intelligence"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _pick(obj: Any, keys: tuple[str,...]) -> Any:
    if isinstance(obj,dict):
        for k in keys:
            if obj.get(k) not in (None,""): return obj[k]
        for value in obj.values():
            found=_pick(value,keys)
            if found not in (None,""): return found
    elif isinstance(obj,list):
        for value in obj:
            found=_pick(value,keys)
            if found not in (None,""): return found
    return None


def lookup_edition(page_url: str, edition: int, timeout: float = 20.0) -> EditionLookup:
    config=discover_public_supabase_config(page_url,timeout)
    collectible_id=extract_collectible_id(page_url,timeout)
    raw=_rpc(config,"find_edition_v2",{"p_collectible_id":collectible_id,"p_edition":int(edition)},timeout)
    if raw in (None,[],{}):
        raise LookupError(f"edition #{edition} not returned by provider")
    returned=_pick(raw,("edition","edition_number","mint","mint_number"))
    if returned is not None and int(returned)!=int(edition):
        raise ValueError(f"provider returned edition {returned}, expected {edition}")
    name=_pick(raw,("name","collectible_name","title"))
    owner=_pick(raw,("owner","owner_address","wallet","holder","holder_address"))
    token_id=_pick(raw,("token_id","tokenId","collect_token_id","nft_token_id"))
    return EditionLookup(collectible_id,int(edition),str(name) if name else None,str(owner) if owner else None,str(token_id) if token_id else None,raw,page_url+f"#edition-{edition}")
