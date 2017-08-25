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

# IMPORTANT: Make sure not to overwrite the default!!!
SUPPORTED_DOCKER_IMAGES = ['jameslp/autograder-sandbox']
DEFAULT_DOCKER_IMAGE = SUPPORTED_DOCKER_IMAGES[0]

DEFAULT_STACK_SIZE_LIMIT = 10000000  # 10 MB
MAX_STACK_SIZE_LIMIT = 100000000  # 100 MB

DEFAULT_VIRTUAL_MEM_LIMIT = 500000000  # 500 MB
MAX_VIRTUAL_MEM_LIMIT = 1000000000  # 1 GB

DEFAULT_PROCESS_LIMIT = 0
MAX_PROCESS_LIMIT = 10
