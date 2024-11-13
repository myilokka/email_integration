from django.urls import re_path
from email_integration.consumers import EmailImportProgressConsumer

websocket_urlpatterns = [
    re_path('ws/email_import/', EmailImportProgressConsumer.as_asgi()),  # Укажите путь к вашему consumer
]
