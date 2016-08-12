import os

from .base import *

MEDIA_ROOT = os.path.join(BASE_DIR, 'dev_filesystem')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split()

INSTALLED_APPS += [
    # Dummy testing models
    'autograder.core.tests.test_models',
    'autograder.core.tests.test_models.test_autograder_test_case',
]

REST_FRAMEWORK.update({
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
})

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('AG_DB_NAME', 'autograder_dev_db'),
        'USER': os.environ.get('AG_DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('AG_DB_PASSWORD', ''),
        'HOST': os.environ.get('AG_DB_HOST', 'localhost'),
        'PORT': os.environ.get('AG_DB_PORT', '5432')
    },
}

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        'LOCATION': '{host}:{port}'.format(
            host=os.environ.get('AG_REDIS_HOST', 'localhost'),
            port=os.environ.get('AG_REDIS_PORT', '6379')),
    },
}

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'


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
