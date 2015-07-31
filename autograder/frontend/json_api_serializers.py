from django.core.urlresolvers import reverse

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

    if with_fields:
        data['attributes'] = {
            'name': course.name,
            'course_admin_names': course.course_admin_names
        }

    return data


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
            'self': reverse('get-semester', args=[semester.pk])
        },
        'meta': {
            'is_staff': user_is_semester_staff
        }
    }

    if with_fields:
        data['attributes'] = {
            'name': semester.name
        }

        if user_is_semester_staff:
            data['attributes']['semester_staff_names'] = semester.semester_staff_names
            data['attributes']['enrolled_student_names'] = semester.enrolled_student_names

            data['meta']['course_admin_names'] = semester.course.course_admin_names

        data['relationships'] = {
            'course': {
                'data': course_to_json(semester.course, with_fields=False)
            }
        }

    return data


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
                    'file_url': <file url>
                },
                ...
            ],
            'visible_to_students': ...,
            'closing_time': ...,
            'disallow_student_submissions': ...,
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

    if with_fields:
        data['attributes'] = {
            'name': project.name,
            'project_files': [
                {
                    'filename': filename,
                    'file_url': reverse(
                        'get-project-file', args=[project.pk, filename])
                }
                for filename in project.get_project_file_basenames()
            ],
            'visible_to_students': project.visible_to_students,
            'closing_time': project.closing_time,
            'disallow_student_submissions': project.disallow_student_submissions,
            'min_group_size': project.min_group_size,
            'max_group_size': project.max_group_size,
            'required_student_files': project.required_student_files,
            'expected_student_file_patterns': project.expected_student_file_patterns,
        }

        data['relationships'] = {
            'semester': {
                'data': semester_to_json(project.semester, with_fields=False)
            }
        }

    return data
