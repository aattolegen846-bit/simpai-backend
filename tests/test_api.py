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
