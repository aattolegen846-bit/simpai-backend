import datetime
from typing import List, Optional

from app.database import db
from app.models.db_models import Achievement, LeagueAssignment, UserProgress, FriendChallenge
from app.models.user import User
from app.services.engagement_service import EngagementService


class GamificationService:
    @staticmethod
    def update_xp(user_id: int, xp_gained: int) -> dict:
        """
        Updates a user's XP, checks daily goals, and marks progress in current league.
        """
        progress = UserProgress.query.filter_by(user_id=user_id).first()
        if not progress:
            progress = UserProgress(user_id=user_id, xp_total=0, daily_xp_current=0)
            db.session.add(progress)
        
        if progress.xp_total is None: progress.xp_total = 0
        if progress.daily_xp_current is None: progress.daily_xp_current = 0

        progress.xp_total += xp_gained
        progress.daily_xp_current += xp_gained
        
        # NEW: Update Quests
        EngagementService.update_quest_progress(user_id, "xp_goal", xp_gained)
        
        # Sync with User points for legacy compatibility
        user = db.session.get(User, user_id)
        if user:
            user.points += xp_gained

        # Check Daily Goal
        goal_reached = False
        if progress.daily_xp_current >= progress.daily_xp_target:
            # We could trigger a special badge here if it's the first time today
            goal_reached = True

        # Update League XP for current week
        today = datetime.date.today()
        # Find start of week (Monday)
        week_start = today - datetime.timedelta(days=today.weekday())
        
        league_assign = LeagueAssignment.query.filter_by(
            user_id=user_id, week_start=week_start
        ).first()
        
        if not league_assign:
            league_assign = LeagueAssignment(
                user_id=user_id,
                league_name=progress.current_league,
                week_start=week_start,
                xp_earned=0
            )
            db.session.add(league_assign)
        
        if league_assign.xp_earned is None: league_assign.xp_earned = 0
        league_assign.xp_earned += xp_gained
        
        # NEW: Update active Friend Challenges
        challenges = FriendChallenge.query.filter(
            ((FriendChallenge.creator_id == user_id) | (FriendChallenge.opponent_id == user_id)),
            FriendChallenge.status == "active"
        ).all()
        for c in challenges:
            if c.creator_xp is None: c.creator_xp = 0
            if c.opponent_xp is None: c.opponent_xp = 0
            
            if c.creator_id == user_id:
                c.creator_xp += xp_gained
            else:
                c.opponent_xp += xp_gained
            
            # Check for completion
            if c.creator_xp >= c.goal_xp or c.opponent_xp >= c.goal_xp:
                c.status = "completed"
                # Nudge winner/loser (Simplified)
                EngagementService.trigger_nudge(c.creator_id, "challenge_finished", {"id": c.id})
                EngagementService.trigger_nudge(c.opponent_id, "challenge_finished", {"id": c.id})
        
        db.session.commit()
        
        return {
            "xp_gained": xp_gained,
            "total_xp": progress.xp_total,
            "daily_xp": progress.daily_xp_current,
            "daily_goal": progress.daily_xp_target,
            "goal_reached": goal_reached,
            "league": progress.current_league
        }

    @staticmethod
    def get_achievements(user_id: int) -> List[dict]:
        achievements = Achievement.query.filter_by(user_id=user_id).all()
        return [
            {
                "name": a.name,
                "description": a.description,
                "unlocked_at": a.unlocked_at.isoformat()
            }
            for a in achievements
        ]

    @staticmethod
    def award_achievement(user_id: int, name: str, description: str) -> bool:
        existing = Achievement.query.filter_by(user_id=user_id, name=name).first()
        if existing:
            return False
            
        new_ach = Achievement(user_id=user_id, name=name, description=description)
        db.session.add(new_ach)
        db.session.commit()
        return True

    @staticmethod
    def get_league_leaderboard(user_id: int) -> dict:
        """
        Returns the leaderboard for the user's current league tier.
        For the demo, we simulate a few other 'pro' users if the league is empty.
        """
        progress = UserProgress.query.filter_by(user_id=user_id).first()
        league_name = progress.current_league if progress else "Bronze"
        
        today = datetime.date.today()
        week_start = today - datetime.timedelta(days=today.weekday())
        
        assignments = LeagueAssignment.query.filter_by(
            league_name=league_name, week_start=week_start
        ).order_by(LeagueAssignment.xp_earned.desc()).limit(30).all()
        
        leaderboard = []
        for i, assign in enumerate(assignments):
            user = db.session.get(User, assign.user_id)
            leaderboard.append({
                "username": user.username if user else f"User_{assign.user_id}",
                "xp_earned": assign.xp_earned,
                "rank": i + 1,
                "is_current_user": assign.user_id == user_id
            })
            
        # Demo simulation: if fewer than 5 users, add some high-score bots
        if len(leaderboard) < 5:
            bots = [
                {"username": "DuolingoMaster", "xp_earned": 1250, "rank": 1},
                {"username": "PolyglotPro", "xp_earned": 980, "rank": 2},
                {"username": "LanguageGeek", "xp_earned": 750, "rank": 3}
            ]
            # Re-rank with bots
            combined = leaderboard + bots
            combined.sort(key=lambda x: x.get("xp_earned", 0), reverse=True)
            for i, item in enumerate(combined):
                item["rank"] = i + 1
            return {"league": league_name, "leaderboard": combined[:10]}

        return {"league": league_name, "leaderboard": leaderboard}
