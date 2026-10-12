import pytest

from app.domain.assets import (
    ASSET_IDS,
    EQUITY_IDS,
    PORTFOLIO_ASSETS,
    AssetClass,
    get_asset,
)


def test_universe_has_eight_assets_with_unique_ids() -> None:
    assert len(PORTFOLIO_ASSETS) == 8
    assert len(set(ASSET_IDS)) == 8


def test_asset_class_composition() -> None:
    classes = [a.asset_class for a in PORTFOLIO_ASSETS]
    assert classes.count(AssetClass.EQUITY) == 6
    assert classes.count(AssetClass.GOVERNMENT_BOND) == 1
    assert classes.count(AssetClass.GOLD) == 1
    assert len(EQUITY_IDS) == 6


def test_canonical_order_is_stable() -> None:
    assert ASSET_IDS == (
        "MM",
        "HDFCBANK",
        "TCS",
        "RELIANCE",
        "HINDUNILVR",
        "SUNPHARMA",
        "GSEC",
        "GOLD",
    )


def test_identifiers_verified_in_phase_2() -> None:
    assert all(a.verified for a in PORTFOLIO_ASSETS)
    assert get_asset("GSEC").symbol == "LTGILTBEES"


def test_unknown_asset_raises() -> None:
    with pytest.raises(KeyError):
        get_asset("NOPE")
