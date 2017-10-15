import enum
import autograder_sandbox

MAX_CHAR_FIELD_LEN = 255

MAX_OUTPUT_LENGTH = 8 * pow(10, 6)  # 8,000,000 characters
MAX_PROJECT_FILE_SIZE = MAX_OUTPUT_LENGTH

# For a given project, the name of the directory that
# user-uploaded project files should be placed in.
PROJECT_FILES_DIRNAME = 'project_files'

# For a given project, the name of the directory that
# student submissions should be placed in.
PROJECT_SUBMISSIONS_DIRNAME = 'submission_groups'

# The subdirectory of settings.MEDIA_ROOT where courses will be placed.
FILESYSTEM_ROOT_COURSES_DIRNAME = 'courses'
FILESYSTEM_RESULT_OUTPUT_DIRNAME = 'output'

MAX_COMMAND_LENGTH = 1000

# Sandbox resource limit settings
DEFAULT_SUBPROCESS_TIMEOUT = 10
MAX_SUBPROCESS_TIMEOUT = 60

DEFAULT_STACK_SIZE_LIMIT = 10000000  # 10 MB
MAX_STACK_SIZE_LIMIT = 100000000  # 100 MB

DEFAULT_VIRTUAL_MEM_LIMIT = 500000000  # 500 MB
MAX_VIRTUAL_MEM_LIMIT = 4000000000  # 4 GB

DEFAULT_PROCESS_LIMIT = 0
MEDIUM_PROCESS_LIMIT = 16
MAX_PROCESS_LIMIT = 100


class SupportedImages(enum.Enum):
    default = 'default'

    eecs280 = 'eecs280'
    eecs485 = 'eecs485'
    eecs490 = 'eecs490'
    engr101 = 'engr101'


DOCKER_IMAGE_IDS_TO_URLS = {
    SupportedImages.eecs280: 'jameslp/eecs280',
    SupportedImages.eecs490: 'jameslp/eecs490',
    SupportedImages.eecs485: 'jameslp/eecs485',
    SupportedImages.engr101: 'jameslp/engr101',
    # # Avoid using this image in development, since we can't host
    # # it publicly due to the MATLAB installation.
    # SupportedImages.engr101: '127.0.0.1:5000/engr101',

    SupportedImages.default: 'jameslp/autograder-sandbox:{}'.format(autograder_sandbox.VERSION)
}
