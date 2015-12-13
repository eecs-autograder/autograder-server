import re

MAX_CHAR_FIELD_LEN = 255

DEFAULT_SUBPROCESS_TIMEOUT = 10
MAX_SUBPROCESS_TIMEOUT = 60

# For a given project, the name of the directory that
# user-uploaded project files should be placed in.
PROJECT_FILES_DIRNAME = 'project_files'

# For a given project, the name of the directory that
# student submissions should be placed in.
PROJECT_SUBMISSIONS_DIRNAME = 'submission_groups'

# The subdirectory of settings.MEDIA_ROOT where courses will be placed.
FILESYSTEM_ROOT_COURSES_DIRNAME = 'courses'

# This regular expression provides the whitelist to be used when validating
# the names of user-uploaded files.
# Filenames can contain:
#   alphanumeric characters, hyphen, underscore, and period
PROJECT_FILENAME_WHITELIST_REGEX = re.compile(
    r"[a-zA-Z0-9-_.]+")

# This regular expression provides the whitelist to be used
# when validating shell-style file patterns.
# File patterns can contain:
#   alphanumeric characters, hyphen, underscore, period, * ? [ ] and !
# Note that submitted files that are meant to match shell patterns
# are still restricted to the same charset as other user-uploaded files.
PROJECT_FILE_PATTERN_WHITELIST_REGEX = re.compile(
    r"[a-zA-Z0-9-_.\*\[\]\?\!]+")

DEFAULT_VALGRIND_FLAGS_WHEN_USED = ['--leak-check=full', '--error-exitcode=1']

# This regular expression provides the whitelist to be used when validating
# command line arguments used in an autograder test case.
# Command line arguments can contain:
#   alphanumeric characters, hyphen, underscore, equals, period
COMMAND_LINE_ARG_WHITELIST_REGEX = re.compile(
    r"^[a-zA-Z0-9-_=.]+$")
