# Simpai Backend Production Runbook

## 1) Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

## 2) Create production env file

```bash
cp .env.production.example .env.production
```

Fill real values in `.env.production` (especially `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `GEMINI_API_KEY`).

## 3) Start PostgreSQL and Redis

Make sure both services are reachable by the URLs in `.env.production`.

Quick local check:

```bash
pg_isready -h 127.0.0.1 -p 5432
redis-cli -h 127.0.0.1 -p 6379 ping
```

## 4) Run migrations

```bash
set -a && source .env.production && set +a
python3 -m flask --app app.main:application db init
python3 -m flask --app app.main:application db migrate -m "initial production schema"
python3 -m flask --app app.main:application db upgrade
```

Notes:
- Run `db init` only once per repo.
- For next schema updates use only `db migrate` + `db upgrade`.

## 5) Start API in production mode

```bash
set -a && source .env.production && set +a
gunicorn -c gunicorn.conf.py app.main:application
```

## 6) Verify service health

```bash
curl -i http://127.0.0.1:5001/health/live
curl -i http://127.0.0.1:5001/health/ready
curl -i http://127.0.0.1:5001/metrics
```

Expected:
- `/health/live` -> `200`
- `/health/ready` -> `200` (db reachable)
- `/metrics` -> prometheus text output

## 7) Quick load test

```bash
locust -f tests/perf_locust.py --host http://127.0.0.1:5001
```

Start with a conservative profile, then increase users gradually while tracking p95/p99 latency and error rate.

## 8) Safe rollback

If deployment degrades:
1. Keep previous release process/config ready.
2. Roll app back to previous commit/tag.
3. Restore previous env values.
4. Re-run health checks.
