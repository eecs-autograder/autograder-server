import os

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False


# ---- Retry settings ----
AG_TEST_MAX_RETRIES = 5
AG_TEST_MIN_RETRY_DELAY = 7
AG_TEST_MAX_RETRY_DELAY = 15
