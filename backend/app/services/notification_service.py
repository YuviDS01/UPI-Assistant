"""
Notification service. Phase 1-era channel is console + DB row (spec §21).
Real email/SMS/push integration is a later-phase concern behind the same
`notify` call — nothing upstream needs to change when that lands.
"""

import logging
import uuid

from sqlalchemy.orm import Session

from app.models import Notification

logger = logging.getLogger("app.notifications")


class NotificationService:
    @staticmethod
    def notify(
        db: Session, user_id: uuid.UUID, title: str, body: str, channel: str = "console"
    ) -> Notification:
        notification = Notification(user_id=user_id, title=title, body=body, channel=channel)
        db.add(notification)
        db.flush()

        if channel == "console":
            logger.info(f"[notification] {title}: {body}", extra={"extra_fields": {"user_id": str(user_id)}})

        return notification