"""Investor profiles and their optimization objectives."""

from dataclasses import dataclass
from enum import StrEnum


class InvestorProfile(StrEnum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    GROWTH = "growth"


@dataclass(frozen=True, slots=True)
class ProfileDefinition:
    profile: InvestorProfile
    label: str
    objective: str
    formulation: str
    requires_max_volatility: bool


_LONG_ONLY = "subject to sum(w) = 1 and 0 <= w_i <= 1"

PROFILE_DEFINITIONS: dict[InvestorProfile, ProfileDefinition] = {
    InvestorProfile.CONSERVATIVE: ProfileDefinition(
        InvestorProfile.CONSERVATIVE,
        "Conservative",
        "Minimize annualized portfolio volatility.",
        f"minimize sqrt(w' Sigma w) {_LONG_ONLY}",
        requires_max_volatility=False,
    ),
    InvestorProfile.BALANCED: ProfileDefinition(
        InvestorProfile.BALANCED,
        "Balanced",
        "Maximize the annualized Sharpe ratio.",
        f"maximize (w' mu - R_f) / sqrt(w' Sigma w) {_LONG_ONLY}",
        requires_max_volatility=False,
    ),
    InvestorProfile.GROWTH: ProfileDefinition(
        InvestorProfile.GROWTH,
        "Growth-oriented",
        "Maximize annualized expected return subject to a maximum acceptable volatility.",
        "maximize w' mu subject to sqrt(w' Sigma w) <= sigma_max, sum(w) = 1 and 0 <= w_i <= 1",
        requires_max_volatility=True,
    ),
}
