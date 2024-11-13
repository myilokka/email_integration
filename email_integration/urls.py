from django.urls import path
from email_integration import views

urlpatterns = [
    path('', views.index, name='index'),
    path('account', views.get_account, name='get_account'),
    path('emails', views.load_emails, name='emails'),
]
