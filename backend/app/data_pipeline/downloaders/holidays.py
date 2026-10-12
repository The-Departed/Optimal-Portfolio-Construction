"""RBI holiday matrix for the Mumbai regional office (official bank-holiday list).

Used only as calendar evidence: the government-securities market and NAV
computation for debt funds follow Mumbai bank holidays, so a missing debt-ETF NAV on
such a date is an expected non-valuation day rather than a data gap.
"""

import html
import re

from app.data_pipeline.downloaders.base import (
    DownloadContext,
    DownloadError,
    checked_get,
    checked_post,
    utc_now,
)
from app.data_pipeline.raw_store import RawFile, RawSnapshot
from app.data_pipeline.source_registry import DatasetSpec

_HIDDEN_INPUT = re.compile(r'<input[^>]+name="([^"]+)"[^>]+value="([^"]*)"', re.I)


def download_rbi_holidays(spec: DatasetSpec, ctx: DownloadContext) -> RawSnapshot:
    url = spec.source.url
    office = spec.source.params["regional_office"]
    page = checked_get(ctx, url).text
    base = {m.group(1): html.unescape(m.group(2)) for m in _HIDDEN_INPUT.finditer(page)}
    files = []
    for year in range(ctx.start.year, ctx.end.year + 1):
        ctx.pause()
        form = {
            **base,
            "drRegionalOffice": office,
            "drMonth": "0",
            "drYear": str(year),
            "btnGo": "GO",
        }
        text = checked_post(ctx, url, data=form).text
        expected = f"{spec.source.expected_name} holiday list for the year {year}"
        if expected not in text:
            raise DownloadError(f"RBI holiday page for {year} lacks '{expected}'")
        files.append(RawFile(f"rbi_holidays_{office}_{year}.html", text.encode("utf-8")))
    return RawSnapshot(
        dataset_id=spec.dataset_id,
        source_kind=spec.source.kind.value,
        retrieved_at=utc_now(),
        files=files,
        request={"url": url, "regional_office": office, "years": [ctx.start.year, ctx.end.year]},
        source_metadata={"office_name": spec.source.expected_name},
    )
