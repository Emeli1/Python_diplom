from __future__ import annotations
import os
from celery import Celery
 
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "orders.settings")
 
app = Celery("orders")
app.config_from_object("django.conf:settings", namespace="CELERY") # Настройки Celery из настроек Django с префиксом CELERY_
app.autodiscover_tasks() # Автоматическое обнаружение задач в приложениях Django