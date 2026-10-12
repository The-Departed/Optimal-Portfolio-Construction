"""Optional smoke tests against the real sources. Run with: uv run pytest --run-online

They fetch a few days/weeks of data, write nothing to data/, and verify only that each
source still responds in the expected format.
"""

from datetime import date

import pytest

from app.data_pipeline.downloaders.base import DownloadContext
from app.data_pipeline.downloaders.fund_nav import download_amfi_nav
from app.data_pipeline.downloaders.yahoo_finance import download_yahoo
from app.data_pipeline.normalization import normalize
from app.data_pipeline.source_registry import BY_ID

pytestmark = pytest.mark.online


def _ctx() -> DownloadContext:
    return DownloadContext(
        date(2024, 1, 1), date(2024, 1, 31), 60, 1, "portfolio-construction-tests"
    )


def test_yahoo_equity_smoke() -> None:
    snap = download_yahoo(BY_ID["TCS"], _ctx())
    df = normalize(BY_ID["TCS"], snap)
    assert len(df) > 15 and df["value"].gt(0).all()
    assert "Tata Consultancy" in snap.source_metadata.get("longName", "")


def test_amfi_nav_smoke() -> None:
    snap = download_amfi_nav(BY_ID["GSEC"], _ctx())
    df = normalize(BY_ID["GSEC"], snap)
    assert len(df) > 15 and set(df["isin"]) == {"INF204KB1882"}
