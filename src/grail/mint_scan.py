from __future__ import annotations

import argparse
from pathlib import Path

from .mint_live import scan_watchlist, write_results


def _signal(c) -> str:
    if c.actionability == "reject-price":
        return "REJECT"
    if c.actionability == "pricing-unverified":
        return "UNVERIFIED"
    if c.mint_score >= 72 and c.actionability == "verify-now" and c.premium_to_floor_pct <= 20 and c.opportunity_score >= 38:
        return "GRAIL"
    if c.actionability == "verify-now" and c.premium_to_floor_pct <= -15 and c.opportunity_score >= 42:
        return "EDGE"
    if c.mint_score >= 65:
        return "WATCH"
    return "MARKET"


def _report(candidates, errors, top: int) -> str:
    groups = {k: [] for k in ("GRAIL", "EDGE", "WATCH", "MARKET", "REJECT", "UNVERIFIED")}
    for c in candidates:
        groups[_signal(c)].append(c)
    spot = next((c.omi_usd for c in candidates if c.omi_usd is not None), None)
    spot_text = f"{spot:.8f}" if spot is not None else "UNAVAILABLE"

    lines = [
        "# GRAIL — Live Collector Intelligence",
        "",
        "> Edition-level collector research across VeVe and StackR. OMI asks are repriced at current spot. Floors are provider daily snapshots, not guaranteed executable prices. Open the marketplace before acting.",
        "",
        f"**OMI/USD:** {spot_text}  ",
        f"**Signals:** {len(groups['GRAIL'])} GRAIL · {len(groups['EDGE'])} EDGE · {len(groups['WATCH'])} WATCH · {len(groups['MARKET'])} MARKET · {len(groups['REJECT'])} REJECT",
        "",
        "## 🏆 GRAIL — mint significance + sane economics",
        "",
    ]

    def add_cards(rows, limit):
        for c in rows[:limit]:
            lines.extend([
                f"### {c.collectible} — #{c.mint}",
                "",
                f"**Score {c.opportunity_score:.1f}/100 · Mint {c.mint_score:.0f}/100 · Evidence {c.confidence:.0f}%**",
                "",
                f"- Ask: **${c.ask_usd:.2f}** / **{c.ask_omi:,} OMI**" if c.ask_omi else f"- Ask: **${c.ask_usd:.2f}**",
                f"- Daily StackR floor snapshot: **${c.floor_usd:.2f}** ({c.premium_to_floor_pct:+.1f}% positioning)",
                *[f"- {reason}" for reason in c.reasons[:5]],
                f"- [Open StackR]({c.stackr_url})" if c.stackr_url else "- StackR shortcut unresolved",
                f"- [Open VeVe]({c.veve_url})" if c.veve_url else "- VeVe shortcut unresolved",
                f"- [Inspect evidence]({c.source_url})",
                "",
            ])

    if groups["GRAIL"]:
        add_cards(groups["GRAIL"], top)
    else:
        lines.extend(["No candidate currently clears the GRAIL bar. That is a valid result.", ""])

    lines.extend(["## ⚡ EDGE — unusual price positioning to verify", ""])
    add_cards(groups["EDGE"], min(top, 12))
    lines.extend(["## 👁 WATCH — interesting mint, insufficient edge", ""])
    add_cards(groups["WATCH"], min(top, 8))

    lines.extend([
        "## How to read the labels",
        "",
        "**GRAIL** requires collector-significant mint semantics and acceptable economics. **EDGE** is a price anomaly only; it is never promoted to grail without a mint reason. **WATCH** has a collector signal but not enough price evidence. **REJECT** means price sanity failed regardless of mint quality.",
        "",
        "## Verification checklist",
        "",
        "Before buying: open the direct StackR/VeVe link, confirm the exact edition is still active, inspect owner/provenance where available, check current floor/depth and recent realised sales, then account for fees and transfer/custody constraints.",
    ])
    if errors:
        lines.extend(["", "## Provider / pricing errors", ""])
        lines.extend(f"- `{e['url']}` — {e['error']}" for e in errors)
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

    counts = {k: sum(1 for c in candidates if _signal(c) == k) for k in ("GRAIL", "EDGE", "WATCH", "MARKET", "REJECT", "UNVERIFIED")}
    print("GRAIL LIVE COLLECTOR INTELLIGENCE")
    print("================================")
    print(" · ".join(f"{v} {k}" for k, v in counts.items()))
    for idx, c in enumerate(sorted(candidates, key=lambda x: ({"GRAIL":5,"EDGE":4,"WATCH":3,"MARKET":2,"UNVERIFIED":1,"REJECT":0}[_signal(x)], x.opportunity_score), reverse=True)[:args.top], 1):
        print(f"{idx:>2}. [{_signal(c)}] {c.collectible} #{c.mint} | {c.opportunity_score:.1f}/100 | ${c.ask_usd:.2f} | mint {c.mint_score:.0f}")
    print(f"\nProvider/pricing errors: {len(errors)}")
    print(f"Evidence: {out}")
    print(f"Report: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
