import re

MAX_CHAR_FIELD_LEN = 255

DEFAULT_SUBPROCESS_TIMEOUT = 10
MAX_SUBPROCESS_TIMEOUT = 60

DEFAULT_STACK_SIZE_LIMIT = 10000000  # 10 MB
MAX_STACK_SIZE_LIMIT = 100000000  # 100 MB

DEFAULT_VIRTUAL_MEM_LIMIT = 500000000  # 500 MB
MAX_VIRTUAL_MEM_LIMIT = 1000000000  # 1 GB

DEFAULT_PROCESS_LIMIT = 0
MAX_PROCESS_LIMIT = 10

# For a given project, the name of the directory that
# user-uploaded project files should be placed in.
PROJECT_FILES_DIRNAME = 'project_files'

# For a given project, the name of the directory that
# student submissions should be placed in.
PROJECT_SUBMISSIONS_DIRNAME = 'submission_groups'

# The subdirectory of settings.MEDIA_ROOT where courses will be placed.
FILESYSTEM_ROOT_COURSES_DIRNAME = 'courses'

# This regular expression provides the whitelist to be used when
# validating the names of user-uploaded files.
# Filenames must start with a capital or lowercase letter.
# Filenames may contain:
#   alphanumeric characters, hyphen, underscore, and period
# Note that this allows the empty string, as emptiness should be
# specified with the 'blank' argument to the respective field.
PROJECT_FILENAME_WHITELIST_REGEX = re.compile(
    r'[a-zA-Z][a-zA-Z0-9-_.]*|^$')
# r"[a-zA-Z0-9-_.]+")

# This regular expression provides the whitelist to be used
# when validating shell-style file patterns.
# File patterns can contain:
#   alphanumeric characters, hyphen, underscore, period, * ? [ ] and !
# Note that submitted files that are meant to match shell patterns
# are still restricted to the same charset as other user-uploaded files.
PROJECT_FILE_PATTERN_WHITELIST_REGEX = re.compile(
    r"^[a-zA-Z0-9-_.\*\[\]\?\!]+$")

DEFAULT_VALGRIND_FLAGS_WHEN_USED = ['--leak-check=full', '--error-exitcode=1']

# This regular expression provides the whitelist to be used when
# validating command line arguments used in an autograder test case.
# Command line arguments can contain:
#   alphanumeric characters, hyphen, underscore, equals, period, plus
COMMAND_LINE_ARG_WHITELIST_REGEX = re.compile(
    r"^[a-zA-Z0-9-_=.+]+$")

SUPPORTED_COMPILERS = ['g++', 'clang++', 'gcc', 'clang']

SUPPORTED_INTERPRETERS = ['python', 'python3']
