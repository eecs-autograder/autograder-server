#! /usr/bin/env python3

import sys
sys.path.append('..')
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "system_test_settings")

import django
django.setup()

import argparse
import json
import multiprocessing
import subprocess
import time
import uuid

from autograder.core.models import (
    Course, Semester, Project, AutograderTestCaseFactory,
    SubmissionGroup, Submission
    # AutograderTestCaseBase,
    # CompiledAutograderTestCase, CompilationOnlyAutograderTestCase
)
# import autograder.core.tests.dummy_object_utils as obj_ut
from django.db.models import Q
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

objects_created = []
workers = []


def main():
    args = parse_args()

    # if args.flush_db:
    #     CompiledAutograderTestCase.objects.all().delete()
    #     CompilationOnlyAutograderTestCase.objects.all().delete()
    #     AutograderTestCaseBase.objects.all().delete()
    #     Project.objects.all().delete()
    #     Semester.objects.all().delete()
    #     Course.objects.get(name='eecs280-stress-test').delete()
    #     return

    data = None
    with open('stress-test-data.json') as f:
        data = json.load(f)

    for obj in data:
        # print(obj)
        model_deserializers[obj['model']](obj)

    start_workers(args.num_workers)

    for i in range(args.num_submissions):
        p = Project.objects.get(name='Project 1 - Romance')
        group = SubmissionGroup.objects.validate_and_create(
            members=['stress_user{}'.format(i)], project=p)
        objects_created.append(group)
        submission = Submission.objects.validate_and_create(
            submission_group=group, submitted_files=_get_files_to_submit())
        objects_created.append(submission)
        # submission.status =
        # submission.save()

    num_submissions_left = get_num_submissions_being_processed()
    while num_submissions_left:
        print("{} Submission(s) remaining".format(num_submissions_left))
        time.sleep(3)
        num_submissions_left = get_num_submissions_being_processed()

    for submission in Submission.objects.all():
        if submission.submission_group.project.name != 'Project 1 - Romance':
            print('skipping submission from project',
                  submission.submission_group.project.name)
        if submission.status != 'finished_grading':
            print('Unexpected status from submission',
                  submission.pk, submission.submission_group.members,
                  'Expected "finished_grading" but was', submission.status)
            print('Reason:', submission.invalid_reason_or_error)

        results = [result.to_json() for result in submission.results.all()]
        total_points = sum(
            result['total_points_awarded']
            for result in results)

        if total_points != 21:
            print('Unexpected number of points from submission',
                  submission.pk, submission.submission_group.members,
                  'Expected', 21, 'but was', total_points)
            print(json.dumps(results, indent=4, sort_keys=True))

    print('yay')
    time.sleep(3)


def get_num_submissions_being_processed():
    return len(Submission.objects.filter(
        Q(status=Submission.GradingStatus.queued) |
        Q(status=Submission.GradingStatus.received) |
        Q(status=Submission.GradingStatus.being_graded))
    )


def parse_args():
    parser = argparse.ArgumentParser()
    # parser.add_argument("--flush_db", action='store_true')
    parser.add_argument('num_workers', type=int)
    parser.add_argument('num_submissions', type=int)

    return parser.parse_args()


def load_course(json_):
    objects_created.append(
        Course.objects.validate_and_create(**json_['fields']))


def load_semester(json_):
    json_['fields']['course'] = Course.objects.get(
        name=json_['fields']['course'])
    objects_created.append(
        Semester.objects.validate_and_create(**json_['fields']))


def load_project(json_):
    json_['fields']['semester'] = Semester.objects.get(
        name=json_['fields']['semester'])
    p = Project.objects.validate_and_create(**json_['fields'])
    objects_created.append(p)
    for filename in json_['proj_files']:
        path = os.path.join('stress-project-files', filename)
        with open(path, 'rb') as f:
            p.add_project_file(
                SimpleUploadedFile(filename, f.read()))


def load_test_case(json_):
    json_['fields']['project'] = Project.objects.get(
        name=json_['fields']['project'])
    objects_created.append(
        AutograderTestCaseFactory.validate_and_create(
            json_['type'], **json_['fields']))


def start_workers(num_workers):
    # for i in range(num_workers):
    log_file = open('listener.log', 'w')
    worker = subprocess.Popen(
        ['python3', '-u',
         '../submission_listener_multiprocessing.py',
         str(num_workers), 'system_test_settings'],
        universal_newlines=True, stderr=subprocess.STDOUT,
        stdout=log_file)
    workers.append((worker, log_file))


_files_to_submit = []
def _get_files_to_submit():
    global _files_to_submit
    if _files_to_submit:
        return _files_to_submit

    uploaded_files = []
    filenames = ["main.cpp", "stats-tests.cpp", "stats.cpp"]
    for filename in filenames:
        path = os.path.join('stress-submission-files', filename)
        with open(path, 'rb') as f:
            uploaded_files.append(SimpleUploadedFile(filename, f.read()))
    _files_to_submit = uploaded_files
    return _files_to_submit


model_deserializers = {
    "autograder.course": load_course,
    "autograder.semester": load_semester,
    "autograder.project": load_project,
    "autograder.compiledautogradertestcase": load_test_case,
    "autograder.compilationonlyautogradertestcase": load_test_case
}


if __name__ == '__main__':
    try:
        main()
    finally:
        print('Destroying db objects...')
        while objects_created:
            objects_created.pop().delete()
        print('Stopping workers...')
        for process, log, in workers:
            log.close()
            process.terminate()
        print('Storing logs...')
        dirname = 'stress_test_{}_{}'.format(
            timezone.now().strftime('%Y-%m-%d_%H.%M.%S'), uuid.uuid4().hex)
        os.mkdir(dirname, mode=0o750)
        subprocess.call(['mv'] + [log.name for p, log in workers] + [dirname])
        subprocess.call(['mv', 'worker_logs', dirname])
        print('Done')
