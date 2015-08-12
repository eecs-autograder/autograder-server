import os

from django.core.urlresolvers import reverse

from autograder.models import CompiledAutograderTestCase

# The json data produced by functions in this module should
# adhere to the JSON API standard: http://jsonapi.org/format/
#
# See also: http://jsonapi.org/format/#document-resource-objects
# for the most common format used in this module.


def course_to_json(course, with_fields=True):
    """
    Returns a JSON representation of the given course of the
    following form:
    {
        'type': 'course',
        'id': <id>,
        'attributes': {
            'name': <name>,
            'course_admin_names': [<admin username>, ...]
        },
        'links': {
            'self': <self link>
        }
    }

    If with_fields is False, the 'attributes' key will NOT be
    included.
    """
    data = {
        'type': 'course',
        'id': course.pk,
        'links': {
            'self': reverse('get-course', args=[course.pk])
        }
    }

    if not with_fields:
        return data

    data['attributes'] = {
        'name': course.name,
        'course_admin_names': course.course_admin_names
    }

    return data


# -----------------------------------------------------------------------------

def semester_to_json(semester, with_fields=True, user_is_semester_staff=False):
    """
    Returns a JSON representation of the given semester of the
    following form:
    {
        'type': 'semester',
        'id': <id>,
        'attributes': {
            'name': <name>,
            'semester_staff_names': [<staff username>, ...],
            'enrolled_student_names': [<student username>, ...]
        },
        'relationships': {
            'course': {
                'links': {
                    'self': <course url>,
                },
                'data': {'type': 'course', 'id': <course-id>}
            }
        },
        'links': {
            'self': <self link>
        },
        'meta': {
            'is_staff': <true> | <false>,
            'course_admin_names': [<course admin username>, ...]
        }
    }

    If with_fields is False, the 'attributes' and 'relationships' keys
    and the 'course_admin_names' meta field will NOT be included.

    user_is_semester_staff indicates the value of the 'is_staff' key in the
    'meta' section. When this value is True, the 'semester_staff_names'
     and 'enrolled_student_names' attributes and
     the 'course_admin_names' meta field will be included.
    """
    data = {
        'type': 'semester',
        'id': semester.pk,
        'links': {
            'self': reverse('semester-handler', args=[semester.pk])
        },
        'meta': {
            'is_staff': user_is_semester_staff
        }
    }

    if not with_fields:
        return data

    data['attributes'] = {
        'name': semester.name
    }

    if user_is_semester_staff:
        data['attributes']['semester_staff_names'] = (
            semester.semester_staff_names)
        data['attributes']['enrolled_student_names'] = (
            semester.enrolled_student_names)

        data['meta']['course_admin_names'] = (
            semester.course.course_admin_names)

    data['relationships'] = {
        'course': {
            'data': course_to_json(semester.course, with_fields=False)
        }
    }

    return data


# -----------------------------------------------------------------------------

def project_to_json(project, with_fields=True):
    """
    Returns a JSON representation of the given project of the
    following form:
    {
        'type': 'project',
        'id': <id>,
        'links': {
            'self': <self link>
        },
        'attributes': {
            'name': ...,
            'project_files': [
                {
                    'filename': <filename>,
                    'file_url': <file url>,
                    'size': <file size>
                },
                ...
            ],
            'test_case_feedback_configuration': {...},
            'visible_to_students': ...,
            'closing_time': ...,
            'disallow_student_submissions': ...,
            'allow_submissions_from_non_enrolled_students': <True | False>
            'min_group_size': ...,
            'max_group_size': ...,
            'required_student_files': [...],
            'expected_student_file_patterns': [...],
        },
        'relationships': {
            'semester': {
                'data': {
                    'type': 'semester',
                    'id': <semester-id>,
                    'links': {
                        'self': <semester url>,
                    }
                }
            }
        }
    }
    """
    data = {
        'type': 'project',
        'id': project.id,
        'links': {
            'self': reverse('project-handler', args=[project.pk])
        }
    }

    if not with_fields:
        return data

    data['attributes'] = {
        'name': project.name,
        'project_files': [
            {
                'filename': os.path.basename(file_.name),
                'size': file_.size,
                'file_url': reverse(
                    'project-file-handler',
                    args=[project.pk, os.path.basename(file_.name)])
            }
            for file_ in project.get_project_files()
        ],
        'test_case_feedback_configuration': (
            project.test_case_feedback_configuration.to_json()),
        'visible_to_students': project.visible_to_students,
        'closing_time': project.closing_time,
        'disallow_student_submissions': (
            project.disallow_student_submissions),
        'allow_submissions_from_non_enrolled_students': (
            project.allow_submissions_from_non_enrolled_students),
        'min_group_size': project.min_group_size,
        'max_group_size': project.max_group_size,
        'required_student_files': project.required_student_files,
        'expected_student_file_patterns': (
            project.expected_student_file_patterns)
    }

    data['relationships'] = {
        'semester': {
            'data': semester_to_json(project.semester, with_fields=False)
        }
    }

    return data


# -----------------------------------------------------------------------------

def autograder_test_case_to_json(autograder_test_case, with_fields=True):
    """
    Returns a JSON representation fo the given test case of the
    following form:
    {
        'type': <type>,
        'id': <id>,
        'links': {
            'self': <self link>
        },
        'attributes': {
            // Present for all types
            'name': <value>,
            'hide_from_students': <value>
            'command_line_arguments': <value>,
            'standard_input': <value>,
            'test_resource_files': <value>,
            'time_limit': <value>,
            'expected_return_code': <value>,
            'expect_any_nonzero_return_code': <value>,
            'expected_standard_output': <value>,
            'expected_standard_error_output': <value>,
            'use_valgrind': <value>,
            'valgrind_flags': <value>,

            'points_for_correct_return_code': <value>,
            'points_for_correct_output': <value>,
            'points_for_no_valgrind_errors': <value>,
            'points_for_compilation_success': <value>,

            // Present depending on type
            'compiler': <value>,
            'compiler_flags': <value>,
            'files_to_compile_together': <value>,
            'executable_name': <value>
        },
        'relationships': {
            'project': {
                'data': <project>
            }
        }
    }

    The 'type' field corresponds to the type of the given test case
    as follows:
        CompiledAutograderTestCase: 'compiled_test_case'
        (support for more test cases will be added in the future)

    Raises TypeError if the type of autograder_test_case is not
    listed in the above type mapping.
    """
    if isinstance(autograder_test_case, CompiledAutograderTestCase):
        type_ = 'compiled_test_case'
    else:
        raise TypeError()

    data = {
        'type': type_,
        'id': autograder_test_case.pk,
        'links': {
            'self': reverse('ag-test-handler', args=[autograder_test_case.pk])
        }
    }

    if not with_fields:
        return data

    data['attributes'] = {
        'name': autograder_test_case.name,
        'hide_from_students': autograder_test_case.hide_from_students,
        'command_line_arguments': (
            autograder_test_case.command_line_arguments),
        'standard_input': autograder_test_case.standard_input,
        'test_resource_files': autograder_test_case.test_resource_files,
        'time_limit': autograder_test_case.time_limit,
        'expected_return_code': autograder_test_case.expected_return_code,
        'expect_any_nonzero_return_code': (
            autograder_test_case.expect_any_nonzero_return_code),
        'expected_standard_output': (
            autograder_test_case.expected_standard_output),
        'expected_standard_error_output': (
            autograder_test_case.expected_standard_error_output),
        'use_valgrind': autograder_test_case.use_valgrind,
        'valgrind_flags': autograder_test_case.valgrind_flags,

        'points_for_correct_return_code': (
            autograder_test_case.points_for_correct_return_code),
        'points_for_correct_output': (
            autograder_test_case.points_for_correct_output),
        'points_for_no_valgrind_errors': (
            autograder_test_case.points_for_no_valgrind_errors),
        'points_for_compilation_success': (
            autograder_test_case.points_for_compilation_success)
    }

    if type_ == 'compiled_test_case':
        data['attributes'].update(
            {
                'compiler': autograder_test_case.compiler,
                'compiler_flags': autograder_test_case.compiler_flags,
                'files_to_compile_together': (
                    autograder_test_case.files_to_compile_together),
                'executable_name': autograder_test_case.executable_name
            }
        )

    data['relationships'] = {
        'project': {
            'data': project_to_json(
                autograder_test_case.project, with_fields=False)
        }
    }

    return data


# -----------------------------------------------------------------------------

def submission_group_to_json(submission_group, with_fields=True):
    """
    Returns a JSON representation of the given submission group
    of the following form:
    {
        'type': 'submission_group',
        'id': <id>,
        'attributes': {
            'members': [<username>, ...],
            'extended_due_date': <date | None>
        },
        'relationships': {
            'project': {
                'data': <project>
            }
        }
    }
    """
    data = {
        'type': 'submission_group',
        'id': submission_group.pk
    }

    if not with_fields:
        return data

    data['attributes'] = {
        'members': [user.username for user in submission_group.members.all()],
        'extended_due_date': submission_group.extended_due_date
    }
    data['relationships'] = {
        'project': {
            'data': project_to_json(
                submission_group.project, with_fields=False)
        }
    }

    return data
