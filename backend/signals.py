from typing import Type
from django.db.models.signals import post_save
from django.dispatch import Signal, receiver
from django_rest_passwordreset.signals import reset_password_token_created
from backend.models import User, ConfirmEmailToken
from backend.tasks import send_email


new_user_registered = Signal()
new_order = Signal()

@receiver(reset_password_token_created)
def password_reset_token_created_receiver(sender, instance, reset_password_token, *args, **kwargs):
    """
    Отправка письма с токеном для сброса пароля.
    Через Celery.
    """
    send_email.delay(
        to_email=reset_password_token.user.email,
        subject=f"Токен сброса пароля для {reset_password_token.user}",
        message=f"Ваш токен для сброса пароля: {reset_password_token.key}",
    )


@receiver(post_save, sender=User)
def new_user_registered_receiver(sender: Type[User], instance: User, created: bool, **kwargs):
    """
    Отправка письма с подтверждением почты.
    Через Celery.
    """
    if created and not instance.is_active:
        token, _ = ConfirmEmailToken.objects.get_or_create(user_id=instance.pk)
        send_email.delay(
            to_email=instance.email,
            subject="Подтвердите свой адрес электронной почты",
            message=f"Ваш токен подтверждения: {token.key}",
        )


@receiver(new_order)
def new_order_signal(sender, user_id, **kwargs):
    """
    Отправка письма с информацией о новом заказе.
    Через Celery.
    """
    try:
        user = User.objects.get(pk=user_id)
        send_email.delay(
            to_email=user.email,
            subject="Новый заказ создан",
            message="Ваш заказ успешно создан.",
        )
    except User.DoesNotExist:
        pass