from typing import Dict, List
from uuid import uuid4

from app.database import db
from app.models.db_models import UserSkill
from app.models.schemas import (
    LessonBlock,
    NextLessonRequest,
    NextLessonResponse,
    SkillObservation,
    WeakSkillScore,
    WeakSkillsResponse,
)


_DRILLS: Dict[str, str] = {
    "past_tense": "10 sentence rewrite (present -> past) with correction loop",
    "article_usage": "A/an/the micro-quiz and contextual fill-in practice",
    "word_order": "Unscramble sentence challenge with speaking replay",
    "listening_detail": "Short audio dictation + key detail extraction",
    "pronunciation": "Shadowing drill with chunk-by-chunk repetition",
}


class AdaptiveLearningService:
    def update_weak_skills(
        self, user_id: str, observations: List[SkillObservation]
    ) -> WeakSkillsResponse:
        uid = int(user_id)
        for obs in observations:
            if obs.attempts <= 0:
                continue
            ratio = min(1.0, max(0.0, obs.mistakes / obs.attempts))
            
            existing = UserSkill.query.filter_by(user_id=uid, skill=obs.skill).first()
            if existing:
                # EMA smoothing
                existing.score = round((existing.score * 0.65) + (ratio * 0.35), 3)
            else:
                new_skill = UserSkill(user_id=uid, skill=obs.skill, score=round(ratio, 3))
                db.session.add(new_skill)
        
        db.session.commit()
        return self.get_weak_skills(user_id)

    def get_weak_skills(self, user_id: str) -> WeakSkillsResponse:
        uid = int(user_id)
        skills = UserSkill.query.filter_by(user_id=uid).order_by(UserSkill.score.desc()).limit(5).all()
        
        weak = [
            WeakSkillScore(
                skill=s.skill,
                weakness_score=s.score,
                suggested_drill=_DRILLS.get(s.skill, "Targeted mixed drill with instant feedback"),
            )
            for s in skills
        ]
        return WeakSkillsResponse(user_id=user_id, weak_skills=weak)

    def recommend_next_lesson(
        self, payload: NextLessonRequest, weak_data: WeakSkillsResponse
    ) -> NextLessonResponse:
        total = max(15, min(payload.available_minutes, 90))
        top_skills = weak_data.weak_skills[:2]
        primary_focus = top_skills[0].skill if top_skills else "general_fluency"

        block1 = max(5, int(total * 0.30))
        block2 = max(5, int(total * 0.35))
        block3 = total - block1 - block2

        focus_2 = top_skills[1].skill if len(top_skills) > 1 else "vocabulary_depth"
        blocks = [
            LessonBlock(
                focus=primary_focus,
                minutes=block1,
                activity=f"Warmup corrective drill: {_DRILLS.get(primary_focus, 'adaptive warmup')}",
            ),
            LessonBlock(
                focus=focus_2,
                minutes=block2,
                activity=f"Structured practice and controlled production for {focus_2}",
            ),
            LessonBlock(
                focus="speaking_application",
                minutes=block3,
                activity="Roleplay task with real-context prompts and self-review checklist",
            ),
        ]

        return NextLessonResponse(
            user_id=payload.user_id,
            lesson_id=f"nbl_{uuid4().hex[:10]}",
            primary_focus=primary_focus,
            total_minutes=total,
            blocks=blocks,
        )
