# GRAIL

**AI collector intelligence for VeVe, StackR, OMI and Collect Chain.**

GRAIL is a read-only intelligence layer that ranks digital-collectible opportunities using market price, mint significance, scarcity, liquidity, provenance and collector-graph context. It is deliberately human-in-the-loop: it finds and explains candidates; it does not autonomously buy assets.

## Core products

1. **Grail Hunter** — rank unusual listings and market discrepancies.
2. **Mint Intelligence** — recognise culturally, historically and IP-significant edition numbers.
3. **Portfolio Intelligence** — distinguish floor value, fair value and plausible liquidation value.
4. **Cross-market Intelligence** — compare VeVe/StackR effective prices and liquidity.
5. **Collector Graph** — connect IPs, characters, releases, editions, mints, owners, transactions and semantic significance.

## First milestone

`v0.1` proves one question:

> Can GRAIL rank genuinely interesting listings above obvious floor-price sorting, with reproducible evidence for every score?

See the Product Architecture Pack in `docs/product/` and the executable Python prototype under `src/grail/`.
