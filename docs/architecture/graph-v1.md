# Collector Graph v1

GRAIL's graph is evidence-first and can run entirely from GitHub Actions + GitHub Pages.

## Public graph

Nodes: universe, brand, character, collectible, mint, marketplace, semantic signal, price observation, owner address (only when chain-resolved), sale/listing event.

Edges: `belongs_to`, `has_mint`, `listed_on`, `priced_at`, `matches_signal`, `owned_by`, `transferred_to`, `sold_on`.

Every ranking-relevant edge carries a source URL and observation timestamp.

## Private user overlay

GitHub Pages is static, so personal profiles stay in the browser by default. A user can create a local profile, add a Collect wallet/VeVe/StackR identifier, mark owned editions, add friends, and export/import the private profile.

No private profile information is published into the repository. At render time the browser merges local ownership/friend data with the public evidence graph.

## Collect Chain

Collect Chain is EVM-compatible and the official explorer used by VeVe is Collectscan/Blockscout. Exact owner edges are added only when GRAIL has an exact token/contract mapping and the explorer resolves the current owner. A mint number is not assumed to equal a Collect token ID. Unknown ownership stays `unresolved`.

## GitHub-native data flow

1. GitHub Actions scans public VeVe/StackR/VeVe Alpha observations.
2. It reprices OMI asks using current OMI/USD.
3. It builds `site/data/opportunities.json` and `site/data/graph.json`.
4. GitHub Pages publishes the static dashboard.
5. Browser-local profiles are layered on top.

This is the production architecture until cross-device accounts require a dedicated auth/data backend.