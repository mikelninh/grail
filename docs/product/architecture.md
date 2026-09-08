# Architecture

## Layers
1. Source adapters: StackR market/activity, VeVe metadata, Collect Chain provenance, optional enrichments. Each emits canonical timestamped observations.
2. Canonical store: relational time-series tables for collectibles, editions, listings, sales, owners and snapshots.
3. Collector Graph: `nodes` + `edges` property-graph semantics initially, portable to Neo4j/AGE later if scale warrants it.
4. Intelligence: deterministic mint, market/reference, liquidity, portfolio and graph-semantic features.
5. Agent: retrieves, compares and explains evidence; never fabricates missing observations; purchases stay human-approved.

## Graph model
Node kinds: `ip`, `brand`, `character`, `collectible`, `edition`, `mint`, `owner`, `wallet`, `sale`, `listing`, `year`, `event`, `creator`, `marketplace`.
Relations: `belongs_to`, `depicts`, `edition_of`, `owned_by`, `listed_on`, `sold_on`, `first_appeared_in_year`, `matches_year`, `references`, `created_by`, `part_of_set`, `transferred_to`.

## Why hybrid
Market snapshots/time series fit relational storage; fandom semantics and provenance traversals fit graph edges. Hybrid storage avoids premature graph-database complexity while preserving graph intelligence.
