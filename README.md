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

3. Base URL (default):

`http://127.0.0.1:5001`

You can override the port with the `PORT` environment variable, for example:

```bash
PORT=8000 python3 app/main.py
```

Production run (recommended):

```bash
gunicorn -c gunicorn.conf.py app.main:application
```

## Performance and scale configuration

Set these environment variables for high-load balanced setup:

```bash
ENV=production
DEBUG=false
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/simpai
REDIS_URL=redis://localhost:6379/0
CACHE_TYPE=RedisCache
RATELIMIT_STORAGE_URI=redis://localhost:6379/1
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
```

Operational endpoints:
- `GET /health/live`
- `GET /health/ready`
- `GET /metrics`

Async/offload endpoints:
- `POST /api/v1/ai/explain` with `{ "async": true, ... }` returns `202` with `job_id`
- `POST /api/v1/ai/feedback` with `{ "async": true, ... }` returns `202` with `job_id`
- `GET /api/v1/jobs/{job_id}` checks job state

## Database migration workflow

```bash
python3 -m flask --app app.main:application db init
python3 -m flask --app app.main:application db migrate -m "schema update"
python3 -m flask --app app.main:application db upgrade
```

## Load testing

Run a quick load test:

```bash
locust -f tests/perf_locust.py --host http://127.0.0.1:5001
```

Production quick-start files:
- `.env` template: `.env.production.example`
- Deployment guide: `DEPLOY_RUNBOOK.md`

## API Endpoints

- `POST /api/v1/auth/register` and `POST /api/v1/auth/login`
  - Registers user and returns JWT token for protected routes.

- `GET /api/v1/social/leaderboard`
  - Returns top users ranked by points.

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

- `POST /api/v1/level-test/submit` (auth required)
  - Stores level-test result, computes CEFR, and proposes first focus area.

- `POST /api/v1/lessons/start` (auth required)
  - Starts a lesson session and returns a focused lesson plan.

- `POST /api/v1/quiz/submit` (auth required)
  - Stores quiz attempt, tracks mistakes, updates weak-topic profile, generates weak-topic next lesson, updates XP + streak, and schedules in-app reminder.

- `GET /api/v1/progress` (auth required)
  - Returns user XP, streak days, and last activity date.

- `GET /api/v1/reminders` and `POST /api/v1/reminders/{id}/ack` (auth required)
  - Fetches in-app reminders and marks reminder as acknowledged.

## Automation flow (login -> reminder)

1. Login and get JWT (`/auth/login`)
2. Submit level test (`/level-test/submit`)
3. Start lesson (`/lessons/start`)
4. Submit quiz (`/quiz/submit`)
5. Backend automatically:
   - stores mistake events,
   - recomputes weak topics,
   - recommends weak-topic next lesson,
   - updates XP and streak,
   - creates in-app follow-up reminder.

Reminder semantics:
- In-app reminders are persisted and exposed via `GET /api/v1/reminders`.
- Client fetches reminders by polling; no push channel is used in this backend.

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
