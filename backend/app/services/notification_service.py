from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification, NotificationChannel


async def notify_user(
    db: AsyncSession,
    *,
    user_id: UUID,
    title: str,
    body: str,
    category: str = "general",
    channel: NotificationChannel = NotificationChannel.IN_APP,
    link: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> Notification:
    """Create an in-app notification and enqueue multi-channel delivery.

    Channel adapters (email/SMS/WhatsApp/push) are pluggable — see
    `app/services/notification_adapters.py`. Credentials come from env vars.
    """
    notification = Notification(
        user_id=user_id,
        title=title,
        body=body,
        category=category,
        channel=channel,
        link=link,
        metadata_json=metadata or {},
        delivery_status="delivered" if channel == NotificationChannel.IN_APP else "pending",
    )
    db.add(notification)
    await db.flush()

    # Dispatch to external adapters when channel is not in-app only.
    # Multi-channel fan-out can be expanded by creating additional Notification rows
    # or a delivery queue consumer.
    if channel != NotificationChannel.IN_APP:
        from app.services.notification_adapters import dispatch_notification

        await dispatch_notification(notification)

    return notification


async def notify_users(
    db: AsyncSession,
    *,
    user_ids: list[UUID],
    title: str,
    body: str,
    category: str = "general",
    link: Optional[str] = None,
) -> list[Notification]:
    notes = []
    for uid in user_ids:
        notes.append(
            await notify_user(
                db,
                user_id=uid,
                title=title,
                body=body,
                category=category,
                link=link,
            )
        )
    return notes
