import json

from django.conf import settings
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.middleware import csrf

from rest_framework.authentication import SessionAuthentication

from oauth2client import client


GOOGLE_API_SCOPES = [
    'https://www.googleapis.com/auth/plus.me',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]


class GoogleOAuth2(SessionAuthentication):
    def authenticate(self, request):
        # THESE TWO CALLS MUST STAY IN THIS ORDER!!!
        # enforce_csrf will raise a permission denied error if the
        # request method is unsafe and the csrf token header is not set.
        # Then, if that check passes we can use get_token to set the
        # csrftoken cookie if it isn't already set.
        #
        # Note: For some reason, calling super() doesn't properly set
        # the csrf cookie.
        self.enforce_csrf(request)
        csrf.get_token(request)

        if SESSION_KEY not in request.session:
            return None

        request.user = User.objects.get(pk=request.session[SESSION_KEY])

        return super().authenticate(request)

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

        return 'Redirect_to: ' + flow.step1_get_authorize_url(
            state=json.dumps(state))


# DO NOT USE IN PRODUCTION
class DevAuth(SessionAuthentication):
    def authenticate(self, request):
        username = request.COOKIES.get('username', 'jameslp@umich.edu')
        user = User.objects.get_or_create(username=username)[0]
        return (user, None)
