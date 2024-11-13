from django.db import models


class EmailAccount(models.Model):
    id = models.AutoField(primary_key=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # Хранить зашифрованным для безопасности


class EmailMessage(models.Model):
    id = models.AutoField(primary_key=True)
    email_account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE)
    subject = models.CharField(max_length=255)
    send_date = models.DateTimeField()
    received_date = models.DateTimeField(auto_now_add=True, null=True)
    text = models.TextField()
    attachments = models.JSONField()
    unique_hash = models.CharField(max_length=255, unique=True, null=True)
