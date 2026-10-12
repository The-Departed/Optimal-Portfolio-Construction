"""Investment-universe registry.

``PORTFOLIO_ASSETS`` defines the single canonical asset ordering used everywhere:
price and return matrices, expected-return vectors, covariance matrices, optimizer
weights and API responses. Never reorder assets anywhere else.

Identifiers are *proposed* until Phase 2 verifies that each source provides a
complete, usable historical series; ``verified`` records that status.
"""

from dataclasses import dataclass
from enum import StrEnum


class AssetClass(StrEnum):
    EQUITY = "equity"
    GOVERNMENT_BOND = "government_bond"
    GOLD = "gold"


class SeriesRole(StrEnum):
    BENCHMARK = "benchmark"
    RISK_FREE = "risk_free"


@dataclass(frozen=True, slots=True)
class Asset:
    id: str
    name: str
    asset_class: AssetClass
    sector: str
    instrument: str
    symbol: str | None
    source: str
    verified: bool
    notes: str = ""


@dataclass(frozen=True, slots=True)
class ReferenceSeries:
    id: str
    name: str
    role: SeriesRole
    symbol: str | None
    source: str
    verified: bool
    notes: str = ""


_YAHOO = "Yahoo Finance"
_AMFI = "AMFI NAV history"
_EQUITY_NOTE = (
    "Identifier verified in Phase 2 (source reports the company name, INR, NSE). "
    "Returns use split- and dividend-adjusted closes."
)


def _equity(asset_id: str, name: str, sector: str, symbol: str) -> Asset:
    return Asset(
        asset_id,
        name,
        AssetClass.EQUITY,
        sector,
        "Listed equity (NSE)",
        symbol,
        _YAHOO,
        True,
        _EQUITY_NOTE,
    )


PORTFOLIO_ASSETS: tuple[Asset, ...] = (
    _equity("MM", "Mahindra & Mahindra", "Automobile", "M&M.NS"),
    _equity("HDFCBANK", "HDFC Bank", "Banking", "HDFCBANK.NS"),
    _equity("TCS", "Tata Consultancy Services", "IT services", "TCS.NS"),
    _equity("RELIANCE", "Reliance Industries", "Diversified business", "RELIANCE.NS"),
    _equity("HINDUNILVR", "Hindustan Unilever", "FMCG", "HINDUNILVR.NS"),
    _equity("SUNPHARMA", "Sun Pharmaceutical Industries", "Pharmaceuticals", "SUNPHARMA.NS"),
    Asset(
        "GSEC",
        "Government bonds",
        AssetClass.GOVERNMENT_BOND,
        "Sovereign debt",
        "Nippon India ETF Nifty 8-13 yr G-Sec Long Term Gilt",
        "LTGILTBEES",
        _AMFI,
        True,
        "NSE: LTGILTBEES, ISIN INF204KB1882, AMFI scheme 139496 (launched July 2016). "
        "Returns use the daily NAV because exchange trading is too illiquid; never yields.",
    ),
    Asset(
        "GOLD",
        "Gold",
        AssetClass.GOLD,
        "Precious metals",
        "Nippon India ETF Gold BeES",
        "GOLDBEES.NS",
        _YAHOO,
        True,
        "ISIN INF204KB17I5. 1:100 unit split on 2019-12-19 (back-adjusted by the source); "
        "two corrupt source rows are excluded after cross-checking against AMFI NAV.",
    ),
)

BENCHMARK = ReferenceSeries(
    "NIFTY50",
    "NIFTY 50",
    SeriesRole.BENCHMARK,
    "^NSEI",
    _YAHOO,
    True,
    "Equity-market benchmark for CAPM. Price index (excludes dividends); the Total "
    "Return Index was not available from an accessible source.",
)

RISK_FREE = ReferenceSeries(
    "RF",
    "91-day Government of India Treasury Bill yield",
    SeriesRole.RISK_FREE,
    "RF_TBILL_91D",
    "RBI Handbook of Statistics",
    True,
    "Implicit yield at cut-off price of weekly primary auctions, percent per annum "
    "(actual/365). Weekly series; daily alignment convention is defined in Phase 3.",
)

ASSET_IDS: tuple[str, ...] = tuple(a.id for a in PORTFOLIO_ASSETS)
EQUITY_IDS: tuple[str, ...] = tuple(
    a.id for a in PORTFOLIO_ASSETS if a.asset_class is AssetClass.EQUITY
)

_BY_ID = {a.id: a for a in PORTFOLIO_ASSETS}


def get_asset(asset_id: str) -> Asset:
    try:
        return _BY_ID[asset_id]
    except KeyError:
        raise KeyError(f"Unknown asset id: {asset_id!r}") from None
