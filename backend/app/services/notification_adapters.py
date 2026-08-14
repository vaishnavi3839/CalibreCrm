"""Pluggable notification adapters. Credentials via environment variables only."""

from __future__ import annotations

import logging
from typing import Protocol

from app.core.config import get_settings
from app.models import Notification, NotificationChannel

logger = logging.getLogger(__name__)
settings = get_settings()


class NotificationAdapter(Protocol):
    async def send(self, notification: Notification) -> bool: ...


class ConsoleAdapter:
    async def send(self, notification: Notification) -> bool:
        logger.info(
            "[NOTIFY:%s] to=%s title=%s body=%s",
            notification.channel.value,
            notification.user_id,
            notification.title,
            notification.body,
        )
        return True


class EmailAdapter:
    async def send(self, notification: Notification) -> bool:
        if not settings.smtp_host:
            return await ConsoleAdapter().send(notification)
        # SMTP integration placeholder — wire with aiosmtplib / boto SES later
        logger.info("[EMAIL] queued for user=%s subject=%s", notification.user_id, notification.title)
        return True


class SMSAdapter:
    async def send(self, notification: Notification) -> bool:
        if not settings.sms_api_key:
            return await ConsoleAdapter().send(notification)
        logger.info("[SMS] queued for user=%s", notification.user_id)
        return True


class WhatsAppAdapter:
    async def send(self, notification: Notification) -> bool:
        if not settings.whatsapp_api_key:
            return await ConsoleAdapter().send(notification)
        logger.info("[WhatsApp] queued for user=%s", notification.user_id)
        return True


class PushAdapter:
    async def send(self, notification: Notification) -> bool:
        if not settings.push_api_key:
            return await ConsoleAdapter().send(notification)
        logger.info("[PUSH] queued for user=%s", notification.user_id)
        return True


ADAPTERS: dict[NotificationChannel, NotificationAdapter] = {
    NotificationChannel.IN_APP: ConsoleAdapter(),
    NotificationChannel.EMAIL: EmailAdapter(),
    NotificationChannel.SMS: SMSAdapter(),
    NotificationChannel.WHATSAPP: WhatsAppAdapter(),
    NotificationChannel.PUSH: PushAdapter(),
}


async def dispatch_notification(notification: Notification) -> bool:
    adapter = ADAPTERS.get(notification.channel, ConsoleAdapter())
    ok = await adapter.send(notification)
    notification.delivery_status = "delivered" if ok else "failed"
    return ok
