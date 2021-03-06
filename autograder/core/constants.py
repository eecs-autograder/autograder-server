import enum
import autograder_sandbox
from django.contrib.auth.models import User


MAX_USERNAME_LEN = User._meta.get_field('username').max_length

MAX_CHAR_FIELD_LEN = 255

# The maximum size for an instructor file.
MAX_INSTRUCTOR_FILE_SIZE = 15 * (10 ** 6)  # 15,000,000 bytes

# Recorded output longer than this value will be truncated.
# Since instructor files can be used as expected stdout/stderr,
# this value must be the SAME as MAX_INSTRUCTOR_FILE_SIZE.
MAX_RECORDED_OUTPUT_LENGTH = MAX_INSTRUCTOR_FILE_SIZE

# For a given project, the name of the directory that
# user-uploaded project files should be placed in.
PROJECT_FILES_DIRNAME = 'project_files'

# For a given project, the name of the directory that
# student submissions should be placed in.
# IMPORTANT: Even though we changed 'submission_group' to 'group',
# LEAVE THIS VALUE as is. Changing it would require changing all
# folders with this name in the media filesystem.
PROJECT_SUBMISSIONS_DIRNAME = 'submission_groups'

# The subdirectory of settings.MEDIA_ROOT where courses will be placed.
FILESYSTEM_ROOT_COURSES_DIRNAME = 'courses'
FILESYSTEM_RESULT_OUTPUT_DIRNAME = 'output'

MAX_COMMAND_LENGTH = 1000

# Sandbox resource limit settings

DEFAULT_SUBPROCESS_TIMEOUT = 10
MAX_SUBPROCESS_TIMEOUT = 90

# IGNORED as of version 4.0.0. Will be removed in 5.0.0
DEFAULT_STACK_SIZE_LIMIT = 10000000  # 10 MB
MAX_STACK_SIZE_LIMIT = 100000000  # 100 MB

DEFAULT_VIRTUAL_MEM_LIMIT = 500000000  # 500 MB

# IGNORED as of version 4.0.0. Will be removed in 5.0.0
DEFAULT_PROCESS_LIMIT = 0
MEDIUM_PROCESS_LIMIT = 16
MAX_PROCESS_LIMIT = 150


# DO NOT USE. This will be removed soon.
class SupportedImages(enum.Enum):
    default = 'default'

    # eecs280 = 'eecs280'
    # eecs285 = 'eecs285'
    # eecs481 = 'eecs481'
    # eecs483 = 'eecs483'
    # eecs485 = 'eecs485'
    # eecs490 = 'eecs490'
    # eecs498_data_mining = 'eecs498_data_mining'
    # eecs598w19_data_mining = 'eecs598w19_data_mining'
    # engr101 = 'engr101'


# DO NOT USE. This will be removed soon.
DOCKER_IMAGE_IDS_TO_URLS = {
    # SupportedImages.eecs280: 'jameslp/eecs280',
    # SupportedImages.eecs285: 'jameslp/eecs285',
    # SupportedImages.eecs481: 'jameslp/eecs481',
    # SupportedImages.eecs483: 'jameslp/eecs483',
    # SupportedImages.eecs485: 'jameslp/eecs485',
    # SupportedImages.eecs490: 'jameslp/eecs490',
    # SupportedImages.eecs498_data_mining: 'jameslp/eecs498_data_mining',
    # SupportedImages.eecs598w19_data_mining: 'jameslp/eecs598w19_data_mining',
    # SupportedImages.engr101: 'jameslp/engr101',

    SupportedImages.default: 'jameslp/autograder-sandbox:3.1.2'
}
