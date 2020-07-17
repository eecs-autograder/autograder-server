from django.http import HttpResponse
from django.urls import path
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from autograder.core.submission_email_receipts import decrypt_message


class DecryptEmailReceiptThrottle(UserRateThrottle):
    rate = '60/minute'


@api_view(['GET'])
@permission_classes([])
@throttle_classes([DecryptEmailReceiptThrottle])
def decrypt_email_receipt_view(request, *args, encrypted_msg):
    return HttpResponse(
        decrypt_message(encrypted_msg), content_type="text/plain"
    )


urlpatterns = [
    path('validate_submission_receipt_email/<str:encrypted_msg>/',
         decrypt_email_receipt_view,
         name='validate-submission-receipt-email')
]
