from datetime import datetime, timezone
from typing import Dict, List
from uuid import uuid4

from app.models.schemas import (
    CohortAnalyticsResponse,
    ReferralCreateResponse,
    ReferralRedeemRequest,
    ReferralRedeemResponse,
    SubscriptionCreateRequest,
    SubscriptionCreateResponse,
    WebhookEventResponse,
)


class RevenueService:
    def __init__(self) -> None:
        self._referral_by_user: Dict[str, str] = {}
        self._user_by_referral: Dict[str, str] = {}
        self._redeemed_pairs: set[tuple[str, str]] = set()
        self._events: List[dict] = []

    def create_subscription(self, payload: SubscriptionCreateRequest) -> SubscriptionCreateResponse:
        subscription_id = f"sub_{uuid4().hex[:12]}"
        self._events.append(
            {
                "user_id": payload.user_id,
                "event": "subscription_created",
                "plan_id": payload.plan_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        return SubscriptionCreateResponse(
            user_id=payload.user_id,
            subscription_id=subscription_id,
            status="pending_checkout",
            checkout_url=f"https://checkout.example.com/{subscription_id}",
        )

    def handle_webhook(self, event_type: str, payload: dict) -> WebhookEventResponse:
        user_id = str(payload.get("user_id", "unknown"))
        self._events.append(
            {
                "user_id": user_id,
                "event": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        return WebhookEventResponse(
            accepted=True,
            event_type=event_type,
            message="Webhook accepted and recorded",
        )

    def create_referral_code(self, user_id: str) -> ReferralCreateResponse:
        if user_id not in self._referral_by_user:
            code = f"REF-{uuid4().hex[:8].upper()}"
            self._referral_by_user[user_id] = code
            self._user_by_referral[code] = user_id
        code = self._referral_by_user[user_id]
        return ReferralCreateResponse(
            user_id=user_id,
            referral_code=code,
            share_link=f"https://app.example.com/invite/{code}",
        )

    def redeem_referral(self, payload: ReferralRedeemRequest) -> ReferralRedeemResponse:
        referrer = self._user_by_referral.get(payload.referral_code)
        if referrer is None:
            raise ValueError("Invalid referral_code")
        if referrer == payload.new_user_id:
            raise ValueError("User cannot redeem own referral code")

        pair = (payload.new_user_id, payload.referral_code)
        if pair in self._redeemed_pairs:
            return ReferralRedeemResponse(
                new_user_id=payload.new_user_id,
                referrer_user_id=referrer,
                reward_points_granted=0,
                redeemed=False,
            )

        self._redeemed_pairs.add(pair)
        self._events.append(
            {
                "user_id": payload.new_user_id,
                "event": "referral_redeemed",
                "referrer": referrer,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        return ReferralRedeemResponse(
            new_user_id=payload.new_user_id,
            referrer_user_id=referrer,
            reward_points_granted=100,
            redeemed=True,
        )

    def cohort_analytics(self, cohort: str) -> CohortAnalyticsResponse:
        cohort_events = [e for e in self._events if e["timestamp"].startswith(cohort)]
        users = {e["user_id"] for e in cohort_events if e["user_id"] != "unknown"}
        activated_users = {
            e["user_id"] for e in cohort_events if e["event"] in {"subscription_created", "referral_redeemed"}
        }
        paid_users = {e["user_id"] for e in cohort_events if e["event"] in {"invoice.paid", "subscription.activated"}}

        total_users = len(users)
        activation_rate = round((len(activated_users) / total_users), 2) if total_users else 0.0
        paid_rate = round((len(paid_users) / total_users), 2) if total_users else 0.0
        return CohortAnalyticsResponse(
            cohort=cohort,
            total_users=total_users,
            activated_users=len(activated_users),
            activation_rate=activation_rate,
            paid_users=len(paid_users),
            paid_conversion_rate=paid_rate,
        )
