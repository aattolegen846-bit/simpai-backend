import time
import uuid

from flask import Flask, g, jsonify, request

from app.api.routes import router


def create_app() -> Flask:
    app = Flask(__name__)
    app.register_blueprint(router)

    @app.before_request
    def _start_request_context() -> None:
        g.request_id = str(uuid.uuid4())
        g.started_at = time.perf_counter()

    @app.after_request
    def _attach_response_metadata(response):
        duration_ms = (time.perf_counter() - g.get("started_at", time.perf_counter())) * 1000
        response.headers["X-Request-Id"] = g.get("request_id", "n/a")
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
        return response

    @app.errorhandler(Exception)
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

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
