MAX_CHAR_FIELD_LEN = 255

# For a given project, the name of the directory that
# user-uploaded project files should be placed in.
PROJECT_FILES_DIRNAME = 'project_files'

# For a given project, the name of the directory that
# student submissions should be placed in.
PROJECT_SUBMISSIONS_DIRNAME = 'submissions_by_student'

# The subdirectory of settings.MEDIA_ROOT where projects will be placed.
FILESYSTEM_ROOT_COURSES_DIRNAME = 'courses'

# This regular expression provides the whitelist to be used when validating
# user-uploaded project filenames.
# Filenames can contain:
#   alphanumeric characters, hyphen, underscore, and period
PROJECT_FILENAME_WHITELIST_REGEX = r"[a-zA-Z0-9-_.]*"
