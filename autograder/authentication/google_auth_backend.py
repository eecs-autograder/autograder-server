from django.contrib.auth.models import User

from oauth2client import client, crypt

# (Receive token by HTTPS POST)

CLIENT_ID = '358440655746-bl5ig1es62n6n4oho525l4f58fgl367c.apps.googleusercontent.com'
APPS_DOMAIN_NAME = 'umich.edu'


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
