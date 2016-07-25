import time

from django.core.files.uploadedfile import SimpleUploadedFile

import autograder.core.models as ag_models
import autograder.core.tests.dummy_object_utils as obj_ut
from autograder.core.tests.temporary_filesystem_test_case import (
    TemporaryFilesystemTestCase)

from .tasks import grade_submission


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

        time.sleep(2)
        # print(ag_models.Submission.objects.all())
        # input('waaaaluigi time')

        self.submission.refresh_from_db()
        self.assertEqual(2, self.submission.basic_score)
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)

    def test_grade_submission_some_deferred(self):
        self.compiled_test.validate_and_update(deferred=True)
        grade_submission(self.submission.pk)

        # There is a potential, but extremely unlikely race condition
        # here.
        self.submission.refresh_from_db()
        self.assertEqual(
            ag_models.Submission.GradingStatus.waiting_for_deferred,
            self.submission.status)
        self.assertEqual(1, self.submission.basic_score)

        while (self.submission.status !=
                ag_models.Submission.GradingStatus.finished_grading):
            self.submission.refresh_from_db()
            time.sleep(2)

        self.submission.refresh_from_db()
        self.assertEqual(2, self.submission.basic_score)
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)

    def test_grade_submission_all_deferred(self):
        self.compiled_test.validate_and_update(deferred=True)
        self.interpreted_test.validate_and_update(deferred=True)
        grade_submission(self.submission.pk)

        self.submission.refresh_from_db()
        self.assertEqual(
            ag_models.Submission.GradingStatus.waiting_for_deferred,
            self.submission.status)
        self.assertEqual(0, self.submission.basic_score)

        while (self.submission.status !=
                ag_models.Submission.GradingStatus.finished_grading):
            self.submission.refresh_from_db()
            time.sleep(2)

        self.submission.refresh_from_db()
        self.assertEqual(2, self.submission.basic_score)
        self.assertEqual(ag_models.Submission.GradingStatus.finished_grading,
                         self.submission.status)

    def test_grade_submission_error_handling(self):
        self.fail()

    def test_grade_ag_test_retry_on_error(self):
        self.fail()

    def test_grade_ag_test_exceed_max_retries(self):
        self.fail()


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
