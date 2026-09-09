from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass
from typing import Any, Iterable

from .ownership import COLLECTSCAN_BASE, VEVE_ERC721_CONTRACT, TokenMapping, _get_json


_EDITION_KEYS = {
    "edition", "edition_number", "editionnumber", "edition_no", "editionno",
    "mint", "mint_number", "mintnumber", "serial", "serial_number", "serialnumber",
}


@dataclass(frozen=True)
class MappingDiscovery:
    mint: int
    expected_name: str
    status: str
    candidates_checked: int
    matches: tuple[dict[str, Any], ...]
    reason: str


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def _name_match(expected: str, metadata: dict[str, Any]) -> bool:
    actual = metadata.get("name") or metadata.get("title") or ""
    a, b = _norm(expected), _norm(actual)
    if not a or not b:
        return False
    # Require meaningful overlap, but allow provider titles to contain rarity / issue suffixes.
    at = {x for x in a.split() if len(x) > 2}
    bt = {x for x in b.split() if len(x) > 2}
    overlap = len(at & bt) / max(1, min(len(at), len(bt)))
    return a in b or b in a or overlap >= 0.65


def _ints(value: Any) -> set[int]:
    found: set[int] = set()
    if isinstance(value, bool) or value is None:
        return found
    if isinstance(value, int):
        return {value}
    if isinstance(value, float) and value.is_integer():
        return {int(value)}
    if isinstance(value, str):
        for part in re.findall(r"\d+", value.replace(",", "")):
            try:
                found.add(int(part))
            except ValueError:
                pass
    return found


def metadata_editions(metadata: dict[str, Any]) -> set[int]:
    """Extract edition/mint numbers only from fields explicitly labelled as edition-like."""
    found: set[int] = set()
    for key, value in metadata.items():
        nk = _norm(key).replace(" ", "_")
        if nk in _EDITION_KEYS:
            found |= _ints(value)
        if isinstance(value, dict):
            found |= metadata_editions(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    # Common NFT attribute shape: {trait_type: Edition, value: 851}
                    trait = _norm(item.get("trait_type") or item.get("type") or item.get("name") or "").replace(" ", "_")
                    if trait in _EDITION_KEYS:
                        found |= _ints(item.get("value"))
                    found |= metadata_editions(item)
    return found


def iter_instances(contract: str = VEVE_ERC721_CONTRACT, *, max_pages: int = 50, timeout: float = 20.0) -> Iterable[dict[str, Any]]:
    """Yield Blockscout NFT instances using its documented cursor pagination."""
    url = f"{COLLECTSCAN_BASE}/tokens/{contract}/instances"
    pages = 0
    while url and pages < max_pages:
        payload = _get_json(url, timeout=timeout)
        pages += 1
        for item in payload.get("items") or []:
            yield item
        params = payload.get("next_page_params")
        if not params:
            break
        query = urllib.parse.urlencode(params, doseq=True)
        url = f"{COLLECTSCAN_BASE}/tokens/{contract}/instances?{query}"


def discover_mapping(*, source_url: str, mint: int, expected_name: str, contract: str = VEVE_ERC721_CONTRACT, max_pages: int = 50, timeout: float = 20.0) -> tuple[TokenMapping | None, MappingDiscovery]:
    matches: list[dict[str, Any]] = []
    checked = 0
    for instance in iter_instances(contract, max_pages=max_pages, timeout=timeout):
        checked += 1
        metadata = instance.get("metadata") or {}
        if mint not in metadata_editions(metadata):
            continue
        if not _name_match(expected_name, metadata):
            continue
        token_id = str(instance.get("id") or "")
        if not token_id.isdigit():
            continue
        matches.append({"token_id": token_id, "name": metadata.get("name"), "owner": (instance.get("owner") or {}).get("hash")})
        if len(matches) > 1:
            break

    if len(matches) != 1:
        status = "not-found" if not matches else "ambiguous"
        reason = "no token metadata exposed the requested edition + collectible match" if not matches else "multiple tokens matched; refusing ambiguous mapping"
        return None, MappingDiscovery(mint, expected_name, status, checked, tuple(matches), reason)

    token_id = matches[0]["token_id"]
    evidence = f"https://collectscan.com/token/{contract}/instance/{token_id}?tab=metadata"
    mapping = TokenMapping(
        source_url=source_url,
        mint=mint,
        contract=contract,
        token_id=token_id,
        evidence_url=evidence,
        mapping_method="collectscan-metadata-edition+name-exact",
        expected_name=expected_name,
    )
    return mapping, MappingDiscovery(mint, expected_name, "resolved", checked, tuple(matches), "unique metadata-backed mapping")
