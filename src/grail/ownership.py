from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


COLLECTSCAN_BASE = "https://collectscan.com/api/v2"
# Public Collectscan pages identify this ERC-721 contract as VeVe (VEVE).
VEVE_ERC721_CONTRACT = "0xbcFEbA7A9dA14f5C9453bDA72E2098537867B3c7"


@dataclass(frozen=True)
class TokenMapping:
    source_url: str
    mint: int
    contract: str
    token_id: str
    evidence_url: str
    mapping_method: str
    expected_name: str | None = None


@dataclass(frozen=True)
class OwnershipResolution:
    source_url: str
    mint: int
    contract: str
    token_id: str
    owner: str | None
    token_name: str | None
    evidence_url: str
    mapping_method: str
    verified: bool
    reason: str
    transfers: tuple[dict[str, Any], ...] = ()


def _valid_address(value: str) -> bool:
    return bool(re.fullmatch(r"0x[a-fA-F0-9]{40}", value or ""))


def _safe_token_id(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9]+", str(value)))


def _get_json(url: str, timeout: float = 15.0) -> dict[str, Any]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "collectscan.com" or not parsed.path.startswith("/api/v2/"):
        raise ValueError("Collectscan resolver only accepts https://collectscan.com/api/v2 URLs")
    req = urllib.request.Request(url, headers={"User-Agent": "GRAIL/0.8 ownership-resolver (+https://github.com/mikelninh/grail)"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def load_mappings(path: str | Path) -> list[TokenMapping]:
    p = Path(path)
    if not p.exists():
        return []
    payload = json.loads(p.read_text(encoding="utf-8"))
    mappings: list[TokenMapping] = []
    for raw in payload.get("mappings", []):
        mapping = TokenMapping(
            source_url=str(raw["source_url"]),
            mint=int(raw["mint"]),
            contract=str(raw["contract"]),
            token_id=str(raw["token_id"]),
            evidence_url=str(raw["evidence_url"]),
            mapping_method=str(raw["mapping_method"]),
            expected_name=raw.get("expected_name"),
        )
        if not _valid_address(mapping.contract) or not _safe_token_id(mapping.token_id):
            raise ValueError(f"invalid token mapping for {mapping.source_url} #{mapping.mint}")
        if not mapping.evidence_url.startswith("https://"):
            raise ValueError("token mapping requires an HTTPS evidence URL")
        mappings.append(mapping)
    return mappings


def _name_matches(expected: str | None, actual: str | None) -> bool:
    if not expected:
        return True
    if not actual:
        return False
    norm = lambda s: re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    a, b = norm(expected), norm(actual)
    return a in b or b in a


def resolve_mapping(mapping: TokenMapping, timeout: float = 15.0) -> OwnershipResolution:
    instance_url = f"{COLLECTSCAN_BASE}/tokens/{mapping.contract}/instances/{mapping.token_id}"
    instance = _get_json(instance_url, timeout=timeout)
    metadata = instance.get("metadata") or {}
    token_name = metadata.get("name") or instance.get("name")
    owner_obj = instance.get("owner") or {}
    owner = owner_obj.get("hash") if isinstance(owner_obj, dict) else None
    owner = owner if owner and _valid_address(owner) else None

    if not _name_matches(mapping.expected_name, token_name):
        return OwnershipResolution(
            source_url=mapping.source_url,
            mint=mapping.mint,
            contract=mapping.contract,
            token_id=mapping.token_id,
            owner=None,
            token_name=token_name,
            evidence_url=mapping.evidence_url,
            mapping_method=mapping.mapping_method,
            verified=False,
            reason="mapped token metadata does not match expected collectible name",
        )

    transfers_url = f"{instance_url}/transfers"
    transfers_payload = _get_json(transfers_url, timeout=timeout)
    transfers = tuple((transfers_payload.get("items") or [])[:30])
    return OwnershipResolution(
        source_url=mapping.source_url,
        mint=mapping.mint,
        contract=mapping.contract,
        token_id=mapping.token_id,
        owner=owner,
        token_name=token_name,
        evidence_url=mapping.evidence_url,
        mapping_method=mapping.mapping_method,
        verified=owner is not None,
        reason="exact mapped Collect Chain token resolved" if owner else "token resolved but current owner was unavailable",
        transfers=transfers,
    )


def resolve_registry(path: str | Path, timeout: float = 15.0) -> tuple[list[OwnershipResolution], list[dict[str, str]]]:
    resolved: list[OwnershipResolution] = []
    errors: list[dict[str, str]] = []
    for mapping in load_mappings(path):
        try:
            resolved.append(resolve_mapping(mapping, timeout=timeout))
        except Exception as exc:
            errors.append({
                "source_url": mapping.source_url,
                "mint": str(mapping.mint),
                "error": f"{type(exc).__name__}: {exc}",
            })
    return resolved, errors


def public_resolution(resolution: OwnershipResolution) -> dict[str, Any]:
    """JSON-safe public representation for a public-chain fact."""
    return asdict(resolution)
