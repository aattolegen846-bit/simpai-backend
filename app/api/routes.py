from dataclasses import asdict
from enum import Enum

from flask import Blueprint, jsonify, request

from app.models.schemas import (
    SentenceUsageRequest,
    SkillLevel,
    UnifiedLessonRequest,
)
from app.services.sentence_usage_service import SentenceUsageService
from app.services.synonym_service import SynonymService
from app.services.unified_learning_service import UnifiedLearningService

router = Blueprint("learning-platform", __name__, url_prefix="/api/v1")

learning_service = UnifiedLearningService()
sentence_service = SentenceUsageService()
synonym_service = SynonymService()


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
