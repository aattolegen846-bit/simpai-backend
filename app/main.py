import time
import uuid
import os
import logging
from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from sqlalchemy import text
try:
    from pythonjsonlogger import jsonlogger
except Exception:  # pragma: no cover
    jsonlogger = None
try:
    import sentry_sdk
except Exception:  # pragma: no cover
    sentry_sdk = None
try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
except Exception:  # pragma: no cover
    CONTENT_TYPE_LATEST = "text/plain"

    class _DummyMetric:
        def labels(self, *args, **kwargs):
            return self

        def inc(self, *_args, **_kwargs):
            return None

        def observe(self, *_args, **_kwargs):
            return None

    def Counter(*_args, **_kwargs):  # type: ignore
        return _DummyMetric()

    def Histogram(*_args, **_kwargs):  # type: ignore
        return _DummyMetric()

    def generate_latest():
        return b""

load_dotenv()

from app.config import Config
from app.extensions import cache, db, limiter, migrate
from app.api.routes import router

REQUEST_COUNT = Counter("simpai_http_requests_total", "Total HTTP requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("simpai_http_request_duration_seconds", "HTTP request latency", ["method", "path"])


def _configure_logging() -> None:
    handler = logging.StreamHandler()
    if jsonlogger:
        formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(message)s")
    else:
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


def create_app() -> Flask:
    _configure_logging()
    webapp = Flask(__name__)
    webapp.config.from_object(Config)
    if str(webapp.config.get("SQLALCHEMY_DATABASE_URI", "")).startswith("sqlite"):
        webapp.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"pool_pre_ping": True}

    db.init_app(webapp)
    cache.init_app(webapp)
    limiter.init_app(webapp)
    migrate.init_app(webapp, db)
    if sentry_sdk and os.getenv("SENTRY_DSN"):
        sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), traces_sample_rate=0.05)

    with webapp.app_context():
        import app.models.user  # noqa: F401
        import app.models.db_models  # noqa: F401
        db.create_all()

    webapp.register_blueprint(router)

    @webapp.before_request
    def _start_request_context() -> None:
        g.request_id = str(uuid.uuid4())
        g.started_at = time.perf_counter()

    @webapp.after_request
    def _attach_response_metadata(response):
        duration_ms = (time.perf_counter() - g.get("started_at", time.perf_counter())) * 1000
        duration_seconds = duration_ms / 1000
        path = request.endpoint or request.path
        REQUEST_COUNT.labels(request.method, path, response.status_code).inc()
        REQUEST_LATENCY.labels(request.method, path).observe(duration_seconds)
        logging.info(
            "request_completed",
            extra={
                "path": request.path,
                "method": request.method,
                "status_code": response.status_code,
                "response_time_ms": round(duration_ms, 2),
                "request_id": g.get("request_id", "n/a"),
            },
        )
        response.headers["X-Request-Id"] = g.get("request_id", "n/a")
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
        return response

    @webapp.errorhandler(Exception)
    def _handle_unexpected_error(error):  # noqa: ANN001
        return (
            jsonify(
                {
                    "error": "internal_server_error",
                    "message": str(error),
                    "request_id": g.get("request_id", "n/a"),
                    "path": request.path,
                }
            ),
            500,
        )

    @webapp.get("/health/live")
    def liveness():
        return jsonify({"status": "live"})

    @webapp.get("/health/ready")
    def readiness():
        try:
            db.session.execute(text("SELECT 1"))
            return jsonify({"status": "ready"})
        except Exception as error:  # noqa: ANN001
            return jsonify({"status": "not_ready", "reason": str(error)}), 503

    @webapp.get("/metrics")
    def metrics():
        return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

    return webapp


application = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    application.run(host="0.0.0.0", port=port, debug=Config.DEBUG)
