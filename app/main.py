import time
import uuid
import os
from dotenv import load_dotenv
from flask import Flask, g, jsonify, request

load_dotenv()

from app.database import db
from app.api.routes import router


def create_app() -> Flask:
    webapp = Flask(__name__)
    webapp.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///simpai.db"
    webapp.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    db.init_app(webapp)
    
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

    return webapp


application = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5001"))
    application.run(host="0.0.0.0", port=port, debug=True)
