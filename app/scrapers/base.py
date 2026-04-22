from __future__ import annotations

from abc import ABC, abstractmethod


class BaseProfileScraper(ABC):
    @abstractmethod
    async def scrape(self, profile_url: str, username_hint: str) -> dict:
        """Scrape a profile and return normalized profile data."""

