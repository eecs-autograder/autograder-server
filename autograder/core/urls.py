from django.conf import settings
from django.http import HttpResponse
from django.urls import path
from rest_framework.decorators import (
    api_view, permission_classes, schema, throttle_classes)
from rest_framework.throttling import UserRateThrottle

import gnupg

from autograder.core.submission_email_receipts import check_signature


class DecryptEmailReceiptThrottle(UserRateThrottle):
    rate = '60/minute'


@api_view(['GET'])
@schema(None)
@permission_classes([])
@throttle_classes([DecryptEmailReceiptThrottle])
def check_email_receipt_signature_view(request, *args, encoded_signed_msg):
    verified, decoded_msg = check_signature(encoded_signed_msg)

    response_data = 'Signature verification '
    if verified:
        response_data += 'SUCCESS. Original message shown below.\n\n'
        response_data += decoded_msg
    else:
        response_data += 'FAILED. This means the message may have been modified.'

    return HttpResponse(response_data, content_type='text/plain')


@api_view(['GET'])
@schema(None)
@permission_classes([])
def get_gpg_public_key_view(*args, **kwargs):
    gpg = gnupg.GPG(gnupghome=settings.SECRETS_DIR)
    return HttpResponse(gpg.export_keys(settings.GPG_KEY_ID), content_type='text/plain')


urlpatterns = [
    path('check_email_submission_receipt_signature/<str:encoded_signed_msg>/',
         check_email_receipt_signature_view,
         name='verify-submission-receipt-email'),
    path('gpg_public_key/', get_gpg_public_key_view)
]
