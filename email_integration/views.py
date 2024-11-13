import json

from django.http import JsonResponse
from django.shortcuts import render

from email_integration.models import EmailAccount
from email_integration.service import EmailService, EmailServiceException
from email_integration.tasks import import_emails


def index(request):
    return render(request, 'email_integration/index.html')


def get_account(request, ):
    data = json.loads(request.body.decode('utf-8'))
    email = data.get('email')
    password = data.get('password')

    try:
        service = EmailService(email=email, password=password)
        service.validate_login_creds()
    except EmailServiceException as e:
        return JsonResponse(status=e.code, data={'error': str(e)})

    account = EmailAccount.objects.filter(email=email).first()
    if not account:
        account = EmailAccount.objects.create(email=email, password=password)
    return JsonResponse({'id': account.id})


def load_emails(request):
    account_id = request.GET.get('account_id')
    try:
        account = EmailAccount.objects.get(id=account_id)
    except EmailAccount.DoesNotExist:
        return JsonResponse(status=404, data={'error': 'EmailAccount not found'})
    import_emails.delay(account.email, account.password)
    # service = EmailService(email=account.email, password=account.password)
    # for email_data in service.fetch_emails():
    #     print(email_data)

    # return JsonResponse({'status': 'success'})
    return render(request, 'email_integration/emails.html')
