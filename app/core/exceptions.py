class ScraperError(Exception):
    """Base exception for scraper-related failures."""


class UnsupportedPlatformError(ScraperError):
    """Raised when a URL does not target a supported platform."""


class InvalidProfileUrlError(ScraperError):
    """Raised when profile URL parsing fails."""

