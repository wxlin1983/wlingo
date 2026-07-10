# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync

# Install with test extras
uv sync --extra test

# Run tests
uv run pytest tests/ -v

# Run a single test
uv run pytest tests/test_api.py::test_home_page_returns_200 -v

# Lint / format
uv run ruff check src/ tests/ scripts/
uv run ruff format src/ tests/ scripts/

# Run locally (requires a running Redis instance)
cd src && uvicorn wlingo.main:app --host 0.0.0.0 --port 8002 --reload

# Run with Docker (recommended — starts Redis automatically)
docker compose up --build

# Frontend dev server (proxies /api, /start, /submit_answer to :8002)
cd frontend && npm install && npm run dev   # → http://localhost:5173

# Build frontend for production (outputs to frontend/dist/)
cd frontend && npm run build
# Copy built files to where FastAPI serves them:
cp -r frontend/dist/* src/static/

# Frontend lint / format / typecheck / test
cd frontend
npm run lint          # eslint
npm run format        # prettier --write
npm run format:check  # prettier --check
npm run typecheck     # tsc --noEmit
npm run test          # vitest run
```

App is available at **http://localhost:8002**. Vite dev server at **http://localhost:5173**. Interactive API docs at **/docs**.

**CI** — `.github/workflows/ci.yml` runs the backend (ruff check/format, pytest) and frontend (eslint, prettier --check, tsc, vitest, vite build) jobs on every push/PR to `main`. The Docker build also gates on both: the `frontend-build` stage runs `npm run lint && npm run test` before `npm run build`, and the `test` stage runs `pytest` before the production image is built — a failure in either stops the build.

### Frontend

The React SPA lives in `frontend/`. Stack: React 18 + TypeScript, Vite, Tailwind CSS v3, Framer Motion, React Router v6.

**Quiz types** — `multiple_choice` renders option buttons; `spelling` and `translation` share the typed-answer flow (`SpellingInput`). Anything that isn't `multiple_choice` must be treated as typed — check `quiz_type !== 'multiple_choice'` rather than enumerating the typed types.

**Root-path handling** — the app defaults to serving from `/` (Docker Compose and the Dockerfile both leave `VITE_ROOT_PATH`/`ROOT_PATH` unset). If you deploy it under a path prefix on a shared domain (e.g. `example.com/wlingo`), set `VITE_ROOT_PATH=/wlingo` at frontend build time and `ROOT_PATH=/wlingo` on the running container — but note the reverse proxy must also strip that prefix before forwarding to the backend, since FastAPI's `root_path` only affects URL generation, not route matching. This controls Vite's `base` for asset URLs, React Router's `basename`, and all API call prefixes in `api.ts`.

Pages:
- `StartPage` — three category sections (Multiple Choice / Spelling / Translation) with topic chips, segmented adaptive/random mode toggle, resume-session banner
- `QuizPage` — progress bar, word card, animated option buttons, keyboard shortcuts (1–4 / Enter / S / Esc)
- `ResultPage` — SVG score ring with CSS animation, scrollable answer review

**Branding** — the app icon (`frontend/public/favicon.svg`) is a "W" monogram: two bold chevrons in the quiz UI's sky palette, with a small accent triangle at the center peak. Referenced from `index.html` as a root-relative `/favicon.svg`, which Vite rewrites to the configured `base` at build time (so it resolves under `/static/` in the built app, matching the `StaticFiles` mount) — swap the file to change the mark without touching any other config.

## Architecture

**wlingo** is a FastAPI + Redis vocabulary quiz app. The backend exposes JSON API endpoints (`/api/*`); the frontend is a React 18 + TypeScript SPA built with Vite and served as static files.

### Key structural details

**Working directory is `src/`** — the app uses relative paths for static files and vocabulary CSVs. `uvicorn` must be launched from inside `src/`. Tests handle this via `conftest.py` which calls `os.chdir(SRC_DIR)` at module level before any wlingo imports.

**App factory** — `app.py:create_app()` constructs the FastAPI instance. Tests import this directly and override the Redis dependency before using it, keeping test setup clean.

**Module-level singletons** — `globals.py` initializes `vocab_manager` (VocabularyManager) at import time. Because it uses a relative path, it only resolves correctly after the cwd is set to `src/`.

### Router layout

Routes are split into two sub-routers mounted in `app.py`:

| Module | Routes |
|---|---|
| `routers/api.py` | All JSON/form endpoints: `/api/*`, `/start`, `/submit_answer` |
| `routers/pages.py` | SPA catch-all: serves `static/index.html` for every non-API path |

Shared FastAPI dependencies (session lookup, cookie extraction, Redis getter) live in `routers/deps.py`. The `get_redis` function is the injection point for tests — override it via `app.dependency_overrides[get_redis]`.

### Redis data layout

Two namespaces stored in Redis:

| Key pattern | Value | TTL |
|---|---|---|
| `session:{session_uuid}` | `SessionData` JSON | `SESSION_TIMEOUT_MINUTES` (120 min) |
| `user_stats:{user_id}:{topic}` | `{"word": wrong_count, ...}` JSON | `USER_STATS_TTL_DAYS` (90 days) |
| `vocab_version` | integer counter, bumped by `/api/admin/reload-vocab` | none |

Session data is also soft-expired on read in `get_active_session()` (belt-and-suspenders alongside the Redis TTL).

### Two-cookie system

- `quiz_session_id` — scoped to a single quiz, set on `/start`, deleted on `/api/reset`
- `wlingo_user_id` — persistent UUID set on first `/` visit, used to look up per-topic word weights across sessions

### Quiz modes

There is a single generator class, `RandomQuizGenerator` (`quiz.py`); the mode only controls whether user history is applied. Valid modes:

- `"adaptive"` — weighted sampling biased toward previously missed words (default)
- `"random"` — pure random shuffle, ignores user history

The module-level `VALID_MODES` set (`quiz.py`) is the single source of truth for valid modes — routers import and check against it rather than keeping a second copy. Only `"adaptive"` mode writes/reads `user_stats` keys and passes `word_weights` into `generator.generate()`; `"random"` passes none.

Adaptive weighting: wrong answers increment a counter in `user_stats`. On `/start`, these weights are fetched and passed to `generator.generate()`, which uses `_weighted_sample` to bias question selection toward previously missed words (boost capped at 3× to prevent domination).

### Session resume

`GET /api/session` returns the current session's topic, mode, `current_index` (= `len(answers)`), and `total_questions`. The start page polls this on load to show a "Resume Quiz" banner when a session is in progress.

### Vocabulary topics

`VocabularyManager` scans `src/vocabulary/` at startup. Top-level `*.csv` files become multiple-choice topics; typed-answer topics live in subdirectories named after their quiz type: `spelling/` (type the reading of a word, e.g. kanji → kana) and `translation/` (type the word's translation, e.g. Chinese → English). Each CSV must have `word` and `translation` columns; an optional `explanation` column is shown on wrong answers (see `scripts/generate_explanations.py` to backfill it via the Claude API). The filename (without extension) becomes the topic ID. `POST /api/admin/reload-vocab` triggers a hot reload without restarting the server — it requires an `X-Admin-Token` header matching `settings.ADMIN_TOKEN` (unset by default, which denies all requests). Because the production image runs multiple uvicorn workers (each with its own in-process `vocab_manager`), the reload endpoint bumps a `vocab_version` counter in Redis; every worker compares its local version against it on vocab-reading requests and lazily reloads when stale.

### Testing

Tests use `fakeredis.FakeRedis(decode_responses=True)` — no real Redis needed. The `client` fixture in `test_api.py` injects the fake client via `app.dependency_overrides[get_redis]`, giving each test an isolated in-memory state.
