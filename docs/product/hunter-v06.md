# GRAIL v0.6 — Hunter

## Product promise

**Three things worth your attention today — and exactly why.**

Hunter is the default decision layer above the full collector research terminal. It is intentionally selective: fewer than three picks is valid when evidence is weak.

## Qualification

A Hunter candidate must:
- be observed `LIVE` in the current provider scan;
- be `GRAIL`, `EDGE`, or `WATCH` — never `REJECT`, `HISTORY`, or `UNVERIFIED`;
- retain sane OMI-repriced economics;
- expose direct market/evidence links;
- state the collector thesis and the main risk separately.

Ranking adds weight for thesis-grade GRAIL status, mint evidence, discount magnitude and confidence, while penalising ownership-source conflicts. Hunter deduplicates the same collectible and avoids filling all three slots from one universe where possible.

## Card contract

Every Hunter card answers:
1. **Why now?** — current live/price condition.
2. **Why this mint?** — semantic/low-mint thesis, or explicitly says the mint is ordinary.
3. **Risk** — stale snapshot, weak thesis, evidence confidence, or owner conflict.
4. **Proof** — LIVE + ownership evidence level + signal class.
5. **Action** — direct StackR / VeVe / evidence shortcut when sourced.

## Reliability

- Static assets are cache-busted with v0.6 query versions.
- Pages builds ship `404.html` fallback.
- Every production Pages deploy is followed by a public HTTP health gate for HTML and `data/opportunities.json`.
- A Pages deployment is not considered healthy merely because `deploy-pages` returned success.

## Research terminal

The full GRAIL card feed remains available behind **Open full research feed**. Hunter compresses; it does not remove evidence.
