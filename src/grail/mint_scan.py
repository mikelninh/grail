from __future__ import annotations

import argparse
from pathlib import Path

from .mint_live import scan_watchlist, write_results


def _report(candidates, errors, top: int) -> str:
    lines = [
        "# GRAIL Mint Sniper",
        "",
        "> Edition-level read-only intelligence. Verify the listing is still live before acting.",
        "",
        "| Rank | Collectible | Mint | Score | Mint score | Ask | Floor | vs floor | Confidence |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for idx, c in enumerate(candidates[:top], 1):
        name = c.collectible.replace("|", "\\|")
        lines.append(
            f"| {idx} | [{name}]({c.source_url}) | #{c.mint} | {c.opportunity_score:.1f} | {c.mint_score:.0f} | "
            f"${c.ask_usd:.2f} | ${c.floor_usd:.2f} | {c.premium_to_floor_pct:+.1f}% | {c.confidence:.0f}% |"
        )
        if c.reasons:
            lines.append(f"|  | ↳ {'; '.join(c.reasons[:3])} |  |  |  |  |  |  |  |")
    if not candidates:
        lines.extend(["", "No edition-level StackR listings were visible in the current public watchlist pages."])
    if errors:
        lines.extend(["", "## Provider errors", ""])
        lines.extend(f"- `{e['url']}` — {e['error']}" for e in errors)
    lines.extend([
        "",
        "## Interpretation",
        "",
        "A high score means the currently visible edition has an unusual combination of mint semantics and price positioning. It is not a profit guarantee or proof of executable arbitrage.",
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

    print("GRAIL MINT SNIPER")
    print("=================")
    for idx, c in enumerate(candidates[: args.top], 1):
        print(f"{idx:>2}. {c.collectible} #{c.mint} | {c.opportunity_score:.1f}/100 | ${c.ask_usd:.2f} vs floor ${c.floor_usd:.2f} | mint {c.mint_score:.0f}")
    print(f"\nVisible StackR edition listings found: {len(candidates)}")
    print(f"Provider errors: {len(errors)}")
    print(f"Evidence: {out}")
    print(f"Report: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
