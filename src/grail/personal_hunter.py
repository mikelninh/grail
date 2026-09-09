from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

STRONG_SIGNAL_TOKENS = (
    "first", "debut", "earth-", "order 66", "501", "identity",
    "release year", "low edition", "top ~1%", "first-appearance",
)
WEAK_SIGNAL_TOKENS = ("repeating", "lucky", "sequence", "palindrom")


@dataclass(slots=True)
class HunterPreferences:
    budget_usd: float | None = None
    categories: set[str] = field(default_factory=set)
    collectible_terms: tuple[str, ...] = ()
    mint_preferences: set[str] = field(default_factory=set)
    exclude_owned: bool = True
    owned_keys: set[str] = field(default_factory=set)
    watch_keys: set[str] = field(default_factory=set)
    friend_owner_hints: dict[str, str] = field(default_factory=dict)


def candidate_key(row: dict) -> str:
    return f"{row.get('source_url','')}#{row.get('mint','')}"


def _reason_text(row: dict) -> str:
    return " ".join(str(x).lower() for x in row.get("reasons", []) or [])


def _mint_match(row: dict, prefs: HunterPreferences) -> tuple[float, list[str]]:
    if not prefs.mint_preferences:
        return 0.0, []
    text = _reason_text(row)
    score = 0.0
    why: list[str] = []
    mapping = {
        "low": ("low edition", "top ~1%"),
        "historical": ("first", "debut", "release year", "first-appearance"),
        "ip": ("earth-", "order 66", "501", "identity"),
        "patterns": WEAK_SIGNAL_TOKENS,
        "lucky8": ("lucky-8", "lucky 8", "repeating 8"),
    }
    for pref in prefs.mint_preferences:
        tokens = mapping.get(pref, ())
        if tokens and any(t in text for t in tokens):
            score += 8 if pref in {"low", "historical", "ip"} else 3
            why.append(f"matches your {pref} mint preference")
    return score, why


def _friend_match(row: dict, prefs: HunterPreferences) -> str | None:
    owner = str(row.get("current_owner") or row.get("onchain_owner") or row.get("owner") or "").lower()
    if not owner:
        return None
    for name, hint in prefs.friend_owner_hints.items():
        h = hint.lower().strip()
        if not h:
            continue
        if "..." in h or "…" in h:
            parts = h.replace("…", "...").split("...", 1)
            pre, suf = parts[0], parts[1] if len(parts) > 1 else ""
            if (not pre or owner.startswith(pre)) and (not suf or owner.endswith(suf)):
                return name
        elif owner == h:
            return name
    return None


def score_personal(row: dict, prefs: HunterPreferences) -> tuple[float, list[str]]:
    if row.get("live_status") != "live":
        return -10_000.0, ["not live"]
    if row.get("signal_class") not in {"GRAIL", "EDGE", "WATCH"}:
        return -10_000.0, ["not actionable"]
    if row.get("actionability") == "reject-price":
        return -10_000.0, ["price rejected"]
    key = candidate_key(row)
    if prefs.exclude_owned and key in prefs.owned_keys:
        return -10_000.0, ["already owned"]

    ask = float(row.get("ask_usd") or 0)
    if prefs.budget_usd is not None and ask > prefs.budget_usd:
        return -5_000.0 - (ask - prefs.budget_usd), ["over budget"]

    score = float(row.get("opportunity_score") or 0)
    why: list[str] = []
    if row.get("signal_class") == "GRAIL":
        score += 16; why.append("thesis-grade GRAIL")
    elif row.get("signal_class") == "EDGE":
        score += 6; why.append("live price edge")

    if key in prefs.watch_keys:
        score += 12
        why.append("on your watchlist")

    category = str(row.get("category") or "")
    if prefs.categories and category in prefs.categories:
        score += 10; why.append(f"matches your {category} universe")

    name = str(row.get("collectible") or "").lower()
    for term in prefs.collectible_terms:
        if term.lower() in name:
            score += 10; why.append(f"matches your '{term}' interest")

    mint_score, mint_why = _mint_match(row, prefs)
    score += mint_score; why.extend(mint_why)

    if prefs.budget_usd is not None and ask <= prefs.budget_usd:
        score += 4; why.append("inside your budget")

    gap = float(row.get("premium_to_floor_pct") or 0)
    if gap < 0:
        score += min(10, abs(gap) / 8)

    friend = _friend_match(row, prefs)
    if friend:
        score -= 8
        why.append(f"currently associated with friend {friend}")

    return score, why


def rank_personal(rows: Iterable[dict], prefs: HunterPreferences, limit: int = 3) -> list[dict]:
    ranked: list[dict] = []
    for row in rows:
        score, why = score_personal(row, prefs)
        if score <= -1_000:
            continue
        ranked.append({**row, "personal_score": round(score, 2), "personal_why": why})
    ranked.sort(key=lambda r: (r["personal_score"], r.get("opportunity_score", 0)), reverse=True)

    out: list[dict] = []
    seen_collectibles: set[str] = set()
    category_counts: dict[str, int] = {}
    for row in ranked:
        src = str(row.get("source_url") or "")
        cat = str(row.get("category") or "Other")
        if src in seen_collectibles:
            continue
        if category_counts.get(cat, 0) >= 2:
            continue
        out.append(row)
        seen_collectibles.add(src)
        category_counts[cat] = category_counts.get(cat, 0) + 1
        if len(out) >= limit:
            break
    return out
