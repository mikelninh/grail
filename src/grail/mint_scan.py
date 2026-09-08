from __future__ import annotations

import argparse
from pathlib import Path

from .mint_live import scan_watchlist, write_results


def _report(candidates, errors, top: int) -> str:
    actionable = [c for c in candidates if c.actionability == "verify-now"]
    recent = [c for c in candidates if c.actionability == "recent-signal"]
    historical = [c for c in candidates if c.actionability == "historical-signal"]

    lines = [
        "# GRAIL Mint Sniper",
        "",
        "> Edition-level read-only intelligence. Public rows are listing **events**, not guaranteed active inventory. Always verify on StackR before acting.",
        "",
        f"**Verify-now:** {len(actionable)} · **Recent signals:** {len(recent)} · **Historical signals:** {len(historical)}",
        "",
        "| Rank | Status | Collectible | Mint | Score | Mint score | Event ask | Current floor | vs floor | Age |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for idx, c in enumerate(candidates[:top], 1):
        name = c.collectible.replace("|", "\\|")
        age = "?" if c.age_days is None else f"{c.age_days}d"
        lines.append(
            f"| {idx} | **{c.actionability}** | [{name}]({c.source_url}) | #{c.mint} | {c.opportunity_score:.1f} | {c.mint_score:.0f} | "
            f"${c.ask_usd:.2f} | ${c.floor_usd:.2f} | {c.premium_to_floor_pct:+.1f}% | {age} |"
        )
        if c.reasons:
            lines.append(f"|  |  | ↳ {'; '.join(c.reasons[:3])} |  |  |  |  |  |  |  |")
    if not candidates:
        lines.extend(["", "No StackR edition listing events were visible in the current public watchlist pages."])
    if not actionable:
        lines.extend(["", "**No verify-now mint candidate is currently proven by this source.** Historical rows remain useful for learning mint-premium behaviour, but are not presented as live snipes."])
    if errors:
        lines.extend(["", "## Provider errors", ""])
        lines.extend(f"- `{e['url']}` — {e['error']}" for e in errors)
    lines.extend([
        "",
        "## Interpretation",
        "",
        "`verify-now` means the listing event is at most one day old and merits checking on StackR. It still does not prove the listing remains active. `recent-signal` is 2–3 days old. Older or undated events are historical evidence only.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run GRAIL edition-level mint sniper")
    parser.add_argument("--watchlist", default="data/watchlist.json")
    parser.add_argument("--output", default="artifacts/latest_mint_scan.json")
    parser.add_argument("--report", default="artifacts/latest_mint_scan.md")
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()

    candidates, errors = scan_watchlist(args.watchlist)
    out, report = Path(args.output), Path(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    write_results(out, candidates, errors)
    report.write_text(_report(candidates, errors, args.top), encoding="utf-8")

    actionable = [c for c in candidates if c.actionability == "verify-now"]
    print("GRAIL MINT SNIPER")
    print("=================")
    for idx, c in enumerate(candidates[: args.top], 1):
        age = "?" if c.age_days is None else f"{c.age_days}d"
        print(f"{idx:>2}. [{c.actionability}] {c.collectible} #{c.mint} | {c.opportunity_score:.1f}/100 | ${c.ask_usd:.2f} vs floor ${c.floor_usd:.2f} | mint {c.mint_score:.0f} | age {age}")
    print(f"\nListing events found: {len(candidates)}")
    print(f"Verify-now candidates: {len(actionable)}")
    print(f"Provider errors: {len(errors)}")
    print(f"Evidence: {out}")
    print(f"Report: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
