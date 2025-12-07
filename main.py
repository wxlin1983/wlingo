import pandas as pd
import random
import json
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import List, Dict, Optional, Any
from urllib.parse import quote

# --- Configuration ---
app = FastAPI()
templates = Jinja2Templates(directory="templates")
WORDS_FILE = "words.csv"
TEST_SIZE = 15

# Global storage for quiz data and session management
ALL_WORDS: List[Dict[str, str]] = []
user_sessions: Dict[str, Dict] = {}
SESSION_ID = "test_session"


# --- Core Logic Functions ---


def load_words() -> List[Dict[str, str]]:
    """Loads the word list from the CSV file."""
    try:
        df = pd.read_csv(WORDS_FILE, encoding="utf-8")
        return df.to_dict("records")
    except FileNotFoundError:
        print(f"ERROR: File {WORDS_FILE} not found. Using dummy data.")
        # Fallback dummy data structure
        dummy_data = {
            "word": ["Hund", "Katze", "Baum", "Haus", "Wasser"],
            "translation": ["dog", "cat", "tree", "house", "water"],
        }
        df_dummy = pd.DataFrame(dummy_data)
        return df_dummy.to_dict("records")


def get_test_words() -> List[Dict[str, str]]:
    """Randomly selects TEST_SIZE words for the quiz."""
    if not ALL_WORDS:
        return []
    # Use min() to prevent error if fewer words exist than TEST_SIZE
    return random.sample(ALL_WORDS, min(TEST_SIZE, len(ALL_WORDS)))


def generate_options(
    correct_translation: str, all_words: List[Dict[str, str]]
) -> List[str]:
    """Generates four options (one correct, three wrong) for a given translation."""
    if not all_words:
        return [correct_translation]

    incorrect_translations = [
        w["translation"] for w in all_words if w["translation"] != correct_translation
    ]

    if len(incorrect_translations) < 3:
        # If not enough incorrect options exist, pad with placeholders
        wrong_options = incorrect_translations
        while len(wrong_options) < 3:
            wrong_options.append("Unknown or Placeholder")
    else:
        wrong_options = random.sample(incorrect_translations, 3)

    options = [correct_translation] + wrong_options
    random.shuffle(options)
    return options


def prepare_quiz_data(
    test_words: List[Dict[str, str]], all_words: List[Dict[str, str]]
) -> List[Dict[str, Any]]:
    """Pre-generates options for all questions in the test list for session consistency."""
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


# --- Application Startup Event ---


@app.on_event("startup")
async def startup_event():
    """Load vocabulary data when the application starts."""
    global ALL_WORDS
    ALL_WORDS = load_words()


# --- Routes ---


@app.get("/", response_class=RedirectResponse)
async def start_quiz():
    """Initializes the quiz session and redirects to the first question."""
    if not ALL_WORDS:
        print("ERROR: Word database is empty.")
        return RedirectResponse(url="/", status_code=500)

    test_words = get_test_words()
    prepared_questions = prepare_quiz_data(test_words, ALL_WORDS)

    # Initialize a new quiz session state
    user_sessions[SESSION_ID] = {
        "test_words": test_words,
        "prepared_questions": prepared_questions,
        "current_index": 0,
        "correct_count": 0,
        "total_questions": len(test_words),
        "answers": [],
    }

    return RedirectResponse(url="/quiz/0", status_code=302)


@app.get("/quiz/{index}", response_class=HTMLResponse)
async def display_question(
    request: Request,
    index: int,
    feedback_data: Optional[str] = None,
):
    """
    Displays a specific question by index.
    Includes logic for feedback display and skipping correctly answered questions.
    """
    session_data = user_sessions.get(SESSION_ID)

    if not session_data:
        return RedirectResponse(url="/", status_code=302)

    total_questions = session_data["total_questions"]

    if index >= total_questions:
        return RedirectResponse(url="/result", status_code=302)

    current_q_data = session_data["prepared_questions"][index]

    # --- Feedback Mode ---
    if feedback_data:
        try:
            feedback = json.loads(feedback_data)
        except json.JSONDecodeError:
            feedback = {
                "is_correct": False,
                "user_answer": "Error",
                "correct_answer": "Error",
            }

        context = {
            "request": request,
            "word": current_q_data["word"],
            "current_index": index,
            "total_questions": total_questions,
            "feedback": feedback,
            "options": [],  # Options hidden during feedback
        }
        return templates.TemplateResponse("index.html", context)

    # --- Standard Question Display/Navigation ---

    # Skip correctly answered questions to the next one pending review/answer
    if (
        index < len(session_data["answers"])
        and session_data["answers"][index]["is_correct"]
    ):
        next_index = len(session_data["answers"])
        if next_index < total_questions:
            return RedirectResponse(url=f"/quiz/{next_index}", status_code=302)
        else:
            return RedirectResponse(url="/result", status_code=302)

    options = current_q_data["options"]

    context = {
        "request": request,
        "word": current_q_data["word"],
        "options": options,
        "current_index": index,
        "total_questions": total_questions,
        "feedback": None,
    }
    return templates.TemplateResponse("index.html", context)


@app.post("/submit_answer", response_class=JSONResponse)
async def submit_answer(
    word: str = Form(...), answer: str = Form(...), current_index: int = Form(...)
):
    """
    Processes the user's answer, records the result, and returns a JSON status.
    The client-side JavaScript handles navigation based on this JSON response.
    """
    session_data = user_sessions.get(SESSION_ID)

    if not session_data or current_index >= session_data["total_questions"]:
        return JSONResponse({"error": "Invalid session or index"}, status_code=400)

    current_q_data = session_data["prepared_questions"][current_index]
    correct_translation = current_q_data["translation"]

    is_correct = answer == correct_translation

    # Store answer only if this question hasn't been recorded yet
    if current_index >= len(session_data["answers"]):
        if is_correct:
            session_data["correct_count"] += 1

        session_data["answers"].append(
            {
                "word": word,
                "user_answer": answer,
                "correct_answer": correct_translation,
                "is_correct": is_correct,
            }
        )

    return JSONResponse(
        {
            "is_correct": is_correct,
            "current_index": current_index,
            "next_index": current_index + 1,
            "total_questions": session_data["total_questions"],
            "user_answer": answer,
            "correct_answer": correct_translation,
        }
    )


# --- Result Route ---


@app.get("/result", response_class=HTMLResponse)
async def show_result(request: Request):
    """Displays the final quiz result page."""
    session_data = user_sessions.get(SESSION_ID)

    # Ensure the quiz is complete before showing results
    if (
        not session_data
        or len(session_data["answers"]) < session_data["total_questions"]
    ):
        return RedirectResponse(url="/", status_code=302)

    correct_count = session_data["correct_count"]
    total_questions = session_data["total_questions"]

    context = {
        "request": request,
        "correct_count": correct_count,
        "total_questions": total_questions,
        "score_percentage": int((correct_count / total_questions) * 100),
        "answers": session_data["answers"],
    }

    return templates.TemplateResponse("result.html", context)


# --- Run Application ---
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
