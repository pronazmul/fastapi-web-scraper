import re
from urllib.parse import urlparse

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)


def detect_platform(url: str) -> str | None:
    host = (urlparse(url).hostname or "").lower()
    if "instagram.com" in host:
        return "instagram"
    if "tiktok.com" in host:
        return "tiktok"
    return None


def extract_username(url: str) -> str | None:
    path = (urlparse(url).path or "").strip("/")
    if not path:
        return None

    parts = [part for part in path.split("/") if part]
    username = parts[-1]
    if username.startswith("@"):
        username = username[1:]
    return username or None


def email_from_text(text: str | None) -> str | None:
    if not text:
        return None
    match = EMAIL_RE.search(text)
    return match.group(0) if match else None


def normalize_email(username: str, email: str | None) -> str:
    candidate = (email or "").strip()
    if not candidate:
        candidate = f"{username}@gmail.com"
    return candidate.lower()

