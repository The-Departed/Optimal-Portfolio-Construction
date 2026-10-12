"""Source clients. Each returns a ``RawSnapshot`` or raises ``DownloadError``.

Only clients for verified sources exist: Yahoo Finance (equities, NIFTY 50, gold ETF
price), AMFI (ETF NAV history), the RBI Handbook of Statistics (91-day T-bill
auctions) and the RBI holiday matrix (Mumbai bank holidays, calendar evidence only).
NSE is not used: it rejects automated clients (HTTP 403).
"""

from collections.abc import Callable

from app.data_pipeline.downloaders.base import DownloadContext, DownloadError
from app.data_pipeline.downloaders.fund_nav import download_amfi_nav
from app.data_pipeline.downloaders.holidays import download_rbi_holidays
from app.data_pipeline.downloaders.risk_free import download_rbi_tbill_auctions
from app.data_pipeline.downloaders.yahoo_finance import download_yahoo
from app.data_pipeline.raw_store import RawSnapshot
from app.data_pipeline.source_registry import DatasetSpec, SourceKind

Downloader = Callable[[DatasetSpec, DownloadContext], RawSnapshot]

DEFAULT_DOWNLOADERS: dict[SourceKind, Downloader] = {
    SourceKind.YAHOO: download_yahoo,
    SourceKind.AMFI_NAV: download_amfi_nav,
    SourceKind.RBI_HANDBOOK: download_rbi_tbill_auctions,
    SourceKind.RBI_HOLIDAYS: download_rbi_holidays,
}

__all__ = ["DEFAULT_DOWNLOADERS", "DownloadContext", "DownloadError", "Downloader"]
