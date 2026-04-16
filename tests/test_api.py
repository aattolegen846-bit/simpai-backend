from app.main import app

client = app.test_client()


def test_healthcheck() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
    assert "X-Request-Id" in response.headers


def test_unified_lesson() -> None:
    payload = {
        "user_id": "user-1",
        "native_language": "kk",
        "target_language": "en",
        "skill_level": "beginner",
        "goals": ["travel", "small talk"],
        "available_minutes": 50,
        "learning_style": "speaking_first",
    }
    response = client.post("/api/v1/lesson/unified", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["units"]) == 3
    assert data["total_estimated_minutes"] > 0
    assert len(data["completion_strategy"]) == 3
    assert "adaptation_reason" in data["units"][0]


def test_sentence_usage() -> None:
    payload = {
        "sentence": "Dear team, I would like to confirm the meeting time.",
        "target_language": "en",
        "scenario": "work",
    }
    response = client.post("/api/v1/sentence/usage", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["register"] == "formal"
    assert len(data["when_to_use"]) >= 1
    assert "confidence_score" in data


def test_synonyms() -> None:
    response = client.get("/api/v1/synonyms/good")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["levels"]) == 4
    assert "usage_hint" in data["levels"][0]
    assert len(data["context_examples"]) == 4


def test_unified_lesson_invalid_level() -> None:
    payload = {
        "user_id": "user-1",
        "native_language": "kk",
        "target_language": "en",
        "skill_level": "expert",
    }
    response = client.post("/api/v1/lesson/unified", json=payload)
    assert response.status_code == 400
    assert "Invalid skill_level" in response.get_json()["error"]


def test_placement_assessment() -> None:
    payload = {
        "user_id": "user-55",
        "correct_answers": 17,
        "total_questions": 20,
        "average_response_seconds": 8.5,
    }
    response = client.post("/api/v1/assessment/placement", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["cefr_level"] in {"B2", "C1"}
    assert len(data["next_7_day_plan"]) >= 3


def test_spaced_repetition_schedule() -> None:
    payload = {
        "user_id": "u-2",
        "items": [
            {"word": "negotiate", "last_score": 35, "days_since_review": 6, "seen_count": 2},
            {"word": "brief", "last_score": 80, "days_since_review": 1, "seen_count": 5},
        ],
    }
    response = client.post("/api/v1/learning/spaced-repetition/schedule", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["scheduled_items"]) == 2
    assert "estimated_session_minutes" in data


def test_monetization_advice() -> None:
    payload = {
        "user_id": "u-99",
        "streak_days": 14,
        "weekly_active_days": 6,
        "completed_lessons": 72,
        "referral_count": 2,
    }
    response = client.post("/api/v1/growth/monetization-advice", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["recommended_plan"] in {"starter_plus", "monthly_pro", "annual_pro"}
    assert data["conversion_probability"] > 0
