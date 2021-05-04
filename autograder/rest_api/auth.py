import json
from urllib.parse import urlparse, urlunparse

from django.conf import settings
from django.contrib.auth.models import User
from django.urls import reverse
from oauth2client import client
from rest_framework.authentication import BaseAuthentication, TokenAuthentication

GOOGLE_API_SCOPES = [
    'openid',
    'email',
    'profile',
]

# For details about the Microsoft Identity Platform and OpenID see
# https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-permissions-and-consent#openid-connect-scopes
AZURE_API_SCOPES = [
    'openid',
    'email',
    'profile',
    'offline_access',  # required for refresh token
]


class OAuth2RedirectTokenAuth(TokenAuthentication):
    scopes = None

    def authenticate_header(self, request):
        assert self.scopes is not None, 'Derived classes must set the "scopes" attr.'

        redirect_uri = request.build_absolute_uri(reverse('oauth2callback'))
        if not settings.DEBUG:
            parsed = urlparse(redirect_uri)
            redirect_uri = urlunparse(('https', *parsed[1:]))

        flow = client.flow_from_clientsecrets(
            settings.OAUTH2_SECRETS_PATH,
            scope=self.scopes,
            redirect_uri=redirect_uri,
            prompt='select_account'
        )

        state = {
            'http_referer': request.META.get('HTTP_REFERER',
                                             request.build_absolute_uri()),
            'redirect_uri': redirect_uri
        }

        return 'Redirect_to: ' + flow.step1_get_authorize_url(state=json.dumps(state))


class GoogleOAuth2(OAuth2RedirectTokenAuth):
    scopes = GOOGLE_API_SCOPES


class AzureOAuth2(OAuth2RedirectTokenAuth):
    scopes = AZURE_API_SCOPES


# DO NOT USE IN PRODUCTION
class DevAuth(BaseAuthentication):
    def authenticate(self, request):
        username = request.COOKIES.get('username', 'jameslp@umich.edu')
        user = User.objects.get_or_create(username=username)[0]
        return user, None
