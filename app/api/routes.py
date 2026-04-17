from dataclasses import asdict
from enum import Enum

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
    UnifiedLessonRequest,
    VocabReviewItem,
)
from app.services.adaptive_learning_service import AdaptiveLearningService
from app.services.growth_service import GrowthService
from app.services.revenue_service import RevenueService
from app.services.sentence_usage_service import SentenceUsageService
from app.services.synonym_service import SynonymService
from app.services.unified_learning_service import UnifiedLearningService

router = Blueprint("learning-platform", __name__, url_prefix="/api/v1")

learning_service = UnifiedLearningService()
sentence_service = SentenceUsageService()
synonym_service = SynonymService()
growth_service = GrowthService()
adaptive_service = AdaptiveLearningService()
revenue_service = RevenueService()
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
    return jsonify(_json_ready(asdict(response)))


@router.get("/user/<user_id>/weak-skills")
def get_weak_skills(user_id: str):
    response = adaptive_service.get_weak_skills(user_id=user_id)
    return jsonify(_json_ready(asdict(response)))


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
