from __future__ import annotations

import json
import re

import httpx

from app.scrapers.base import BaseProfileScraper
from app.scrapers.helpers import email_from_text, normalize_email


def _first_match(html: str, pattern: re.Pattern) -> str | None:
    match = pattern.search(html)
    return match.group(1) if match else None


async def scrape_tiktok(profile_url: str, username_hint: str) -> dict:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    profile_target = f"https://www.tiktok.com/@{username_hint}"

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        try:
            html_response = await client.get(profile_target, headers=headers)
            if html_response.status_code == 200 and html_response.text:
                html = html_response.text

                def _json_from_script(script_id: str) -> dict | None:
                    script_match = re.search(
                        rf'<script[^>]+id="{re.escape(script_id)}"[^>]*>([\s\S]*?)</script>',
                        html,
                        re.I,
                    )
                    if not script_match:
                        return None

                    try:
                        return json.loads((script_match.group(1) or "").strip())
                    except Exception:
                        return None

                sigi = _json_from_script("SIGI_STATE")
                if isinstance(sigi, dict):
                    user_module = sigi.get("UserModule") if isinstance(sigi.get("UserModule"), dict) else {}
                    users = user_module.get("users") if isinstance(user_module.get("users"), dict) else {}
                    stats = user_module.get("stats") if isinstance(user_module.get("stats"), dict) else {}

                    user = users.get(username_hint) if isinstance(users.get(username_hint), dict) else None
                    if not user and users:
                        try:
                            user = next(iter(users.values()))
                        except Exception:
                            user = None

                    stat = stats.get(username_hint) if isinstance(stats.get(username_hint), dict) else None
                    if not stat and stats:
                        try:
                            stat = next(iter(stats.values()))
                        except Exception:
                            stat = None

                    if isinstance(user, dict):
                        bio = (user.get("signature") or "").strip()
                        email = normalize_email(username_hint, email_from_text(bio))
                        return {
                            "platform": "tiktok",
                            "username": user.get("uniqueId") or username_hint,
                            "name": user.get("nickname") or user.get("uniqueId") or username_hint,
                            "bio": bio,
                            "avatar": user.get("avatarLarger") or user.get("avatarMedium") or "",
                            "email": email,
                            "followers": (stat or {}).get("followerCount") if isinstance(stat, dict) else None,
                        }

                universal = _json_from_script("__UNIVERSAL_DATA_FOR_REHYDRATION__")
                if isinstance(universal, dict):
                    default_scope = (
                        universal.get("__DEFAULT_SCOPE__")
                        if isinstance(universal.get("__DEFAULT_SCOPE__"), dict)
                        else {}
                    )
                    detail = (
                        default_scope.get("webapp.user-detail")
                        if isinstance(default_scope.get("webapp.user-detail"), dict)
                        else {}
                    )
                    user_info = detail.get("userInfo") if isinstance(detail.get("userInfo"), dict) else {}
                    user = user_info.get("user") if isinstance(user_info.get("user"), dict) else None
                    stat = user_info.get("stats") if isinstance(user_info.get("stats"), dict) else None

                    if isinstance(user, dict):
                        bio = (user.get("signature") or "").strip()
                        email = normalize_email(username_hint, email_from_text(bio))
                        return {
                            "platform": "tiktok",
                            "username": user.get("uniqueId") or username_hint,
                            "name": user.get("nickname") or user.get("uniqueId") or username_hint,
                            "bio": bio,
                            "avatar": user.get("avatarLarger") or user.get("avatarMedium") or "",
                            "email": email,
                            "followers": (stat or {}).get("followerCount") if isinstance(stat, dict) else None,
                        }

                og_title = _first_match(
                    html,
                    re.compile(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', re.I),
                )
                og_description = _first_match(
                    html,
                    re.compile(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', re.I),
                )
                og_image = _first_match(
                    html,
                    re.compile(r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"', re.I),
                )

                name = (og_title or "").strip() or username_hint
                bio = (og_description or "").strip()
                email = normalize_email(username_hint, email_from_text(bio))
                avatar = (og_image or "").strip()

                if name or bio or avatar:
                    return {
                        "platform": "tiktok",
                        "username": username_hint,
                        "name": name,
                        "bio": bio,
                        "avatar": avatar,
                        "email": email,
                    }
        except Exception:
            pass

        oembed_url = f"https://www.tiktok.com/oembed?url={profile_target}"
        try:
            response = await client.get(
                oembed_url,
                headers={**headers, "Accept": "application/json,text/plain,*/*"},
            )
            if response.status_code != 200:
                raise ValueError("oEmbed request failed")

            payload = response.json()
            bio = payload.get("title") or ""
            email = normalize_email(username_hint, email_from_text(bio))
            return {
                "platform": "tiktok",
                "username": username_hint,
                "name": payload.get("author_name") or username_hint,
                "bio": bio,
                "avatar": payload.get("thumbnail_url") or "",
                "email": email,
            }
        except Exception:
            email = normalize_email(username_hint, None)
            return {
                "platform": "tiktok",
                "username": username_hint,
                "name": username_hint,
                "bio": "",
                "avatar": "",
                "email": email,
            }


class TikTokScraper(BaseProfileScraper):
    async def scrape(self, profile_url: str, username_hint: str) -> dict:
        return await scrape_tiktok(profile_url, username_hint)

