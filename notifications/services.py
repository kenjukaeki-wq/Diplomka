"""Уведомление сохраняется в базе, после чего событие передаётся браузеру."""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from .models import Notification, TelegramDelivery

logger = logging.getLogger(__name__)


def broadcast(group_name, payload):
    """Отправить событие всем соединениям выбранной группы Channels."""
    channel_layer = get_channel_layer()
    message = {"type": "event", "payload": payload}
    try:
        async_to_sync(channel_layer.group_send)(group_name, message)
    except Exception:
        # Сбой Redis не должен отменять уже сохранённую оценку или занятие.
        logger.exception("Не удалось отправить WebSocket-событие")


def after_commit(group_name, payload):
    """Сначала сохранить изменения БД, затем сообщить о них браузеру."""

    def send():
        broadcast(group_name, payload)

    transaction.on_commit(send)


@transaction.atomic
def notify(user, text, url, event_key):
    # event_key — имя события, например lesson:5:start.
    # get_or_create не создаёт повторное уведомление о том же событии.
    notification, created = Notification.objects.get_or_create(
        recipient=user,
        event_key=event_key,
        defaults={"text": text[:500], "url": url},
    )
    if not created:
        return notification

    if hasattr(user, "telegram"):
        TelegramDelivery.objects.create(notification=notification)

    after_commit(
        f"user_{user.pk}",
        {
            "event": "notification.created",
            "text": notification.text,
            "url": url,
        },
    )
    return notification


def notify_group(group, text, url, event_key):
    """Создать персональное уведомление каждому ученику группы."""
    for membership in group.memberships.select_related("student"):
        notify(membership.student, text, url, event_key)
