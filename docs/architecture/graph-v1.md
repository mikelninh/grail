# Collector Graph v1

GRAIL's graph is evidence-first and can run entirely from GitHub Actions + GitHub Pages.

## Public graph

Nodes: universe, brand, character, collectible, mint, marketplace, semantic signal, price observation, owner address (only when chain-resolved), sale/listing event.

Edges: belongs_to, depicts, has_mint, listed_on, priced_at, matches_semantic_signal, owned_by, transferred_to, sold_on, observed_from.

Every edge that affects opportunity ranking carries a source URL and observation timestamp.

## Private user overlay

GitHub Pages is static, so personal profiles stay in the browser by default. A user can create a local profile, add wallet/VeVe/StackR identifiers, mark owned editions, add friends, export/import a profile file, and merge that private overlay with the public graph at render time.

No private profile information is published into the repository or shared with other visitors.

## Chain resolution

Collect Chain is EVM-compatible and exposes a Blockscout explorer at collectscan.com. Exact owner edges are only added when GRAIL has an exact token/contract mapping and the explorer resolves the current owner. Otherwise ownership remains `unresolved` rather than guessed.

## Pages data flow

1. GitHub Actions scans public VeVe/StackR/VeVe Alpha observations.
2. It reprices OMI asks using current OMI/USD.
3. It builds `site/data/opportunities.json` and `site/data/graph.json`.
4. GitHub Pages deploys the static dashboard.
5. Browser-local profiles are layered on top.

This keeps the first public product cheap, auditable and host-independent while leaving room for a real account backend later.