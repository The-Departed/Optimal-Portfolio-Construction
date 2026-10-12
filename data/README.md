# Data directory

Populated by the Phase 2 pipeline. Rebuild everything from `backend/`:

```bash
uv run python -m scripts.download_datasets            # reuse cached raw data, download what is missing
uv run python -m scripts.download_datasets --refresh  # download new raw snapshots
uv run python -m scripts.download_datasets --offline  # never use the network
```

Exit code 0 means PASS or PASS_WITH_WARNINGS, 1 means BLOCKED (or warnings with
`--strict`), and 2 means the pipeline crashed.

| Directory | Contents | Rules |
|---|---|---|
| `raw/<category>/<dataset>/<timestamp>/` | Source responses exactly as downloaded, plus `metadata.json` (request, UTC retrieval time, SHA-256 per file). Categories: `equities`, `benchmark`, `bonds`, `gold`, `risk_free`, `reference`. | Immutable. New retrievals create new timestamped folders; checksums are verified on reuse. |
| `interim/prices`, `interim/risk_free` | One normalized record table per dataset, including invalid records with flags and exclusion reasons. | Regenerated on every run. |
| `processed/` | Cleaned individual series, aligned portfolio/benchmark prices and returns, native-frequency risk-free auctions, metadata, `manifest.json`. | Regenerated on every run; deleted first so a failed run cannot leave stale outputs. |
| `reports/` | Data-quality report, validation summary, source manifest, coverage/missing/excluded/extreme/cross-source reports. | Tracked in git so validation outcomes are reviewable. |

`raw/`, `interim/` and `processed/` contents are git-ignored. They are reproducible from
the documented sources, and redistributing vendor data may be restricted.

Cleaning rules (details in `docs/methodology.md` and the report):

- Records are flagged, then excluded, for: invalid dates, missing or non-numeric values,
  infinities, non-positive prices or out-of-range yields, conflicting duplicate dates, and
  source errors (gold price vs NAV deviation above 20%).
- Nothing is forward-filled, interpolated, zero-filled or repaired.
- Extreme returns are flagged and kept.
- Common-date alignment is an inner join; dropped dates are listed in
  `processed/metadata/alignment.json`.
- The risk-free series stays at its native weekly frequency.

Phase 3 analytics outputs (`processed/returns/asset_daily_returns.csv`, etc.) are written by
`uv run python -m scripts.run_analytics`. Because a pipeline run clears `processed/`, rerun
the analytics after the pipeline.

No credentials are needed. Sources: Yahoo Finance (via `yfinance`), AMFI NAV history,
and RBI (Handbook of Statistics tables and the holiday matrix) on www.rbi.org.in.
