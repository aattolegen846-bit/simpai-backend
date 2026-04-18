from app.database import db
from app.models.db_models import LevelTestAttempt
from app.models.schemas import (
    LevelTestSubmitRequest,
    LevelTestSubmitResponse,
    PlacementAssessmentRequest,
)
from app.services.growth_service import GrowthService


class AssessmentService:
    def __init__(self) -> None:
        self._growth_service = GrowthService()

    def submit_level_test(self, payload: LevelTestSubmitRequest) -> LevelTestSubmitResponse:
        if payload.total_questions <= 0:
            raise ValueError("total_questions must be greater than zero")

        placement = self._growth_service.evaluate_placement(
            PlacementAssessmentRequest(
                user_id=payload.user_id,
                correct_answers=payload.correct_answers,
                total_questions=payload.total_questions,
                average_response_seconds=payload.average_response_seconds,
                target_language=payload.target_language,
            )
        )

        attempt = LevelTestAttempt(
            user_id=int(payload.user_id),
            correct_answers=payload.correct_answers,
            total_questions=payload.total_questions,
            average_response_seconds=payload.average_response_seconds,
            score_percent=placement.score_percent,
            cefr_level=placement.cefr_level,
            weak_skills=placement.weak_skills,
        )
        db.session.add(attempt)
        db.session.commit()

        focus = placement.weak_skills[0] if placement.weak_skills else "general_fluency"
        return LevelTestSubmitResponse(
            user_id=payload.user_id,
            attempt_id=attempt.id,
            cefr_level=placement.cefr_level,
            score_percent=placement.score_percent,
            weak_skills=placement.weak_skills,
            first_lesson_focus=focus,
        )
