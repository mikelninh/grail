from __future__ import annotations

import argparse
from pathlib import Path

from .mint_live import scan_watchlist, write_results


def _report(candidates, errors, top: int) -> str:
    actionable = [c for c in candidates if c.actionability == "verify-now"]
    watching = [c for c in candidates if c.actionability == "watch"]
    rejected = [c for c in candidates if c.actionability == "reject-price"]
    unverified = [c for c in candidates if c.actionability == "pricing-unverified"]

    spot = next((c.omi_usd for c in candidates if c.omi_usd is not None), None)
    spot_text = f"{spot:.8f}" if spot is not None else "UNAVAILABLE"

    lines = [
        "# GRAIL Mint Sniper",
        "",
        "> Provider-reported active StackR listings, repriced from OMI into USD using the current OMI/USD spot observation. Always open the listing before acting.",
        "",
        f"**OMI/USD used:** {spot_text}",
        "",
        f"**Verify-now:** {len(actionable)} · **Watch:** {len(watching)} · **Price rejects:** {len(rejected)} · **Pricing unverified:** {len(unverified)}",
        "",
        "| Rank | Status | Collectible | Mint | Score | Mint score | Current ask | OMI ask | Current floor | vs floor | Listed age |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for idx, c in enumerate(candidates[:top], 1):
        name = c.collectible.replace("|", "\\|")
        age = "?" if c.age_days is None else f"{c.age_days}d"
        omi = "—" if c.ask_omi is None else f"{c.ask_omi:,}"
        lines.append(
            f"| {idx} | **{c.actionability}** | [{name}]({c.source_url}) | #{c.mint} | {c.opportunity_score:.1f} | {c.mint_score:.0f} | "
            f"${c.ask_usd:.2f} | {omi} | ${c.floor_usd:.2f} | {c.premium_to_floor_pct:+.1f}% | {age} |"
        )
        if c.reasons:
            lines.append(f"|  |  | ↳ {'; '.join(c.reasons[:3])} |  |  |  |  |  |  |  |  |")
    if not candidates:
        lines.extend(["", "No StackR edition listings were visible in the current public watchlist pages."])
    if not actionable:
        lines.extend(["", "**No verify-now mint candidate currently clears GRAIL's price guardrails.** That is a valid result; the scanner does not manufacture a snipe."])
    if errors:
        lines.extend(["", "## Provider / pricing errors", ""])
        lines.extend(f"- `{e['url']}` — {e['error']}" for e in errors)
    lines.extend([
        "",
        "## Interpretation",
        "",
        "`verify-now` means provider-reported active inventory with current OMI repricing and no >20% premium to the current StackR floor. `watch` is still plausible but carries a larger premium. `reject-price` fails the margin-of-safety guardrail. `pricing-unverified` is never actionable because a current OMI/USD observation was unavailable.",
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
        print(f"{idx:>2}. [{c.actionability}] {c.collectible} #{c.mint} | {c.opportunity_score:.1f}/100 | ${c.ask_usd:.2f} vs floor ${c.floor_usd:.2f} | mint {c.mint_score:.0f} | listed {age}")
    print(f"\nListings observed: {len(candidates)}")
    print(f"Verify-now candidates: {len(actionable)}")
    print(f"Provider/pricing errors: {len(errors)}")
    print(f"Evidence: {out}")
    print(f"Report: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
