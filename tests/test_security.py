import pytest
from app.main import create_app
from app.database import db
from app.models.user import User
from app.services.auth_service import AuthService
import time

@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def auth_service():
    return AuthService()

def test_refresh_token_reuse_detection(client, auth_service, app):
    with app.app_context():
        # 1. Register and login
        auth_service.register_user("testuser", "test@example.com", "password123")
        user = User.query.filter_by(username="testuser").first()
        
        # 2. Generate initial refresh token
        rt1 = auth_service.generate_refresh_token(user.id)
        
        # 3. Rotate once (rt1 -> rt2)
        rotated1 = auth_service.rotate_refresh_token(rt1)
        assert rotated1 is not None
        rt2 = rotated1[1]
        
        # 4. Attempt to REUSE rt1
        reused = auth_service.rotate_refresh_token(rt1)
        assert reused is None
        
        # 5. Verify rt2 is NOW REVOKED because of rt1 reuse detection
        from app.models.db_models import RefreshToken
        rt2_record = RefreshToken.query.filter_by(user_id=user.id, revoked=False).first()
        assert rt2_record is None  # Should be empty because all were revoked

def test_rbac_admin_only(client, auth_service, app):
    with app.app_context():
        auth_service.register_user("admin", "admin@example.com", "password123")
        auth_service.register_user("user", "user@example.com", "password123")
        
        admin = User.query.filter_by(username="admin").first()
        admin.role = "admin"
        db.session.commit()
        
        user = User.query.filter_by(username="user").first()
        
        admin_token = auth_service.generate_token(admin.id)
        user_token = auth_service.generate_token(user.id)
        
        # Attempt access as user
        resp = client.get("/api/v1/admin/health/overview", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 403
        
        # Attempt access as admin
        resp = client.get("/api/v1/admin/health/overview", headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200

def test_account_locking(client, auth_service, app):
    with app.app_context():
        auth_service.register_user("lockme", "lock@example.com", "password123")
        
        # Fail 5 times
        for _ in range(5):
            user = auth_service.authenticate_user("lockme", "wrong")
            
        # Verify locked
        user_record = User.query.filter_by(username="lockme").first()
        assert user_record.locked_until is not None
        
        # Next attempt should return None even with correct password
        user = auth_service.authenticate_user("lockme", "password123")
        assert user is None
