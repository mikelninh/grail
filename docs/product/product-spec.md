# Product Spec

## Surfaces
1. Grail Hunter ranking feed.
2. Mint Intelligence explanation.
3. Portfolio valuation (floor / fair / liquidation).
4. Cross-market discrepancy detector.
5. Collector Graph query layer.

## Opportunity score v0.1
- price/reference dislocation: 34%
- mint intelligence: 31%
- liquidity: 20%
- scarcity: 15%

Confidence is computed independently from evidence availability and attenuates the final score.

## Acceptance criteria
- Every candidate contains component scores, confidence and evidence.
- A meaningful mint at a modest premium can outrank an ordinary floor listing.
- Extreme overpay cannot be rescued by a meaningful mint alone.
- Portfolio valuation never equates floor with liquidation value.
- Graph can retrieve multi-hop semantic paths.
