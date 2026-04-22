from __future__ import annotations

import json
import os
import re

import anyio
import httpx
from playwright.sync_api import sync_playwright

from app.core.config import Settings
from app.scrapers.base import BaseProfileScraper
from app.scrapers.helpers import email_from_text, normalize_email

COUNT_TOKEN_RE = re.compile(r"(?P<num>[\d,.]+)\s*(?P<suf>[kKmM])?")


def _get_ig_sessionid() -> str | None:
    return os.environ.get("EATMAP_IG_SESSIONID") or os.environ.get("IG_SESSIONID")


def _parse_count_token(token: str | None) -> int | None:
    if not token:
        return None

    match = COUNT_TOKEN_RE.fullmatch(token.strip().replace(" ", ""))
    if not match:
        return None

    number = match.group("num").replace(",", "")
    suffix = (match.group("suf") or "").lower()

    try:
        value = float(number)
    except ValueError:
        return None

    if suffix == "k":
        value *= 1_000
    elif suffix == "m":
        value *= 1_000_000

    return int(value)


def _extract_counts_from_description(
    description: str | None,
) -> tuple[int | None, int | None, int | None]:
    if not description:
        return None, None, None

    text = description.replace("\n", " ")
    followers = None
    following = None
    posts = None

    followers_match = re.search(r"([\d.,]+\s*[kKmM]?)\s+Followers", text)
    if followers_match:
        followers = _parse_count_token(followers_match.group(1))

    following_match = re.search(r"([\d.,]+\s*[kKmM]?)\s+Following", text)
    if following_match:
        following = _parse_count_token(following_match.group(1))

    posts_match = re.search(r"([\d.,]+\s*[kKmM]?)\s+Posts", text)
    if posts_match:
        posts = _parse_count_token(posts_match.group(1))

    return followers, following, posts


def _try_extract_ld_json(html: str) -> dict | None:
    match = re.search(
        r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>',
        html,
        re.S | re.I,
    )
    if not match:
        return None

    raw = match.group(1).strip()
    try:
        data = json.loads(raw)
    except Exception:
        return None

    if isinstance(data, dict):
        return data
    if isinstance(data, list) and data and isinstance(data[0], dict):
        return data[0]
    return None


def _try_extract_instagram_user_from_html(html: str) -> dict | None:
    if not html:
        return None

    match = re.search(
        r"__additionalDataLoaded\(\s*'profilePage_[^']*'\s*,\s*(\{.*?\})\s*\);",
        html,
        re.S,
    )
    if not match:
        return None

    try:
        data = json.loads(match.group(1))
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    user = None
    try:
        if isinstance(data.get("graphql"), dict) and isinstance(
            data["graphql"].get("user"), dict
        ):
            user = data["graphql"]["user"]
        elif isinstance(data.get("data"), dict) and isinstance(data["data"].get("user"), dict):
            user = data["data"]["user"]
    except Exception:
        user = None

    return user if isinstance(user, dict) else None


async def _scrape_instagram_via_web_profile_info(
    username_hint: str,
    settings: Settings,
) -> dict | None:
    url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username_hint}"
    headers = {
        "Accept": "application/json,text/plain,*/*",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "X-IG-App-ID": "936619743392459",
        "X-ASBD-ID": "129477",
    }

    if settings.ig_use_session:
        session_id = _get_ig_sessionid()
        if session_id:
            headers["Cookie"] = f"sessionid={session_id}"

    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                return None

            payload = response.json()
            user = payload.get("data", {}).get("user") if isinstance(payload, dict) else None
            if not isinstance(user, dict):
                return None

            returned_username = (user.get("username") or "").strip().lower()
            if returned_username and returned_username != username_hint.strip().lower():
                return None

            biography = (user.get("biography") or "").strip()
            email = normalize_email(username_hint, email_from_text(biography))
            avatar = user.get("profile_pic_url_hd") or user.get("profile_pic_url") or ""

            followers = None
            following = None
            posts = None

            try:
                followers = int(user.get("edge_followed_by", {}).get("count"))
            except Exception:
                pass

            try:
                following = int(user.get("edge_follow", {}).get("count"))
            except Exception:
                pass

            try:
                posts = int(user.get("edge_owner_to_timeline_media", {}).get("count"))
            except Exception:
                pass

            website = user.get("external_url")
            if not (isinstance(website, str) and website.startswith("http")):
                website = None

            is_verified = user.get("is_verified") if isinstance(user.get("is_verified"), bool) else None
            is_private = user.get("is_private") if isinstance(user.get("is_private"), bool) else None

            return {
                "platform": "instagram",
                "username": user.get("username") or username_hint,
                "name": user.get("full_name") or user.get("username") or username_hint,
                "bio": biography,
                "avatar": avatar,
                "email": email,
                "followers": followers,
                "following": following,
                "posts": posts,
                "website": website,
                "is_verified": is_verified,
                "is_private": is_private,
            }
    except Exception:
        return None


def _parse_header_count_text(text: str | None) -> int | None:
    if not text:
        return None
    match = re.search(r"([\d.,]+\s*[kKmM]?)", text.strip())
    return _parse_count_token(match.group(1)) if match else None


def _scrape_instagram_sync(profile_url: str, username_hint: str, use_session: bool) -> dict:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            viewport={"width": 1365, "height": 768},
        )

        if use_session:
            session_id = _get_ig_sessionid()
            if session_id:
                context.add_cookies(
                    [
                        {
                            "name": "sessionid",
                            "value": session_id,
                            "domain": ".instagram.com",
                            "path": "/",
                            "httpOnly": True,
                            "secure": True,
                            "sameSite": "Lax",
                        }
                    ]
                )

        page = context.new_page()

        def _route_handler(route) -> None:
            try:
                if route.request.resource_type in {"image", "media", "font"}:
                    route.abort()
                else:
                    route.continue_()
            except Exception:
                try:
                    route.continue_()
                except Exception:
                    pass

        page.route("**/*", _route_handler)
        page.set_default_timeout(10_000)
        page.goto(profile_url, wait_until="domcontentloaded", timeout=30_000)

        try:
            page.wait_for_timeout(800)
        except Exception:
            pass

        try:
            page.wait_for_selector("header", timeout=5000)
        except Exception:
            pass

        def _meta(selector: str) -> str | None:
            try:
                return page.locator(selector).get_attribute("content")
            except Exception:
                return None

        og_title = _meta('meta[property="og:title"]')
        og_description = _meta('meta[property="og:description"]')
        meta_description = _meta('meta[name="description"]')
        og_image = _meta('meta[property="og:image"]')

        display_name = None
        bio_from_dom = None
        website = None
        is_verified = None
        followers_from_dom = None
        following_from_dom = None
        posts_from_dom = None
        is_private = None

        try:
            display_name_value = page.locator("header h2").first.inner_text(timeout=1500)
            display_name_value = (display_name_value or "").strip()
            if display_name_value:
                display_name = display_name_value
        except Exception:
            pass

        try:
            bio_candidate = page.locator("header section").first.inner_text(timeout=1500)
            bio_candidate = (bio_candidate or "").strip()
            if bio_candidate:
                bio_from_dom = bio_candidate
        except Exception:
            pass

        try:
            link = page.locator("header a[rel='me'], header a[href^='http']").first
            href = link.get_attribute("href")
            if href and href.startswith("http"):
                website = href
        except Exception:
            pass

        try:
            is_verified = page.locator("header svg[aria-label='Verified']").count() > 0
        except Exception:
            is_verified = None

        try:
            items = page.locator("header ul li")
            if items.count() >= 3:
                posts_from_dom = _parse_header_count_text(items.nth(0).inner_text(timeout=1500))
                followers_from_dom = _parse_header_count_text(items.nth(1).inner_text(timeout=1500))
                following_from_dom = _parse_header_count_text(items.nth(2).inner_text(timeout=1500))
        except Exception:
            pass

        try:
            is_private = page.get_by_text("This Account is Private", exact=False).count() > 0
        except Exception:
            is_private = None

        email = None
        try:
            mailto = page.locator('a[href^="mailto:"]').first.get_attribute("href")
        except Exception:
            mailto = None

        if mailto and "mailto:" in mailto:
            email = mailto.split("mailto:", 1)[1].split("?", 1)[0]
        if not email:
            email = email_from_text(og_description) or email_from_text(meta_description)
        email = normalize_email(username_hint, email)

        name = og_title.split("(")[0].strip() if og_title else None
        if display_name:
            name = display_name
        if not name:
            name = username_hint

        try:
            html = page.content() or ""
        except Exception:
            html = ""

        user_json = _try_extract_instagram_user_from_html(html) if html else None
        ld_json = _try_extract_ld_json(html) if html else None

        bio = ""
        if isinstance(ld_json, dict):
            bio = (ld_json.get("description") or "").strip()
            if ld_json.get("name"):
                candidate_name = str(ld_json.get("name")).strip()
                if candidate_name:
                    name = candidate_name

            if not og_image:
                image_value = ld_json.get("image")
                if isinstance(image_value, str):
                    og_image = image_value
                elif isinstance(image_value, dict) and isinstance(image_value.get("url"), str):
                    og_image = image_value["url"]
                elif isinstance(image_value, list) and image_value and isinstance(image_value[0], str):
                    og_image = image_value[0]

        if not bio:
            bio = (og_description or meta_description or "").strip()

        followers, following, posts = _extract_counts_from_description(
            meta_description or og_description
        )
        followers = followers_from_dom if followers_from_dom is not None else followers
        following = following_from_dom if following_from_dom is not None else following
        posts = posts_from_dom if posts_from_dom is not None else posts

        if bio_from_dom:
            lines = [line.strip() for line in bio_from_dom.splitlines() if line.strip()]
            filtered_lines = [
                line
                for line in lines
                if not re.search(r"\b(posts?|followers?|following)\b", line.lower())
                and not re.fullmatch(r"[\d.,]+\s*[kKmM]?", line)
            ]
            if filtered_lines:
                bio = "\n".join(filtered_lines[:8]).strip()

        if isinstance(user_json, dict):
            full_name = (user_json.get("full_name") or "").strip()
            biography = (user_json.get("biography") or "").strip()
            external_url = user_json.get("external_url")
            verified = user_json.get("is_verified")
            private = user_json.get("is_private")

            try:
                posts = int(user_json.get("edge_owner_to_timeline_media", {}).get("count"))
            except Exception:
                pass

            try:
                followers = int(user_json.get("edge_followed_by", {}).get("count"))
            except Exception:
                pass

            try:
                following = int(user_json.get("edge_follow", {}).get("count"))
            except Exception:
                pass

            avatar = user_json.get("profile_pic_url_hd") or user_json.get("profile_pic_url")

            if full_name:
                name = full_name
            if biography:
                bio = biography
            if isinstance(external_url, str) and external_url.startswith("http"):
                website = external_url
            if isinstance(verified, bool):
                is_verified = verified
            if isinstance(private, bool):
                is_private = private
            if isinstance(avatar, str) and avatar.startswith("http"):
                og_image = avatar

        if (not bio) or ("Instagram" in bio and "Followers" in bio):
            try:
                header_text = page.locator("header").inner_text(timeout=2000)
                candidate = (header_text or "").strip()
                if candidate and not candidate.lower().startswith("posts"):
                    bio = candidate
            except Exception:
                pass

        try:
            page.close()
        except Exception:
            pass

        try:
            context.close()
        except Exception:
            pass

        try:
            browser.close()
        except Exception:
            pass

        return {
            "platform": "instagram",
            "username": username_hint,
            "name": name,
            "bio": bio,
            "avatar": og_image or "",
            "email": email,
            "followers": followers,
            "following": following,
            "posts": posts,
            "website": website,
            "is_verified": is_verified,
            "is_private": is_private,
        }


async def scrape_instagram(profile_url: str, username_hint: str, settings: Settings) -> dict:
    if settings.ig_fast_path:
        fast_data = await _scrape_instagram_via_web_profile_info(username_hint, settings)
        if fast_data:
            return fast_data

    return await anyio.to_thread.run_sync(
        _scrape_instagram_sync,
        profile_url,
        username_hint,
        settings.ig_browser_session,
    )


class InstagramScraper(BaseProfileScraper):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def scrape(self, profile_url: str, username_hint: str) -> dict:
        return await scrape_instagram(profile_url, username_hint, self._settings)

