import subprocess
import time
from unittest import mock

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

import autograder.core.models as ag_models
import autograder.core.tests.dummy_object_utils as obj_ut
from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from .tasks import grade_submission, grade_ag_test, grade_ag_test_impl


class _MockException(Exception):
    pass


class TasksTestCase(TemporaryFilesystemTestCase):
    def setUp(self):
        super().setUp()

        self.group = obj_ut.build_submission_group()
        self.project = self.group.project

        impl_h = ag_models.UploadedFile.objects.validate_and_create(
            file_obj=SimpleUploadedFile('impl.h', _IMPL_H),
            project=self.project)

        needs_files_test = ag_models.UploadedFile.objects.validate_and_create(
            file_obj=SimpleUploadedFile('needs_files_test.py',
                                        _NEEDS_FILES_TEST),
            project=self.project)

        unit_test = ag_models.UploadedFile.objects.validate_and_create(
            file_obj=SimpleUploadedFile('unit_test.cpp', _UNIT_TEST),
            project=self.project)

        impl_cpp = ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            pattern='impl.cpp',
            project=self.project)

        test_star_cpp = ag_models.ExpectedStudentFilePattern.objects.validate_and_create(
            pattern='test*.cpp', min_num_matches=1, max_num_matches=4,
            project=self.project)

        self.compiled_test = ag_models.AutograderTestCaseFactory.validate_and_create(
            'compiled_and_run_test_case', name='compiley', compiler='g++',
            expected_return_code=0, points_for_correct_return_code=1,
            feedback_configuration=ag_models.FeedbackConfig.create_with_max_fdbk(),
            project=self.project)
        self.compiled_test.test_resource_files.add(impl_h)
        self.compiled_test.project_files_to_compile_together.add(unit_test)
        self.compiled_test.student_files_to_compile_together.add(impl_cpp)

        self.interpreted_test = ag_models.AutograderTestCaseFactory.validate_and_create(
            'interpreted_test_case', name='interprety', interpreter='python3',
            entry_point_filename=needs_files_test.name,
            expected_return_code=0, points_for_correct_return_code=1,
            feedback_configuration=ag_models.FeedbackConfig.create_with_max_fdbk(),
            project=self.project)
        self.interpreted_test.test_resource_files.add(needs_files_test)
        self.interpreted_test.student_resource_files.add(test_star_cpp)

        test_files = [SimpleUploadedFile('test{}.cpp'.format(i), b'waaaa')
                      for i in range(2)]
        self.submission = ag_models.Submission.objects.validate_and_create(
            test_files + [SimpleUploadedFile('impl.cpp', _IMPL_CPP)],
            submission_group=self.group)

    def test_grade_submission_no_deferred(self):
        print(self.submission.pk)
        grade_submission(self.submission.pk)

        self._wait_for_deferreds()

        self.submission.refresh_from_db()
        self.assertEqual(2, self.submission.basic_score)
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)

    def test_grade_submission_some_deferred(self):
        self.compiled_test.validate_and_update(deferred=True)
        grade_submission(self.submission.pk)

        self._check_deferred_grading_results(1, 2)

    def test_grade_submission_all_deferred(self):
        self._mark_all_as_deferred()
        grade_submission(self.submission.pk)

        self._check_deferred_grading_results(0, 2)

    @mock.patch('autograder.grading_tasks.tasks.grade_ag_test_impl')
    def test_non_deferred_retry_on_called_process_error(self, sandbox_mock):
        sandbox_mock.side_effect = TasksTestCase._SideEffectSequence([
            subprocess.CalledProcessError(42, ['waaaluigi']),
            grade_ag_test_impl,
            subprocess.CalledProcessError(42, ['waaaluigi']),
            grade_ag_test_impl])
        grade_submission(self.submission.pk)

        self._wait_for_deferreds()

        self.submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)
        self.assertEqual(2, self.submission.basic_score)

    class _SideEffectSequence:
        '''
        In some situations, we want to pass a mix of values, exceptions,
        and callables to the side_effects parameter of a mock object.
        This class enables that.
        '''

        def __init__(self, side_effects):
            self._side_effects = side_effects
            self._iter = iter(self._side_effects)

        def __call__(self, *args, **kwargs):
            print(args, kwargs)
            next_item = next(self._iter)
            try:
                return next_item(*args, **kwargs)
            except TypeError as e:
                print(e)

            try:
                raise next_item
            except TypeError as e:
                print(e)

            return next_item

    @mock.patch('autograder.grading_tasks.tasks.AutograderSandbox')
    def test_non_deferred_fatal_error_handling(self, sandbox_mock):
        sandbox_mock.side_effect = _MockException('O noez, teh fatal errorz')
        with self.assertRaises(_MockException):
            grade_submission(self.submission.pk)

        self._wait_for_deferreds()

        self.submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.error,
                         self.submission.status)
        self.assertEqual(0, self.submission.basic_score)

    @mock.patch('autograder.grading_tasks.tasks.AutograderSandbox')
    def test_non_deferred_max_num_retries_exceeded(self, sandbox_mock):
        sandbox_mock.side_effect = [
            subprocess.CalledProcessError(42, ['waaaluigi'])
            for i in range(settings.AG_TEST_MAX_RETRIES + 1)]
        with self.assertRaises(subprocess.CalledProcessError):
            grade_submission(self.submission.pk)

        self._wait_for_deferreds()

        self.submission.refresh_from_db()
        self.assertEqual(ag_models.Submission.GradingStatus.error,
                         self.submission.status)
        self.assertEqual(0, self.submission.basic_score)

    @mock.patch('autograder.grading_tasks.tasks.AutograderSandbox')
    def test_deferred_retry_on_called_process_error(self, sandbox_mock):
        self.interpreted_test.validate_and_update(deferred=True)
        self.compiled_test.delete()
        sandbox_mock.side_effect = [
            subprocess.CalledProcessError(42, ['waaaluigi']),
            mock.DEFAULT]
        grade_submission(self.submission.pk)

        self._check_deferred_grading_results(0, 1)

    @mock.patch('autograder.grading_tasks.tasks.AutograderSandbox')
    def test_deferred_ag_test_fatal_error(self, sandbox_mock):
        sandbox_mock.side_effect = _MockException('very bad error')
        with self.assertRaises(_MockException):
            grade_ag_test(self.compiled_test.pk, self.submission.pk)

    @mock.patch('autograder.grading_tasks.tasks.AutograderSandbox')
    def test_deferred_ag_test_max_retries_exceeded(self, sandbox_mock):
        sandbox_mock.side_effect = [
            subprocess.CalledProcessError(42, ['waaaluigi'])
            for i in range(settings.AG_TEST_MAX_RETRIES + 1)]
        with self.assertRaises(subprocess.CalledProcessError):
            grade_ag_test(self.compiled_test.pk, self.submission.pk)

    def _check_deferred_grading_results(self, expected_non_deferred_score,
                                        expected_total_score):
        # There is a potential but extremely unlikely race condition
        # here. Since the deferred test grading should take seconds,
        # we probably don't need to worry about the deferred tests
        # finishing before we check the waiting_for_deferred status.
        self.submission.refresh_from_db()
        self.assertEqual(
            ag_models.Submission.GradingStatus.waiting_for_deferred,
            self.submission.status)
        self.assertEqual(expected_non_deferred_score,
                         self.submission.basic_score)

        self._wait_for_deferreds()

        self.submission.refresh_from_db()
        self.assertEqual(expected_total_score, self.submission.basic_score)
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)

    def _wait_for_deferreds(self):
        time_waited = 0
        while (self.submission.status !=
                ag_models.Submission.GradingStatus.finished_grading and
               self.submission.status !=
                ag_models.Submission.GradingStatus.error):
            if time_waited > 30:
                self.fail('Waited to long for deferred tests')
            self.submission.refresh_from_db()
            time.sleep(2)
            time_waited += 2

    def _mark_all_as_deferred(self):
        self.compiled_test.validate_and_update(deferred=True)
        self.interpreted_test.validate_and_update(deferred=True)
        for test in self.project.autograder_test_cases.all():
            self.assertTrue(test.deferred)


_NEEDS_FILES_TEST = b'''
import os
import fnmatch

def main():
    num_files = len(fnmatch.filter(os.listdir('.'), 'test*.cpp'))
    if num_files != 2:
        print('booooo')
        raise SystemExit(1)

    print('yay')


if __name__ == '__main__':
    main()
'''

_UNIT_TEST = b'''
#include "impl.h"

#include <iostream>
#include <cassert>

using namespace std;

int main()
{
    assert(spam() == 42);
    cout << "yay!" << endl;
}
'''

_IMPL_H = b'''
#ifndef IMPL_H
#define IMPL_H

int spam();

#endif
'''

_IMPL_CPP = b'''
#include "impl.h"

int spam()
{
    return 42;
}
'''
