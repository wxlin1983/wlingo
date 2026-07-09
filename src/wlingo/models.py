from __future__ import annotations

from datetime import datetime
from typing import Literal, TypedDict

from pydantic import BaseModel

QuizType = Literal["multiple_choice", "spelling"]


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
    created_at: datetime
    topic: str
    mode: str = "standard"
    quiz_type: str = "multiple_choice"
