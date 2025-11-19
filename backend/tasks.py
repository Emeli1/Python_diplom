from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives


@shared_task(name="backend.send_email")
def send_email(to_email: str, subject: str, message: str) -> None:
    """
    Отправка электронного письма.
    Через Celery.
    """
    msg = EmailMultiAlternatives(
        subject,
        message,
        getattr(settings, "DEFAULT_FROM_EMAIL", None),
        [to_email],
    )
    msg.send()


@shared_task(name="backend.do_import")
def do_import(file_path: str | None = None) -> dict:
    """
    Импорт данных из YAML файла.
    Через Celery.
    """
    from backend.services.importer import import_data_from_yaml
    return import_data_from_yaml(file_path)
