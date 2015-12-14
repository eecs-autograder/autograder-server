#! /usr/bin/env python3

"""
Tests database locking for SubmissionGroup.objects.validate_and_create()
to prevent a race condition that allows multiple SubmissionGroup for
a user to be created.
"""

import sys
sys.path.append('..')

import os
import multiprocessing


COURSE_NAME = 'test-course'
SEMESTER_NAME = 'test-semester'
PROJECT_NAME = 'test-project'
GROUP_MEMBERS = ['test-student1']

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "system_test_settings")


def main():
    tried_to_create = multiprocessing.Event()
    lock_acquired = multiprocessing.Event()

    acquire_lock_proc = multiprocessing.Process(
        target=acquire_lock, args=[tried_to_create, lock_acquired])
    acquire_lock_proc.start()

    lock_acquired.wait()
    print('lock was acquired')

    group_created = multiprocessing.Event()

    try_to_create_proc = multiprocessing.Process(
        target=try_to_create, args=[group_created])
    try_to_create_proc.start()
    try_to_create_proc.join(3)

    import django
    django.setup()

    from django.core.exceptions import ObjectDoesNotExist
    from autograder.core.models import (
        SubmissionGroup, Course, Semester, Project)

    try:
        try:
            SubmissionGroup.objects.get(
                project__name=PROJECT_NAME)
            print('Exception not thrown')
            assert False
        except ObjectDoesNotExist:
            pass

        tried_to_create.set()
        acquire_lock_proc.join()
        print('locking process done.')

        group_created.wait()

        new_group = SubmissionGroup.objects.get(
            project__name=PROJECT_NAME)
        assert list(new_group.members) == GROUP_MEMBERS

        try_to_create_proc.join()
    except Exception:
        acquire_lock_proc.terminate()
        try_to_create_proc.terminate()
        raise
    finally:
        Course.objects.get(name=COURSE_NAME).delete()


def try_to_create(group_created):
    try:
        import django
        django.setup()

        from autograder.core.models import (
            SubmissionGroup, Course, Semester, Project)

        # try:
        #     print('aksdfajsdklfsad')
        #     Course.objects.filter(name=COURSE_NAME).delete()
        # except Exception as e:
        #     print('blaaaaaaaaah', e)
        #     pass

        course = Course(name=COURSE_NAME)
        course.save()

        semester = Semester.objects.validate_and_create(
            name=SEMESTER_NAME, course=course)
        project = Project.objects.validate_and_create(
            name=PROJECT_NAME, semester=semester,
            allow_submissions_from_non_enrolled_students=True
        )

        print('Trying to create group')
        SubmissionGroup.objects.validate_and_create(
            members=GROUP_MEMBERS, project=project)
        print('group created')
    except Exception as e:
        print('ERROR')
        print(e)
        import traceback
        traceback.print_exc()
    finally:
        group_created.set()


def acquire_lock(tried_to_create, lock_acquired):
    import django

    django.setup()

    from django.db import connection, transaction
    from autograder.core.models import SubmissionGroup

    print('grabbing lock for:', SubmissionGroup.objects.model._meta.db_table)
    with connection.cursor() as c, transaction.atomic():
        # print(c.db.settings_dict)
        # c.execute('BEGIN')
        c.execute(
            'LOCK TABLE {} IN ROW EXCLUSIVE MODE'.format(
                SubmissionGroup.objects.model._meta.db_table)
        )
        lock_acquired.set()
        tried_to_create.wait()
        print('about to release lock')


if __name__ == '__main__':
    main()
