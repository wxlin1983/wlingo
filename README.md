<img src="frontend/public/favicon.svg" width="64" height="64" alt="wlingo icon" align="left" />

# wlingo

A web-based quiz application for learning vocabulary. FastAPI + Redis backend, React SPA frontend.

<br clear="left" />

## Features

- **Three quiz types** — multiple choice (pick the right translation), spelling practice (type the reading of a word, e.g. kanji → kana), and translation practice (type the word's translation)
- **Adaptive mode** — questions are weighted toward words you've previously missed
- **Romaji input** — typed-answer topics with kana answers convert romaji to kana live as you type
- **Keyboard shortcuts** — `1`–`4` to select an answer, `Enter` to advance, `S` to hear the word spoken aloud
- **Text-to-speech** — pronunciation support for English, Korean, Japanese, and Chinese
- **Learner notes** — wrong answers surface a short explanation of the word in the results review
- **Add your own topics** — drop a CSV file in `src/vocabulary/` and it's available on next start
- **REST API** — all quiz data accessible via JSON endpoints

## Getting Started

### Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) for dependency management
- Docker + Docker Compose (for containerized deployment)
- A running Redis instance (handled automatically by Docker Compose)

### Run with Docker Compose (recommended)

```bash
docker compose up --build
```

This starts the web app and Redis together. The app is available at:

- **http://localhost:8002**

To stop: `Ctrl+C`, or `docker compose down` if running detached (`-d`).

### Run locally

Start a Redis instance, then run the backend:

```bash
uv sync
cd src
uvicorn wlingo.main:app --host 0.0.0.0 --port 8002 --reload
```

In a separate terminal, run the frontend dev server:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** — the dev server proxies API calls through to the backend on `:8002`.

## Running Tests

```bash
# Backend
uv sync --extra test
uv run pytest tests/ -v

# Frontend
cd frontend
npm run lint      # eslint
npm run typecheck # tsc --noEmit
npm run test      # vitest run
```

Both suites also run in CI (`.github/workflows/ci.yml`) on every push/PR, and the Docker build fails if either fails.

## Adding Vocabulary Topics

Create a UTF-8 CSV file under `src/vocabulary/`. The filename becomes the topic name, and the directory decides the quiz type:

| Location | Quiz type |
|---|---|
| `src/vocabulary/*.csv` | Multiple choice — pick the right `translation` for `word` |
| `src/vocabulary/spelling/*.csv` | Spelling — type the reading of `word` (e.g. kanji → kana; kana answers get live romaji input) |
| `src/vocabulary/translation/*.csv` | Translation — type the `translation` of `word` |

**Example: `src/vocabulary/Spanish.csv`**

```csv
word,translation
hola,hello
adiós,goodbye
gracias,thank you
```

The topic appears automatically on the next application start.

### Generating learner-note explanations

Each CSV can have an optional third `explanation` column — a short, learner-facing note shown when a wrong answer is reviewed (see the "Learner notes" feature above). Writing these by hand doesn't scale, so `scripts/generate_explanations.py` fills them in by calling the Claude API in batches for any row with an empty `explanation`:

```bash
uv sync --extra scripts
ANTHROPIC_API_KEY=... uv run python scripts/generate_explanations.py [--topic NAME] [--force] [--dry-run]
```

- Only rows with an empty `explanation` are processed, so it's safe to re-run after adding new words.
- `--topic NAME` scopes the run to `src/vocabulary/NAME.csv`; omit it to process every CSV.
- `--force` regenerates explanations that already exist; `--dry-run` prints what would be written without saving.
- This is an offline maintenance script — the running app never calls an LLM itself.

## Configuration

All settings are in [`src/wlingo/config.py`](src/wlingo/config.py):

| Setting | Default | Description |
|---|---|---|
| `PROJECT_NAME` | `"wlingo"` | FastAPI app title (shown in `/docs`) |
| `DEBUG` | `False` | FastAPI debug mode |
| `LOG_DIR` / `LOG_FILE` | `"log"` / `"wlingo.log"` | Rotating log file location (5MB × 3 backups) |
| `REDIS_URL` | `redis://localhost:6379/0` | Override via `REDIS_URL` env var |
| `VOCAB_DIR` | `"vocabulary"` | Vocabulary CSV directory |
| `STATIC_DIR` | `"static"` | Built frontend files (`frontend/dist`) served from here |
| `TEST_SIZE` | `15` | Number of questions per quiz |
| `SESSION_COOKIE_NAME` | `"quiz_session_id"` | Cookie holding the active quiz session ID |
| `SESSION_TIMEOUT_MINUTES` | `120` | Redis session TTL |
| `USER_COOKIE_NAME` | `"wlingo_user_id"` | Persistent per-browser cookie used for adaptive-mode word weighting |
| `USER_STATS_TTL_DAYS` | `90` | How long per-topic word-weight stats are kept |
| `ROOT_PATH` | `""` | URL prefix for reverse-proxy deployments (e.g. `/wlingo`) — see [CLAUDE.md](CLAUDE.md#frontend) for the matching frontend build flag |
| `ADMIN_TOKEN` | `""` (unconfigured = always denied) | Shared secret required in the `X-Admin-Token` header for `POST /api/admin/reload-vocab` |
| `COOKIE_SECURE` | `False` | Set `COOKIE_SECURE=true` when serving over HTTPS to mark cookies `Secure` |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/topics` | List available quiz topics |
| `POST` | `/start` | Start a new quiz session |
| `GET` | `/api/quiz/{index}` | Get question data (JSON) |
| `POST` | `/submit_answer` | Submit an answer |
| `GET` | `/api/result` | Get quiz results (JSON) |
| `POST` | `/api/reset` | Clear the current session |

Interactive API docs are available at **http://localhost:8002/docs**.
