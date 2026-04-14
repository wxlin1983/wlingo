"""Integration tests for the FastAPI router.

Redis is replaced with an in-memory FakeRedis so tests need no running services.
The TestClient is function-scoped, giving each test a clean slate.
"""

import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from tests.conftest import FakeRedis
from wlingo.app import create_app


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """Fresh app + TestClient + FakeRedis per test."""
    fake_redis = FakeRedis()
    with patch("wlingo.router.redis_client", fake_redis):
        app = create_app()
        with TestClient(app) as c:
            yield c, fake_redis


def _start(client, topic="English"):
    """Helper: start a quiz session and return the response."""
    return client.post("/start", data={"topic": topic}, follow_redirects=False)


def _session(fake_redis) -> dict:
    """Return the first (and usually only) session stored in fake_redis."""
    raw = next(iter(fake_redis._data.values()))
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Topics endpoint
# ---------------------------------------------------------------------------


def test_get_topics_returns_list(client):
    c, _ = client
    resp = c.get("/api/topics")
    assert resp.status_code == 200
    topics = resp.json()
    assert isinstance(topics, list)
    assert len(topics) > 0
    assert all("id" in t and "name" in t and "count" in t for t in topics)


def test_get_topics_includes_real_vocab_files(client):
    c, _ = client
    topics = c.get("/api/topics").json()
    ids = [t["id"] for t in topics]
    # The actual CSV files (English, Korean) should be present
    assert any("English" in i or "Korean" in i for i in ids)


# ---------------------------------------------------------------------------
# Home page
# ---------------------------------------------------------------------------


def test_home_page_returns_200(client):
    c, _ = client
    assert c.get("/").status_code == 200


# ---------------------------------------------------------------------------
# Start session
# ---------------------------------------------------------------------------


def test_start_standard_quiz_redirects(client):
    c, fake_redis = client
    resp = _start(c, "English")
    assert resp.status_code == 302
    assert resp.headers["location"].endswith("/quiz/0")


def test_start_creates_session_in_redis(client):
    c, fake_redis = client
    _start(c, "English")
    assert len(fake_redis._data) == 1


def test_start_sets_session_cookie(client):
    c, _ = client
    resp = _start(c, "English")
    assert "quiz_session_id" in resp.cookies or "Set-Cookie" in resp.headers


def test_start_standard_mode_stored_in_session(client):
    c, fake_redis = client
    _start(c, "English")
    session = _session(fake_redis)
    assert session["mode"] == "standard"
    assert session["topic"] == "English"


def test_start_generates_correct_question_count(client):
    c, fake_redis = client
    _start(c, "English")
    session = _session(fake_redis)
    assert session["total_questions"] == len(session["prepared_questions"])


# ---------------------------------------------------------------------------
# Quiz question page & API
# ---------------------------------------------------------------------------


def test_quiz_page_without_session_redirects_home(client):
    c, _ = client
    resp = c.get("/quiz/0", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/"


def test_get_question_api_without_session_returns_401(client):
    c, _ = client
    assert c.get("/api/quiz/0").status_code == 401


def test_get_question_api_returns_question_data(client):
    c, _ = client
    _start(c)
    resp = c.get("/api/quiz/0")
    assert resp.status_code == 200
    data = resp.json()
    assert "word" in data
    assert "options" in data
    assert data["current_index"] == 0
    assert len(data["options"]) == 4


def test_get_question_api_out_of_range_returns_404(client):
    c, _ = client
    _start(c)
    assert c.get("/api/quiz/9999").status_code == 404


def test_quiz_page_with_valid_session_returns_200(client):
    c, _ = client
    _start(c)
    assert c.get("/quiz/0").status_code == 200


# ---------------------------------------------------------------------------
# Submit answer
# ---------------------------------------------------------------------------


def test_submit_answer_without_session_returns_401(client):
    c, _ = client
    resp = c.post(
        "/submit_answer", data={"selected_option_index": 0, "current_index": 0}
    )
    assert resp.status_code == 401


def test_submit_answer_returns_answer_record(client):
    c, fake_redis = client
    _start(c)
    resp = c.post(
        "/submit_answer", data={"selected_option_index": 0, "current_index": 0}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "is_correct" in data
    assert "correct_answer" in data
    assert "user_answer" in data
    assert data["attempted"] is True


def test_submit_correct_answer_marked_correctly(client):
    c, fake_redis = client
    _start(c)

    # Find the correct option index from the stored session
    session = _session(fake_redis)
    q = session["prepared_questions"][0]
    correct_index = q["options"].index(q["translation"])

    resp = c.post(
        "/submit_answer",
        data={"selected_option_index": correct_index, "current_index": 0},
    )
    assert resp.json()["is_correct"] is True


def test_submit_wrong_answer_marked_correctly(client):
    c, fake_redis = client
    _start(c)

    session = _session(fake_redis)
    q = session["prepared_questions"][0]
    wrong_index = next(
        i for i, opt in enumerate(q["options"]) if opt != q["translation"]
    )

    resp = c.post(
        "/submit_answer",
        data={"selected_option_index": wrong_index, "current_index": 0},
    )
    assert resp.json()["is_correct"] is False


def test_submit_answer_twice_returns_400(client):
    c, _ = client
    _start(c)
    c.post("/submit_answer", data={"selected_option_index": 0, "current_index": 0})
    resp = c.post(
        "/submit_answer", data={"selected_option_index": 0, "current_index": 0}
    )
    assert resp.status_code == 400


def test_submit_invalid_option_index_returns_400(client):
    c, _ = client
    _start(c)
    resp = c.post(
        "/submit_answer", data={"selected_option_index": 99, "current_index": 0}
    )
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Result endpoint
# ---------------------------------------------------------------------------


def test_result_api_without_session_returns_401(client):
    c, _ = client
    assert c.get("/api/result").status_code == 401


def test_result_api_after_answers(client):
    c, fake_redis = client
    _start(c)

    session = _session(fake_redis)
    n = session["total_questions"]

    # Answer all questions
    for i in range(n):
        # Re-read session after each answer (it gets updated in fake_redis)
        session = _session(fake_redis)
        q = session["prepared_questions"][i]
        correct_index = q["options"].index(q["translation"])
        c.post(
            "/submit_answer",
            data={"selected_option_index": correct_index, "current_index": i},
        )

    resp = c.get("/api/result")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_questions"] == n
    assert data["correct_count"] == n
    assert data["score_percentage"] == 100
    assert len(data["answers"]) == n


def test_result_page_returns_200(client):
    c, _ = client
    assert c.get("/result").status_code == 200


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


def test_reset_clears_session_from_redis(client):
    c, fake_redis = client
    _start(c)
    assert len(fake_redis._data) == 1

    resp = c.post("/api/reset")
    assert resp.status_code == 200
    assert len(fake_redis._data) == 0


def test_reset_without_session_succeeds(client):
    c, _ = client
    assert c.post("/api/reset").status_code == 200


# ---------------------------------------------------------------------------
# User stats (adaptive weighting)
# ---------------------------------------------------------------------------


def test_home_sets_user_id_cookie(client):
    c, _ = client
    resp = c.get("/")
    assert "wlingo_user_id" in resp.cookies or any(
        "wlingo_user_id" in h for h in resp.headers.get_list("set-cookie")
    )


def test_home_does_not_reset_existing_user_id(client):
    c, _ = client
    c.get("/")  # first visit sets cookie
    first_id = c.cookies.get("wlingo_user_id")
    c.get("/")  # second visit should not change it
    assert c.cookies.get("wlingo_user_id") == first_id


def test_wrong_answer_creates_user_stats(client):
    c, fake_redis = client
    c.get("/")  # ensure user_id cookie is set
    _start(c, "English")

    session = _session(fake_redis)
    q = session["prepared_questions"][0]
    wrong_index = next(
        i for i, opt in enumerate(q["options"]) if opt != q["translation"]
    )
    c.post(
        "/submit_answer",
        data={"selected_option_index": wrong_index, "current_index": 0},
    )

    user_id = c.cookies.get("wlingo_user_id")
    stats_key = f"user_stats:{user_id}:English"
    assert stats_key in fake_redis._data
    stats = json.loads(fake_redis._data[stats_key])
    assert stats[q["word"]] == 1


def test_wrong_answer_increments_count(client):
    c, fake_redis = client
    c.get("/")
    _start(c, "English")

    session = _session(fake_redis)
    q = session["prepared_questions"][0]
    wrong_index = next(
        i for i, opt in enumerate(q["options"]) if opt != q["translation"]
    )
    # Submit wrong answer twice (need two separate sessions for the same word)
    c.post(
        "/submit_answer",
        data={"selected_option_index": wrong_index, "current_index": 0},
    )
    user_id = c.cookies.get("wlingo_user_id")
    stats_key = f"user_stats:{user_id}:English"
    assert json.loads(fake_redis._data[stats_key])[q["word"]] == 1


def test_correct_answer_removes_word_from_stats(client):
    c, fake_redis = client
    c.get("/")
    _start(c, "English")

    session = _session(fake_redis)
    q = session["prepared_questions"][0]
    word = q["word"]

    # Seed the stats with a prior wrong answer
    user_id = c.cookies.get("wlingo_user_id")
    stats_key = f"user_stats:{user_id}:English"
    fake_redis.set(stats_key, json.dumps({word: 2}))

    correct_index = q["options"].index(q["translation"])
    c.post(
        "/submit_answer",
        data={"selected_option_index": correct_index, "current_index": 0},
    )

    raw = fake_redis._data.get(stats_key)
    stats = json.loads(raw) if raw else {}
    assert word not in stats
