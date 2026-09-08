from __future__ import annotations

import argparse
from pathlib import Path

from .live import LiveCandidate, load_watchlist, scan_urls, write_scan


def _markdown(candidates: list[LiveCandidate], errors: list[dict[str, str]], top: int) -> str:
    lines = [
        "# GRAIL Live Scan",
        "",
        "> Read-only collector intelligence. A floor gap is **not** executable arbitrage until fees, depth, custody and transfer constraints are verified.",
        "",
        "| Rank | Collectible | Score | Cheaper market | Cheap floor | Other floor | Gap | Confidence |",
        "|---:|---|---:|---|---:|---:|---:|---:|",
    ]
    for idx, c in enumerate(candidates[:top], 1):
        name = c.collectible.replace("|", "\\|")
        lines.append(
            f"| {idx} | [{name}]({c.source_url}) | {c.opportunity_score:.1f} | {c.cheaper_market} | "
            f"${c.cheap_floor_usd:.2f} | ${c.expensive_floor_usd:.2f} | {c.nominal_gap_pct:.1f}% | {c.confidence:.0f}% |"
        )
    lines.extend(["", "## Guardrails", ""])
    lines.extend([
        "- Verify the exact edition/listing is still available before acting.",
        "- Verify OMI/USD, marketplace fees, custody/transfer rules and exit liquidity.",
        "- Prefer realised-sales depth over displayed floor when deciding fair value.",
        "- Never infer a guaranteed profit from the score.",
    ])
    if errors:
        lines.extend(["", "## Provider errors", ""])
        for err in errors:
            lines.append(f"- `{err['url']}` — {err['error']}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the GRAIL live cross-market scanner")
    parser.add_argument("--watchlist", default="data/watchlist.json")
    parser.add_argument("--output", default="artifacts/latest_scan.json")
    parser.add_argument("--report", default="artifacts/latest_scan.md")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    urls = load_watchlist(args.watchlist)
    candidates, errors = scan_urls(urls)
    out = Path(args.output)
    report = Path(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    report.parent.mkdir(parents=True, exist_ok=True)
    write_scan(out, candidates, errors)
    report.write_text(_markdown(candidates, errors, args.top), encoding="utf-8")

    print("GRAIL LIVE SCAN")
    print("===============")
    if not candidates:
        print("No candidates produced.")
    for idx, candidate in enumerate(candidates[: args.top], 1):
        print(
            f"{idx:>2}. {candidate.collectible} | {candidate.opportunity_score:>5.1f}/100 | "
            f"{candidate.cheaper_market} ${candidate.cheap_floor_usd:.2f} vs ${candidate.expensive_floor_usd:.2f} | "
            f"gap {candidate.nominal_gap_pct:.1f}% | conf {candidate.confidence:.0f}%"
        )
    if errors:
        print(f"\nProvider errors: {len(errors)} (preserved in {out})")
    print(f"\nEvidence artifact: {out}")
    print(f"Readable report: {report}")
    return 0 if candidates else 2


if __name__ == "__main__":
    raise SystemExit(main())
