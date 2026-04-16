from typing import List

from app.models.schemas import (
    MonetizationAdviceRequest,
    MonetizationAdviceResponse,
    PlacementAssessmentRequest,
    PlacementAssessmentResponse,
    ScheduledReviewItem,
    SpacedRepetitionRequest,
    SpacedRepetitionResponse,
)


class GrowthService:
    def evaluate_placement(
        self, payload: PlacementAssessmentRequest
    ) -> PlacementAssessmentResponse:
        if payload.total_questions <= 0:
            raise ValueError("total_questions must be greater than zero")

        score_percent = round((payload.correct_answers / payload.total_questions) * 100, 2)
        pace_penalty = 0
        if payload.average_response_seconds > 16:
            pace_penalty = 5
        adjusted = max(0, score_percent - pace_penalty)

        if adjusted >= 88:
            cefr = "C1"
            track = "advanced_fluency_track"
        elif adjusted >= 74:
            cefr = "B2"
            track = "upper_intermediate_track"
        elif adjusted >= 58:
            cefr = "B1"
            track = "intermediate_track"
        elif adjusted >= 40:
            cefr = "A2"
            track = "elementary_track"
        else:
            cefr = "A1"
            track = "starter_track"

        weak_skills: List[str] = []
        if payload.average_response_seconds > 14:
            weak_skills.append("processing_speed")
        if adjusted < 60:
            weak_skills.extend(["core_grammar", "high_frequency_vocabulary"])
        if not weak_skills:
            weak_skills.append("pronunciation_consistency")

        next_7_day_plan = [
            "Day 1-2: 20-minute grammar sprint + 15-minute listening",
            "Day 3-4: Context vocabulary with sentence production",
            "Day 5-6: Guided speaking roleplay and error correction",
            "Day 7: Weekly diagnostic quiz and progress reflection",
        ]

        return PlacementAssessmentResponse(
            user_id=payload.user_id,
            cefr_level=cefr,
            score_percent=adjusted,
            recommended_track=track,
            weak_skills=weak_skills,
            next_7_day_plan=next_7_day_plan,
        )

    def build_spaced_repetition_schedule(
        self, payload: SpacedRepetitionRequest
    ) -> SpacedRepetitionResponse:
        scheduled = []
        for item in payload.items:
            urgency_score = (100 - item.last_score) + (item.days_since_review * 7) - (
                item.seen_count * 2
            )
            if urgency_score >= 70:
                scheduled.append(
                    ScheduledReviewItem(
                        word=item.word,
                        priority="high",
                        next_review_in_hours=2,
                        reason="Low retention and long gap since last review.",
                    )
                )
            elif urgency_score >= 45:
                scheduled.append(
                    ScheduledReviewItem(
                        word=item.word,
                        priority="medium",
                        next_review_in_hours=12,
                        reason="Moderate retention risk; reinforce in same day.",
                    )
                )
            else:
                scheduled.append(
                    ScheduledReviewItem(
                        word=item.word,
                        priority="low",
                        next_review_in_hours=24,
                        reason="Stable retention; normal spaced repetition interval.",
                    )
                )

        high_priority_count = len([x for x in scheduled if x.priority == "high"])
        estimated_session_minutes = max(10, min(40, 8 + len(scheduled) * 2 + high_priority_count * 2))
        return SpacedRepetitionResponse(
            user_id=payload.user_id,
            scheduled_items=scheduled,
            estimated_session_minutes=estimated_session_minutes,
        )

    def get_monetization_advice(
        self, payload: MonetizationAdviceRequest
    ) -> MonetizationAdviceResponse:
        base = 0.22
        base += min(0.24, payload.streak_days * 0.01)
        base += min(0.20, payload.weekly_active_days * 0.025)
        base += min(0.18, payload.completed_lessons * 0.0025)
        base += min(0.08, payload.referral_count * 0.02)
        conversion_probability = round(min(base, 0.95), 2)

        if conversion_probability >= 0.65:
            plan = "annual_pro"
            offer = "30% off annual plan + 14-day AI speaking coach"
            reason = "High engagement and strong retention signal."
        elif conversion_probability >= 0.45:
            plan = "monthly_pro"
            offer = "7-day premium unlock + streak freeze perks"
            reason = "Consistent activity suggests near-term paid conversion."
        else:
            plan = "starter_plus"
            offer = "First month at $4.99 with guided onboarding"
            reason = "Needs lower-friction entry before full subscription."

        return MonetizationAdviceResponse(
            user_id=payload.user_id,
            recommended_plan=plan,
            conversion_probability=conversion_probability,
            offer=offer,
            offer_reason=reason,
            features_to_unlock=[
                "Unlimited roleplay speaking simulations",
                "Adaptive spaced repetition at sentence level",
                "Pronunciation feedback and weekly performance report",
            ],
        )
