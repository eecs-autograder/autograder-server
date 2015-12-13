import os

from django.core.urlresolvers import reverse

# import autograder.shared.utilities as ut

# The json data produced by functions in this module should
# loosely adhere to the JSON API standard: http://jsonapi.org/format/
#
# See also: http://jsonapi.org/format/#document-resource-objects
# for the most common format used in this module.


def course_to_json(course, all_fields=True):
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

    If all_fields is False, 'name' will be the only field
    included.
    """
    data = {
        'type': 'course',
        'id': course.pk,
        'links': {
            'self': reverse('get-course', args=[course.pk])
        },
        'attributes': {
            'name': course.name
        }
    }

    if not all_fields:
        return data

    data['attributes'].update({
        'course_admin_names': course.course_admin_names
    })

    return data


# -----------------------------------------------------------------------------

# TODO: get rid of user_is_semester_staff
#       add meta 'permissions' field to response content
#       i.e. {
#           'data': {...},
#           'meta': {
#               'permissions': {
#                   can_edit: tf,
#                   can_view_other_students tf,
#
#               }
#           }
#       }
def semester_to_json(semester, all_fields=True):
    """
    Returns a JSON representation of the given semester of the
    following form:
    {
        'type': 'semester',
        'id': <id>,
        'attributes': {
            'name': <name>
        },
        'relationships': {
            'course': {
                'data': {
                    <course (all_fields=False)>
            }
        },
        'links': {
            'self': <self link>
        }
    }

    If all_fields is False, 'name' will be the only field included
    (the rest of the fields under the 'attributes' and 'relationships' keys
    will be omitted).
    """
    data = {
        'type': 'semester',
        'id': semester.pk,
        'links': {
            'self': reverse('semester-handler', args=[semester.pk])
        },
        # 'meta': {
        #     'is_staff': user_is_semester_staff
        # },
        'attributes': {
            'name': semester.name
        }
    }

    if not all_fields:
        return data

    # if user_is_semester_staff:
    #     data['attributes']['semester_staff_names'] = (
    #         semester.semester_staff_names)
    #     data['attributes']['enrolled_student_names'] = (
    #         semester.enrolled_student_names)

    #     data['meta']['course_admin_names'] = (
    #         semester.course.course_admin_names)

    data['relationships'] = {
        'course': {
            'data': course_to_json(semester.course, all_fields=False)
        }
    }

    return data


# -----------------------------------------------------------------------------

def project_to_json(project, all_fields=True):
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
                'data': <semester (all_fields=False)>
            }
        }
    }

    When all_fields is False, 'name' will be the only field included
    (the rest of the fields under the 'attributes' and 'relationships'
    keys are not included).
    """
    data = {
        'type': 'project',
        'id': project.id,
        'links': {
            'self': reverse('project-handler', args=[project.pk])
        },
        'attributes': {
            'name': project.name
        }
    }

    if not all_fields:
        return data

    data['attributes'].update({
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
    })

    data['relationships'] = {
        'semester': {
            'data': semester_to_json(project.semester, all_fields=False)
        }
    }

    return data


# -----------------------------------------------------------------------------

def autograder_test_case_to_json(autograder_test_case, all_fields=True):
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
            'command_line_arguments': <value>,
            'standard_input': <value>,
            'test_resource_files': <value>,
            'student_resource_files': <value>,
            'time_limit': <value>,
            'expected_return_code': <value>,
            'expect_any_nonzero_return_code': <value>,
            'expected_standard_output': <value>,
            'expected_standard_error_output': <value>,
            'use_valgrind': <value>,
            'valgrind_flags': <value>,

            'points_for_correct_return_code': <value>,
            'points_for_correct_output': <value>,
            'deduction_for_valgrind_errors': <value>,
            'points_for_compilation_success': <value>,

            'feedback_configuration': <value>,

            // Present depending on type
            'compiler': <value>,
            'compiler_flags': <value>,
            'files_to_compile_together': <value>,
            'executable_name': <value>
        },
        'relationships': {
            'project': {
                'data': <project (all_fields=False)>
            }
        }
    }

    When all_fields is False, 'name' will be the only field included
    (the other fields under the 'attributes' and 'relationships'
    keys are not included).

    The 'type' field will be a string representing the dynamic type
    of the test case, and when that string is passed to the autograder
    test factory, the same kind of test case should be returned.
    """
    data = {
        'type': autograder_test_case.get_type_str(),
        'id': autograder_test_case.pk,
        'links': {
            'self': reverse('ag-test-handler', args=[autograder_test_case.pk])
        },
        'attributes': {
            'name': autograder_test_case.name
        }
    }

    if not all_fields:
        return data

    data['attributes'].update({
        'command_line_arguments': (
            autograder_test_case.command_line_arguments),
        'standard_input': autograder_test_case.standard_input,
        'student_resource_files': autograder_test_case.student_resource_files,
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
        'deduction_for_valgrind_errors': (
            autograder_test_case.deduction_for_valgrind_errors),
        'points_for_compilation_success': (
            autograder_test_case.points_for_compilation_success),
        'feedback_configuration': (
            autograder_test_case.feedback_configuration.to_json())
    })

    data['relationships'] = {
        'project': {
            'data': project_to_json(
                autograder_test_case.project, all_fields=False)
        }
    }

    if autograder_test_case.compiler:
        data['attributes'].update(
            {
                'compiler': autograder_test_case.compiler,
                'compiler_flags': autograder_test_case.compiler_flags,
                'files_to_compile_together': (
                    autograder_test_case.files_to_compile_together),
                'executable_name': autograder_test_case.executable_name
            }
        )

    return data


# -----------------------------------------------------------------------------

def submission_group_to_json(submission_group, all_fields=True):
    """
    Returns a JSON representation of the given submission group
    of the following form:
    {
        'type': 'submission_group',
        'id': <id>,
        'links': {
            'self': <self link>
        },
        'attributes': {
            'members': [<username>, ...],
            'extended_due_date': <date | None>
        },
        'relationships': {
            'project': {
                'data': <project (all_fields=False)>
            }
        }
    }

    When all_fields is False, 'members' will be the only field included
    (the other fields under the 'attributes' and 'relationships'
    keys are not included).
    """
    data = {
        'type': 'submission_group',
        'id': submission_group.pk,
        'links': {
            'self': reverse(
                'submission-group-with-id', args=[submission_group.pk])
        },
        'attributes': {
            'members': submission_group.members
        }
    }

    if not all_fields:
        return data

    data['attributes'].update({
        'extended_due_date': submission_group.extended_due_date
    })
    data['relationships'] = {
        'project': {
            'data': project_to_json(
                submission_group.project, all_fields=False)
        }
    }

    return data


# -----------------------------------------------------------------------------

def submission_to_json(submission, all_fields=True):
    """
    Returns a JSON representation of the given submission group of the
    following form:
    {
        'type': 'submission',
        'id': <id>,
        'links': {
            'self': <self link>
        }
        'attributes': {
            'submitted_files': [
                {
                    'filename': <filename>,
                    'file_url': <file_url>,
                    'size': <size>
                }
            ],
            'discarded_files': [<filename>, ...],
            'timestamp': <timestamp>,
            'status': <status>,
            'invalid_reason_or_error': <reason>
        },
        'relationships': {
            'submission_group': {
                'data': <submission_group (all_fields=False)>
            },
        }
    }

    When all_fields is False, 'timestamp' will be the only field included
    (the other fields under the 'attributes' and 'relationships' keys
    will be omitted).
    """
    data = {
        'type': 'submission',
        'id': submission.pk,
        'links': {
            'self': reverse('submission-handler', args=[submission.pk])
        },
        'attributes': {
            'timestamp': submission.timestamp
        }
    }

    if not all_fields:
        return data

    data['attributes'].update({
        'submitted_files': [
            {
                'filename': os.path.basename(file_.name),
                'file_url': reverse(
                    'get-submitted-file',
                    args=[submission.pk, os.path.basename(file_.name)]),
                'size': file_.size
            }
            for file_ in submission.submitted_files
        ],
        'discarded_files': submission.discarded_files,
        'status': submission.status,
        'invalid_reason_or_error': submission.invalid_reason_or_error
    })

    data['relationships'] = {
        'submission_group': {
            'data': submission_group_to_json(submission.submission_group)
        }
    }

    return data
