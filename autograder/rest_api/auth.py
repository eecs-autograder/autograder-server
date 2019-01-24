import json

from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse

from rest_framework.authentication import BaseAuthentication, TokenAuthentication

from oauth2client import client


GOOGLE_API_SCOPES = [
    'openid',
    'email',
    'profile',
]


class GoogleOAuth2(TokenAuthentication):
    def authenticate_header(self, request):
        redirect_uri = request.build_absolute_uri(reverse('oauth2callback'))
        flow = client.flow_from_clientsecrets(
            settings.OAUTH2_SECRETS_PATH,
            scope=GOOGLE_API_SCOPES,
            redirect_uri=redirect_uri)

        state = {
            'http_referer': request.META.get('HTTP_REFERER',
                                             request.build_absolute_uri()),
            'redirect_uri': redirect_uri
        }

        return 'Redirect_to: ' + flow.step1_get_authorize_url(state=json.dumps(state))


# DO NOT USE IN PRODUCTION
class DevAuth(BaseAuthentication):
    def authenticate(self, request):
        username = request.COOKIES.get('username', 'jameslp@umich.edu')
        user = User.objects.get_or_create(username=username)[0]
        return user, None
