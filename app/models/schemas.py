from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class LearningProvider(str, Enum):
    duolingo = "duolingo"
    alem = "alem"
    edvibe = "edvibe"


class SkillLevel(str, Enum):
    beginner = "beginner"
    elementary = "elementary"
    intermediate = "intermediate"
    advanced = "advanced"


@dataclass(frozen=True)
class UnifiedLessonRequest:
    user_id: str
    native_language: str
    target_language: str
    skill_level: SkillLevel
    goals: List[str]
    available_minutes: int = 45
    focus_areas: Optional[List[str]] = None
    learning_style: str = "balanced"


@dataclass(frozen=True)
class LearningUnit:
    provider: LearningProvider
    title: str
    objective: str
    estimated_minutes: int
    exercises: List[str]
    adaptation_reason: str


@dataclass(frozen=True)
class UnifiedLessonResponse:
    user_id: str
    generated_at: str
    units: List[LearningUnit]
    total_estimated_minutes: int
    completion_strategy: List[str]


@dataclass(frozen=True)
class SentenceUsageRequest:
    sentence: str
    target_language: str = "en"
    scenario: str = "general"


@dataclass(frozen=True)
class SentenceUsageResponse:
    sentence: str
    language: str
    scenario: str
    register: str
    usage_rule: str
    when_to_use: List[str]
    when_not_to_use: List[str]
    alternatives: List[str]
    confidence_score: float
    risk_flags: List[str]


class SynonymLevel(str, Enum):
    level_1 = "level_1_basic"
    level_2 = "level_2_common"
    level_3 = "level_3_nuanced"
    level_4 = "level_4_advanced"


@dataclass(frozen=True)
class SynonymLevelResult:
    level: SynonymLevel
    words: List[str]
    usage_hint: str


@dataclass(frozen=True)
class SynonymResponse:
    query: str
    language: str
    levels: List[SynonymLevelResult]
    notes: Dict[str, str]
    context_examples: List[str]


@dataclass(frozen=True)
class PlacementAssessmentRequest:
    user_id: str
    correct_answers: int
    total_questions: int
    average_response_seconds: float
    target_language: str = "en"


@dataclass(frozen=True)
class PlacementAssessmentResponse:
    user_id: str
    cefr_level: str
    score_percent: float
    recommended_track: str
    weak_skills: List[str]
    next_7_day_plan: List[str]


@dataclass(frozen=True)
class VocabReviewItem:
    word: str
    last_score: int
    days_since_review: int
    seen_count: int


@dataclass(frozen=True)
class SpacedRepetitionRequest:
    user_id: str
    items: List[VocabReviewItem]


@dataclass(frozen=True)
class ScheduledReviewItem:
    word: str
    priority: str
    next_review_in_hours: int
    reason: str


@dataclass(frozen=True)
class SpacedRepetitionResponse:
    user_id: str
    scheduled_items: List[ScheduledReviewItem]
    estimated_session_minutes: int


@dataclass(frozen=True)
class MonetizationAdviceRequest:
    user_id: str
    streak_days: int
    weekly_active_days: int
    completed_lessons: int
    referral_count: int = 0


@dataclass(frozen=True)
class MonetizationAdviceResponse:
    user_id: str
    recommended_plan: str
    conversion_probability: float
    offer: str
    offer_reason: str
    features_to_unlock: List[str]
