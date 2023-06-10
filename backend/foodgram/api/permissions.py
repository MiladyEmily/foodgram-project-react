from rest_framework import permissions
from django.contrib.auth import get_user_model


User = get_user_model()


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Проверяет, является ли пользователь админом или суперюзером.
    """
    def has_permission(self, request, view):
        is_safe = request.method in permissions.SAFE_METHODS
        return (
            is_safe
            or check_user_is_admin_or_superuser(request.user)
        )


class IsAuthorOrAdminOrReadOnly(permissions.BasePermission):
    """
    Проверяет, является ли пользователь админом или суперюзером.
    """
    def has_permission(self, request, view):
        is_safe = request.method in permissions.SAFE_METHODS
        return (
            is_safe
            or request.user.is_staff
            or check_user_is_admin_or_superuser(request.user)
        )


def check_user_is_admin_or_superuser(user):
    return (
        user.is_authenticated
        and (
            user.is_superuser
            or user.is_admin
        )
    )
