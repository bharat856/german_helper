# German Helper

German Helper is a small, free-by-default learning app built around daily German news. It fetches RSS summaries, adapts them to A1–C2 with Gemini (or a local mock provider), teaches vocabulary, and produces a five-question comprehension quiz.

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

Open http://localhost:5173. Without `GEMINI_API_KEY`, the app uses a deterministic mock adapter and quiz so local development costs nothing. Add a Gemini key only when you want generated adaptations; the key stays server-side. `GEMINI_MODEL` defaults to `gemini-2.5-flash-lite`.

## Ingestion and scheduling

Run `PYTHONPATH=backend python -m app.cli` for local ingestion. The GitHub Actions job runs daily near 06:00 Europe/Berlin and commits `data/german_helper.db` as a durable artifact. A deployed app should mount that repository artifact/database volume or run the same ingestion against a durable SQLite volume; GitHub-hosted runners do not share a local database with the running app. In production, protect the admin endpoint with `X-Admin-Token` and use `POST /api/admin/ingest` instead.

The initial adapters use Tagesschau and Deutsche Welle RSS. Only feed summaries are stored, source links and attribution are preserved, stale items are rejected, and the app does not bypass paywalls or republish full articles.

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
