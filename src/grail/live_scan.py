from __future__ import annotations

import argparse
from pathlib import Path

from .live import load_watchlist, scan_urls, write_scan


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the GRAIL live cross-market scanner")
    parser.add_argument("--watchlist", default="data/watchlist.json")
    parser.add_argument("--output", default="artifacts/latest_scan.json")
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    urls = load_watchlist(args.watchlist)
    candidates, errors = scan_urls(urls)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_scan(out, candidates, errors)

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
    return 0 if candidates else 2


if __name__ == "__main__":
    raise SystemExit(main())
