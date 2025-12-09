import pandas as pd
import random
import uuid
import logging
from fastapi import (
    FastAPI,
    Request,
    Form,
    Response,
    Cookie,
    Depends,
)
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import List, Dict, Optional, Any
from fastapi.staticfiles import StaticFiles
from logging.handlers import RotatingFileHandler

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Persist logs to a rotating file.
LOG_FILE = "lingo.log"
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5_000_000, backupCount=3)
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(name)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


# --- Setup ---
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Constants & State ---
WORDS_FILE = "vocabulary/words.csv"
TEST_SIZE = 15
SESSION_COOKIE_NAME = "quiz_session_id"

# In-memory storage for words and user sessions.
# In a production environment, this would be a database.
ALL_WORDS: List[Dict[str, str]] = []
user_sessions: Dict[str, Dict] = {}


# --- Core Logic ---
def load_words() -> List[Dict[str, str]]:
    """Loads words from the CSV, with a fallback to dummy data."""
    try:
        df = pd.read_csv(WORDS_FILE, encoding="utf-8")
        logger.info(f"Loaded {len(df)} words from {WORDS_FILE}.")
        return df.to_dict("records")
    except FileNotFoundError:
        logger.warning(f"'{WORDS_FILE}' not found. Using dummy data.")
        return [
            {"word": "Hund", "translation": "dog"},
            {"word": "Katze", "translation": "cat"},
            {"word": "Baum", "translation": "tree"},
            {"word": "Haus", "translation": "house"},
            {"word": "Wasser", "translation": "water"},
        ]


def get_test_words() -> List[Dict[str, str]]:
    """Selects a random sample of words for a quiz."""
    if not ALL_WORDS:
        return []
    return random.sample(ALL_WORDS, min(TEST_SIZE, len(ALL_WORDS)))


def generate_options(
    correct_translation: str, all_words: List[Dict[str, str]]
) -> List[str]:
    """Creates a list of 4 multiple-choice options, one of which is correct."""
    incorrect_translations = [
        w["translation"] for w in all_words if w["translation"] != correct_translation
    ]

    # Ensure there are always 3 incorrect options.
    if len(incorrect_translations) < 3:
        wrong_options = incorrect_translations
        while len(wrong_options) < 3:
            wrong_options.append(f"Option {len(wrong_options) + 1}")
    else:
        wrong_options = random.sample(incorrect_translations, 3)

    options = [correct_translation] + wrong_options
    random.shuffle(options)
    return options


def prepare_quiz_data(
    test_words: List[Dict[str, str]], all_words: List[Dict[str, str]]
) -> List[Dict[str, Any]]:
    """Pre-generates all questions and their options for a single quiz session."""
    prepared_questions = []
    for item in test_words:
        correct_translation = item["translation"]
        options = generate_options(correct_translation, all_words)
        prepared_questions.append(
            {
                "word": item["word"],
                "translation": correct_translation,
                "options": options,
            }
        )
    return prepared_questions


# --- Dependencies ---
def get_session_id(session_id: Optional[str] = Cookie(None, alias=SESSION_COOKIE_NAME)):
    """FastAPI dependency to extract the session ID from a cookie."""
    return session_id


# --- Lifecycle Events ---
@app.on_event("startup")
async def startup_event():
    """Loads the vocabulary from the CSV file when the application starts."""
    global ALL_WORDS
    logger.info("Application startup: loading vocabulary.")
    ALL_WORDS = load_words()
    logger.info("Vocabulary loaded.")


# --- Routes ---
@app.get("/", response_class=RedirectResponse)
async def start_quiz(
    response: Response, session_id: Optional[str] = Depends(get_session_id)
):
    """
    Handles the start of the quiz.

    If a session cookie exists, it redirects to the first question.
    Otherwise, it creates a new session, sets a cookie, and then redirects.
    """
    if not ALL_WORDS:
        logger.error("Word database is empty. Cannot start quiz.")
        return HTMLResponse("<h1>Error: Word database is empty.</h1>", status_code=500)

    # If session is active, redirect to the current question.
    if session_id in user_sessions:
        logger.info(f"Existing session found: {session_id}. Redirecting.")
        return RedirectResponse(url="/quiz/0", status_code=302)

    # Create a new session if one doesn't exist.
    new_session_id = str(uuid.uuid4())
    test_words = get_test_words()
    prepared_questions = prepare_quiz_data(test_words, ALL_WORDS)

    user_sessions[new_session_id] = {
        "prepared_questions": prepared_questions,
        "correct_count": 0,
        "total_questions": len(test_words),
        "answers": [],
    }

    logger.info(f"Created new session: {new_session_id}")
    response.set_cookie(
        key=SESSION_COOKIE_NAME, value=new_session_id, httponly=True, samesite="Lax"
    )

    # Redirect to the first question.
    return RedirectResponse(url="/quiz/0", status_code=302, headers=response.headers)


@app.get("/api/quiz/{index}", response_class=JSONResponse)
async def get_question_data(index: int, session_id: str = Depends(get_session_id)):
    """API endpoint to fetch data for a single quiz question."""
    session_data = user_sessions.get(session_id)
    if not session_data:
        return JSONResponse({"error": "Session invalid"}, status_code=401)

    total_questions = session_data["total_questions"]
    if not (0 <= index < total_questions):
        return JSONResponse({"error": "Question index out of bounds"}, status_code=404)

    current_q_data = session_data["prepared_questions"][index]

    # Include previous answer if it exists.
    answer_record = None
    if index < len(session_data["answers"]):
        answer_record = session_data["answers"][index]

    return {
        "word": current_q_data["word"],
        "options": current_q_data["options"],
        "current_index": index,
        "total_questions": total_questions,
        "answer_record": answer_record,
    }


@app.get("/quiz/{index}", response_class=HTMLResponse)
async def display_question_page(
    request: Request, index: int, session_id: str = Depends(get_session_id)
):
    """
    Displays the main quiz page.

    This route serves the HTML skeleton. The page then uses JavaScript
    to fetch the question data from the `/api/quiz/{index}` endpoint.
    """
    session_data = user_sessions.get(session_id)

    # If session is invalid or quiz is over, redirect appropriately.
    if not session_data:
        return RedirectResponse(url="/", status_code=302)
    if index >= session_data["total_questions"]:
        return RedirectResponse(url="/result", status_code=302)

    return templates.TemplateResponse(
        "index.html", {"request": request, "current_index": index}
    )


@app.post("/submit_answer", response_class=JSONResponse)
async def submit_answer(
    answer: str = Form(...),
    current_index: int = Form(...),
    session_id: str = Depends(get_session_id),
):
    """
    Accepts a user's answer submission via AJAX.

    It validates the answer, updates the session score, and records the
    result. Prevents re-submission for an already answered question.
    """
    session_data = user_sessions.get(session_id)
    if not session_data or not (0 <= current_index < session_data["total_questions"]):
        return JSONResponse({"error": "Invalid session or index"}, status_code=401)

    # Prevent re-submission.
    if current_index < len(session_data["answers"]):
        return JSONResponse({"error": "Question already answered"}, status_code=400)

    current_q_data = session_data["prepared_questions"][current_index]
    correct_translation = current_q_data["translation"]
    word = current_q_data["word"]
    is_correct = answer == correct_translation

    if is_correct:
        session_data["correct_count"] += 1

    logger.info(
        f"Session {session_id} Q{current_index}: Answer for '{word}' was {'CORRECT' if is_correct else 'INCORRECT'}."
    )

    record = {
        "word": word,
        "user_answer": answer,
        "correct_answer": correct_translation,
        "is_correct": is_correct,
        "attempted": True,
    }
    session_data["answers"].append(record)

    return JSONResponse(record)


# 1. NEW: API Endpoint to get result data (JSON)
@app.get("/api/result", response_class=JSONResponse)
async def get_result_data(session_id: str = Depends(get_session_id)):
    session_data = user_sessions.get(session_id)

    if not session_data:
        return JSONResponse({"error": "Session invalid"}, status_code=401)

    answers = session_data["answers"]
    total_questions = session_data["total_questions"]

    # Calculate score
    correct_count = sum(1 for a in answers if a["is_correct"])
    score_percentage = 0
    if total_questions > 0:
        score_percentage = round((correct_count / total_questions) * 100)

    return {
        "correct_count": correct_count,
        "total_questions": total_questions,
        "score_percentage": score_percentage,
        "answers": answers,
    }


# 2. MODIFIED: View Route (Returns Skeleton HTML)
@app.get("/result", response_class=HTMLResponse)
async def result_page(request: Request):
    # No data passed to Jinja context, just the request
    return templates.TemplateResponse("result.html", {"request": request})


# Add this new endpoint to main.py
@app.post("/api/reset")
async def reset_session(session_id: str = Depends(get_session_id)):
    # Remove the session data if it exists
    if session_id in user_sessions:
        del user_sessions[session_id]
        # Alternatively, if you want to keep the ID but reset data:
        # user_sessions[session_id] = { "questions": generate_questions(), "answers": [], ... }

    return {"status": "success"}


# --- Main ---
if __name__ == "__main__":
    import uvicorn

    logger.info("Starting application server.")
    uvicorn.run(app, host="0.0.0.0", port=8000)
