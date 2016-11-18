import os

from .base import *

MEDIA_ROOT += '_dev'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

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
