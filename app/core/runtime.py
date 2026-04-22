from __future__ import annotations

import asyncio
import sys


def configure_event_loop_policy() -> None:
    if sys.platform == "win32":
        # Playwright launches browsers via subprocess on Windows.
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

