from datetime import date, timedelta

from app.database import db
from app.models.db_models import UserProgress
from app.models.schemas import ProgressSnapshot


class ProgressService:
    def award_xp_and_update_streak(self, user_id: str, xp_delta: int) -> ProgressSnapshot:
        progress = UserProgress.query.filter_by(user_id=int(user_id)).first()
        if not progress:
            progress = UserProgress(user_id=int(user_id), xp_total=0, streak_days=0)
            db.session.add(progress)

        xp_delta = max(0, xp_delta)
        today = date.today()
        yesterday = today - timedelta(days=1)

        if progress.last_activity_date == today:
            # Same day activity should not increment streak repeatedly.
            pass
        elif progress.last_activity_date == yesterday:
            progress.streak_days += 1
        else:
            progress.streak_days = 1

        progress.last_activity_date = today
        progress.xp_total += xp_delta
        db.session.commit()

        return ProgressSnapshot(
            user_id=user_id,
            xp_total=progress.xp_total,
            streak_days=progress.streak_days,
            last_activity_date=progress.last_activity_date.isoformat(),
        )

    def get_progress(self, user_id: str) -> ProgressSnapshot:
        progress = UserProgress.query.filter_by(user_id=int(user_id)).first()
        if not progress:
            return ProgressSnapshot(
                user_id=user_id,
                xp_total=0,
                streak_days=0,
                last_activity_date=None,
            )
        return ProgressSnapshot(
            user_id=user_id,
            xp_total=progress.xp_total,
            streak_days=progress.streak_days,
            last_activity_date=(
                progress.last_activity_date.isoformat() if progress.last_activity_date else None
            ),
        )
