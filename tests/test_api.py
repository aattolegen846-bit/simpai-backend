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


def test_subscription_create() -> None:
    payload = {"user_id": "u-bill", "plan_id": "monthly_pro", "billing_cycle": "monthly"}
    response = client.post("/api/v1/billing/subscriptions", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "pending_checkout"
    assert data["subscription_id"].startswith("sub_")


def test_stripe_webhook() -> None:
    payload = {
        "event_type": "invoice.paid",
        "data": {"user_id": "u-bill"},
    }
    response = client.post(
        "/api/v1/billing/webhooks/stripe",
        json=payload,
        headers={"X-Webhook-Secret": "dev_stripe_webhook_secret"},
    )
    assert response.status_code == 200
    assert response.get_json()["accepted"] is True


def test_referral_flow() -> None:
    created = client.post("/api/v1/referrals/create", json={"user_id": "ref-1"})
    assert created.status_code == 200
    code = created.get_json()["referral_code"]

    redeemed = client.post(
        "/api/v1/referrals/redeem",
        json={"new_user_id": "new-100", "referral_code": code},
    )
    assert redeemed.status_code == 200
    data = redeemed.get_json()
    assert data["redeemed"] is True
    assert data["reward_points_granted"] == 100


def test_cohort_analytics() -> None:
    cohort = "2026-04"
    response = client.get(f"/api/v1/analytics/cohort?cohort={cohort}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["cohort"] == cohort
    assert "paid_conversion_rate" in data


def test_adaptive_weak_skills_update_and_get() -> None:
    payload = {
        "user_id": "learner-1",
        "observations": [
            {"skill": "past_tense", "mistakes": 7, "attempts": 10},
            {"skill": "word_order", "mistakes": 4, "attempts": 8},
        ],
    }
    updated = client.post("/api/v1/user/skills/update", json=payload)
    assert updated.status_code == 200
    updated_data = updated.get_json()
    assert updated_data["user_id"] == "learner-1"
    assert len(updated_data["weak_skills"]) >= 1

    fetched = client.get("/api/v1/user/learner-1/weak-skills")
    assert fetched.status_code == 200
    fetched_data = fetched.get_json()
    assert fetched_data["user_id"] == "learner-1"
    assert fetched_data["weak_skills"][0]["skill"] in {"past_tense", "word_order"}


def test_next_best_lesson() -> None:
    # Seed weak skill profile first
    client.post(
        "/api/v1/user/skills/update",
        json={
            "user_id": "learner-2",
            "observations": [
                {"skill": "article_usage", "mistakes": 8, "attempts": 10},
                {"skill": "listening_detail", "mistakes": 6, "attempts": 10},
            ],
        },
    )

    response = client.post(
        "/api/v1/lesson/next",
        json={
            "user_id": "learner-2",
            "available_minutes": 40,
            "current_level": "a2",
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["user_id"] == "learner-2"
    assert data["lesson_id"].startswith("nbl_")
    assert data["total_minutes"] == 40
    assert len(data["blocks"]) == 3
