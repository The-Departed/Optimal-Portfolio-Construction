"""Centralized application configuration.

All tunable parameters live here and can be overridden with environment variables
prefixed by ``APP_`` (see ``.env.example`` at the repository root).
"""

from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> repository root is three parents above ``app``.
REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=(REPO_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "CAPM & Multi-Asset Portfolio Optimization API"
    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Data layout (see data/README.md).
    data_dir: Path = REPO_ROOT / "data"

    # Study period (subject to data-availability validation in Phase 2).
    study_start: date = date(2019, 1, 1)
    study_end: date = date(2025, 12, 31)

    # Annualization convention for daily data.
    trading_days_per_year: int = Field(default=252, gt=0)

    # Descriptive analytics (Phase 3): CAGR is not reported for shorter samples.
    analytics_min_annualization_days: int = Field(default=365, gt=0)

    # Monte Carlo defaults.
    monte_carlo_simulations: int = Field(default=50_000, gt=0)
    max_monte_carlo_simulations: int = Field(default=200_000, gt=0)
    random_seed: int = Field(default=42, ge=0)

    # Data acquisition (Phase 2). No credentials are needed for any source.
    http_timeout_seconds: float = Field(default=60.0, gt=0)
    http_pause_seconds: float = Field(default=1.0, ge=0)
    http_user_agent: str = (
        "Mozilla/5.0 (compatible; portfolio-construction-research/0.2; academic use)"
    )

    @model_validator(mode="after")
    def _check_consistency(self) -> "Settings":
        if self.study_start >= self.study_end:
            raise ValueError("study_start must be earlier than study_end")
        if self.monte_carlo_simulations > self.max_monte_carlo_simulations:
            raise ValueError("monte_carlo_simulations exceeds max_monte_carlo_simulations")
        return self

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def interim_dir(self) -> Path:
        return self.data_dir / "interim"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def reports_dir(self) -> Path:
        return self.data_dir / "reports"


@lru_cache
def get_settings() -> Settings:
    return Settings()
