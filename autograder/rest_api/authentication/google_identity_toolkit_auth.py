from django.contrib.auth.models import User
from rest_framework.authentication import BasicAuthentication

from oauth2client import client, crypt

WEB_CLIENT_ID = "405101394-6mv8jvt0t7l172490hh8qsrq1mikn1bn.apps.googleusercontent.com"
APPS_DOMAIN_NAME = 'umich.edu'


# Adapted from the Google Identity Toolkit docs
class GoogleIdentityToolkitAuth(BasicAuthentication):
    def authenticate(self, request):
        gtoken = request.COOKIES.get('gtoken')
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
