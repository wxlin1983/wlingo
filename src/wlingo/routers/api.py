import json
import logging
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, HTTPException, Response
from fastapi.responses import JSONResponse, RedirectResponse

from ..config import settings
from ..globals import vocab_manager
from ..models import AnswerRecord, SessionData
from ..quiz import QuizFactory
from .deps import get_active_session, get_redis, get_session_id, get_user_id

router = APIRouter()
logger = logging.getLogger("wlingo")

VALID_MODES = {"adaptive", "random"}


def _user_stats_key(user_id: str, topic: str) -> str:
    return f"user_stats:{user_id}:{topic}"


@router.get("/api/topics")
def get_topics():
    return vocab_manager.get_topics()


@router.get("/api/session")
def get_session_info(session_data: SessionData | None = Depends(get_active_session)):
    if not session_data:
        return {"active": False}
    next_index = len(session_data.answers)
    completed = next_index >= session_data.total_questions
    return {
        "active": True,
        "completed": completed,
        "topic": session_data.topic,
        "mode": session_data.mode,
        "current_index": next_index,
        "total_questions": session_data.total_questions,
    }


@router.post("/start", response_class=RedirectResponse)
def start_quiz_session(
    topic: str = Form(...),
    mode: str = Form("adaptive"),
    user_id: str | None = Depends(get_user_id),
    redis=Depends(get_redis),
):
    topic = topic.strip()[:100]
    if not vocab_manager.get_words(topic):
        raise HTTPException(status_code=400, detail=f"Unknown topic: {topic!r}")
    mode = mode if mode in VALID_MODES else "adaptive"

    generator = QuizFactory.create(mode, vocab_manager)

    word_weights: dict[str, int] = {}
    if mode == "adaptive" and user_id:
        raw = redis.get(_user_stats_key(user_id, topic))
        if raw:
            word_weights = json.loads(raw)

    prepared_questions = generator.generate(topic, settings.TEST_SIZE, word_weights=word_weights)

    new_id = str(uuid.uuid4())
    session_data = SessionData(
        prepared_questions=prepared_questions,
        correct_count=0,
        total_questions=len(prepared_questions),
        answers=[],
        created_at=datetime.now(),
        topic=topic,
        mode=mode,
    )
    redis.set(
        new_id,
        session_data.model_dump_json(),
        ex=timedelta(minutes=settings.SESSION_TIMEOUT_MINUTES),
    )
    logger.info(f"New session: {new_id} [Topic: {topic}, Mode: {mode}]")

    redirect = RedirectResponse(url="/quiz/0", status_code=302)
    redirect.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=new_id,
        httponly=True,
        samesite="Lax",
    )
    return redirect


@router.get("/api/quiz/{index}")
def get_question_data(
    index: int, session_data: SessionData | None = Depends(get_active_session)
):
    if not session_data:
        return JSONResponse({"error": "Session invalid"}, status_code=401)
    if not (0 <= index < session_data.total_questions):
        return JSONResponse({"error": "Index error"}, status_code=404)

    current_q = session_data.prepared_questions[index]
    # None when not yet answered; lets the frontend show review state for revisited questions
    record = session_data.answers[index] if index < len(session_data.answers) else None

    return {
        "word": current_q.word,
        "options": current_q.options,
        "current_index": index,
        "total_questions": session_data.total_questions,
        "answer_record": record,
    }


@router.post("/submit_answer", response_model=AnswerRecord)
def submit_answer(
    selected_option_index: int = Form(...),
    current_index: int = Form(...),
    session_id: str | None = Depends(get_session_id),
    session_data: SessionData | None = Depends(get_active_session),
    user_id: str | None = Depends(get_user_id),
    redis=Depends(get_redis),
):
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
    )
    session_data.answers.append(record)
    redis.set(
        session_id,
        session_data.model_dump_json(),
        ex=timedelta(minutes=settings.SESSION_TIMEOUT_MINUTES),
    )

    # Track wrong answers for adaptive mode; "standard" treated as alias for backward compat
    if session_data.mode in ("adaptive", "standard") and user_id:
        _update_user_stats(redis, user_id, session_data.topic, current_q.word, is_correct)

    return record


def _update_user_stats(redis, user_id: str, topic: str, word: str, is_correct: bool) -> None:
    key = _user_stats_key(user_id, topic)
    raw = redis.get(key)
    stats: dict[str, int] = json.loads(raw) if raw else {}

    if is_correct:
        stats.pop(word, None)
    else:
        stats[word] = stats.get(word, 0) + 1

    if stats:
        redis.set(key, json.dumps(stats), ex=timedelta(days=settings.USER_STATS_TTL_DAYS))
    else:
        # Avoid persisting empty dicts when all words are mastered
        redis.delete(key)


@router.get("/api/result")
def get_result_data(session_data: SessionData | None = Depends(get_active_session)):
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


@router.post("/api/reset")
def reset_session(
    response: Response,
    session_id: str | None = Depends(get_session_id),
    redis=Depends(get_redis),
):
    if session_id:
        redis.delete(session_id)
    response.delete_cookie(settings.SESSION_COOKIE_NAME)
    return {"status": "success"}


@router.post("/api/admin/reload-vocab")
def reload_vocab():
    vocab_manager.load_all()
    topics = vocab_manager.get_topics()
    return {"loaded": len(topics), "topics": [t["id"] for t in topics]}
