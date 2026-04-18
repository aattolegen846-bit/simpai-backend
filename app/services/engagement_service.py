import datetime
from typing import List, Optional

from app.database import db
from app.models.db_models import UserQuest, InAppReminder, UserEvent
from app.models.user import User


class EngagementService:
    @staticmethod
    def initialize_daily_quests(user_id: int):
        """
        Creates 3 daily quests for the user if they don't have them for today.
        """
        today = datetime.datetime.now(datetime.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        deadline = today + datetime.timedelta(days=1)
        
        existing = UserQuest.query.filter(
            UserQuest.user_id == user_id, 
            UserQuest.deadline == deadline
        ).first()
        
        if existing:
            return
            
        quests = [
            UserQuest(user_id=user_id, quest_type="xp_goal", target_value=100, deadline=deadline),
            UserQuest(user_id=user_id, quest_type="perfect_lesson", target_value=1, deadline=deadline),
            UserQuest(user_id=user_id, quest_type="vocab_master", target_value=5, deadline=deadline)
        ]
        db.session.add_all(quests)
        db.session.commit()

    @staticmethod
    def update_quest_progress(user_id: int, quest_type: str, increment: int = 1):
        """
        Updates the progress of a specific quest type for the user.
        """
        now = datetime.datetime.now(datetime.timezone.utc)
        quests = UserQuest.query.filter(
            UserQuest.user_id == user_id,
            UserQuest.quest_type == quest_type,
            UserQuest.status == "in_progress",
            UserQuest.deadline > now
        ).all()
        
        for q in quests:
            if q.current_value is None: q.current_value = 0
            q.current_value += increment
            if q.current_value >= q.target_value:
                q.status = "completed"
                # Trigger a nudge
                EngagementService.trigger_nudge(
                    user_id, 
                    "quest_completed", 
                    {"quest_type": quest_type, "message": f"Congratulations! You completed the {quest_type} quest!"}
                )
        
        db.session.commit()

    @staticmethod
    def trigger_nudge(user_id: int, nudge_type: str, payload: dict):
        """
        Creates an in-app reminder (nudge) for the user.
        """
        nudge = InAppReminder(
            user_id=user_id,
            reminder_type=nudge_type,
            due_at=datetime.datetime.now(datetime.timezone.utc),
            payload=payload
        )
        db.session.add(nudge)
        db.session.commit()

    @staticmethod
    def get_active_quests(user_id: int) -> List[dict]:
        now = datetime.datetime.now(datetime.timezone.utc)
        quests = UserQuest.query.filter(
            UserQuest.user_id == user_id,
            UserQuest.deadline > now
        ).all()
        return [
            {
                "id": q.id,
                "type": q.quest_type,
                "target": q.target_value,
                "current": q.current_value,
                "status": q.status,
                "deadline": q.deadline.isoformat()
            }
            for q in quests
        ]
