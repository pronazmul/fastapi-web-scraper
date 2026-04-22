from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    api_v1_prefix: str
    ig_fast_path: bool
    ig_use_session: bool
    ig_browser_session: bool


@lru_cache
def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        app_name=os.getenv("APP_NAME", "FastAPI Web Scraper"),
        app_version=os.getenv("APP_VERSION", "0.1.0"),
        api_v1_prefix=os.getenv("API_V1_PREFIX", "/api/v1"),
        ig_fast_path=_env_bool("IG_FAST_PATH", True),
        ig_use_session=_env_bool("IG_USE_SESSION", True),
        ig_browser_session=_env_bool("IG_BROWSER_SESSION", False),
    )

