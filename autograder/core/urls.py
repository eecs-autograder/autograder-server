from django.http import HttpResponse
from django.urls import path

from autograder.core.submission_email_receipts import decrypt_message


def decrypt_email_receipt_view(request, *args, encrypted_msg):
    return HttpResponse(
        decrypt_message(encrypted_msg), content_type="text/plain"
    )


urlpatterns = [
    path('validate_submission_receipt_email/<str:encrypted_msg>/',
         decrypt_email_receipt_view,
         name='validate-submission-receipt-email')
]
