# Outcome Loom

Outcome Loom is a commit-reveal forecasting primitive for events resolved from two independently hosted public records. Forecasts remain hidden until reveal, exported recovery secrets prevent browser loss, and anyone may finalize after the reveal deadline.

## Lifecycle

`create_market` opens immutable options, sources and deadlines. `commit_forecast` stores a SHA-256 commitment. `reveal_forecast` verifies `OPTION|salt`. `finalize` refetches both sources, binds their digests and stores a bounded outcome only after validator review.

Duplicate market IDs, same-host evidence, duplicate commitments, bad reveals, early reveals and repeated finalization are rejected. The contract is advisory and transfers no funds.

## Verify

Run `python -m pytest forecast_tests -q` and `genvm-lint market_engine/outcome_loom.py`. `evidence/network-run.json` records the complete StudioNet lifecycle. The loom app saves recovery material locally and keeps submitted, accepted and final states distinct.

## StudioNet

Deployment metadata and source revision are in `evidence/deployment.json`.
