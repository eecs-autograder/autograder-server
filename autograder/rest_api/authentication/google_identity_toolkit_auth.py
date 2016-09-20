from django.contrib.auth.models import User
from django.middleware import csrf
from rest_framework.authentication import SessionAuthentication

from oauth2client import client, crypt

WEB_CLIENT_ID = "358440655746-bl5ig1es62n6n4oho525l4f58fgl367c.apps.googleusercontent.com"
APPS_DOMAIN_NAME = 'umich.edu'


class DevAuth(SessionAuthentication):
    def authenticate(self, request):
        user = User.objects.get_or_create(username='jameslp@umich.edu')[0]
        return (user, None)


# Adapted from the Google Identity Toolkit docs.
# This needs to inherit from SessionAuthentication so that we can use
# its enforce_csrf method.
class GoogleIdentityToolkitAuth(SessionAuthentication):
    def authenticate(self, request):
        gtoken = request.COOKIES.get('gtoken')
        print('gtoken:', gtoken)
        if not gtoken:
            print('user not logged in')
            return None
        try:
            id_info = client.verify_id_token(gtoken, WEB_CLIENT_ID)
            if id_info['aud'] != WEB_CLIENT_ID:
                raise crypt.AppIdentityError("Unrecognized client.")
            if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise crypt.AppIdentityError("Wrong issuer.")
            # Limit logins to umich.edu
            if id_info['hd'] != APPS_DOMAIN_NAME:
                raise crypt.AppIdentityError("Wrong hosted domain.")
        except crypt.AppIdentityError as e:
            print(e)
            return None
        except KeyError:
            print('gtoken not set')
            return None

        # THESE TWO CALLS MUST STAY IN THIS ORDER!!!
        # enforce_csrf will raise a permission denied error if the
        # request method is unsafe and the csrf token header is not set.
        # Then, if that check passes we can use get_token to set the
        # csrftoken cookie if it isn't already set.
        self.enforce_csrf(request)
        csrf.get_token(request)

        print(id_info)
        username = id_info['email']
        # TODO: add additional user info
        user = User.objects.get_or_create(username=username)[0]
        # print(user)
        return (user, None)
        # userid = id_info['sub']
        # print(userid)

    # We're overriding the WWW-Authenticate header value so that the
    # browser doesn't use its own username/password prompt.
    def authenticate_header(self, request):
        return 'Google Identity Toolkit Auth'
