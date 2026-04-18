import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True, scope="session")
def _reset_test_database():
    from app.main import application
    from app.database import db
    import app.models.user  # noqa: F401
    import app.models.db_models  # noqa: F401

    with application.app_context():
        db.drop_all()
        db.create_all()

    yield
