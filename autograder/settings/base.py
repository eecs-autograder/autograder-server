"""
Django settings for autograder project.
"""

import os
import json
import uuid

from django.utils.crypto import get_random_string

VERSION = '3.0.0.beta2'

# This is the autograder-server directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# autograder-server/autograder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# autograder-server/media_root
MEDIA_ROOT = os.environ.get('MEDIA_ROOT', os.path.join(PROJECT_ROOT, 'media_root'))

SETTINGS_DIR = os.path.dirname(os.path.abspath(__file__))

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split()

SITE_DOMAIN = os.environ.get('SITE_DOMAIN', 'autograder.io').strip()

OAUTH2_SECRETS_FILENAME = os.environ.get('OAUTH2_SECRETS_FILENAME', 'dev_oauth2_secrets.json')
OAUTH2_SECRETS_PATH = os.path.join(SETTINGS_DIR, OAUTH2_SECRETS_FILENAME)


def generate_secrets(overwrite_prompt=True):
    """
    Generates an app secret key and a database password and writes
    them to a json file.
    """
    secrets_file = os.path.join(SETTINGS_DIR, 'secrets.json')
    if os.path.exists(secrets_file) and overwrite_prompt:
        choice = input(
            'Secrets file already exists. Overwrite? [y/N]'
        ).strip().lower()
        if choice != "y":
            print('Exiting')
            raise SystemExit()

    chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
    secrets = {
        'secret_key': get_random_string(50, chars),
        # 'db_password': get_random_string(50, chars)
    }

    with open(secrets_file, 'w') as f:
        json.dump(secrets, f)


# SECURITY WARNING: keep the secret key used in production secret!
_secrets_filename = os.path.join(SETTINGS_DIR, 'secrets.json')
if not os.path.exists(_secrets_filename):
    generate_secrets(overwrite_prompt=False)

SECRET_KEY = ''
with open(_secrets_filename) as f:
    secrets = json.load(f)
    SECRET_KEY = secrets.pop('secret_key')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    # 'django.contrib.sessions',

    'rest_framework',
    'rest_framework.authtoken',

    'drf_yasg',

    'django_extensions',

    'timezone_field',

    'autograder.core',
    'autograder.rest_api',
    'autograder.grading_tasks',
    'autograder.utils',
    'autograder.handgrading',

    # Used for testing ag_model_base
    'autograder.core.tests.test_models',
]

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'autograder.rest_api.auth.GoogleOAuth2',
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
            'NAME': 'test_db_{}'.format(uuid.uuid4().hex)
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

from autograder.settings.celery_settings import *  # noqa
