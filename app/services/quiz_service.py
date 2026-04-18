from collections import defaultdict

from app.database import db
from app.models.db_models import LessonSession, MistakeEvent, QuizAttempt
from app.models.schemas import MistakeRecord, QuizQuestionResult


class QuizService:
    def submit_quiz(
        self, user_id: str, lesson_id: str, results: list[QuizQuestionResult]
    ) -> tuple[QuizAttempt, list[MistakeRecord]]:
        lesson = LessonSession.query.filter_by(lesson_id=lesson_id, user_id=int(user_id)).first()
        if not lesson:
            raise ValueError("lesson session not found")
        if lesson.status == "completed":
            raise ValueError("lesson already completed")
        if not results:
            raise ValueError("results must not be empty")

        total_questions = len(results)
        correct_answers = len([item for item in results if item.is_correct])
        attempt = QuizAttempt(
            lesson_session_id=lesson.id,
            user_id=int(user_id),
            score=correct_answers,
            total_questions=total_questions,
        )
        db.session.add(attempt)
        db.session.flush()

        counters: dict[str, dict[str, int]] = defaultdict(lambda: {"mistakes": 0, "attempts": 0})
        for item in results:
            counters[item.skill]["attempts"] += 1
            if item.is_correct:
                continue
            counters[item.skill]["mistakes"] += 1
            db.session.add(
                MistakeEvent(
                    quiz_attempt_id=attempt.id,
                    user_id=int(user_id),
                    skill=item.skill,
                    error_type=item.error_type,
                    user_answer=item.user_answer,
                    expected_answer=item.expected_answer,
                )
            )

        lesson.status = "completed"
        db.session.commit()

        mistakes = [
            MistakeRecord(skill=skill, mistakes=counts["mistakes"], attempts=counts["attempts"])
            for skill, counts in counters.items()
            if counts["mistakes"] > 0
        ]
        return attempt, mistakes
