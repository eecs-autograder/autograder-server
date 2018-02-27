import json

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.shortcuts import redirect

from oauth2client import client
from apiclient import discovery

import httplib2
from rest_framework.authtoken.models import Token

from autograder.rest_api.auth import GOOGLE_API_SCOPES

from autograder import utils


_DJANGO_FIRST_NAME_MAX_LEN = 30
_DJANGO_LAST_NAME_MAX_LEN = 150


def oauth2_callback(request):
    state = json.loads(request.GET['state'])
    credentials = client.credentials_from_clientsecrets_and_code(
        settings.OAUTH2_SECRETS_PATH, GOOGLE_API_SCOPES, request.GET,
        redirect_uri=state['redirect_uri'])

    http = credentials.authorize(httplib2.Http())
    google_plus_service = discovery.build('plus', 'v1', http=http)
    user_info = google_plus_service.people().get(userId='me').execute()

    # Restrict login to umich.edu
    if user_info.get('domain', None) != 'umich.edu':
        return redirect(state['http_referer'])

    email = utils.find_if(user_info['emails'], lambda data: data['type'] == 'account')
    if email is None:
        raise RuntimeError('Email was None in user info')

    email = email['value']

    first_name = user_info['name']['givenName'][:_DJANGO_FIRST_NAME_MAX_LEN]
    last_name = user_info['name']['familyName'][:_DJANGO_LAST_NAME_MAX_LEN]
    user = User.objects.get_or_create(
        username=email, defaults={'first_name': first_name,'last_name': last_name})[0]
    if user.first_name != first_name or user.last_name != last_name:
        user.first_name = first_name
        user.last_name = last_name
        user.save()

    token, created = Token.objects.get_or_create(user=user)

    response = HttpResponseRedirect(state['http_referer'])
    response.set_cookie('token', token.key, domain=settings.SITE_DOMAIN)
    return response
