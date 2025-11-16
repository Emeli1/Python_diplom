from typing import Type
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models.signals import post_save
from django.dispatch import Signal, receiver
from django_rest_passwordreset.signals import reset_password_token_created

from backend.models import User, ConfirmEmailToken

new_user_registered = Signal()
new_order = Signal()

@receiver(reset_password_token_created)
def password_reset_token_created_receiver(sender, instance, reset_password_token, *kwargs):
    """
    Отправка письма с токеном для сброса пароля.
    """
    msg = EmailMultiAlternatives(
        # title:
        f"Токен сброса пароля для {reset_password_token.user}",
        # message:
        f"Ваш токен для сброса пароля: {reset_password_token.key}",
        # from:
        settings.DEFAULT_FROM_EMAIL,
        # to:
        [reset_password_token.user.email]
    )
    msg.send()


@receiver(post_save, sender=User)
def new_user_registered_receiver(sender: Type[User], instance: User, created: bool, **kwargs):
    """
    Отправка письма с подтверждением почты.
    """
    if created and not instance.is_active:
        token, _ = ConfirmEmailToken.objects.get_or_create(user_id=instance.pk)
        msg = EmailMultiAlternatives(
            # title:
            "Подтвердите свой адрес электронной почты",
            # message:
            f"Ваш токен подтверждения: {token.key}",
            # from:
            settings.DEFAULT_FROM_EMAIL,
            # to:
            [instance.email]
        )
        msg.send()


@receiver(new_order)
def new_order_signal(user_id, **kwargs):
    """
    Отправка письма с информацией о новом заказе.
    """
    try:
        user = User.objects.get(pk=user_id)
        msg = EmailMultiAlternatives(
            # title:
            "Новый заказ создан",
            # message:
            "Ваш заказ успешно создан.",
            # from:
            settings.DEFAULT_FROM_EMAIL,
            # to:
            [user.email]
        )
        msg.send()
    except User.DoesNotExist:
        pass