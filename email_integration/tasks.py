from celery import shared_task
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from email_integration.service import EmailService


@shared_task(bind=True, )
def import_emails(self, email: str, password: str):
    service = EmailService(email=email, password=password)
    channel_layer = get_channel_layer()
    for email_data in service.fetch_emails():
        if email_data.get('checked_messages'):
            async_to_sync(channel_layer.group_send)(
                "email_import_progress", {
                    "type": "update_message_progress",
                    "checked_messages": email_data['checked_messages'],
                })
        else:
            idx = email_data.pop('k')
            async_to_sync(channel_layer.group_send)(
                "email_import_progress", {
                    "type": "update_message_progress",
                    "progress": (idx + 1) / email_data.pop('messages_count') * 100,
                    "message": email_data
                }
            )
