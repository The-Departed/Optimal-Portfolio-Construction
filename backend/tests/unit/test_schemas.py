import pytest
from pydantic import ValidationError

from app.domain.profiles import PROFILE_DEFINITIONS, InvestorProfile
from app.schemas.portfolio import OptimizationRequest, SimulationRequest


def test_every_profile_has_a_definition() -> None:
    assert set(PROFILE_DEFINITIONS) == set(InvestorProfile)
    assert [p for p, d in PROFILE_DEFINITIONS.items() if d.requires_max_volatility] == [
        InvestorProfile.GROWTH
    ]


def test_growth_requires_max_volatility() -> None:
    with pytest.raises(ValidationError, match="required for the growth profile"):
        OptimizationRequest(profile=InvestorProfile.GROWTH)
    assert OptimizationRequest(profile="growth", max_volatility=0.15).max_volatility == 0.15


@pytest.mark.parametrize("profile", ["conservative", "balanced"])
def test_max_volatility_rejected_for_other_profiles(profile: str) -> None:
    with pytest.raises(ValidationError, match="only to the growth profile"):
        OptimizationRequest(profile=profile, max_volatility=0.2)


@pytest.mark.parametrize("sigma", [0, -0.1, 5])
def test_max_volatility_bounds(sigma: float) -> None:
    with pytest.raises(ValidationError):
        OptimizationRequest(profile="growth", max_volatility=sigma)


def test_simulation_request_bounds() -> None:
    assert SimulationRequest().n_portfolios == 50_000
    with pytest.raises(ValidationError):
        SimulationRequest(n_portfolios=0)
    with pytest.raises(ValidationError):
        SimulationRequest(n_portfolios=200_001)
