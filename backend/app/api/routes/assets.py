from dataclasses import asdict

from fastapi import APIRouter

from app.domain.assets import BENCHMARK, PORTFOLIO_ASSETS, RISK_FREE
from app.schemas.common import AssetOut, AssetUniverseResponse, ReferenceSeriesOut

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=AssetUniverseResponse)
def asset_universe() -> AssetUniverseResponse:
    return AssetUniverseResponse(
        assets=[AssetOut(**asdict(a)) for a in PORTFOLIO_ASSETS],
        benchmark=ReferenceSeriesOut(**asdict(BENCHMARK)),
        risk_free=ReferenceSeriesOut(**asdict(RISK_FREE)),
    )
