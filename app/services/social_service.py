from typing import List, Dict, Optional
import datetime
from app.models.user import User
from app.models.db_models import UserConnection, UserEvent, FriendChallenge
from app.database import db

class SocialService:
    @staticmethod
    def get_leaderboard(limit: int = 10) -> List[Dict]:
        """
        Returns top users by points.
        """
        top_users = User.query.order_by(User.points.desc()).limit(limit).all()
        return [
            {
                "username": u.username,
                "points": u.points,
                "cefr_level": u.cefr_level,
                "rank": i + 1
            }
            for i, u in enumerate(top_users)
        ]

    @staticmethod
    def award_points(user_id: int, points: int) -> bool:
        user = db.session.get(User, user_id)
        if user:
            user.points += points
            db.session.commit()
            return True
        return False

    @staticmethod
    def check_achievements(user_id: int) -> List[str]:
        """
        Logic to check if user unlocked any badges.
        """
        user = db.session.get(User, user_id)
        achievements = []
        if user.points > 1000:
            achievements.append("Language Master")
        if user.points > 500:
            achievements.append("Determined Learner")
        return achievements

    @staticmethod
    def follow_user(follower_id: int, target_username: str) -> bool:
        target = User.query.filter_by(username=target_username).first()
        if not target or target.id == follower_id:
            return False
            
        existing = UserConnection.query.filter_by(follower_id=follower_id, followed_id=target.id).first()
        if existing:
            return True
            
        new_conn = UserConnection(follower_id=follower_id, followed_id=target.id)
        db.session.add(new_conn)
        db.session.commit()
        return True

    @staticmethod
    def get_following_activity(user_id: int, limit: int = 20) -> List[Dict]:
        """
        Returns a feed of activity from people the user follows.
        """
        following = UserConnection.query.filter_by(follower_id=user_id).all()
        followed_ids = [c.followed_id for c in following]
        
        if not followed_ids:
            return []
            
        events = UserEvent.query.filter(UserEvent.user_id.in_(followed_ids)).order_by(UserEvent.timestamp.desc()).limit(limit).all()
        
        feed = []
        for e in events:
            user = db.session.get(User, e.user_id)
            feed.append({
                "username": user.username if user else "Unknown",
                "event_type": e.event_type,
                "data": e.data,
                "timestamp": e.timestamp.isoformat()
            })
        return feed

    @staticmethod
    def create_friend_challenge(creator_id: int, opponent_username: str, goal_xp: int = 500) -> Optional[dict]:
        opponent = User.query.filter_by(username=opponent_username).first()
        if not opponent or opponent.id == creator_id:
            return None
            
        expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)
        challenge = FriendChallenge(
            creator_id=creator_id,
            opponent_id=opponent.id,
            goal_xp=goal_xp,
            expires_at=expires_at
        )
        db.session.add(challenge)
        db.session.commit()
        
        return {
            "challenge_id": challenge.id,
            "opponent": opponent.username,
            "goal_xp": goal_xp,
            "expires_at": expires_at.isoformat()
        }

    @staticmethod
    def get_active_challenges(user_id: int) -> List[Dict]:
        challenges = FriendChallenge.query.filter(
            ((FriendChallenge.creator_id == user_id) | (FriendChallenge.opponent_id == user_id)),
            FriendChallenge.status == "active"
        ).all()
        
        results = []
        for c in challenges:
            creator = db.session.get(User, c.creator_id)
            opponent = db.session.get(User, c.opponent_id)
            results.append({
                "id": c.id,
                "creator": creator.username,
                "opponent": opponent.username,
                "creator_xp": c.creator_xp,
                "opponent_xp": c.opponent_xp,
                "goal_xp": c.goal_xp,
                "expires_at": c.expires_at.isoformat()
            })
        return results
