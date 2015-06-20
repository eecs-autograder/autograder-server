import os

from django.conf import settings


def get_course_root_dir(course):
    return os.path.join(settings.MEDIA_ROOT, 'courses', course.name)


def get_semester_root_dir(semester):
    return os.path.join(get_course_root_dir(semester.course), semester.name)


def get_project_root_dir(project):
    return os.path.join(
        get_semester_root_dir(project.semester), project.name)


def get_project_files_dir(project):
    return os.path.join(
        get_project_root_dir(project), 'project_files')


# def get_project_submissions_by_student_dir

# def get_student_project_submissions_dir(project, semester, student_id):
#     return os.path.join(
#         get_project_root_dir(
#             project, 'students_by_semester', semester.name, student_id))


# def get_student_submission_dir(submission):
#     pass
