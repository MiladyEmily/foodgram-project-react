from django.contrib.auth import get_user_model
from rest_framework import permissions

from .utils import check_user_is_admin_or_superuser


User = get_user_model()


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Проверяет, является ли пользователь админом или суперюзером.
    Иначе доступ только для чтения.
    """
    def has_permission(self, request, view):
        is_safe = request.method in permissions.SAFE_METHODS
        return (
            is_safe
            or check_user_is_admin_or_superuser(request.user)
        )


class IsAuthorOrAdminOrReadOnly(permissions.BasePermission):
    """
    Проверяет, является ли пользователь админом, суперюзером или автором
    контента.
    Иначе доступ только для чтения.
    """
    def has_permission(self, request, view):
        return (
            request.method in permissions.SAFE_METHODS
            or request.user.is_authenticated
        )

    def has_object_permission(self, request, view, obj):
        return (
            request.method in permissions.SAFE_METHODS
            or (
                request.user.is_authenticated
                and (
                    obj.author == request.user
                    or check_user_is_admin_or_superuser(request.user)
                )
            )
        )
