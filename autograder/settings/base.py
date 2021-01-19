"""
Django settings for autograder project.
"""

import os
import sys

from django.utils.crypto import get_random_string

VERSION = '4.2.1'

# This is the autograder-server directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# autograder-server/autograder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# autograder-server/media_root
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', os.path.join(PROJECT_ROOT, 'media_root'))

SETTINGS_DIR = os.path.dirname(os.path.abspath(__file__))

# UPDATE THESE TWO FIELDS IN _prod.env and _dev.env
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split()
SITE_DOMAIN = os.environ.get('SITE_DOMAIN', '').strip()  # This is used for authentication

OAUTH2_SECRETS_FILENAME = os.environ.get('OAUTH2_SECRETS_FILENAME', 'dev_oauth2_secrets.json')
OAUTH2_SECRETS_PATH = os.path.join(SETTINGS_DIR, OAUTH2_SECRETS_FILENAME)

PREFERRED_DOMAIN = '@umich.edu'

SECRETS_DIR = os.path.join(SETTINGS_DIR, 'secrets')
SECRET_KEY_FILENAME = os.path.join(SECRETS_DIR, 'secret_key')
SECRET_KEY = 'this value will be overwritten'

GPG_KEY_ID_FILENAME = os.path.join(SECRETS_DIR, 'gpg_key_id_file')
GPG_KEY_ID = 'this value will be overwritten'
GPG_KEY_PASSWORD_FILENAME = os.path.join(SECRETS_DIR, 'gpg_key_password')
GPG_KEY_PASSWORD = 'this value will be overwritten'

# HACK: Don't try to load the secrets if we're generating them.
if sys.argv[0] != 'generate_secrets.py':
    if not os.path.exists(SECRET_KEY_FILENAME):
        error_msg = f"""
The file {SECRET_KEY_FILENAME} does not exist.
Please run "python3 generate_secrets.py" to generate this file."""
        print(error_msg, file=sys.stderr)
        exit(1)

    with open(SECRET_KEY_FILENAME) as f:
        SECRET_KEY = f.read()

    if not os.path.exists(GPG_KEY_PASSWORD_FILENAME):
        error_msg = f"""
The file {GPG_KEY_PASSWORD_FILENAME} does not exist.
Please run "python3 generate_secrets.py" to generate this file."""
        print(error_msg, file=sys.stderr)
        exit(1)

    with open(GPG_KEY_PASSWORD_FILENAME) as f:
        GPG_KEY_PASSWORD = f.read()

    if not os.path.exists(GPG_KEY_ID_FILENAME):
        error_msg = f"""
The file {GPG_KEY_ID_FILENAME} does not exist.
Please run "python3 generate_secrets.py" to generate this file."""
        print(error_msg, file=sys.stderr)
        exit(1)

    with open(GPG_KEY_ID_FILENAME) as f:
        GPG_KEY_ID = f.read()


OAUTH2_PROVIDER = os.environ.get('OAUTH2_PROVIDER', 'google')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',

    'rest_framework',
    'rest_framework.authtoken',

    'django_extensions',

    'timezone_field',

    'autograder.core',
    'autograder.rest_api.apps.RestApiConfig',
    'autograder.grading_tasks',
    'autograder.utils',
    'autograder.handgrading',
]

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

APPEND_SLASH = False

OAUTH2_AUTH_CLASSES = {
    'google': 'autograder.rest_api.auth.GoogleOAuth2',
    'azure': 'autograder.rest_api.auth.AzureOAuth2',
}

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        OAUTH2_AUTH_CLASSES[OAUTH2_PROVIDER],
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    )
}

ROOT_URLCONF = 'autograder.urls'

WSGI_APPLICATION = 'autograder.wsgi.application'

SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('AG_DB_NAME', 'postgres'),
        'USER': os.environ.get('AG_DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('AG_DB_PASSWORD', 'postgres'),
        'HOST': os.environ.get('AG_DB_HOST', 'localhost'),
        'PORT': os.environ.get('AG_DB_PORT', '5432'),
        'TEST': {
            'NAME': os.environ.get('AG_TEST_DB_NAME', 'test_postgres')
        }
    },
}


CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://{host}:{port}'.format(
            host=os.environ.get('AG_REDIS_HOST', 'localhost'),
            port=os.environ.get('AG_REDIS_PORT', '6379')),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "SERIALIZER": "django_redis.serializers.json.JSONSerializer",
        }
    },
}

# See https://docs.djangoproject.com/en/2.2/ref/settings/#std:setting-EMAIL_HOST
# for Django docs on these settings
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 25))

EMAIL_FROM_ADDR = os.environ.get('EMAIL_FROM_ADDR', 'admin@autograder.io')

SWAGGER_SETTINGS = {
    'USE_SESSION_AUTH': False,
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'DOC_EXPANSION': 'None'
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

INSTALLED_APPS += [
    'django.contrib.staticfiles',
]


STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[contactor] %(levelname)s %(asctime)s %(message)s'
        },
    },
    'handlers': {
        # Send all messages to console
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        # This is the "catch all" logger
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    }
}

SANDBOX_IMAGE_REGISTRY_HOST = os.environ.get(
    'SANDBOX_IMAGE_REGISTRY_HOST', '127.0.0.1')
SANDBOX_IMAGE_REGISTRY_PORT = os.environ.get('SANDBOX_IMAGE_REGISTRY_PORT', '5001')

from autograder.settings.celery_settings import *  # noqa
