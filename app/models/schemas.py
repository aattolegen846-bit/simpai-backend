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


@dataclass(frozen=True)
class SubscriptionCreateRequest:
    user_id: str
    plan_id: str
    billing_cycle: str
    payment_provider: str = "stripe"


@dataclass(frozen=True)
class SubscriptionCreateResponse:
    user_id: str
    subscription_id: str
    status: str
    checkout_url: str


@dataclass(frozen=True)
class WebhookEventResponse:
    accepted: bool
    event_type: str
    message: str


@dataclass(frozen=True)
class ReferralCreateResponse:
    user_id: str
    referral_code: str
    share_link: str


@dataclass(frozen=True)
class ReferralRedeemRequest:
    new_user_id: str
    referral_code: str


@dataclass(frozen=True)
class ReferralRedeemResponse:
    new_user_id: str
    referrer_user_id: str
    reward_points_granted: int
    redeemed: bool


@dataclass(frozen=True)
class CohortAnalyticsResponse:
    cohort: str
    total_users: int
    activated_users: int
    activation_rate: float
    paid_users: int
    paid_conversion_rate: float


@dataclass(frozen=True)
class SkillObservation:
    skill: str
    mistakes: int
    attempts: int


@dataclass(frozen=True)
class WeakSkillsUpdateRequest:
    user_id: str
    observations: List[SkillObservation]


@dataclass(frozen=True)
class WeakSkillScore:
    skill: str
    weakness_score: float
    suggested_drill: str


@dataclass(frozen=True)
class WeakSkillsResponse:
    user_id: str
    weak_skills: List[WeakSkillScore]


@dataclass(frozen=True)
class NextLessonRequest:
    user_id: str
    available_minutes: int
    current_level: str


@dataclass(frozen=True)
class LessonBlock:
    focus: str
    minutes: int
    activity: str


@dataclass(frozen=True)
class NextLessonResponse:
    user_id: str
    lesson_id: str
    primary_focus: str
    total_minutes: int
    blocks: List[LessonBlock]


@dataclass(frozen=True)
class LevelTestSubmitRequest:
    user_id: str
    correct_answers: int
    total_questions: int
    average_response_seconds: float
    target_language: str = "en"


@dataclass(frozen=True)
class LevelTestSubmitResponse:
    user_id: str
    attempt_id: int
    cefr_level: str
    score_percent: float
    weak_skills: List[str]
    first_lesson_focus: str


@dataclass(frozen=True)
class LessonStartRequest:
    user_id: str
    current_level: str
    available_minutes: int


@dataclass(frozen=True)
class LessonStartResponse:
    user_id: str
    lesson_id: str
    primary_focus: str
    total_minutes: int
    blocks: List[LessonBlock]
    status: str


@dataclass(frozen=True)
class QuizQuestionResult:
    skill: str
    is_correct: bool
    user_answer: str
    expected_answer: str
    error_type: str


@dataclass(frozen=True)
class QuizSubmitRequest:
    user_id: str
    lesson_id: str
    current_level: str
    available_minutes: int
    results: List[QuizQuestionResult]


@dataclass(frozen=True)
class MistakeRecord:
    skill: str
    mistakes: int
    attempts: int


@dataclass(frozen=True)
class ProgressSnapshot:
    user_id: str
    xp_total: int
    streak_days: int
    last_activity_date: str | None


@dataclass(frozen=True)
class ReminderDto:
    id: int
    reminder_type: str
    due_at: str
    status: str
    payload: Dict[str, object]


@dataclass(frozen=True)
class QuizSubmitResponse:
    user_id: str
    lesson_id: str
    quiz_attempt_id: int
    score: int
    total_questions: int
    mistakes: List[MistakeRecord]
    weak_skills: List[WeakSkillScore]
    next_lesson: NextLessonResponse
    progress: ProgressSnapshot
    reminder: ReminderDto
