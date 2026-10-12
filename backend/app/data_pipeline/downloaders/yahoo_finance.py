"""Yahoo Finance daily history via yfinance (unadjusted OHLC + Adj Close + actions)."""

import json
from datetime import timedelta
from typing import Any

from app.data_pipeline.downloaders.base import DownloadContext, DownloadError, utc_now
from app.data_pipeline.raw_store import RawFile, RawSnapshot
from app.data_pipeline.source_registry import DatasetSpec

_METADATA_KEYS = (
    "symbol",
    "longName",
    "shortName",
    "currency",
    "exchangeName",
    "fullExchangeName",
    "instrumentType",
    "exchangeTimezoneName",
    "firstTradeDate",
    "dataGranularity",
)


def download_yahoo(spec: DatasetSpec, ctx: DownloadContext) -> RawSnapshot:
    import yfinance as yf

    symbol = spec.source.identifier
    request = {
        "symbol": symbol,
        "start": ctx.start.isoformat(),
        # yfinance treats ``end`` as exclusive; request through the inclusive end date.
        "end_exclusive": (ctx.end + timedelta(days=1)).isoformat(),
        "interval": "1d",
        "auto_adjust": False,
        "actions": True,
        "repair": False,
        "yfinance_version": yf.__version__,
    }
    ticker = yf.Ticker(symbol)
    try:
        history = ticker.history(
            start=request["start"],
            end=request["end_exclusive"],
            interval="1d",
            auto_adjust=False,
            actions=True,
            repair=False,
            timeout=ctx.timeout_seconds,
            raise_errors=True,
        )
    except Exception as exc:  # yfinance raises many exception types
        raise DownloadError(f"Yahoo Finance download failed for {symbol}: {exc}") from exc
    if history is None or history.empty:
        raise DownloadError(f"Yahoo Finance returned no rows for {symbol}")
    if "Adj Close" not in history.columns or "Close" not in history.columns:
        raise DownloadError(f"Yahoo Finance response for {symbol} lacks Close/Adj Close")

    metadata: dict[str, Any] = {
        k: v for k, v in (ticker.history_metadata or {}).items() if k in _METADATA_KEYS
    }
    csv = history.to_csv(index_label="Date").encode("utf-8")
    ctx.pause()
    return RawSnapshot(
        dataset_id=spec.dataset_id,
        source_kind=spec.source.kind.value,
        retrieved_at=utc_now(),
        files=[
            RawFile("history.csv", csv),
            RawFile(
                "history_metadata.json",
                json.dumps(metadata, indent=2, sort_keys=True, default=str).encode("utf-8"),
            ),
        ],
        request=request,
        source_metadata=metadata,
    )
