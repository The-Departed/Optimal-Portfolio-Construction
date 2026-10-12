"""Dataset and source definitions for the Phase 2 pipeline.

Each ``DatasetSpec`` records the verified identifier, the source actually used, the
exact value field selected, units and known limitations. The registry is the single
place where source decisions are made; see docs/data_dictionary.md for rationale.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from app.domain.assets import ASSET_IDS


class SourceKind(StrEnum):
    YAHOO = "yahoo_finance"
    AMFI_NAV = "amfi_nav"
    RBI_HANDBOOK = "rbi_handbook"
    RBI_HOLIDAYS = "rbi_holiday_matrix"


class Category(StrEnum):
    """Raw-data sub-directory."""

    EQUITIES = "equities"
    BENCHMARK = "benchmark"
    BONDS = "bonds"
    GOLD = "gold"
    RISK_FREE = "risk_free"
    REFERENCE = "reference"


class DatasetRole(StrEnum):
    PORTFOLIO_ASSET = "portfolio_asset"
    BENCHMARK = "benchmark"
    RISK_FREE = "risk_free"
    CROSS_CHECK = "cross_check"
    CALENDAR_REFERENCE = "calendar_reference"


class ValueKind(StrEnum):
    PRICE = "price"
    INDEX_LEVEL = "index_level"
    NAV = "nav"
    YIELD = "yield"
    CALENDAR = "calendar"


@dataclass(frozen=True, slots=True)
class CorporateAction:
    kind: str
    effective_date: date
    ratio: float
    description: str


@dataclass(frozen=True, slots=True)
class SourceSpec:
    kind: SourceKind
    identifier: str
    source_name: str
    url: str
    value_field: str
    expected_name: str
    params: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DatasetSpec:
    dataset_id: str
    name: str
    role: DatasetRole
    category: Category
    asset_class: str
    sector: str | None
    source: SourceSpec
    value_kind: ValueKind
    currency: str | None
    units: str
    frequency: str
    adjustment: str
    critical: bool
    extreme_return_threshold: float | None = None
    reference_dataset: str | None = None
    exclude_on_reference_deviation: bool = False
    corporate_actions: tuple[CorporateAction, ...] = ()
    # True only when the source is *unadjusted* for ``corporate_actions`` and the
    # validation checks must express it in post-action units.
    adjust_for_actions: bool = False
    # Missing NSE sessions that coincide with RBI Mumbai holidays or weekend special
    # sessions are expected non-valuation days for AMFI NAV series.
    nav_calendar: bool = False
    known_limitations: tuple[str, ...] = ()

    @property
    def is_daily(self) -> bool:
        return self.value_kind not in (ValueKind.YIELD, ValueKind.CALENDAR)


_YAHOO = "Yahoo Finance (chart API via yfinance)"
_YAHOO_URL = "https://finance.yahoo.com/quote/{symbol}/history"
_AMFI = "AMFI (Association of Mutual Funds in India) NAV history"
_AMFI_URL = "https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx"
_RBI = "Reserve Bank of India, Handbook of Statistics on Indian Economy"
_RBI_URL = (
    "https://www.rbi.org.in/Scripts/AnnualPublications.aspx"
    "?head=Handbook+of+Statistics+on+Indian+Economy"
)

_EQUITY_ADJ = (
    "Yahoo 'Adj Close': back-adjusted for splits/bonus issues and cash dividends. "
    "'Close' is split-adjusted only. Levels depend on the download date; returns do not."
)
_ADJ_LIMITATION = (
    "Adjusted-close levels are rescaled whenever later dividends occur, so absolute "
    "levels differ between download dates; daily returns are unaffected."
)


def _equity(dataset_id: str, name: str, sector: str, symbol: str) -> DatasetSpec:
    return DatasetSpec(
        dataset_id=dataset_id,
        name=name,
        role=DatasetRole.PORTFOLIO_ASSET,
        category=Category.EQUITIES,
        asset_class="equity",
        sector=sector,
        source=SourceSpec(
            SourceKind.YAHOO,
            symbol,
            _YAHOO,
            _YAHOO_URL.format(symbol=symbol),
            value_field="Adj Close",
            expected_name=name,
        ),
        value_kind=ValueKind.PRICE,
        currency="INR",
        units="INR per share (adjusted)",
        frequency="daily (NSE trading sessions)",
        adjustment=_EQUITY_ADJ,
        critical=True,
        extreme_return_threshold=0.15,
        known_limitations=(
            _ADJ_LIMITATION,
            "No independent secondary source: NSE blocks automated access (HTTP 403).",
        ),
    )


GOLD_SPLIT_NOTE = (
    "1:100 unit split (face value Rs 100 -> Rs 1). Exchange ex-date 2019-12-19 "
    "(NSE circular, record date 2019-12-20); AMFI NAV per unit changes from 2019-12-23."
)

DATASETS: tuple[DatasetSpec, ...] = (
    _equity("MM", "Mahindra & Mahindra", "Automobile", "M&M.NS"),
    _equity("HDFCBANK", "HDFC Bank", "Banking", "HDFCBANK.NS"),
    _equity("TCS", "Tata Consultancy Services", "IT services", "TCS.NS"),
    _equity("RELIANCE", "Reliance Industries", "Diversified business", "RELIANCE.NS"),
    _equity("HINDUNILVR", "Hindustan Unilever", "FMCG", "HINDUNILVR.NS"),
    _equity("SUNPHARMA", "Sun Pharmaceutical Industries", "Pharmaceuticals", "SUNPHARMA.NS"),
    DatasetSpec(
        dataset_id="GSEC",
        name="Nippon India ETF Nifty 8-13 yr G-Sec Long Term Gilt",
        role=DatasetRole.PORTFOLIO_ASSET,
        category=Category.BONDS,
        asset_class="government_bond",
        sector="Sovereign debt",
        source=SourceSpec(
            SourceKind.AMFI_NAV,
            "139496",
            _AMFI,
            _AMFI_URL,
            value_field="Net Asset Value",
            expected_name="Nippon India ETF Nifty 8-13 yr G-Sec Long Term Gilt",
            params={"mf": "21", "isin": "INF204KB1882", "nse_symbol": "LTGILTBEES"},
        ),
        value_kind=ValueKind.NAV,
        currency="INR",
        units="INR per unit (NAV)",
        frequency="daily (AMFI NAV business days)",
        adjustment="NAV is a total-return measure net of fund expenses (growth ETF, no "
        "distributions); no corporate actions in the study period.",
        critical=True,
        extreme_return_threshold=0.03,
        reference_dataset="GSEC_EXCHANGE",
        nav_calendar=True,
        known_limitations=(
            "NAV is used instead of the NSE price because LTGILTBEES exchange trading is "
            "too illiquid for daily returns (see GSEC_EXCHANGE cross-check).",
            "Investors trading on NSE transact at market prices that can deviate from NAV.",
        ),
    ),
    DatasetSpec(
        dataset_id="GOLD",
        name="Nippon India ETF Gold BeES",
        role=DatasetRole.PORTFOLIO_ASSET,
        category=Category.GOLD,
        asset_class="gold",
        sector="Precious metals",
        source=SourceSpec(
            SourceKind.YAHOO,
            "GOLDBEES.NS",
            _YAHOO,
            _YAHOO_URL.format(symbol="GOLDBEES.NS"),
            value_field="Adj Close",
            expected_name="Nippon India ETF Gold BeES",
        ),
        value_kind=ValueKind.PRICE,
        currency="INR",
        units="INR per unit (split-adjusted exchange price)",
        frequency="daily (NSE trading sessions)",
        adjustment="Yahoo back-adjusts pre-split prices for the 2019 1:100 unit split. "
        "No distributions. " + GOLD_SPLIT_NOTE,
        critical=True,
        extreme_return_threshold=0.06,
        reference_dataset="GOLD_NAV",
        exclude_on_reference_deviation=True,
        corporate_actions=(
            CorporateAction("unit_split", date(2019, 12, 19), 100.0, GOLD_SPLIT_NOTE),
        ),
        known_limitations=(
            "Records deviating from the split-adjusted AMFI NAV by more than the "
            "source-error threshold are excluded as source errors (not repaired).",
        ),
    ),
    DatasetSpec(
        dataset_id="NIFTY50",
        name="NIFTY 50",
        role=DatasetRole.BENCHMARK,
        category=Category.BENCHMARK,
        asset_class="equity_index",
        sector=None,
        source=SourceSpec(
            SourceKind.YAHOO,
            "^NSEI",
            _YAHOO,
            _YAHOO_URL.format(symbol="%5ENSEI"),
            value_field="Close",
            expected_name="NIFTY 50",
        ),
        value_kind=ValueKind.INDEX_LEVEL,
        currency="INR",
        units="index points (price index)",
        frequency="daily (NSE trading sessions)",
        adjustment="Price-return index: excludes dividends. 'Adj Close' equals 'Close'.",
        critical=True,
        extreme_return_threshold=0.10,
        known_limitations=(
            "Price index, not the NIFTY 50 Total Return Index: the benchmark excludes "
            "dividends while equity returns include them (adjusted close).",
            "Preferred source (NSE / NSE Indices) is not accessible to automated clients; "
            "Yahoo Finance is used instead.",
        ),
    ),
    DatasetSpec(
        dataset_id="RF_TBILL_91D",
        name="91-Day Government of India Treasury Bill - implicit yield at cut-off price",
        role=DatasetRole.RISK_FREE,
        category=Category.RISK_FREE,
        asset_class="risk_free_rate",
        sector=None,
        source=SourceSpec(
            SourceKind.RBI_HANDBOOK,
            "Auctions of 91-Day Government of India Treasury Bills",
            _RBI,
            _RBI_URL,
            value_field="Implicit Yield at Cut-off Price (percent)",
            expected_name="Auctions of 91-Day Government of India Treasury Bills",
            params={"edition_years": "2019,2020,2021,2022,2023,2024,2025,2026"},
        ),
        value_kind=ValueKind.YIELD,
        currency=None,
        units="percent per annum, actual/365, primary-auction implicit yield",
        frequency="weekly (primary auctions)",
        adjustment="Not applicable (rate series).",
        critical=True,
        known_limitations=(
            "Weekly primary-auction yields, not a daily secondary-market yield.",
            "Each Handbook edition covers about one fiscal year; editions are combined.",
        ),
    ),
    # Cross-check series: retrieved and validated, never used as analysis inputs.
    DatasetSpec(
        dataset_id="GSEC_EXCHANGE",
        name="LTGILTBEES NSE exchange price (cross-check)",
        role=DatasetRole.CROSS_CHECK,
        category=Category.BONDS,
        asset_class="government_bond",
        sector="Sovereign debt",
        source=SourceSpec(
            SourceKind.YAHOO,
            "LTGILTBEES.NS",
            _YAHOO,
            _YAHOO_URL.format(symbol="LTGILTBEES.NS"),
            value_field="Close",
            expected_name="Nippon India ETF Nifty 8-13 yr G-Sec Long Term Gilt",
        ),
        value_kind=ValueKind.PRICE,
        currency="INR",
        units="INR per unit (exchange close)",
        frequency="daily (NSE sessions with trades)",
        adjustment="No corporate actions.",
        critical=False,
        extreme_return_threshold=0.03,
    ),
    DatasetSpec(
        dataset_id="GOLD_NAV",
        name="Nippon India ETF Gold BeES NAV (cross-check)",
        role=DatasetRole.CROSS_CHECK,
        category=Category.GOLD,
        asset_class="gold",
        sector="Precious metals",
        source=SourceSpec(
            SourceKind.AMFI_NAV,
            "140088",
            _AMFI,
            _AMFI_URL,
            value_field="Net Asset Value",
            expected_name="Nippon India ETF Gold BeES",
            params={"mf": "21", "isin": "INF204KB17I5", "nse_symbol": "GOLDBEES"},
        ),
        value_kind=ValueKind.NAV,
        currency="INR",
        units="INR per unit (NAV, unadjusted)",
        frequency="daily (AMFI NAV business days)",
        adjustment="Unadjusted NAV; divided by 100 before 2019-12-23 for comparison only.",
        critical=False,
        extreme_return_threshold=0.06,
        corporate_actions=(
            CorporateAction("unit_split", date(2019, 12, 23), 100.0, GOLD_SPLIT_NOTE),
        ),
        adjust_for_actions=True,
        nav_calendar=True,
    ),
    DatasetSpec(
        dataset_id="RBI_HOLIDAYS_MUMBAI",
        name="RBI holiday list - Mumbai regional office",
        role=DatasetRole.CALENDAR_REFERENCE,
        category=Category.REFERENCE,
        asset_class="calendar",
        sector=None,
        source=SourceSpec(
            SourceKind.RBI_HOLIDAYS,
            "Mumbai (regional office 28)",
            "Reserve Bank of India, Holiday Matrix",
            "https://www.rbi.org.in/Scripts/HolidayMatrixDisplay.aspx",
            value_field="Holiday",
            expected_name="Mumbai regional office",
            params={"regional_office": "28"},
        ),
        value_kind=ValueKind.CALENDAR,
        currency=None,
        units="dates",
        frequency="annual list",
        adjustment="Not applicable.",
        critical=False,
        known_limitations=(
            "Bank holidays are evidence for missing debt-fund NAVs, not an NSE trading "
            "calendar (NSE's own holiday circulars are not accessible to automated clients).",
        ),
    ),
)

BY_ID: dict[str, DatasetSpec] = {d.dataset_id: d for d in DATASETS}
PORTFOLIO_DATASETS: tuple[DatasetSpec, ...] = tuple(BY_ID[a] for a in ASSET_IDS)
BENCHMARK_DATASET = BY_ID["NIFTY50"]
RISK_FREE_DATASET = BY_ID["RF_TBILL_91D"]
EQUITY_DATASET_IDS: tuple[str, ...] = tuple(
    d.dataset_id for d in DATASETS if d.category is Category.EQUITIES
)
