import pytest
from app.main import create_app
from app.database import db
from app.models.user import User
from app.models.db_models import UserQuest, UserConnection, FriendChallenge
from app.services.engagement_service import EngagementService
from app.services.social_service import SocialService
from app.services.gamification_service import GamificationService

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "CACHE_TYPE": "NullCache",
        "RATELIMIT_ENABLED": False
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_quest_initialization(app):
    with app.app_context():
        # Create user
        user = User(username="testuser", email="test@example.com", password_hash="hash")
        db.session.add(user)
        db.session.commit()
        
        # Initialize quests
        EngagementService.initialize_daily_quests(user.id)
        quests = UserQuest.query.filter_by(user_id=user.id).all()
        
        assert len(quests) == 3
        assert any(q.quest_type == "xp_goal" for q in quests)

def test_social_following(app):
    with app.app_context():
        u1 = User(username="user1", email="u1@ex.com", password_hash="h")
        u2 = User(username="user2", email="u2@ex.com", password_hash="h")
        db.session.add_all([u1, u2])
        db.session.commit()
        
        # Follow
        success = SocialService.follow_user(u1.id, "user2")
        assert success is True
        
        conn = UserConnection.query.filter_by(follower_id=u1.id, followed_id=u2.id).first()
        assert conn is not None

def test_challenge_progression(app):
    with app.app_context():
        u1 = User(username="u1", email="u1@ex.com", password_hash="h")
        u2 = User(username="u2", email="u2@ex.com", password_hash="h")
        db.session.add_all([u1, u2])
        db.session.commit()
        
        # Create challenge
        SocialService.create_friend_challenge(u1.id, "u2", goal_xp=100)
        
        # Update XP
        # This should trigger challenge XP update via GamificationService
        GamificationService.update_xp(u1.id, 50)
        
        challenge = FriendChallenge.query.filter_by(creator_id=u1.id).first()
        assert challenge.creator_xp == 50
        assert challenge.status == "active"
        
        # Finish challenge
        GamificationService.update_xp(u1.id, 60)
        assert challenge.status == "completed"

def test_quest_progress_via_xp(app):
    with app.app_context():
        user = User(username="q_user", email="q@ex.com", password_hash="h")
        db.session.add(user)
        db.session.commit()
        
        EngagementService.initialize_daily_quests(user.id)
        
        # Earn XP
        GamificationService.update_xp(user.id, 120)
        
        quest = UserQuest.query.filter_by(user_id=user.id, quest_type="xp_goal").first()
        assert quest.current_value >= 100
        assert quest.status == "completed"
