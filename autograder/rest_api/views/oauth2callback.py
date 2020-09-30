import json
import sys
import traceback
from typing import TypedDict, Optional, Mapping

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect, HttpResponse

from oauth2client import client

import httplib2
from rest_framework.authtoken.models import Token

from autograder.rest_api.auth import GOOGLE_API_SCOPES

from autograder import utils


def oauth2_callback(request):
    handler = OAUTH2_CALLBACK_CLASSES[settings.OAUTH2_PROVIDER]()
    return handler.handle_request(request)


class _UserInfo(TypedDict):
    email: str
    first_name: str
    last_name: str


class OAuth2CallbackHandler:
    def __init__(self):
        self._state: Optional[Mapping] = None

    def handle_request(self, request):
        self.load_state(request)

        user_info = self.load_user_info(request)
        user = User.objects.get_or_create(
            username=user_info['email'],
            defaults={'first_name': user_info['first_name'], 'last_name': user_info['last_name']}
        )[0]
        if user.first_name != user_info['first_name'] or user.last_name != user_info['last_name']:
            user.first_name = user_info['first_name']
            user.last_name = user_info['last_name']
            user.save()

        token, created = Token.objects.get_or_create(user=user)
        if self._state is not None and 'http_referer' in self._state:
            response = HttpResponseRedirect(self._state['http_referer'])
        else:
            response = HttpResponse()

        response.set_cookie('token', token.key, domain=settings.SITE_DOMAIN)
        return response

    def load_state(self, request):
        if 'state' in request.GET:
            self._state = json.loads(request.GET['state'])

    def load_user_info(self, request) -> _UserInfo:
        """
        Loads user information from the OAuth2 provider and returns
        a dictionary of {'email': ..., 'first_name': ..., 'last_name': ...}.
        Derived classes MUST override this method.
        """
        raise NotImplementedError


_DJANGO_FIRST_NAME_MAX_LEN = User._meta.get_field('first_name').max_length
_DJANGO_LAST_NAME_MAX_LEN = User._meta.get_field('last_name').max_length


class GoogleOAuth2CallbackHandler(OAuth2CallbackHandler):
    def load_user_info(self, request):
        response = None
        content = None
        try:
            credentials = client.credentials_from_clientsecrets_and_code(
                settings.OAUTH2_SECRETS_PATH, GOOGLE_API_SCOPES, request.GET,
                redirect_uri=self._state['redirect_uri'])

            http = credentials.authorize(httplib2.Http())

            url = (
                'https://content-people.googleapis.com'
                '/v1/people/me?personFields=names,emailAddresses'
            )
            response, content = http.request(url, 'GET')
            user_info = json.loads(content)

            try:
                email = utils.find_if(
                    user_info['emailAddresses'], lambda data: data['metadata']['primary'])
                email = email['value']
            except KeyError:
                print('WARNING: emailAddress not found. Using alternate API')
                em_url = ('https://www.googleapis.com/userinfo/v2/me?fields=email')
                em_response, em_content = http.request(em_url, 'GET')
                em_user_info = json.loads(em_content)
                email = em_user_info['email']

            if email is None:
                raise RuntimeError('Primary email not found in user info')

            # It is possible for 'names' to be absent in some rare cases.
            if 'names' not in user_info:
                name = {}
            else:
                name = utils.find_if(user_info['names'], lambda data: data['metadata']['primary'])

            # The documentation says that 'familyName' can be absent.
            # I added a similar check for 'givenName' to be safe because
            # this is difficult to test.
            first_name = ('' if 'givenName' not in name
                          else name['givenName'][:_DJANGO_FIRST_NAME_MAX_LEN])
            last_name = ('' if 'familyName' not in name
                         else name['familyName'][:_DJANGO_LAST_NAME_MAX_LEN])

            return {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
            }
        except Exception as e:
            print('Unexpected auth error', file=sys.stderr, flush=True)
            print(e, file=sys.stderr, flush=True)
            traceback.print_exc()
            print(response, content)
            raise


OAUTH2_CALLBACK_CLASSES: Mapping[str, OAuth2CallbackHandler] = {
    'google': GoogleOAuth2CallbackHandler
}
