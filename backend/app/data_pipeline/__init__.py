"""Phase 2 data pipeline: acquisition, cleaning, validation and alignment.

Run it with ``uv run python -m scripts.download_datasets`` from ``backend/``.
The pipeline never fabricates observations: failed retrievals are reported as
failures and invalid records are flagged and excluded, never repaired.
"""

PIPELINE_VERSION = "2.0.0"
SCHEMA_VERSION = 1
