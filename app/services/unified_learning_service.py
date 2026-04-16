from datetime import datetime, timezone
from typing import Dict, List

from app.models.schemas import (
    LearningProvider,
    LearningUnit,
    SkillLevel,
    UnifiedLessonRequest,
    UnifiedLessonResponse,
)


_LEVEL_BY_SKILL: Dict[SkillLevel, str] = {
    SkillLevel.beginner: "A1",
    SkillLevel.elementary: "A2",
    SkillLevel.intermediate: "B1-B2",
    SkillLevel.advanced: "C1-C2",
}


class UnifiedLearningService:
    def build_cross_platform_lesson(
        self, payload: UnifiedLessonRequest
    ) -> UnifiedLessonResponse:
        mapped_level = _LEVEL_BY_SKILL[payload.skill_level]
        goals = payload.goals or ["daily communication"]
        goal_string = ", ".join(goals[:3])
        focus_areas = payload.focus_areas or ["vocabulary", "grammar", "speaking"]
        max_total_minutes = max(18, min(payload.available_minutes, 120))

        base_distribution = [0.3, 0.35, 0.35]
        if payload.learning_style == "speaking_first":
            base_distribution = [0.2, 0.25, 0.55]
        elif payload.learning_style == "grammar_first":
            base_distribution = [0.2, 0.55, 0.25]

        allocated = [max(6, int(max_total_minutes * ratio)) for ratio in base_distribution]
        total_allocated = sum(allocated)
        if total_allocated > max_total_minutes:
            allocated[2] = max(6, allocated[2] - (total_allocated - max_total_minutes))
        elif total_allocated < max_total_minutes:
            allocated[2] += max_total_minutes - total_allocated

        units: List[LearningUnit] = [
            LearningUnit(
                provider=LearningProvider.duolingo,
                title=f"Warm-up vocabulary ({mapped_level})",
                objective=(
                    f"Core word activation for {payload.target_language} conversations."
                ),
                estimated_minutes=allocated[0],
                exercises=[
                    f"Flashcards focused on: {goal_string}",
                    "Quick translate challenge with streak scoring",
                    "Listening mini-quiz",
                ],
                adaptation_reason=(
                    f"Prioritizes lexical activation for goals: {goal_string}. "
                    f"Focus areas considered: {', '.join(focus_areas[:2])}."
                ),
            ),
            LearningUnit(
                provider=LearningProvider.alem,
                title="Grammar and sentence patterns",
                objective=(
                    "Practice pattern-based grammar for realistic speaking situations."
                ),
                estimated_minutes=allocated[1],
                exercises=[
                    "Transform present tense to past and future forms",
                    "Fix mistakes in 8 contextualized sentences",
                    "Build your own sentence from provided prompts",
                ],
                adaptation_reason=(
                    "Builds structural accuracy for longer-term fluency and exam-like tasks."
                ),
            ),
            LearningUnit(
                provider=LearningProvider.edvibe,
                title="Tutor-style speaking drill",
                objective="Apply words and grammar in guided role-play scenarios.",
                estimated_minutes=allocated[2],
                exercises=[
                    "Role-play: ordering food / business call / study discussion",
                    "Pronunciation feedback checklist",
                    "Self-evaluation rubric with next action tips",
                ],
                adaptation_reason=(
                    "Converts passive knowledge to active speaking under realistic pressure."
                ),
            ),
        ]

        completion_strategy = [
            "Start with the shortest streak to build momentum in first 5 minutes.",
            "Do not skip correction loops in grammar block; accuracy compounds fast.",
            "End with speaking replay and self-score to lock retention.",
        ]

        return UnifiedLessonResponse(
            user_id=payload.user_id,
            generated_at=datetime.now(timezone.utc).isoformat(),
            units=units,
            total_estimated_minutes=sum(unit.estimated_minutes for unit in units),
            completion_strategy=completion_strategy,
        )
