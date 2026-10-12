from fastapi import APIRouter

from app.api.routes import analytics, assets, capm, data_status, health, portfolio

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(data_status.router)
api_router.include_router(assets.router)
api_router.include_router(analytics.router)
api_router.include_router(capm.router)
api_router.include_router(portfolio.router)
