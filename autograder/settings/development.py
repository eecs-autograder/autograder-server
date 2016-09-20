import os

from .base import *


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MEDIA_ROOT = os.path.join(BASE_DIR, 'dev_filesystem')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

INSTALLED_APPS += [
    # Dummy testing models
    'autograder.core.tests.test_models',
    'autograder.core.tests.test_models.test_autograder_test_case',
]

REST_FRAMEWORK.update({
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
})


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('AG_DB_NAME', 'autograder_dev_db'),
        'USER': os.environ.get('AG_DB_USER', ''),
        'PASSWORD': os.environ.get('AG_DB_PASSWORD', ''),
        'HOST': os.environ.get('AG_DB_HOST', ''),
        'PORT': os.environ.get('AG_DB_PORT', '')
    },
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'autograder.rest_api.authentication.google_identity_toolkit_auth.DevAuth',
    )
}

# ----- Celery settings ----- #

# For testing without celery server running
TEST_RUNNER = 'autograder.grading_tasks.celery_test_runner.CeleryTestSuiteRunner'

# CELERY_ACCEPT_CONTENT = ['json']  # Ignore other content
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_RESULT_SERIALIZER = 'json'
# CELERY_QUEUES = {
#     'default': {
#         'serializer': 'json'
#     }
# }

# Override these values in production settings
AG_TEST_MAX_RETRIES = 2
AG_TEST_MIN_RETRY_DELAY = 1
AG_TEST_MAX_RETRY_DELAY = 2
