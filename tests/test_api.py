import uuid

from app.main import application

client = application.test_client()


def _register_and_login() -> tuple[str, str]:
    suffix = uuid.uuid4().hex[:8]
    username = f"user_{suffix}"
    email = f"{suffix}@test.dev"
    password = "Pass1234!"
    registered = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": password},
    )
    assert registered.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"identifier": username, "password": password},
    )
    assert login.status_code == 200
    payload = login.get_json()
    return payload["token"], str(payload["user"]["id"])


def test_healthcheck() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_content_endpoints() -> None:
    lesson = client.post(
        "/api/v1/lesson/unified",
        json={
            "user_id": "1",
            "native_language": "kk",
            "target_language": "en",
            "skill_level": "beginner",
            "goals": ["travel"],
        },
    )
    assert lesson.status_code == 200
    assert len(lesson.get_json()["units"]) == 3

    sentence = client.post(
        "/api/v1/sentence/usage",
        json={"sentence": "Could you send me the report?", "target_language": "en"},
    )
    assert sentence.status_code == 200
    assert "register" in sentence.get_json()

    synonyms = client.get("/api/v1/synonyms/good")
    assert synonyms.status_code == 200
    assert len(synonyms.get_json()["levels"]) == 4


def test_learning_automation_flow() -> None:
    token, user_id = _register_and_login()
    auth = {"Authorization": f"Bearer {token}"}

    level = client.post(
        "/api/v1/level-test/submit",
        json={"correct_answers": 14, "total_questions": 20, "average_response_seconds": 9.0},
        headers=auth,
    )
    assert level.status_code == 200
    level_data = level.get_json()
    assert level_data["cefr_level"] in {"A2", "B1", "B2", "C1"}

    started = client.post(
        "/api/v1/lessons/start",
        json={"current_level": "a2", "available_minutes": 30},
        headers=auth,
    )
    assert started.status_code == 200
    lesson_id = started.get_json()["lesson_id"]

    quiz = client.post(
        "/api/v1/quiz/submit",
        json={
            "lesson_id": lesson_id,
            "current_level": "a2",
            "available_minutes": 35,
            "results": [
                {
                    "skill": "past_tense",
                    "is_correct": False,
                    "user_answer": "I go yesterday",
                    "expected_answer": "I went yesterday",
                    "error_type": "grammar",
                },
                {
                    "skill": "word_order",
                    "is_correct": True,
                    "user_answer": "She is always late",
                    "expected_answer": "She is always late",
                    "error_type": "none",
                },
            ],
        },
        headers=auth,
    )
    assert quiz.status_code == 200
    quiz_data = quiz.get_json()
    assert quiz_data["quiz_attempt_id"] > 0
    assert quiz_data["progress"]["xp_total"] > 0
    assert quiz_data["reminder"]["status"] == "pending"
    assert quiz_data["next_lesson"]["lesson_id"].startswith("nbl_")

    progress = client.get("/api/v1/progress", headers=auth)
    assert progress.status_code == 200
    assert progress.get_json()["user_id"] == user_id

    reminders = client.get("/api/v1/reminders", headers=auth)
    assert reminders.status_code == 200
    reminders_data = reminders.get_json()
    assert len(reminders_data) >= 1

    reminder_id = reminders_data[0]["id"]
    ack = client.post(f"/api/v1/reminders/{reminder_id}/ack", headers=auth)
    assert ack.status_code == 200
    assert ack.get_json()["status"] == "acknowledged"


def test_same_day_streak_idempotent() -> None:
    token, _ = _register_and_login()
    auth = {"Authorization": f"Bearer {token}"}

    started = client.post(
        "/api/v1/lessons/start",
        json={"current_level": "a2", "available_minutes": 20},
        headers=auth,
    )
    lesson_id = started.get_json()["lesson_id"]

    payload = {
        "lesson_id": lesson_id,
        "results": [
            {
                "skill": "article_usage",
                "is_correct": False,
                "user_answer": "I have car",
                "expected_answer": "I have a car",
                "error_type": "grammar",
            }
        ],
    }
    first = client.post("/api/v1/quiz/submit", json=payload, headers=auth)
    assert first.status_code == 200
    streak_1 = first.get_json()["progress"]["streak_days"]

    second_lesson = client.post(
        "/api/v1/lessons/start",
        json={"current_level": "a2", "available_minutes": 20},
        headers=auth,
    )
    second_payload = payload | {"lesson_id": second_lesson.get_json()["lesson_id"]}
    second = client.post("/api/v1/quiz/submit", json=second_payload, headers=auth)
    assert second.status_code == 200
    streak_2 = second.get_json()["progress"]["streak_days"]
    assert streak_2 == streak_1


def test_invalid_token_blocked() -> None:
    response = client.post(
        "/api/v1/level-test/submit",
        json={"correct_answers": 5, "total_questions": 10, "average_response_seconds": 12},
        headers={"Authorization": "Bearer invalid.token"},
    )
    assert response.status_code == 401
