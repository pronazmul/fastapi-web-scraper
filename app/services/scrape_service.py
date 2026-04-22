from app.core.exceptions import InvalidProfileUrlError, UnsupportedPlatformError
from app.scrapers.factory import ScraperFactory
from app.scrapers.helpers import detect_platform, extract_username


class ScrapeService:
    def __init__(self, factory: ScraperFactory | None = None) -> None:
        self._factory = factory or ScraperFactory()

    async def scrape_profile(self, url: str) -> dict:
        platform = detect_platform(url)
        if not platform:
            raise UnsupportedPlatformError(
                "Unsupported platform. Use an Instagram or TikTok profile URL."
            )

        username = extract_username(url)
        if not username:
            raise InvalidProfileUrlError("Could not extract username from URL.")

        scraper = self._factory.get_scraper(platform)
        return await scraper.scrape(url, username)

