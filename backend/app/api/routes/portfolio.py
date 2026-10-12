from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.dependencies import PortfolioServiceDep
from app.domain.profiles import PROFILE_DEFINITIONS
from app.schemas.common import ErrorResponse
from app.schemas.portfolio import (
    FrontierResponse,
    OptimizationRequest,
    OptimizationResponse,
    ProfileDefinitionOut,
    SimulationRequest,
    SimulationResponse,
)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

_ERRORS = {422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}


@router.get("/profiles", response_model=list[ProfileDefinitionOut])
def profiles() -> list[ProfileDefinitionOut]:
    return [ProfileDefinitionOut(**asdict(d)) for d in PROFILE_DEFINITIONS.values()]


@router.post("/simulate", response_model=SimulationResponse, responses=_ERRORS)
def simulate(request: SimulationRequest, service: PortfolioServiceDep) -> SimulationResponse:
    return service.simulate(request)


@router.post("/optimize", response_model=OptimizationResponse, responses=_ERRORS)
def optimize(request: OptimizationRequest, service: PortfolioServiceDep) -> OptimizationResponse:
    return service.optimize(request)


@router.get("/frontier", response_model=FrontierResponse, responses=_ERRORS)
def frontier(
    service: PortfolioServiceDep, points: Annotated[int, Query(ge=5, le=100)] = 30
) -> FrontierResponse:
    return service.frontier(points)
