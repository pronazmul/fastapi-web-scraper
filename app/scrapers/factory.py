from app.core.config import get_settings
from app.core.exceptions import UnsupportedPlatformError
from app.scrapers.base import BaseProfileScraper
from app.scrapers.instagram import InstagramScraper
from app.scrapers.tiktok import TikTokScraper


class ScraperFactory:
    def __init__(self) -> None:
        settings = get_settings()
        self._scrapers: dict[str, BaseProfileScraper] = {
            "instagram": InstagramScraper(settings),
            "tiktok": TikTokScraper(),
        }

    def get_scraper(self, platform: str) -> BaseProfileScraper:
        scraper = self._scrapers.get(platform)
        if not scraper:
            raise UnsupportedPlatformError(
                f"Unsupported platform '{platform}'. Supported: instagram, tiktok."
            )
        return scraper

