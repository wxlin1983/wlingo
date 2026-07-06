"""Integration tests for the FastAPI router.

Redis is replaced with fakeredis so tests need no running services.
The TestClient is function-scoped, giving each test a clean slate.
"""

import json
import uuid
from datetime import datetime, timedelta

import fakeredis
import pytest
from fastapi.testclient import TestClient

from wlingo.app import create_app
from wlingo.config import settings
from wlingo.models import Question, SessionData
from wlingo.routers.api import _update_user_stats
from wlingo.routers.deps import get_redis

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """Fresh app + TestClient + fakeredis per test."""
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    app = create_app()
    app.dependency_overrides[get_redis] = lambda: fake_redis
    with TestClient(app) as c:
        yield c, fake_redis


def _start(client, topic="English", mode="adaptive"):
    """Helper: start a quiz session and return the response."""
    return client.post(
        "/start", data={"topic": topic, "mode": mode}, follow_redirects=False
    )


def _session(fake_redis, client) -> dict:
    """Return the session for the current client, looked up by cookie."""
    session_id = client.cookies.get(settings.SESSION_COOKIE_NAME)
    raw = fake_redis.get(session_id)
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


def test_health_check_returns_ok_when_redis_up(client):
    c, _ = client
    resp = c.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_check_returns_503_when_redis_down(client, monkeypatch):
    c, fake_redis = client

    def broken_ping():
        from redis.exceptions import ConnectionError as RedisConnectionError

        raise RedisConnectionError("simulated outage")

    monkeypatch.setattr(fake_redis, "ping", broken_ping)
    resp = c.get("/api/health")
    assert resp.status_code == 503


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
    assert len(list(fake_redis.keys())) == 1


def test_start_sets_session_cookie(client):
    c, _ = client
    resp = _start(c, "English")
    assert "quiz_session_id" in resp.cookies or "Set-Cookie" in resp.headers


def test_session_and_user_cookies_share_the_same_attributes(client):
    c, _ = client
    session_cookie = _start(c, "English").headers.get_list("set-cookie")[0]
    user_cookie = c.get("/", follow_redirects=False).headers.get_list("set-cookie")[0]

    for attr in ("HttpOnly", "SameSite=Lax"):
        assert attr in session_cookie
        assert attr in user_cookie


def test_start_adaptive_mode_stored_in_session(client):
    c, fake_redis = client
    _start(c, "English", mode="adaptive")
    session = _session(fake_redis, c)
    assert session["mode"] == "adaptive"
    assert session["topic"] == "English"


def test_start_random_mode_stored_in_session(client):
    c, fake_redis = client
    _start(c, "English", mode="random")
    session = _session(fake_redis, c)
    assert session["mode"] == "random"


def test_start_invalid_mode_defaults_to_adaptive(client):
    c, fake_redis = client
    c.post("/start", data={"topic": "English", "mode": "bogus"}, follow_redirects=False)
    session = _session(fake_redis, c)
    assert session["mode"] == "adaptive"


def test_start_generates_correct_question_count(client):
    c, fake_redis = client
    _start(c, "English")
    session = _session(fake_redis, c)
    assert session["total_questions"] == len(session["prepared_questions"])


# ---------------------------------------------------------------------------
# Quiz question page & API
# ---------------------------------------------------------------------------


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


def test_get_question_api_negative_index_returns_404(client):
    c, _ = client
    _start(c)
    assert c.get("/api/quiz/-1").status_code == 404


def test_quiz_page_with_valid_session_returns_200(client):
    c, _ = client
    _start(c)
    assert c.get("/quiz/0").status_code == 200


def test_catch_all_serves_spa(client):
    """Non-API paths serve the SPA shell (index.html or minimal fallback)."""
    c, _ = client
    for path in ["/quiz/0", "/quiz/-1", "/result", "/some/unknown/path"]:
        resp = c.get(path)
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]


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


def test_submit_correct_answer_marked_correctly(client):
    c, fake_redis = client
    _start(c)

    # Find the correct option index from the stored session
    session = _session(fake_redis, c)
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

    session = _session(fake_redis, c)
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


def test_submit_answer_out_of_order_returns_400(client):
    c, fake_redis = client
    _start(c)
    # Skip ahead to index 1 before answering index 0.
    resp = c.post(
        "/submit_answer", data={"selected_option_index": 0, "current_index": 1}
    )
    assert resp.status_code == 400
    # The answers list must stay untouched, not corrupted with a
    # misplaced record.
    session = _session(fake_redis, c)
    assert session["answers"] == []


def test_submit_answer_skipping_ahead_after_first_answer_returns_400(client):
    c, fake_redis = client
    _start(c)
    c.post("/submit_answer", data={"selected_option_index": 0, "current_index": 0})
    # Now try to answer index 2, skipping index 1.
    resp = c.post(
        "/submit_answer", data={"selected_option_index": 0, "current_index": 2}
    )
    assert resp.status_code == 400
    session = _session(fake_redis, c)
    assert len(session["answers"]) == 1


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

    session = _session(fake_redis, c)
    n = session["total_questions"]

    # Answer all questions
    for i in range(n):
        # Re-read session after each answer (it gets updated in fake_redis)
        session = _session(fake_redis, c)
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
    assert len(list(fake_redis.keys())) == 1

    resp = c.post("/api/reset")
    assert resp.status_code == 200
    assert len(list(fake_redis.keys())) == 0


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


def test_update_user_stats_survives_concurrent_write(monkeypatch):
    """A concurrent writer touching the stats key between our read and our
    write must not be silently clobbered (the pre-fix GET->mutate->SET
    pattern would have lost this update)."""
    fake_redis = fakeredis.FakeRedis(decode_responses=True)
    key = "user_stats:user1:English"
    pipe = fake_redis.pipeline()
    original_multi = pipe.multi
    calls = {"n": 0}

    def flaky_multi(*args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            # Simulate another request writing to this key right after our
            # WATCH/GET but before our MULTI/EXEC.
            fake_redis.set(key, json.dumps({"interloper": 1}))
        return original_multi(*args, **kwargs)

    monkeypatch.setattr(pipe, "multi", flaky_multi)
    monkeypatch.setattr(fake_redis, "pipeline", lambda **kw: pipe)

    _update_user_stats(fake_redis, "user1", "English", "hola", is_correct=False)

    assert calls["n"] == 2, "expected exactly one retry after the WatchError"
    stats = json.loads(fake_redis.get(key))
    assert stats == {"interloper": 1, "hola": 1}


def test_wrong_answer_creates_user_stats(client):
    c, fake_redis = client
    c.get("/")  # ensure user_id cookie is set
    _start(c, "English")

    session = _session(fake_redis, c)
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
    assert fake_redis.exists(stats_key)
    stats = json.loads(fake_redis.get(stats_key))
    assert stats[q["word"]] == 1


def test_random_mode_does_not_create_user_stats(client):
    """Random mode skips user-stats tracking."""
    c, fake_redis = client
    c.get("/")
    _start(c, "English", mode="random")

    session = _session(fake_redis, c)
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
    assert not fake_redis.exists(stats_key)


def test_wrong_answer_increments_count(client):
    c, fake_redis = client
    c.get("/")
    user_id = c.cookies.get("wlingo_user_id")

    # First session: wrong answer → count becomes 1
    _start(c, "English")
    session = _session(fake_redis, c)
    q = session["prepared_questions"][0]
    word = q["word"]
    wrong_index = next(
        i for i, opt in enumerate(q["options"]) if opt != q["translation"]
    )
    c.post(
        "/submit_answer",
        data={"selected_option_index": wrong_index, "current_index": 0},
    )

    stats_key = f"user_stats:{user_id}:English"
    assert json.loads(fake_redis.get(stats_key))[word] == 1

    # Seed a second session where the same word appears first
    second_q = Question(word=word, translation=q["translation"], options=q["options"])
    session2 = SessionData(
        prepared_questions=[second_q],
        correct_count=0,
        total_questions=1,
        answers=[],
        created_at=datetime.now(),
        topic="English",
        mode="adaptive",
    )
    session2_id = str(uuid.uuid4())
    fake_redis.set(session2_id, session2.model_dump_json())
    c.cookies.set(settings.SESSION_COOKIE_NAME, session2_id)

    # Wrong answer again → count increments to 2
    c.post(
        "/submit_answer",
        data={"selected_option_index": wrong_index, "current_index": 0},
    )
    assert json.loads(fake_redis.get(stats_key))[word] == 2


def test_correct_answer_removes_word_from_stats(client):
    c, fake_redis = client
    c.get("/")
    _start(c, "English")

    session = _session(fake_redis, c)
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

    raw = fake_redis.get(stats_key)
    stats = json.loads(raw) if raw else {}
    assert word not in stats


def test_correct_answer_deletes_stats_key_when_last_word(client):
    """When the only tracked word is answered correctly, the stats key is removed."""
    c, fake_redis = client
    c.get("/")
    _start(c, "English")

    session = _session(fake_redis, c)
    q = session["prepared_questions"][0]
    word = q["word"]

    user_id = c.cookies.get("wlingo_user_id")
    stats_key = f"user_stats:{user_id}:English"
    fake_redis.set(stats_key, json.dumps({word: 1}))

    correct_index = q["options"].index(q["translation"])
    c.post(
        "/submit_answer",
        data={"selected_option_index": correct_index, "current_index": 0},
    )

    assert not fake_redis.exists(stats_key)


# ---------------------------------------------------------------------------
# Session expiry
# ---------------------------------------------------------------------------


def _inject_session(fake_redis, client, created_at: datetime, topic: str = "English"):
    """Insert a synthetic SessionData into fake_redis and set the cookie."""
    q = Question(word="test", translation="测试", options=["测试", "a", "b", "c"])
    session = SessionData(
        prepared_questions=[q],
        correct_count=0,
        total_questions=1,
        answers=[],
        created_at=created_at,
        topic=topic,
        mode="adaptive",
    )
    session_id = str(uuid.uuid4())
    fake_redis.set(session_id, session.model_dump_json())
    client.cookies.set(settings.SESSION_COOKIE_NAME, session_id)
    return session_id


def test_expired_session_returns_401(client):
    c, fake_redis = client
    expired_at = datetime.now() - timedelta(
        minutes=settings.SESSION_TIMEOUT_MINUTES + 1
    )
    _inject_session(fake_redis, c, created_at=expired_at)

    assert c.get("/api/quiz/0").status_code == 401


def test_expired_session_is_deleted_from_redis(client):
    c, fake_redis = client
    expired_at = datetime.now() - timedelta(
        minutes=settings.SESSION_TIMEOUT_MINUTES + 1
    )
    session_id = _inject_session(fake_redis, c, created_at=expired_at)

    c.get("/api/quiz/0")

    assert not fake_redis.exists(session_id)


# ---------------------------------------------------------------------------
# Malformed Redis payloads
# ---------------------------------------------------------------------------


def test_corrupt_session_payload_treated_as_no_session(client):
    c, fake_redis = client
    session_id = str(uuid.uuid4())
    fake_redis.set(session_id, "not valid json at all")
    c.cookies.set(settings.SESSION_COOKIE_NAME, session_id)

    resp = c.get("/api/session")
    assert resp.status_code == 200
    assert resp.json()["active"] is False


def test_corrupt_session_payload_is_deleted_from_redis(client):
    c, fake_redis = client
    session_id = str(uuid.uuid4())
    fake_redis.set(session_id, "not valid json at all")
    c.cookies.set(settings.SESSION_COOKIE_NAME, session_id)

    c.get("/api/session")

    assert not fake_redis.exists(session_id)


def test_corrupt_user_stats_treated_as_empty(client):
    c, fake_redis = client
    user_id = str(uuid.uuid4())
    c.cookies.set(settings.USER_COOKIE_NAME, user_id)
    fake_redis.set(f"user_stats:{user_id}:English", "{not json")

    # Starting an adaptive-mode session reads word_weights from the corrupt
    # key; it should fall back to no weighting instead of 500ing.
    resp = c.post(
        "/start", data={"topic": "English", "mode": "adaptive"}, follow_redirects=False
    )
    assert resp.status_code == 302


# ---------------------------------------------------------------------------
# Input sanitization on /start
# ---------------------------------------------------------------------------


def test_start_with_invalid_topic_returns_400(client):
    c, _ = client
    resp = c.post("/start", data={"topic": "nonexistent_topic"}, follow_redirects=False)
    assert resp.status_code == 400


def test_start_strips_whitespace_from_topic(client):
    c, _ = client
    resp = c.post("/start", data={"topic": "  English  "}, follow_redirects=False)
    assert resp.status_code == 302


# ---------------------------------------------------------------------------
# Session API (resume)
# ---------------------------------------------------------------------------


def test_session_api_no_active_session(client):
    c, _ = client
    resp = c.get("/api/session")
    assert resp.status_code == 200
    assert resp.json()["active"] is False


def test_session_api_with_active_session(client):
    c, fake_redis = client
    _start(c, "English")
    resp = c.get("/api/session")
    assert resp.status_code == 200
    data = resp.json()
    assert data["active"] is True
    assert data["completed"] is False
    assert data["topic"] == "English"
    assert data["current_index"] == 0
    assert data["total_questions"] > 0


def test_session_api_advances_index_after_answer(client):
    c, fake_redis = client
    _start(c, "English")
    c.post("/submit_answer", data={"selected_option_index": 0, "current_index": 0})
    data = c.get("/api/session").json()
    assert data["current_index"] == 1


def test_session_api_completed_when_all_answered(client):
    c, fake_redis = client
    _start(c, "English")
    session = _session(fake_redis, c)
    n = session["total_questions"]
    for i in range(n):
        c.post("/submit_answer", data={"selected_option_index": 0, "current_index": i})
    data = c.get("/api/session").json()
    assert data["completed"] is True


# ---------------------------------------------------------------------------
# Vocab reload
# ---------------------------------------------------------------------------


def test_reload_vocab_without_token_returns_403(client, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_TOKEN", "s3cret")
    c, _ = client
    resp = c.post("/api/admin/reload-vocab")
    assert resp.status_code == 403


def test_reload_vocab_with_wrong_token_returns_403(client, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_TOKEN", "s3cret")
    c, _ = client
    resp = c.post("/api/admin/reload-vocab", headers={"X-Admin-Token": "wrong"})
    assert resp.status_code == 403


def test_reload_vocab_when_unconfigured_returns_403(client, monkeypatch):
    # No ADMIN_TOKEN set at all -> the endpoint must deny everyone, not
    # fail open.
    monkeypatch.setattr(settings, "ADMIN_TOKEN", "")
    c, _ = client
    resp = c.post("/api/admin/reload-vocab", headers={"X-Admin-Token": ""})
    assert resp.status_code == 403


def test_reload_vocab_with_correct_token_returns_topics(client, monkeypatch):
    monkeypatch.setattr(settings, "ADMIN_TOKEN", "s3cret")
    c, _ = client
    resp = c.post("/api/admin/reload-vocab", headers={"X-Admin-Token": "s3cret"})
    assert resp.status_code == 200
    data = resp.json()
    assert "loaded" in data
    assert "topics" in data
    assert data["loaded"] > 0


# ---------------------------------------------------------------------------
# /api/result with zero questions
# ---------------------------------------------------------------------------


def test_result_api_with_zero_questions_returns_zero_score(client):
    c, fake_redis = client
    session = SessionData(
        prepared_questions=[],
        correct_count=0,
        total_questions=0,
        answers=[],
        created_at=datetime.now(),
        topic="English",
        mode="adaptive",
    )
    session_id = str(uuid.uuid4())
    fake_redis.set(session_id, session.model_dump_json())
    c.cookies.set(settings.SESSION_COOKIE_NAME, session_id)

    resp = c.get("/api/result")
    assert resp.status_code == 200
    data = resp.json()
    assert data["score_percentage"] == 0
    assert data["total_questions"] == 0


# ---------------------------------------------------------------------------
# RandomQuizGenerator._weighted_sample
# ---------------------------------------------------------------------------


def test_weighted_sample_returns_exact_count():
    from wlingo.globals import vocab_manager
    from wlingo.quiz import RandomQuizGenerator

    gen = RandomQuizGenerator(vocab_manager)
    word_list = vocab_manager.get_words(vocab_manager.get_topics()[0]["id"])
    k = min(5, len(word_list))
    # Give every word a heavy weight to exercise the weighted path
    weights = {w["word"]: 3 for w in word_list}
    result = gen._weighted_sample(word_list, weights, k)
    assert len(result) == k


def test_weighted_sample_no_duplicates():
    from wlingo.globals import vocab_manager
    from wlingo.quiz import RandomQuizGenerator

    gen = RandomQuizGenerator(vocab_manager)
    word_list = vocab_manager.get_words(vocab_manager.get_topics()[0]["id"])
    k = min(5, len(word_list))
    weights = {w["word"]: 3 for w in word_list}
    result = gen._weighted_sample(word_list, weights, k)
    assert len({w["word"] for w in result}) == k
