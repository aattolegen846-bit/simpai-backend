# Unified Language Learning Backend

This backend combines core features inspired by Duolingo, Alem, and Edvibe into one service:

- Unified lesson flow from multiple provider styles
- Sentence usage guidance (when to use / when not to use)
- 4-level synonym generation for a given word
- Personalized pacing by available minutes and learning style
- Request tracing headers (`X-Request-Id`, `X-Response-Time-Ms`)

## Stack

- Flask
- Pytest

## Run locally

1. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

2. Start API:

```bash
python3 app/main.py
```

3. Base URL:

`http://127.0.0.1:5000`

## API Endpoints

- `POST /api/v1/lesson/unified`
  - Builds a combined lesson track from Duolingo + Alem + Edvibe style units.
  - Supports `available_minutes`, `focus_areas`, and `learning_style`.

- `POST /api/v1/sentence/usage`
  - Returns sentence usage advice, register, alternatives, confidence score, and risk flags.

- `GET /api/v1/synonyms/{word}`
  - Returns synonyms split by 4 levels:
    - level_1_basic
    - level_2_common
    - level_3_nuanced
    - level_4_advanced
  - Includes usage hints and context examples by level.

- `POST /api/v1/assessment/placement`
  - Estimates CEFR level from diagnostic results and returns 7-day improvement plan.

- `POST /api/v1/learning/spaced-repetition/schedule`
  - Schedules vocabulary reviews by memory risk and returns session duration estimate.

- `POST /api/v1/growth/monetization-advice`
  - Returns plan recommendation and conversion probability for premium upsell logic.

- `POST /api/v1/billing/subscriptions`
  - Creates subscription checkout intent and returns checkout URL.

- `POST /api/v1/billing/webhooks/stripe`
  - Handles Stripe-style webhook events (configured with `X-Webhook-Secret` header).

- `POST /api/v1/referrals/create` and `POST /api/v1/referrals/redeem`
  - Creates referral codes and redeems referral rewards.

- `GET /api/v1/analytics/cohort?cohort=YYYY-MM`
  - Returns activation and paid conversion metrics for a cohort period.

- `POST /api/v1/user/skills/update`
  - Updates learner weak-skill profile from exercise observations.

- `GET /api/v1/user/{user_id}/weak-skills`
  - Returns ranked weak skills and suggested targeted drills.

- `POST /api/v1/lesson/next`
  - Recommends the next best lesson plan based on weak skills and available time.

## Quick examples

Unified lesson request:

```json
{
  "user_id": "student-101",
  "native_language": "kk",
  "target_language": "en",
  "skill_level": "beginner",
  "goals": ["travel", "small talk"],
  "available_minutes": 50,
  "focus_areas": ["vocabulary", "speaking"],
  "learning_style": "speaking_first"
}
```

Sentence usage request:

```json
{
  "sentence": "Could you please send me the report by 5 PM?",
  "target_language": "en",
  "scenario": "work"
}
```
