import json
from typing import Dict, Optional

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from email_integration.models import EmailAccount
from email_integration.service import EmailService, EmailServiceException
from email_integration.tasks import import_emails


@require_http_methods(["GET"])
def index(request) -> JsonResponse:
    return render(request, 'email_integration/index.html')


@require_http_methods(["POST"])
def get_account(request) -> JsonResponse:
    try:
        data: Dict[str, str] = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError as e:
        return JsonResponse(status=400, data={'error': str(e)})

    email: Optional[str] = data.get('email')
    password: Optional[str] = data.get('password')

    if not email or not password:
        return JsonResponse(status=400, data={'error': 'Email and password are required'})

    try:
        service = EmailService(email=email, password=password)
        service.validate_login_creds()
    except EmailServiceException as e:
        return JsonResponse(status=e.code, data={'error': str(e)})

    account, _ = EmailAccount.objects.get_or_create(email=email, defaults={'password': password})
    return JsonResponse({'id': account.id})


@require_http_methods(["GET"])
def load_emails(request) -> JsonResponse:
    account_id: Optional[str] = request.GET.get('account_id')
    if not account_id:
        return JsonResponse(status=400, data={'error': 'Account ID is required'})

    try:
        account = EmailAccount.objects.get(id=account_id)
    except EmailAccount.DoesNotExist:
        return JsonResponse(status=404, data={'error': 'EmailAccount not found'})

    import_emails.delay(account.email, account.password)
    return render(request, 'email_integration/emails.html')