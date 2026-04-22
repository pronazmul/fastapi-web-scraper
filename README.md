# fastapi-web-scraper

Reusable FastAPI boilerplate for scraping Instagram and TikTok profile data with a layered project structure.

## Project Structure

```text
app/
  api/
    v1/
      endpoints/
  core/
  schemas/
  scrapers/
  services/
  main.py
```

## Layers

- `api`: HTTP route handlers and API versioning.
- `schemas`: Pydantic request/response models.
- `services`: Business orchestration and use-case logic.
- `scrapers`: External platform adapters (Instagram/TikTok).
- `core`: App settings, runtime setup, and shared exceptions.

## Endpoints

- `GET /health` (legacy compatibility)
- `POST /scrape-profile` (legacy compatibility)
- `GET /api/v1/health`
- `POST /api/v1/scrape-profile`
- `POST /api/v1/scrape/profile` (hidden alias)

## Environment Variables

- `APP_NAME` (default: `FastAPI Web Scraper`)
- `APP_VERSION` (default: `0.1.0`)
- `API_V1_PREFIX` (default: `/api/v1`)
- `IG_FAST_PATH` (default: `true`)
- `IG_USE_SESSION` (default: `true`)
- `IG_BROWSER_SESSION` (default: `false`)
- `EATMAP_IG_SESSIONID` or `IG_SESSIONID` (optional Instagram session cookie)

## Run

```bash
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --reload
```

