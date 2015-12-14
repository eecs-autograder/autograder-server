# import os

from django.contrib.auth.models import User, AnonymousUser

# from oauth2client import client, crypt
from .identitytoolkit import gitkitclient

from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect

# import logging

# logger = logging.getLogger(__name__)

gitkit_instance = gitkitclient.GitkitClient.FromConfigFile(
    settings.GOOGLE_IDENTITY_TOOLKIT_CONFIG_FILE)


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

        if (gitkit_user.email.split('@')[-1] not in
                settings.GOOGLE_IDENTITY_TOOLKIT_APPS_DOMAIN_NAMES):
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
