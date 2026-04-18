import os

try:
    from flask_caching import Cache
except Exception:  # pragma: no cover
    class Cache:  # type: ignore[no-redef]
        def init_app(self, app):
            return None

        def cached(self, timeout=0, query_string=False):
            def decorator(fn):
                return fn

            return decorator

        def get(self, key):
            return None

        def set(self, key, value, timeout=0):
            return None

        def delete(self, key):
            return None

        def clear(self):
            return None


try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except Exception:  # pragma: no cover
    class Limiter:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            pass

        def init_app(self, app):
            return None

        def limit(self, _rule):
            def decorator(fn):
                return fn

            return decorator

    def get_remote_address():
        return "0.0.0.0"


try:
    from flask_migrate import Migrate
except Exception:  # pragma: no cover
    class Migrate:  # type: ignore[no-redef]
        def init_app(self, app, db):
            return None

from app.database import db

cache = Cache()
migrate = Migrate()
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
    default_limits=[os.getenv("RATELIMIT_DEFAULT", "300 per minute")],
)
