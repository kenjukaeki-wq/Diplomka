from django.core.exceptions import PermissionDenied
from django.db.models import Q
from .models import StudyGroup


def groups_for(user):
    """Вернуть группы, которые пользователь ведёт или посещает."""
    return StudyGroup.objects.filter(
        Q(teacher=user) | Q(memberships__student=user)
    ).distinct()


def can_access(user, group):
    """Вернуть True, если пользователь — преподаватель или ученик группы."""
    return user.is_authenticated and (
        group.teacher_id == user.pk or group.memberships.filter(student=user).exists()
    )


def require_access(user, group):
    """Запретить доступ к чужой группе (HTTP 403)."""
    if not can_access(user, group):
        raise PermissionDenied("Нет доступа к этой группе.")


def require_teacher(user, group=None):
    """Разрешить действие только преподавателю этой группы."""
    if (
        not user.is_authenticated
        or not user.is_teacher
        or (group and group.teacher_id != user.pk)
    ):
        raise PermissionDenied("Действие доступно только преподавателю этой группы.")
