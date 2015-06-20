import os

from django.conf import settings

import autograder.shared.global_constants as gc


def get_course_root_dir(course):
    """
    Computes the absolute path of the root directory for the given course.
    For example: {MEDIA_ROOT}/courses/eecs280

    NOTE: DO NOT COMPUTE COURSE ROOT DIRECTORIES MANUALLY.
          ALWAYS DO SO BY USING THIS FUNCTION.
          This will allow for the filesystem layout to be easily
          modified if necessary.
    """
    return os.path.join(settings.MEDIA_ROOT, 'courses', course.name)


# -----------------------------------------------------------------------------

def get_semester_root_dir(semester):
    """
    Computes the absolute path of the root directory for the given semester.
    For example: {MEDIA_ROOT}/courses/eecs280/fall2015

    NOTE: DO NOT COMPUTE SEMESTER ROOT DIRECTORIES MANUALLY.
          ALWAYS DO SO BY USING THIS FUNCTION.
          This will allow for the filesystem layout to be easily
          modified if necessary.
    """
    return os.path.join(get_course_root_dir(semester.course), semester.name)


# -----------------------------------------------------------------------------

def get_project_root_dir(project):
    """
    Computes the absolute path of the root directory for the given project.
    For example: {MEDIA_ROOT}/courses/eecs280/fall2015/project3

    NOTE: DO NOT COMPUTE PROJECT ROOT DIRECTORIES MANUALLY.
          ALWAYS DO SO BY USING THIS FUNCTION.
          This will allow for the filesystem layout to be easily
          modified if necessary.
    """
    return os.path.join(
        get_semester_root_dir(project.semester), project.name)


# -----------------------------------------------------------------------------

def get_project_files_dir(project):
    """
    Computes the absolute path of the directory where uploaded files
    should be stored for the given project.
    For example: {MEDIA_ROOT}/courses/eecs280/fall2015/project3/project_files

    NOTE: DO NOT COMPUTE THIS PATH MANUALLY.
          ALWAYS DO SO BY USING THIS FUNCTION.
          This will allow for the filesystem layout to be easily
          modified if necessary.
    """
    return os.path.join(
        get_project_root_dir(project), gc.PROJECT_FILES_DIRNAME)


# -----------------------------------------------------------------------------

def get_project_submissions_by_student_dir(project):
    """
    Computes the absolute path of the directory where student submissions
    should be stored for the given project.
    For example:
        {MEDIA_ROOT}/courses/eecs280/fall2015/project3/submissions_by_student
    """
    return os.path.join(
        get_project_root_dir(project), gc.PROJECT_SUBMISSIONS_DIRNAME)


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

class ChangeDirectory(object):
    """
    Enables moving into and out of a given directory using "with" statements.
    """
    def __init__(self, new_dir):
        self._original_dir = os.getcwd()
        self._new_dir = new_dir

    def __enter__(self):
        os.chdir(self._new_dir)

    def __exit__(self, *args):
        os.chdir(self._original_dir)
