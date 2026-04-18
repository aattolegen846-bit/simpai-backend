from datetime import datetime, timezone

from app.database import db
from app.models.db_models import WeakSkillHistory
from app.models.schemas import NextLessonRequest


class PersonalizationService:
    def record_weak_skills(self, user_id: str, weak_skills: list[dict], source: str = "quiz") -> None:
        for item in weak_skills:
            db.session.add(
                WeakSkillHistory(
                    user_id=int(user_id),
                    skill=str(item["skill"]),
                    weakness_score=float(item["weakness_score"]),
                    source=source,
                )
            )
        db.session.commit()

    def get_weak_skill_trends(self, user_id: str, limit: int = 50) -> list[dict]:
        rows = (
            WeakSkillHistory.query.filter_by(user_id=int(user_id))
            .order_by(WeakSkillHistory.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "skill": row.skill,
                "weakness_score": row.weakness_score,
                "source": row.source,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]

    def next_best_action(self, user_id: str, available_minutes: int, current_level: str) -> dict:
        latest = (
            WeakSkillHistory.query.filter_by(user_id=int(user_id))
            .order_by(WeakSkillHistory.created_at.desc())
            .limit(3)
            .all()
        )
        if latest:
            top = latest[0].skill
            return {
                "action": "targeted_weak_topic_lesson",
                "focus_skill": top,
                "recommended_minutes": max(15, min(available_minutes, 45)),
                "reason": "Recent quiz history shows persistent weakness.",
                "current_level": current_level,
            }
        return {
            "action": "balanced_revision_lesson",
            "focus_skill": "general_fluency",
            "recommended_minutes": max(15, min(available_minutes, 40)),
            "reason": "No strong weak-skill trend found.",
            "current_level": current_level,
        }
