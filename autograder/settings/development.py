import os

import sys

from .base import *

MEDIA_ROOT += '_dev'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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
    'debug_toolbar',
]


def show_toolbar_callback(request):
    return DEBUG

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': show_toolbar_callback
}

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# MIDDLEWARE_CLASSES += ('autograder.sql_middleware.SqlPrintingMiddleware',)
MIDDLEWARE_CLASSES += (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'autograder.non_html_debug_toolbar_middleware.NonHtmlDebugToolbarMiddleware',
)

REST_FRAMEWORK.update({
    'TEST_REQUEST_DEFAULT_FORMAT': 'json'
})

if os.environ.get('USE_REAL_AUTH', 'true').lower() == 'false':
    REST_FRAMEWORK.update({
        'DEFAULT_AUTHENTICATION_CLASSES': (
            'autograder.rest_api.auth.DevAuth',
        )
    })

# ----- Celery settings ----- #

# For testing without celery server running
TEST_RUNNER = 'autograder.grading_tasks.celery_test_runner.CeleryTestSuiteRunner'

AG_TEST_MAX_RETRIES = 2
AG_TEST_MIN_RETRY_DELAY = 1
AG_TEST_MAX_RETRY_DELAY = 2
