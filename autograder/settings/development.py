import os

from .base import *

MEDIA_ROOT += '_dev'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

INSTALLED_APPS += [
    # Dummy testing models
    'autograder.core.tests.test_models',
    'autograder.core.tests.test_models.test_autograder_test_case',
]

REST_FRAMEWORK.update({
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'autograder.rest_api.authentication.google_identity_toolkit_auth.DevAuth',
    )
})


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('AG_DB_NAME', 'postgres'),
        'USER': os.environ.get('AG_DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('AG_DB_PASSWORD', 'postgres'),
        'HOST': os.environ.get('AG_DB_HOST', 'localhost'),
        'PORT': os.environ.get('AG_DB_PORT', '5432')
    },
}

# ----- Celery settings ----- #

# For testing without celery server running
TEST_RUNNER = 'autograder.grading_tasks.celery_test_runner.CeleryTestSuiteRunner'

# Override these values in production settings
AG_TEST_MAX_RETRIES = 2
AG_TEST_MIN_RETRY_DELAY = 1
AG_TEST_MAX_RETRY_DELAY = 2
