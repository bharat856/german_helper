# German Helper

German Helper is a small, free-by-default learning app built around daily German news. It fetches German headlines from GNews, optionally falls back to RSS, adapts source excerpts to A1–C2 with Gemini (or a local mock provider), teaches vocabulary, and produces a five-question comprehension quiz.

## Run locally

```bash
cd german_helper
cp .env.example .env
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
PYTHONPATH=backend python -m app.sample_data
PYTHONPATH=backend uvicorn app.main:app --reload
```

In another terminal:

```bash
cd german_helper/frontend
npm install
npm run dev
```

Open http://localhost:5173. Set `GNEWS_API_KEY` and `GEMINI_API_KEY` in `.env`; both keys stay server-side. `GNEWS_API_KEY` is required for real news. Without `GEMINI_API_KEY`, adaptations use the deterministic local mock. `GEMINI_MODEL` defaults to `gemini-2.5-flash-lite`.

## Ingestion and scheduling

Run `PYTHONPATH=backend python -m app.cli` for local ingestion, or use the dashboard’s rate-limited **Refresh news** button. The protected automation endpoint is `POST /api/admin/ingest` with `X-Admin-Token`; `POST /api/news/refresh` is intended for the local dashboard and enforces a server-side cooldown. `GET /api/news/status` reports the last successful refresh and provider error.

The GitHub Actions job runs daily near 06:00 Europe/Berlin, uses the `GNEWS_API_KEY` repository secret, and commits `data/german_helper.db` as a durable artifact. GitHub-hosted runners do not share a local database with a running app, so a deployment must mount this committed artifact or run ingestion against its own durable SQLite volume. GNews free plans may publish headlines with up to a 12-hour delay; this is shown in the dashboard.

GNews is the primary provider with Tagesschau and Deutsche Welle RSS preserved as an optional fallback via `NEWS_RSS_FALLBACK=true`. Only API excerpts/summaries are stored, source links and attribution are preserved, and the app does not bypass paywalls or republish full articles.

## Docker

```bash
cp .env.example .env
docker compose up --build
```

The API is at http://localhost:8000 and the Vite frontend at http://localhost:5173.

## Checks

```bash
PYTHONPATH=backend pytest backend/tests
ruff check backend
cd frontend && npm run build
```

The MVP deliberately has no authentication. Progress is local to the shared SQLite database, and settings are stored locally in the browser UI; add identity only when a multi-user deployment is needed.
