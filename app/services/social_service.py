from typing import List, Dict
from app.models.user import User
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
