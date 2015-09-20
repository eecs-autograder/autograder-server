#! /usr/bin/env python3

"""
Tests database locking for Submission POST request handler
to prevent a race condition that allows multiple Submissions
for a user to be queued at the same time.
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

    submission_created = multiprocessing.Event()

    try_to_create_proc = multiprocessing.Process(
        target=try_to_create, args=[submission_created])
    try_to_create_proc.start()
    try_to_create_proc.join(3)

    import django
    django.setup()

    from django.core.exceptions import ObjectDoesNotExist
    from autograder.models import (
        Submission, SubmissionGroup, Course, Semester, Project)

    try:
        try:
            Submission.objects.get(
                submission_group__project__name=PROJECT_NAME)
            print('Exception not thrown')
            assert False
        except ObjectDoesNotExist:
            pass

        tried_to_create.set()
        acquire_lock_proc.join()
        print('locking process done.')

        submission_created.wait()

        Submission.objects.get(
            submission_group__project__name=PROJECT_NAME)

        try_to_create_proc.join()
    except Exception:
        acquire_lock_proc.terminate()
        try_to_create_proc.terminate()
        raise
    finally:
        Course.objects.get(name=COURSE_NAME).delete()


def try_to_create(submission_created):
    try:
        import django
        django.setup()

        from django.test import RequestFactory
        from django.contrib.auth.models import User

        from autograder.frontend.ajax_request_handlers.submission_request_handlers import SubmissionRequestHandler
        from autograder.models import (
            SubmissionGroup, Course, Semester, Project)

        course = Course.objects.validate_and_create(name=COURSE_NAME)

        semester = Semester.objects.validate_and_create(
            name=SEMESTER_NAME, course=course)
        project = Project.objects.validate_and_create(
            name=PROJECT_NAME, semester=semester,
            allow_submissions_from_non_enrolled_students=True
        )
        group = SubmissionGroup.objects.validate_and_create(
            members=GROUP_MEMBERS, project=project)

        print('Trying to create submission')
        # Submission.objects.validate_and_create(
        #     submission_group=group, submitted_files=[])
        request = RequestFactory().post(
            '/submissions/submission/',
            {'files': [], 'submission_group_id': group.pk})
        request.user = User.objects.get_or_create(username=GROUP_MEMBERS[0])[0]

        response = SubmissionRequestHandler.as_view()(request)
        print('Response code:', response.status_code)
        print(response.content)
        assert response.status_code == 201
        request.user.delete()
    except Exception as e:
        import traceback
        print('ERROR')
        print(e)
        traceback.print_exc()
    finally:
        submission_created.set()


def acquire_lock(tried_to_create, lock_acquired):
    import django

    django.setup()

    from django.db import connection
    from autograder.models import Submission

    print('grabbing lock for:', Submission.objects.model._meta.db_table)
    with connection.cursor() as c:
        # print(c.db.settings_dict)
        c.execute('BEGIN')
        c.execute(
            'LOCK TABLE {} IN ROW EXCLUSIVE MODE'.format(
                Submission.objects.model._meta.db_table)
        )
        lock_acquired.set()
        tried_to_create.wait()
        print('about to release lock')


if __name__ == '__main__':
    main()
