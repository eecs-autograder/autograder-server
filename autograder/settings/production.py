from .base import *  # noqa

DEBUG = False

EMAIL_USE_SSL = True

# ---- Retry settings ----
AG_TEST_MAX_RETRIES = 5
AG_TEST_MIN_RETRY_DELAY = 7
AG_TEST_MAX_RETRY_DELAY = 15
