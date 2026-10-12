from datetime import date

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_defaults(tmp_path) -> None:
    s = Settings(data_dir=tmp_path)
    assert s.trading_days_per_year == 252
    assert s.monte_carlo_simulations == 50_000
    assert s.processed_dir == tmp_path / "processed"


def test_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_RANDOM_SEED", "7")
    assert Settings().random_seed == 7


def test_rejects_inverted_study_period() -> None:
    with pytest.raises(ValidationError):
        Settings(study_start=date(2026, 1, 1), study_end=date(2019, 1, 1))
