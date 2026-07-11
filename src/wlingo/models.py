from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import AwareDatetime, BaseModel

QuizType = Literal["multiple_choice", "spelling", "translation"]


class Word(TypedDict):
    word: str
    translation: str
    explanation: str


class Topic(TypedDict):
    id: str
    name: str
    count: int
    quiz_type: str


# --- Models ---
class Question(BaseModel):
    word: str
    translation: str
    options: list[str] = []
    explanation: str = ""
    quiz_type: str = "multiple_choice"
    romaji_input: bool = False
    hangul_input: bool = False


class AnswerRecord(BaseModel):
    word: str
    user_answer: str
    correct_answer: str
    is_correct: bool
    explanation: str = ""


class SessionData(BaseModel):
    prepared_questions: list[Question]
    correct_count: int
    total_questions: int
    answers: list[AnswerRecord]
    # Aware (UTC) so expiry math in deps.py is well-defined; pre-existing
    # sessions with naive timestamps fail validation and are dropped.
    created_at: AwareDatetime
    topic: str
    mode: str = "adaptive"
    quiz_type: str = "multiple_choice"
