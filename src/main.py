import logging
import os
import random
import uuid
import glob
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from typing import Dict, List, Optional, Any

import pandas as pd
import uvicorn
from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    Form,
    Request,
    Response,
)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel


class Question(BaseModel):
    word: str
    translation: str
    options: List[str]


class SessionData(BaseModel):
    prepared_questions: List[Question]
    correct_count: int
    total_questions: int
    answers: List[Dict[str, Any]]
    created_at: datetime
    topic: str  # Selected vocabulary set


class AnswerRecord(BaseModel):
    word: str
    user_answer: str
    correct_answer: str
    is_correct: bool
    attempted: bool


# --- Configuration ---
class Settings:
    PROJECT_NAME: str = "wlingo"
    DEBUG: bool = False
    LOG_DIR: str = "log"
    LOG_FILE: str = "wlingo.log"
    VOCAB_DIR: str = "vocabulary"
    TEST_SIZE: int = 15
    SESSION_COOKIE_NAME: str = "quiz_session_id"
    SESSION_TIMEOUT_MINUTES: int = 120


settings = Settings()

# --- Logging Setup ---
if not os.path.exists(settings.LOG_DIR):
    os.makedirs(settings.LOG_DIR)
log_path = os.path.join(settings.LOG_DIR, settings.LOG_FILE)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
file_handler = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=3)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
logger.addHandler(file_handler)

app = FastAPI(title=settings.PROJECT_NAME, debug=settings.DEBUG)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Storage ---
# Key: filename (e.g., 'german_basic'), Value: word list
ALL_VOCAB_SETS: Dict[str, List[Dict[str, str]]] = {}
sessions: Dict[str, SessionData] = {}

# --- Core Logic ---


def load_all_vocabularies():
    """Load all .csv files from the vocabulary directory."""
    global ALL_VOCAB_SETS
    ALL_VOCAB_SETS = {}

    # Ensure directory exists
    if not os.path.exists(settings.VOCAB_DIR):
        os.makedirs(settings.VOCAB_DIR)
        logger.warning(f"Created directory {settings.VOCAB_DIR}. Please add CSV files.")
        return

    # Find all CSV files
    csv_files = glob.glob(os.path.join(settings.VOCAB_DIR, "*.csv"))

    for file_path in csv_files:
        try:
            # Use filename as ID
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            df = pd.read_csv(file_path, encoding="utf-8")

            # Validate columns
            if "word" in df.columns and "translation" in df.columns:
                ALL_VOCAB_SETS[file_name] = df.to_dict("records")
                logger.info(f"Loaded {len(df)} words from {file_name}")
            else:
                logger.error(
                    f"Skipping {file_name}: Missing 'word' or 'translation' columns."
                )

        except Exception as e:
            logger.error(f"Failed to load {file_path}: {e}")

    # Fallback to dummy data if no files found
    if not ALL_VOCAB_SETS:
        logger.warning("No valid CSV files found. Loading dummy data.")
        ALL_VOCAB_SETS["default_dummy"] = [
            {"word": "Hund", "translation": "dog"},
            {"word": "Katze", "translation": "cat"},
            {"word": "Baum", "translation": "tree"},
        ]


def get_test_words(topic: str) -> List[Dict[str, str]]:
    """Select random words based on topic."""
    word_list = ALL_VOCAB_SETS.get(topic, [])
    if not word_list:
        return []
    return random.sample(word_list, min(settings.TEST_SIZE, len(word_list)))


def generate_options(correct_translation: str, topic: str) -> List[str]:
    """Generate options from the specific topic."""
    word_list = ALL_VOCAB_SETS.get(topic, [])
    all_translations = {w["translation"] for w in word_list}
    all_translations.discard(correct_translation)

    num_options_to_generate = 3
    if len(all_translations) < num_options_to_generate:
        incorrect_options = list(all_translations)
        while len(incorrect_options) < num_options_to_generate:
            incorrect_options.append(f"Option {len(incorrect_options)+1}")
    else:
        incorrect_options = random.sample(
            list(all_translations), num_options_to_generate
        )

    options = [correct_translation] + incorrect_options
    random.shuffle(options)
    return options


def prepare_quiz_data(test_words: List[Dict[str, str]], topic: str) -> List[Question]:
    return [
        Question(
            word=item["word"],
            translation=item["translation"],
            options=generate_options(item["translation"], topic),
        )
        for item in test_words
    ]


def get_active_session(session_id: str) -> Optional[SessionData]:
    if not session_id or session_id not in sessions:
        return None
    session = sessions[session_id]
    if datetime.now() - session.created_at > timedelta(
        minutes=settings.SESSION_TIMEOUT_MINUTES
    ):
        del sessions[session_id]
        return None
    return session


def get_session_id(
    session_id: Optional[str] = Cookie(None, alias=settings.SESSION_COOKIE_NAME)
) -> Optional[str]:
    return session_id


# --- Lifecycle ---
@app.on_event("startup")
async def startup_event():
    load_all_vocabularies()


# --- Routes ---


# API: Return vocabulary topics
@app.get("/api/topics")
async def get_topics():
    """Returns a list of available vocabulary sets."""
    topics = []
    if not ALL_VOCAB_SETS:
        # Return default if empty
        return [{"id": "default_dummy", "name": "Default Demo Set", "count": 5}]

    for key in ALL_VOCAB_SETS.keys():
        display_name = key.replace("_", " ").title()
        topics.append(
            {"id": key, "name": display_name, "count": len(ALL_VOCAB_SETS[key])}
        )

    # Sort by name
    topics.sort(key=lambda x: x["name"])
    return topics


# Serve start page
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serves the welcome page skeleton."""
    return templates.TemplateResponse("start.html", {"request": request})


# Create session with selected topic
@app.post("/start", response_class=RedirectResponse)
async def start_quiz_session(
    response: Response, topic: str = Form(...)  # Topic from form
):
    # Validate topic
    if topic not in ALL_VOCAB_SETS:
        # Default to first if invalid
        topic = list(ALL_VOCAB_SETS.keys())[0] if ALL_VOCAB_SETS else "default_dummy"

    new_id = str(uuid.uuid4())
    test_words = get_test_words(topic)
    prepared_questions = prepare_quiz_data(test_words, topic)

    sessions[new_id] = SessionData(
        prepared_questions=prepared_questions,
        correct_count=0,
        total_questions=len(prepared_questions),
        answers=[],
        created_at=datetime.now(),
        topic=topic,  # Record selected topic
    )

    logger.info(f"New session started: {new_id} [Topic: {topic}]")

    redirect = RedirectResponse(url="/quiz/0", status_code=302)
    redirect.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=new_id,
        httponly=True,
        samesite="Lax",
    )
    return redirect


@app.get("/api/quiz/{index}")
async def get_question_data(index: int, session_id: str = Depends(get_session_id)):
    session_data = get_active_session(session_id)
    if not session_data:
        return JSONResponse({"error": "Session invalid"}, status_code=401)
    if not (0 <= index < session_data.total_questions):
        return JSONResponse({"error": "Index error"}, status_code=404)

    current_q = session_data.prepared_questions[index]
    record = session_data.answers[index] if index < len(session_data.answers) else None

    return {
        "word": current_q.word,
        "options": current_q.options,
        "current_index": index,
        "total_questions": session_data.total_questions,
        "answer_record": record,
    }


@app.get("/quiz/{index}", response_class=HTMLResponse)
async def display_question_page(
    request: Request, index: int, session_id: str = Depends(get_session_id)
):
    session_data = get_active_session(session_id)
    if not session_data:
        return RedirectResponse(url="/", status_code=302)
    if index >= session_data.total_questions:
        return RedirectResponse(url="/result", status_code=302)
    return templates.TemplateResponse(
        "quiz.html", {"request": request, "current_index": index}
    )


@app.post("/submit_answer", response_model=AnswerRecord)
async def submit_answer(
    selected_option_index: int = Form(...),
    current_index: int = Form(...),
    session_id: str = Depends(get_session_id),
):
    session_data = get_active_session(session_id)
    if not session_data or not (0 <= current_index < session_data.total_questions):
        return JSONResponse({"error": "Invalid session"}, status_code=401)
    if current_index < len(session_data.answers):
        return JSONResponse({"error": "Already answered"}, status_code=400)

    current_q = session_data.prepared_questions[current_index]
    if not (0 <= selected_option_index < len(current_q.options)):
        return JSONResponse({"error": "Invalid option"}, status_code=400)

    user_answer_str = current_q.options[selected_option_index]
    is_correct = user_answer_str == current_q.translation

    if is_correct:
        session_data.correct_count += 1

    record = AnswerRecord(
        word=current_q.word,
        user_answer=user_answer_str,
        correct_answer=current_q.translation,
        is_correct=is_correct,
        attempted=True,
    )
    session_data.answers.append(record)
    return record


@app.get("/api/result")
async def get_result_data(session_id: str = Depends(get_session_id)):
    session_data = get_active_session(session_id)
    if not session_data:
        return JSONResponse({"error": "Session invalid"}, status_code=401)

    total = session_data.total_questions
    score = round((session_data.correct_count / total) * 100) if total > 0 else 0
    return {
        "correct_count": session_data.correct_count,
        "total_questions": total,
        "score_percentage": score,
        "answers": session_data.answers,
    }


@app.get("/result", response_class=HTMLResponse)
async def result_page(request: Request):
    return templates.TemplateResponse("result.html", {"request": request})


@app.post("/api/reset")
async def reset_session(response: Response, session_id: str = Depends(get_session_id)):
    if session_id in sessions:
        del sessions[session_id]
    response.delete_cookie(settings.SESSION_COOKIE_NAME)
    return {"status": "success"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
