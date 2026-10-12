"""AMFI NAV history for ETF schemes.

AMFI serves one semicolon-separated text file per fund house and date range. Each
calendar-year response is fetched once per run; the header line and the lines for
the requested scheme code are stored verbatim (the full response's size and SHA-256
are recorded in metadata).
"""

from datetime import date

from app.data_pipeline.downloaders.base import (
    DownloadContext,
    DownloadError,
    checked_get,
    utc_now,
)
from app.data_pipeline.raw_store import RawFile, RawSnapshot, sha256
from app.data_pipeline.source_registry import DatasetSpec

HEADER_PREFIX = "Scheme Code;"


def _fmt(d: date) -> str:
    return d.strftime("%d-%b-%Y")


def _year_chunks(start: date, end: date) -> list[tuple[date, date]]:
    return [
        (max(start, date(y, 1, 1)), min(end, date(y, 12, 31)))
        for y in range(start.year, end.year + 1)
    ]


def _fetch_fund_house(ctx: DownloadContext, url: str, mf: str, lo: date, hi: date) -> str:
    key = ("amfi", mf, lo, hi)
    if key not in ctx.cache:
        params = {"mf": mf, "tp": "1", "frmdt": _fmt(lo), "todt": _fmt(hi)}
        text = checked_get(ctx, url, params=params).text
        if not text.lstrip().startswith(HEADER_PREFIX):
            raise DownloadError(f"AMFI response for mf={mf} {lo}..{hi} has no NAV header")
        ctx.cache[key] = text
        ctx.pause()
    return ctx.cache[key]


def download_amfi_nav(spec: DatasetSpec, ctx: DownloadContext) -> RawSnapshot:
    scheme = spec.source.identifier
    mf = spec.source.params["mf"]
    files: list[RawFile] = []
    chunks_meta = []
    total_rows = 0
    for lo, hi in _year_chunks(ctx.start, ctx.end):
        text = _fetch_fund_house(ctx, spec.source.url, mf, lo, hi)
        lines = text.splitlines()
        header = next(line for line in lines if line.startswith(HEADER_PREFIX))
        rows = [line for line in lines if line.startswith(f"{scheme};")]
        total_rows += len(rows)
        full = text.encode("utf-8")
        chunks_meta.append(
            {
                "from": lo.isoformat(),
                "to": hi.isoformat(),
                "scheme_rows": len(rows),
                "full_response_bytes": len(full),
                "full_response_sha256": sha256(full),
            }
        )
        content = "\n".join([header, *rows]) + "\n"
        files.append(RawFile(f"nav_{lo.year}.txt", content.encode("utf-8")))
    if total_rows == 0:
        raise DownloadError(f"AMFI returned no NAV rows for scheme {scheme}")
    return RawSnapshot(
        dataset_id=spec.dataset_id,
        source_kind=spec.source.kind.value,
        retrieved_at=utc_now(),
        files=files,
        request={"url": spec.source.url, "mf": mf, "scheme_code": scheme, "tp": "1"},
        source_metadata={"chunks": chunks_meta, "isin": spec.source.params.get("isin")},
    )
