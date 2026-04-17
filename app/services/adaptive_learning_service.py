from typing import Dict, List
from uuid import uuid4

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
    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, float]] = {}

    def update_weak_skills(
        self, user_id: str, observations: List[SkillObservation]
    ) -> WeakSkillsResponse:
        skill_scores = self._store.setdefault(user_id, {})
        for obs in observations:
            if obs.attempts <= 0:
                continue
            ratio = min(1.0, max(0.0, obs.mistakes / obs.attempts))
            previous = skill_scores.get(obs.skill, 0.0)
            # EMA smoothing to avoid unstable jumps after single attempts
            skill_scores[obs.skill] = round((previous * 0.65) + (ratio * 0.35), 3)
        return self.get_weak_skills(user_id)

    def get_weak_skills(self, user_id: str) -> WeakSkillsResponse:
        data = self._store.get(user_id, {})
        ordered = sorted(data.items(), key=lambda x: x[1], reverse=True)
        weak = [
            WeakSkillScore(
                skill=skill,
                weakness_score=score,
                suggested_drill=_DRILLS.get(skill, "Targeted mixed drill with instant feedback"),
            )
            for skill, score in ordered[:5]
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
