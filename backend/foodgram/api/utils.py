def check_user_is_admin_or_superuser(user):
    """
    Проверяет, является ли пользователь админом или суперюзером.
    """
    return (
        user.is_authenticated
        and (
            user.is_superuser
            or user.is_staff
        )
    )