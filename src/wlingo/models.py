from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from pydantic import BaseModel


class Word(TypedDict):
    word: str
    translation: str


class Topic(TypedDict):
    id: str
    name: str
    count: int


# --- Models ---
class Question(BaseModel):
    word: str
    translation: str
    options: list[str]


class SessionData(BaseModel):
    prepared_questions: list[Question]
    correct_count: int
    total_questions: int
    answers: list[AnswerRecord]
    created_at: datetime
    topic: str
    mode: str = "standard"


class AnswerRecord(BaseModel):
    word: str
    user_answer: str
    correct_answer: str
    is_correct: bool
    attempted: bool
