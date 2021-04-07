import os

from .base import *  # noqa

DEBUG = False

# When true, the function autograder.rest_api.serve_file.serve_file
# will return a response that uses nginx's X-accel capability
# https://www.nginx.com/resources/wiki/start/topics/examples/x-accel/
# Can be overridden by settings the environment variable with the same
# name to "false" to disable or "true" to enable.
USE_NGINX_X_ACCEL = os.environ.get('USE_NGINX_X_ACCEL', 'true') == 'true'

EMAIL_USE_TLS = True

# ---- Retry settings ----
AG_TEST_MAX_RETRIES = 5
AG_TEST_MIN_RETRY_DELAY = 7
AG_TEST_MAX_RETRY_DELAY = 15
