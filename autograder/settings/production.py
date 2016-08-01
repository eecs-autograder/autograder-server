import os

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['class1.eecs.umich.edu']

MEDIA_ROOT = os.path.join(BASE_DIR, 'filesystem')

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'autograder_db',
        'USER': 'jameslp',
        'PASSWORD': secrets.pop('db_password')
    }
}

# FIXME
CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': 'localhost:6379',
    },
}


STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'  # FIXME

# FIXME
AG_TEST_MAX_RETRIES = 2
AG_TEST_MIN_RETRY_DELAY = 1
AG_TEST_MAX_RETRY_DELAY = 2
