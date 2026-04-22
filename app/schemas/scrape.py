from pydantic import BaseModel, ConfigDict, HttpUrl


class ScrapeRequest(BaseModel):
    url: HttpUrl


class ScrapedProfile(BaseModel):
    platform: str
    username: str
    name: str
    bio: str = ""
    avatar: str = ""
    email: str
    followers: int | None = None
    following: int | None = None
    posts: int | None = None
    website: str | None = None
    is_verified: bool | None = None
    is_private: bool | None = None

    model_config = ConfigDict(extra="allow")


class ScrapeResponse(BaseModel):
    success: bool = True
    data: ScrapedProfile

