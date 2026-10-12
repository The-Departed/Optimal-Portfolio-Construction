from app.data_pipeline.source_registry import (
    BY_ID,
    DATASETS,
    PORTFOLIO_DATASETS,
    DatasetRole,
    ValueKind,
)
from app.domain.assets import ASSET_IDS


def test_portfolio_datasets_follow_canonical_asset_order() -> None:
    assert tuple(d.dataset_id for d in PORTFOLIO_DATASETS) == ASSET_IDS


def test_benchmark_and_risk_free_are_not_portfolio_assets() -> None:
    assert BY_ID["NIFTY50"].role is DatasetRole.BENCHMARK
    assert BY_ID["RF_TBILL_91D"].role is DatasetRole.RISK_FREE
    assert "NIFTY50" not in ASSET_IDS and "RF_TBILL_91D" not in ASSET_IDS


def test_risk_free_metadata_is_a_yield_not_a_price() -> None:
    rf = BY_ID["RF_TBILL_91D"]
    assert rf.value_kind is ValueKind.YIELD
    assert rf.currency is None
    assert "percent" in rf.units and "weekly" in rf.frequency
    assert not rf.is_daily


def test_bond_uses_etf_nav_not_a_yield_series() -> None:
    gsec = BY_ID["GSEC"]
    assert gsec.value_kind is ValueKind.NAV
    assert gsec.source.params["isin"] == "INF204KB1882"


def test_only_unadjusted_sources_are_split_adjusted() -> None:
    adjusted = {d.dataset_id for d in DATASETS if d.adjust_for_actions}
    assert adjusted == {"GOLD_NAV"}  # Yahoo GOLD is already adjusted by the source


def test_dataset_ids_unique() -> None:
    ids = [d.dataset_id for d in DATASETS]
    assert len(ids) == len(set(ids))
