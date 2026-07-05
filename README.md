<img src="frontend/public/favicon.svg" width="64" height="64" alt="wlingo icon" align="left" />

# wlingo

A web-based quiz application for learning vocabulary. FastAPI + Redis backend, React SPA frontend.

<br clear="left" />

## Features

- **Vocabulary quizzes** — multiple-choice questions drawn from CSV word lists
- **Adaptive mode** — questions are weighted toward words you've previously missed
- **Keyboard shortcuts** — `1`–`4` to select an answer, `Enter` to advance, `S` to hear the word spoken aloud
- **Text-to-speech** — pronunciation support for English and Korean
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
uv sync --extra test
uv run pytest tests/ -v
```

## Adding Vocabulary Topics

Create a UTF-8 CSV file in `src/vocabulary/`. The filename becomes the topic name.

**Example: `src/vocabulary/Spanish.csv`**

```csv
word,translation
hola,hello
adiós,goodbye
gracias,thank you
```

The topic appears automatically on the next application start.

## Configuration

All settings are in [`src/wlingo/config.py`](src/wlingo/config.py):

| Setting | Default | Description |
|---|---|---|
| `TEST_SIZE` | `15` | Number of questions per quiz |
| `SESSION_TIMEOUT_MINUTES` | `120` | Redis session TTL |
| `REDIS_URL` | `redis://localhost:6379/0` | Override via `REDIS_URL` env var |
| `ROOT_PATH` | `""` | URL prefix for reverse-proxy deployments (e.g. `/wlingo`) — see [CLAUDE.md](CLAUDE.md#frontend) for the matching frontend build flag |
| `STATIC_DIR` | `"static"` | Built frontend files (`frontend/dist`) served from here |
| `VOCAB_DIR` | `"vocabulary"` | Vocabulary CSV directory |

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
