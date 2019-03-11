import json
import sys
import traceback

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect

from oauth2client import client

import httplib2
from rest_framework.authtoken.models import Token

from autograder.rest_api.auth import GOOGLE_API_SCOPES

from autograder import utils


_DJANGO_FIRST_NAME_MAX_LEN = User._meta.get_field('first_name').max_length
_DJANGO_LAST_NAME_MAX_LEN = User._meta.get_field('last_name').max_length


def oauth2_callback(request):
    response = None
    content = None
    try:
        state = json.loads(request.GET['state'])
        credentials = client.credentials_from_clientsecrets_and_code(
            settings.OAUTH2_SECRETS_PATH, GOOGLE_API_SCOPES, request.GET,
            redirect_uri=state['redirect_uri'])

        http = credentials.authorize(httplib2.Http())

        url = (
            'https://content-people.googleapis.com/v1/people/me?personFields=names,emailAddresses')
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
        user = User.objects.get_or_create(
            username=email, defaults={'first_name': first_name, 'last_name': last_name})[0]
        if user.first_name != first_name or user.last_name != last_name:
            user.first_name = first_name
            user.last_name = last_name
            user.save()

        token, created = Token.objects.get_or_create(user=user)

        response = HttpResponseRedirect(state['http_referer'])
        response.set_cookie('token', token.key, domain=settings.SITE_DOMAIN)
        return response
    except Exception as e:
        print('Unexpected auth error', file=sys.stderr, flush=True)
        print(e, file=sys.stderr, flush=True)
        traceback.print_exc()
        print(response, content)
        raise
