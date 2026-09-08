# Verification

## Automated gate
`python -m unittest discover -s tests -v`

## Demo gate
`python -m grail.demo`

## Live-data validation
1. Snapshot StackR listings + VeVe references + Collect Chain provenance.
2. Freeze snapshot before semantic enrichment.
3. Add sourced IP/number relations to graph.
4. Compare GRAIL with lowest-ask and floor-discount baselines.
5. Blind-label candidates with experienced collectors.
6. Measure Precision@10 / nDCG and false-positive overpays.
7. Backtest historical listings without future leakage.

## Definition of awesome deal
A listing with demonstrably unusual collector desirability or market dislocation relative to comparable observations, at a price leaving reasonable margin of safety—not simply an asset that later rose.

Every production candidate retains observed ask/time, reference evidence/time, mint, marketplace, semantic edges, confidence and missing-data flags.
