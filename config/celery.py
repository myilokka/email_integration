from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

from django.conf import settings

# Задаем настройки Django для Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
app = Celery('config', broker=f'redis://{settings.REDIS_HOST_ENV}:{settings.REDIS_PORT_ENV}/0',
             backend=f'redis://{settings.REDIS_HOST_ENV}:{settings.REDIS_PORT_ENV}/0')
app.config_from_object(f'django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(settings.INSTALLED_APPS)
