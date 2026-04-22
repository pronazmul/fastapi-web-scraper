from fastapi import APIRouter, HTTPException

from app.core.exceptions import InvalidProfileUrlError, UnsupportedPlatformError
from app.schemas.scrape import ScrapeRequest, ScrapeResponse, ScrapedProfile
from app.services.scrape_service import ScrapeService

router = APIRouter()
scrape_service = ScrapeService()


@router.post("/scrape-profile", response_model=ScrapeResponse)
@router.post("/scrape/profile", response_model=ScrapeResponse, include_in_schema=False)
async def scrape_profile_endpoint(body: ScrapeRequest) -> ScrapeResponse:
    try:
        data = await scrape_service.scrape_profile(str(body.url))
        return ScrapeResponse(success=True, data=ScrapedProfile.model_validate(data))
    except (UnsupportedPlatformError, InvalidProfileUrlError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        message = str(exc) or repr(exc)
        raise HTTPException(status_code=500, detail=f"Scrape failed: {message}") from exc

