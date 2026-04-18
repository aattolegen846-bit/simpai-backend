from datetime import datetime, timedelta, timezone

from typing import List, Optional

from app.database import db
from app.models.db_models import InAppReminder
from app.models.schemas import ReminderDto


class ReminderService:
    def schedule_followup_reminder(
        self, user_id: str, reminder_type: str, payload: dict, after_hours: int = 24
    ) -> ReminderDto:
        reminder = InAppReminder(
            user_id=int(user_id),
            reminder_type=reminder_type,
            due_at=datetime.now(timezone.utc) + timedelta(hours=max(1, after_hours)),
            payload=payload,
            status="pending",
        )
        db.session.add(reminder)
        db.session.commit()
        return self._to_dto(reminder)

    def get_user_reminders(self, user_id: str, status: Optional[str] = None) -> List[ReminderDto]:
        query = InAppReminder.query.filter_by(user_id=int(user_id))
        if status:
            query = query.filter_by(status=status)
        reminders = query.order_by(InAppReminder.due_at.asc()).all()
        return [self._to_dto(item) for item in reminders]

    def acknowledge_reminder(self, user_id: str, reminder_id: int) -> ReminderDto:
        reminder = InAppReminder.query.filter_by(id=reminder_id, user_id=int(user_id)).first()
        if not reminder:
            raise ValueError("reminder not found")
        reminder.status = "acknowledged"
        reminder.acknowledged_at = datetime.now(timezone.utc)
        db.session.commit()
        return self._to_dto(reminder)

    @staticmethod
    def _to_dto(reminder: InAppReminder) -> ReminderDto:
        return ReminderDto(
            id=reminder.id,
            reminder_type=reminder.reminder_type,
            due_at=reminder.due_at.isoformat(),
            status=reminder.status,
            payload=reminder.payload or {},
        )
