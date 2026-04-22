from fastapi import APIRouter

from app.api.v1.endpoints.health import health_check
from app.api.v1.endpoints.scrape import scrape_profile_endpoint
from app.schemas.health import HealthResponse
from app.schemas.scrape import ScrapeRequest, ScrapeResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["legacy"])
async def legacy_health() -> HealthResponse:
    return await health_check()


@router.post("/scrape-profile", response_model=ScrapeResponse, tags=["legacy"])
async def legacy_scrape_profile(body: ScrapeRequest) -> ScrapeResponse:
    return await scrape_profile_endpoint(body)

