import os

from django.contrib.auth.models import User, AnonymousUser

from oauth2client import client, crypt
from autograder.identitytoolkit import gitkitclient

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect

# import logging

# logger = logging.getLogger(__name__)

CLIENT_ID = '358440655746-bl5ig1es62n6n4oho525l4f58fgl367c.apps.googleusercontent.com'
APPS_DOMAIN_NAME = 'umich.edu'

server_config_json = os.path.join(
    settings.BASE_DIR, 'gitkit-server-config.json')
gitkit_instance = gitkitclient.GitkitClient.FromConfigFile(server_config_json)


class GoogleIdentityToolkitSessionMiddleware(object):
    # def process_request(self, request):
    #     # dummy version because my internet is shit
    #     request.user = User.objects.get_or_create(
    #         username='jameslp@umich.edu')[0]

    def process_request(self, request):
        # logger.info('process_request, GITkit middleware')

        if request.path == '/callback/':
            # logger.info('login page requested. setting anonymous user')
            request.user = AnonymousUser()
            return None

        gtoken = request.COOKIES.get('gtoken', None)
        if gtoken is None:
            # logger.info('gtoken not set. redirecting...')
            return self.redirect_to_login(request, '')
            # request.user = AnonymousUser()
            # return HttpResponseRedirect('/callback/?mode=select')

        gitkit_user = gitkit_instance.VerifyGitkitToken(gtoken)
        # logger.info(gitkit_user)
        if not gitkit_user:
            # logger.info('error verifying token')
            return self.redirect_to_login(
                request,
                'Error signing in. '
                'Please try again with your umich.edu email address')
            # return HttpResponse(
            #     'Unable to validate user', content_type='text/plain')

        # logger.info(gitkit_user.email)

        if gitkit_user.email.split('@')[-1] != APPS_DOMAIN_NAME:
            # logger.info('email is not umich.edu. redirecting...')
            return self.redirect_to_login(
                request,
                'Please sign in with a umich.edu email address')

        user = User.objects.get_or_create(username=gitkit_user.email)[0]
        request.user = user

        # logger.info('success')
        return None

    def redirect_to_login(self, request, reason):
        return HttpResponseRedirect(
            '/callback/?mode=select&next={}&reason={}'.format(
                request.path, reason))


class GoogleAuthBackend(object):
    def authenticate(self, token=None):
        print('authenticating...............')
        try:
            id_info = client.verify_id_token(token, CLIENT_ID)
            if id_info['aud'] != CLIENT_ID:
                raise crypt.AppIdentityError("Unrecognized client.")
            if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise crypt.AppIdentityError("Wrong issuer.")
            # Limit logins to umich.edu
            if id_info['hd'] != APPS_DOMAIN_NAME:
                raise crypt.AppIdentityError("Wrong hosted domain.")
        except crypt.AppIdentityError as e:
            print(e)
            return None
        except Exception:
            return None

        username = id_info['email']
        user = User.objects.get_or_create(username=username)[0]
        # print(user)
        return user
        # userid = id_info['sub']
        # print(userid)

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
