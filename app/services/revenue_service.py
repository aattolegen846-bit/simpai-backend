from datetime import datetime, timezone
from typing import Dict, List
from uuid import uuid4

from app.database import db
from app.models.db_models import Referral, Subscription, UserEvent
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
    def create_subscription(self, payload: SubscriptionCreateRequest) -> SubscriptionCreateResponse:
        # Note: mapping str(user_id) to int if needed, but assuming user_id matches DB ID
        subscription_id_str = f"sub_{uuid4().hex[:12]}"
        
        new_sub = Subscription(
            user_id=int(payload.user_id),
            plan_id=payload.plan_id,
            status="pending_checkout"
        )
        db.session.add(new_sub)
        
        event = UserEvent(
            user_id=int(payload.user_id),
            event_type="subscription_created",
            data={"plan_id": payload.plan_id, "subscription_id": subscription_id_str}
        )
        db.session.add(event)
        db.session.commit()

        return SubscriptionCreateResponse(
            user_id=payload.user_id,
            subscription_id=subscription_id_str,
            status="pending_checkout",
            checkout_url=f"https://checkout.example.com/{subscription_id_str}",
        )

    def handle_webhook(self, event_type: str, payload: dict) -> WebhookEventResponse:
        user_id = payload.get("user_id")
        if user_id:
            event = UserEvent(
                user_id=int(user_id),
                event_type=event_type,
                data=payload
            )
            db.session.add(event)
            db.session.commit()

        return WebhookEventResponse(
            accepted=True,
            event_type=event_type,
            message="Webhook accepted and recorded",
        )

    def create_referral_code(self, user_id: str) -> ReferralCreateResponse:
        uid = int(user_id)
        existing = Referral.query.filter_by(referrer_id=uid).first()
        if not existing:
            code = f"REF-{uuid4().hex[:8].upper()}"
            new_ref = Referral(referrer_id=uid, code=code)
            db.session.add(new_ref)
            db.session.commit()
            existing = new_ref

        return ReferralCreateResponse(
            user_id=user_id,
            referral_code=existing.code,
            share_link=f"https://app.example.com/invite/{existing.code}",
        )

    def redeem_referral(self, payload: ReferralRedeemRequest) -> ReferralRedeemResponse:
        ref_record = Referral.query.filter_by(code=payload.referral_code).first()
        if not ref_record:
            raise ValueError("Invalid referral_code")
        
        if int(ref_record.referrer_id) == int(payload.new_user_id):
            raise ValueError("User cannot redeem own referral code")

        # Check if this user already redeemed this code
        if ref_record.redeemed and ref_record.referee_id == int(payload.new_user_id):
             return ReferralRedeemResponse(
                new_user_id=payload.new_user_id,
                referrer_user_id=str(ref_record.referrer_id),
                reward_points_granted=0,
                redeemed=False,
            )

        ref_record.referee_id = int(payload.new_user_id)
        ref_record.redeemed = True
        
        event = UserEvent(
            user_id=int(payload.new_user_id),
            event_type="referral_redeemed",
            data={"referrer_id": ref_record.referrer_id, "code": payload.referral_code}
        )
        db.session.add(event)
        db.session.commit()

        return ReferralRedeemResponse(
            new_user_id=payload.new_user_id,
            referrer_user_id=str(ref_record.referrer_id),
            reward_points_granted=100,
            redeemed=True,
        )

    def cohort_analytics(self, cohort: str) -> CohortAnalyticsResponse:
        # Query events filtered by timestamp prefix
        all_events = UserEvent.query.all()
        cohort_events = [e for e in all_events if e.timestamp.strftime("%Y-%m").startswith(cohort)]
        
        users = {e.user_id for e in cohort_events}
        activated_users = {
            e.user_id for e in cohort_events if e.event_type in {"subscription_created", "referral_redeemed"}
        }
        paid_users = {e.user_id for e in cohort_events if e.event_type in {"invoice.paid", "subscription.activated"}}

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
