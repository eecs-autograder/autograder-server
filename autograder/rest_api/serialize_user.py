from django.contrib.auth.models import User


def serialize_user(user: User) -> dict:
    return {
        'pk': user.pk,
        'username': user.username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'is_superuser': user.is_superuser,
    }
