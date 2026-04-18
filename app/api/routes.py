from dataclasses import asdict
from enum import Enum
from functools import wraps

from flask import Blueprint, jsonify, request

from app.models.schemas import (
    CohortAnalyticsResponse,
    MonetizationAdviceRequest,
    ReferralRedeemRequest,
    PlacementAssessmentRequest,
    SentenceUsageRequest,
    SkillLevel,
    SkillObservation,
    SpacedRepetitionRequest,
    SubscriptionCreateRequest,
    NextLessonRequest,
    LessonStartRequest,
    LessonStartResponse,
    LevelTestSubmitRequest,
    UnifiedLessonRequest,
    QuizQuestionResult,
    QuizSubmitRequest,
    VocabReviewItem,
)
from app.services.auth_service import AuthService
from app.services.adaptive_learning_service import AdaptiveLearningService
from app.services.assessment_service import AssessmentService
from app.services.growth_service import GrowthService
from app.services.progress_service import ProgressService
from app.services.quiz_service import QuizService
from app.services.reminder_service import ReminderService
from app.services.revenue_service import RevenueService
from app.services.job_service import JobService
from app.services.personalization_service import PersonalizationService
from app.services.sentence_usage_service import SentenceUsageService
from app.services.synonym_service import SynonymService
from app.services.unified_learning_service import UnifiedLearningService
from app.models.db_models import LessonSession, UserEvent
from app.models.user import User
from app.services.ai_tutor_service import AITutorService
from app.services.social_service import SocialService
from app.services.gamification_service import GamificationService
from app.services.content_service import ContentService
from app.services.review_service import ReviewService
from app.services.analytics_service import AnalyticsService
from app.services.engagement_service import EngagementService
from app.database import db
from uuid import uuid4
from app.extensions import cache, limiter

router = Blueprint("learning-platform", __name__, url_prefix="/api/v1")

auth_service = AuthService()
ai_tutor_service = AITutorService()
social_service = SocialService()
gamification_service = GamificationService()
content_service = ContentService()
review_service = ReviewService()
analytics_service = AnalyticsService()
engagement_service = EngagementService()
personalization_service = PersonalizationService()

from app.middleware.auth import token_required, role_required


@router.post("/auth/register")
@limiter.limit("20 per minute")
def register():
    payload = request.get_json(force=True)
    username = payload.get("username")
    email = payload.get("email")
    password = payload.get("password")
    
    if not all([username, email, password]):
        return _bad_request("Missing fields")
        
    success, message = auth_service.register_user(username, email, password)
    if not success:
        return _bad_request(message)
        
    return jsonify({"message": message}), 201


@router.post("/auth/login")
@limiter.limit("30 per minute")
def login():
    payload = request.get_json(force=True)
    identifier = payload.get("identifier")  # username or email
    password = payload.get("password")
    
    user = auth_service.authenticate_user(identifier, password)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401
        
    token = auth_service.generate_token(user.id)
    refresh_token = auth_service.generate_refresh_token(user.id)
    return jsonify({
        "token": token,
        "refresh_token": refresh_token,
        "user": user.to_dict()
    })


@router.post("/auth/refresh")
@limiter.limit("40 per minute")
def refresh_token():
    payload = request.get_json(force=True)
    raw_refresh = payload.get("refresh_token")
    if not raw_refresh:
        return _bad_request("Missing refresh_token")
    rotated = auth_service.rotate_refresh_token(raw_refresh)
    if not rotated:
        return jsonify({"error": "Invalid refresh token"}), 401
    access_token, new_refresh_token = rotated
    return jsonify({"token": access_token, "refresh_token": new_refresh_token})


@router.post("/auth/revoke")
@limiter.limit("40 per minute")
def revoke_token():
    payload = request.get_json(force=True)
    raw_refresh = payload.get("refresh_token")
    if not raw_refresh:
        return _bad_request("Missing refresh_token")
    revoked = auth_service.revoke_refresh_token(raw_refresh)
    return jsonify({"revoked": revoked})


@router.get("/auth/me")
@token_required
def auth_me(current_user):
    return jsonify(current_user.to_dict())


@router.get("/social/leaderboard")
@cache.cached(timeout=30, query_string=True)
def get_leaderboard():
    limit = request.args.get("limit", 10, type=int)
    leaderboard = social_service.get_leaderboard(limit)
    return jsonify(leaderboard)


@router.post("/ai/explain")
@token_required
@limiter.limit("30 per minute")
def ai_explain(current_user):
    payload = request.get_json(force=True)
    sentence = payload.get("sentence")
    target_lang = payload.get("target_language", "en")
    native_lang = payload.get("native_language", "kk")
    async_mode = bool(payload.get("async", False))
    
    if not sentence:
        return _bad_request("Missing sentence")
        
    if async_mode:
        job_id = job_service.enqueue(ai_tutor_service.explain_sentence, sentence, target_lang, native_lang)
        return jsonify({"job_id": job_id, "status": "queued"}), 202

    explanation = ai_tutor_service.explain_sentence(sentence, target_lang, native_lang)
    return jsonify(asdict(explanation))


@router.post("/ai/feedback")
@token_required
@limiter.limit("30 per minute")
def ai_feedback(current_user):
    payload = request.get_json(force=True)
    user_input = payload.get("user_input")
    target_text = payload.get("target_text")
    async_mode = bool(payload.get("async", False))
    
    if not user_input or not target_text:
        return _bad_request("Missing fields")
        
    if async_mode:
        job_id = job_service.enqueue(ai_tutor_service.provide_feedback, user_input, target_text)
        return jsonify({"job_id": job_id, "status": "queued"}), 202

    feedback = ai_tutor_service.provide_feedback(user_input, target_text)
    
    # Award points for effort
    social_service.award_points(current_user.id, 10)
    cache.clear()
    
    return jsonify(feedback)


@router.get("/jobs/<job_id>")
@token_required
def get_job_status(current_user, job_id: str):
    return jsonify(job_service.get_status(job_id))


learning_service = UnifiedLearningService()
sentence_service = SentenceUsageService()
synonym_service = SynonymService()
growth_service = GrowthService()
adaptive_service = AdaptiveLearningService()
revenue_service = RevenueService()
assessment_service = AssessmentService()
quiz_service = QuizService()
progress_service = ProgressService()
reminder_service = ReminderService()
job_service = JobService()
WEBHOOK_SECRET = "dev_stripe_webhook_secret"


def _json_ready(payload):
    if isinstance(payload, dict):
        return {key: _json_ready(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [_json_ready(value) for value in payload]
    if isinstance(payload, Enum):
        return payload.value
    return payload


def _bad_request(message: str):
    return jsonify({"error": message}), 400


def _normalize_goals(goals):
    if goals is None:
        return []
    if not isinstance(goals, list):
        raise ValueError("goals must be an array of strings")
    cleaned = [str(goal).strip().lower() for goal in goals if str(goal).strip()]
    return list(dict.fromkeys(cleaned))[:8]


@router.get("/health")
def healthcheck():
    return jsonify({"status": "ok"})


@router.post("/lesson/unified")
def create_unified_lesson():
    payload = request.get_json(force=True)
    required_fields = ["user_id", "native_language", "target_language", "skill_level"]
    for field in required_fields:
        if field not in payload:
            return _bad_request(f"Missing required field: {field}")

    try:
        level = SkillLevel(payload["skill_level"])
    except ValueError:
        allowed = [level.value for level in SkillLevel]
        return _bad_request(f"Invalid skill_level. Allowed values: {allowed}")

    try:
        goals = _normalize_goals(payload.get("goals"))
        available_minutes = int(payload.get("available_minutes", 45))
        focus_areas = payload.get("focus_areas")
        learning_style = str(payload.get("learning_style", "balanced")).strip().lower()
    except (TypeError, ValueError) as error:
        return _bad_request(str(error))

    model = UnifiedLessonRequest(
        user_id=payload["user_id"],
        native_language=payload["native_language"],
        target_language=payload["target_language"],
        skill_level=level,
        goals=goals,
        available_minutes=available_minutes,
        focus_areas=focus_areas,
        learning_style=learning_style,
    )
    response = learning_service.build_cross_platform_lesson(model)
    return jsonify(_json_ready(asdict(response)))


@router.post("/sentence/usage")
def get_sentence_usage():
    payload = request.get_json(force=True)
    if "sentence" not in payload:
        return _bad_request("Missing required field: sentence")

    model = SentenceUsageRequest(
        sentence=payload["sentence"],
        target_language=payload.get("target_language", "en"),
        scenario=payload.get("scenario", "general"),
    )
    response = sentence_service.analyze(model)
    return jsonify(_json_ready(asdict(response)))


@router.get("/synonyms/<word>")
@cache.cached(timeout=300, query_string=True)
def get_synonyms(word: str):
    language = request.args.get("language", "en")
    response = synonym_service.get_synonyms_by_levels(word=word, language=language)
    return jsonify(_json_ready(asdict(response)))


@router.post("/assessment/placement")
def placement_assessment():
    payload = request.get_json(force=True)
    required_fields = [
        "user_id",
        "correct_answers",
        "total_questions",
        "average_response_seconds",
    ]
    for field in required_fields:
        if field not in payload:
            return _bad_request(f"Missing required field: {field}")

    try:
        model = PlacementAssessmentRequest(
            user_id=str(payload["user_id"]),
            correct_answers=int(payload["correct_answers"]),
            total_questions=int(payload["total_questions"]),
            average_response_seconds=float(payload["average_response_seconds"]),
            target_language=str(payload.get("target_language", "en")),
        )
        response = growth_service.evaluate_placement(model)
    except ValueError as error:
        return _bad_request(str(error))

    return jsonify(_json_ready(asdict(response)))


@router.post("/learning/spaced-repetition/schedule")
def spaced_repetition_schedule():
    payload = request.get_json(force=True)
    if "user_id" not in payload or "items" not in payload:
        return _bad_request("Missing required fields: user_id, items")
    if not isinstance(payload["items"], list):
        return _bad_request("items must be an array")

    try:
        items = [
            VocabReviewItem(
                word=str(item["word"]),
                last_score=int(item["last_score"]),
                days_since_review=int(item["days_since_review"]),
                seen_count=int(item["seen_count"]),
            )
            for item in payload["items"]
        ]
        model = SpacedRepetitionRequest(user_id=str(payload["user_id"]), items=items)
        response = growth_service.build_spaced_repetition_schedule(model)
    except (KeyError, TypeError, ValueError) as error:
        return _bad_request(f"Invalid items payload: {error}")

    return jsonify(_json_ready(asdict(response)))


@router.post("/growth/monetization-advice")
def monetization_advice():
    payload = request.get_json(force=True)
    required_fields = ["user_id", "streak_days", "weekly_active_days", "completed_lessons"]
    for field in required_fields:
        if field not in payload:
            return _bad_request(f"Missing required field: {field}")

    try:
        model = MonetizationAdviceRequest(
            user_id=str(payload["user_id"]),
            streak_days=int(payload["streak_days"]),
            weekly_active_days=int(payload["weekly_active_days"]),
            completed_lessons=int(payload["completed_lessons"]),
            referral_count=int(payload.get("referral_count", 0)),
        )
        response = growth_service.get_monetization_advice(model)
    except ValueError as error:
        return _bad_request(str(error))

    return jsonify(_json_ready(asdict(response)))


@router.post("/billing/subscriptions")
def create_subscription():
    payload = request.get_json(force=True)
    required_fields = ["user_id", "plan_id", "billing_cycle"]
    for field in required_fields:
        if field not in payload:
            return _bad_request(f"Missing required field: {field}")
    model = SubscriptionCreateRequest(
        user_id=str(payload["user_id"]),
        plan_id=str(payload["plan_id"]),
        billing_cycle=str(payload["billing_cycle"]),
        payment_provider=str(payload.get("payment_provider", "stripe")),
    )
    response = revenue_service.create_subscription(model)
    return jsonify(_json_ready(asdict(response)))


@router.post("/billing/webhooks/stripe")
def stripe_webhook():
    signature = request.headers.get("X-Webhook-Secret")
    if signature != WEBHOOK_SECRET:
        return jsonify({"error": "Invalid webhook signature"}), 401

    payload = request.get_json(force=True)
    event_type = str(payload.get("event_type", "unknown"))
    event_payload = payload.get("data", {})
    response = revenue_service.handle_webhook(event_type=event_type, payload=event_payload)
    return jsonify(_json_ready(asdict(response)))


@router.post("/referrals/create")
def create_referral():
    payload = request.get_json(force=True)
    user_id = payload.get("user_id")
    if not user_id:
        return _bad_request("Missing required field: user_id")
    response = revenue_service.create_referral_code(str(user_id))
    return jsonify(_json_ready(asdict(response)))


@router.post("/referrals/redeem")
def redeem_referral():
    payload = request.get_json(force=True)
    if "new_user_id" not in payload or "referral_code" not in payload:
        return _bad_request("Missing required fields: new_user_id, referral_code")
    model = ReferralRedeemRequest(
        new_user_id=str(payload["new_user_id"]),
        referral_code=str(payload["referral_code"]),
    )
    try:
        response = revenue_service.redeem_referral(model)
    except ValueError as error:
        return _bad_request(str(error))
    return jsonify(_json_ready(asdict(response)))


@router.get("/analytics/cohort")
def cohort_analytics():
    cohort = request.args.get("cohort")
    if not cohort:
        return _bad_request("Missing required query param: cohort (YYYY-MM)")
    response: CohortAnalyticsResponse = revenue_service.cohort_analytics(cohort)
    return jsonify(_json_ready(asdict(response)))


@router.post("/user/skills/update")
def update_user_skills():
    payload = request.get_json(force=True)
    if "user_id" not in payload or "observations" not in payload:
        return _bad_request("Missing required fields: user_id, observations")
    if not isinstance(payload["observations"], list):
        return _bad_request("observations must be an array")
    try:
        observations = [
            SkillObservation(
                skill=str(item["skill"]).strip().lower(),
                mistakes=int(item["mistakes"]),
                attempts=int(item["attempts"]),
            )
            for item in payload["observations"]
        ]
    except (KeyError, TypeError, ValueError) as error:
        return _bad_request(f"Invalid observations payload: {error}")

    response = adaptive_service.update_weak_skills(
        user_id=str(payload["user_id"]),
        observations=observations,
    )
    cache.delete(f"user_weak_skills:{payload['user_id']}")
    return jsonify(_json_ready(asdict(response)))


@router.get("/user/<user_id>/weak-skills")
def get_weak_skills(user_id: str):
    cache_key = f"user_weak_skills:{user_id}"
    cached = cache.get(cache_key)
    if cached is not None:
        return jsonify(cached)
    response = adaptive_service.get_weak_skills(user_id=user_id)
    payload = _json_ready(asdict(response))
    cache.set(cache_key, payload, timeout=30)
    return jsonify(payload)


@router.post("/lesson/next")
def get_next_best_lesson():
    payload = request.get_json(force=True)
    required_fields = ["user_id", "available_minutes", "current_level"]
    for field in required_fields:
        if field not in payload:
            return _bad_request(f"Missing required field: {field}")
    model = NextLessonRequest(
        user_id=str(payload["user_id"]),
        available_minutes=int(payload["available_minutes"]),
        current_level=str(payload["current_level"]).strip().lower(),
    )
    weak_data = adaptive_service.get_weak_skills(model.user_id)
    response = adaptive_service.recommend_next_lesson(model, weak_data)
    return jsonify(_json_ready(asdict(response)))


@router.post("/level-test/submit")
@token_required
def submit_level_test(current_user):
    payload = request.get_json(force=True)
    required_fields = ["correct_answers", "total_questions", "average_response_seconds"]
    for field in required_fields:
        if field not in payload:
            return _bad_request(f"Missing required field: {field}")

    model = LevelTestSubmitRequest(
        user_id=str(current_user.id),
        correct_answers=int(payload["correct_answers"]),
        total_questions=int(payload["total_questions"]),
        average_response_seconds=float(payload["average_response_seconds"]),
        target_language=str(payload.get("target_language", "en")),
    )
    try:
        response = assessment_service.submit_level_test(model)
    except ValueError as error:
        return _bad_request(str(error))

    current_user.cefr_level = response.cefr_level
    db.session.add(
        UserEvent(
            user_id=current_user.id,
            event_type="level_test_submitted",
            data={"attempt_id": response.attempt_id, "cefr_level": response.cefr_level},
        )
    )
    db.session.commit()
    return jsonify(_json_ready(asdict(response)))


@router.post("/lessons/start")
@token_required
def start_lesson(current_user):
    payload = request.get_json(force=True)
    required_fields = ["current_level", "available_minutes"]
    for field in required_fields:
        if field not in payload:
            return _bad_request(f"Missing required field: {field}")

    model = LessonStartRequest(
        user_id=str(current_user.id),
        current_level=str(payload["current_level"]).strip().lower(),
        available_minutes=int(payload["available_minutes"]),
    )
    weak_data = adaptive_service.get_weak_skills(str(current_user.id))
    next_lesson = adaptive_service.recommend_next_lesson(
        NextLessonRequest(
            user_id=model.user_id,
            available_minutes=model.available_minutes,
            current_level=model.current_level,
        ),
        weak_data,
    )

    session = LessonSession(
        lesson_id=next_lesson.lesson_id,
        user_id=current_user.id,
        focus_topic=next_lesson.primary_focus,
        current_level=model.current_level,
        status="started",
    )
    db.session.add(session)
    db.session.add(
        UserEvent(
            user_id=current_user.id,
            event_type="lesson_started",
            data={"lesson_id": next_lesson.lesson_id, "focus": next_lesson.primary_focus},
        )
    )
    db.session.commit()

    response = LessonStartResponse(
        user_id=str(current_user.id),
        lesson_id=next_lesson.lesson_id,
        primary_focus=next_lesson.primary_focus,
        total_minutes=next_lesson.total_minutes,
        blocks=next_lesson.blocks,
        status="started",
    )
    return jsonify(_json_ready(asdict(response)))


@router.post("/quiz/submit")
@token_required
@limiter.limit("120 per minute")
def submit_quiz(current_user):
    payload = request.get_json(force=True)
    if "lesson_id" not in payload or "results" not in payload:
        return _bad_request("Missing required fields: lesson_id, results")
    if not isinstance(payload["results"], list):
        return _bad_request("results must be an array")

    try:
        results = [
            QuizQuestionResult(
                skill=str(item["skill"]).strip().lower(),
                is_correct=bool(item["is_correct"]),
                user_answer=str(item["user_answer"]),
                expected_answer=str(item["expected_answer"]),
                error_type=str(item.get("error_type", "accuracy")),
            )
            for item in payload["results"]
        ]
    except (KeyError, TypeError, ValueError) as error:
        return _bad_request(f"Invalid quiz results payload: {error}")

    idempotency_key = request.headers.get("Idempotency-Key")
    cache_key = None
    if idempotency_key:
        cache_key = f"quiz_idempotency:{current_user.id}:{idempotency_key}"
        cached_response = cache.get(cache_key)
        if cached_response:
            return jsonify(cached_response)

    try:
        quiz_model = QuizSubmitRequest(
            user_id=str(current_user.id),
            lesson_id=str(payload["lesson_id"]),
            current_level=str(payload.get("current_level", current_user.cefr_level)).strip().lower(),
            available_minutes=int(payload.get("available_minutes", 30)),
            results=results,
        )
        attempt, mistakes = quiz_service.submit_quiz(
            user_id=quiz_model.user_id,
            lesson_id=quiz_model.lesson_id,
            results=quiz_model.results,
        )
    except ValueError as error:
        return _bad_request(str(error))

    observations = [
        SkillObservation(skill=item.skill, mistakes=item.mistakes, attempts=item.attempts)
        for item in mistakes
    ]
    weak_data = adaptive_service.update_weak_skills(str(current_user.id), observations) if observations else adaptive_service.get_weak_skills(str(current_user.id))
    next_lesson = adaptive_service.recommend_next_lesson(
        NextLessonRequest(
            user_id=str(current_user.id),
            available_minutes=quiz_model.available_minutes,
            current_level=quiz_model.current_level,
        ),
        weak_data,
    )
    personalization_service.record_weak_skills(
        str(current_user.id),
        [asdict(item) for item in weak_data.weak_skills],
        source="quiz_submit",
    )

    xp_gain = (attempt.score * 10) + (5 if attempt.score == attempt.total_questions else 0)
    
    # NEW: Unified Pro Gamification
    gamification_payload = gamification_service.update_xp(current_user.id, xp_gain)
    
    progress = progress_service.award_xp_and_update_streak(str(current_user.id), xp_gain)
    reminder = reminder_service.schedule_followup_reminder(
        user_id=str(current_user.id),
        reminder_type="weak_topic_followup",
        payload={"lesson_id": next_lesson.lesson_id, "focus": next_lesson.primary_focus},
        after_hours=24,
    )

    event_payload = {
        "quiz_attempt_id": attempt.id,
        "score": attempt.score,
        "total_questions": attempt.total_questions,
        "next_lesson_id": next_lesson.lesson_id,
    }
    db.session.add(
        UserEvent(
            user_id=current_user.id,
            event_type="quiz_submitted",
            data=event_payload,
        )
    )
    db.session.commit()

    response_payload = _json_ready(
        {
            "user_id": str(current_user.id),
            "lesson_id": quiz_model.lesson_id,
            "quiz_attempt_id": attempt.id,
            "score": attempt.score,
            "total_questions": attempt.total_questions,
            "mistakes": [asdict(item) for item in mistakes],
            "weak_skills": [asdict(item) for item in weak_data.weak_skills],
            "next_lesson": asdict(next_lesson),
            "progress": asdict(progress),
            "reminder": asdict(reminder),
        }
    )
    if cache_key:
        cache.set(cache_key, response_payload, timeout=120)

    cache.delete(f"user_weak_skills:{current_user.id}")
    cache.delete(f"user_reminders:{current_user.id}:all")
    return jsonify(response_payload)


@router.get("/progress")
@token_required
def get_progress(current_user):
    response = progress_service.get_progress(str(current_user.id))
    return jsonify(_json_ready(asdict(response)))


@router.get("/personalization/weak-skill-trends")
@token_required
def weak_skill_trends(current_user):
    limit = request.args.get("limit", 50, type=int)
    return jsonify(personalization_service.get_weak_skill_trends(str(current_user.id), limit=limit))


@router.get("/personalization/next-best-action")
@token_required
def next_best_action(current_user):
    available_minutes = request.args.get("available_minutes", 30, type=int)
    current_level = request.args.get("current_level", current_user.cefr_level)
    payload = personalization_service.next_best_action(
        str(current_user.id), available_minutes=available_minutes, current_level=current_level
    )
    return jsonify(payload)


@router.get("/admin/health/overview")
@role_required("admin")
def admin_health_overview(current_user):
    return jsonify(
        {
            "status": "ok",
            "cache_enabled": True,
            "rate_limit_default": "enabled",
            "note": "Admin-only lightweight operational overview.",
        }
    )


@router.get("/reminders")
@token_required
def get_reminders(current_user):
    status = request.args.get("status")
    normalized_status = status or "all"
    cache_key = f"user_reminders:{current_user.id}:{normalized_status}"
    cached_reminders = cache.get(cache_key)
    if cached_reminders is not None:
        return jsonify(cached_reminders)

    reminders = reminder_service.get_user_reminders(str(current_user.id), status=status)
    payload = _json_ready([asdict(item) for item in reminders])
    cache.set(cache_key, payload, timeout=30)
    return jsonify(payload)


@router.post("/reminders/<int:reminder_id>/ack")
@token_required
def acknowledge_reminder(current_user, reminder_id: int):
    try:
        response = reminder_service.acknowledge_reminder(str(current_user.id), reminder_id)
    except ValueError as error:
        return _bad_request(str(error))
    cache.delete(f"user_reminders:{current_user.id}:all")
    cache.delete(f"user_reminders:{current_user.id}:pending")
    return jsonify(_json_ready(asdict(response)))


# --- UNIFIED PRO BACKEND ROUTES (Duolingo, EdVibe, Alem) ---

@router.get("/courses")
@token_required
def get_courses(current_user):
    lang = request.args.get("language")
    return jsonify(content_service.get_courses(lang))


@router.get("/courses/<int:course_id>")
@token_required
def get_course_details(current_user, course_id: int):
    return jsonify(content_service.get_course_details(course_id))


@router.get("/lessons/<int:lesson_id>/tasks")
@token_required
def get_lesson_tasks(current_user, lesson_id: int):
    return jsonify(content_service.get_lesson_tasks(lesson_id))


@router.get("/gamification/leaderboard")
@token_required
def get_league_leaderboard(current_user):
    return jsonify(gamification_service.get_league_leaderboard(current_user.id))


@router.get("/gamification/achievements")
@token_required
def get_achievements(current_user):
    return jsonify(gamification_service.get_achievements(current_user.id))


@router.get("/review/mistakes")
@token_required
def get_mistake_review(current_user):
    limit = request.args.get("limit", 10, type=int)
    return jsonify(review_service.get_mistake_review_session(current_user.id, limit))


@router.get("/progress/vocabulary")
@token_required
def get_vocab_stats(current_user):
    return jsonify(review_service.get_vocabulary_stats(current_user.id))


@router.post("/admin/seed-demo")
@role_required("admin")
def seed_demo_content(current_user):
    content_service.seed_demo_content()
    analytics_service.seed_simulated_activity()
    engagement_service.initialize_daily_quests(current_user.id)
    return jsonify({"message": "Pro Demo content, analytics, and quests seeded successfully."})


# --- GROWTH & ENGAGEMENT ROUTES (Social, Quests, Nudges) ---

@router.post("/social/follow")
@token_required
def follow_user(current_user):
    payload = request.get_json(force=True)
    target = payload.get("username")
    if not target:
        return _bad_request("Missing target username")
    success = social_service.follow_user(current_user.id, target)
    return jsonify({"success": success})


@router.get("/social/feed")
@token_required
def get_social_feed(current_user):
    limit = request.args.get("limit", 20, type=int)
    return jsonify(social_service.get_following_activity(current_user.id, limit))


@router.post("/social/challenge")
@token_required
def create_challenge(current_user):
    payload = request.get_json(force=True)
    opponent = payload.get("opponent")
    goal_xp = payload.get("goal_xp", 500)
    if not opponent:
        return _bad_request("Missing opponent username")
    result = social_service.create_friend_challenge(current_user.id, opponent, goal_xp)
    if not result:
        return _bad_request("Could not create challenge")
    return jsonify(result)


@router.get("/social/challenges")
@token_required
def get_challenges(current_user):
    return jsonify(social_service.get_active_challenges(current_user.id))


@router.get("/user/quests")
@token_required
def get_user_quests(current_user):
    engagement_service.initialize_daily_quests(current_user.id)
    return jsonify(engagement_service.get_active_quests(current_user.id))


@router.get("/analytics/dashboard")
@token_required
@role_required("admin")
def get_analytics_dashboard(current_user):
    return jsonify(analytics_service.get_dashboard_metrics())


@router.get("/health/technical")
@role_required("admin")
def get_technical_health(current_user):
    # Simulated technical health metrics for the demo
    return jsonify({
        "status": "healthy",
        "services": {
            "postgres": "up (5ms latency)",
            "redis": "up (2ms latency)",
            "worker_queue": "active (0 backlog)",
            "gemini_api": "active (circuit_breaker: closed)"
        },
        "performance": {
            "p95_latency_ms": 124,
            "cache_hit_rate": "88%",
            "active_connections": 12
        }
    })
