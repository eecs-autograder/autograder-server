#! /usr/bin/env python3

import os
import sys
sys.path.append(os.path.basename(os.path.abspath(__file__)))
import traceback
import time
import uuid
import datetime
import signal
import argparse
import multiprocessing
import contextlib

DIVIDER = '=' * 79 + '\n'
DEFAULT_LOG_DIRNAME = 'worker_logs'


def main():
    try:
        args = parse_args()
        os.makedirs(args.log_dirname, mode=0o750, exist_ok=True)
        # main_listener_log_file = os.path.join(
        #     args.log_dirname, 'submission_listener.log')
        # with open(main_listener_log_file, 'a') as f, \
        #         contextlib.redirect_stdout(f):
        listen_for_and_grade_received_submissions(
            args.num_workers, args.django_settings_module, args.log_dirname)
    except KeyboardInterrupt:
        print('KEYBOARD INTERRUPT. Shutting down...')
    except Exception as e:
        print('SOMETHING VERY BAD HAPPENED')
        print(e)
        print(traceback.format_exc())


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("num_workers", type=int)
    parser.add_argument("django_settings_module")
    parser.add_argument("--log_dirname", '-d', default=DEFAULT_LOG_DIRNAME)

    return parser.parse_args()


def listen_for_and_grade_received_submissions(num_workers,
                                            django_settings_module,
                                            log_dirname):
    print(os.getpid())
    print('hello world')

    multiprocessing.set_start_method('spawn')

    initialize_process(django_settings_module)

    from autograder.models import Submission
    from django.db import transaction

    with multiprocessing.Pool(processes=num_workers,
                              initializer=initialize_process,
                              initargs=[django_settings_module]) as workers:
        while True:
            submission_ids = []
            with transaction.atomic():
                received_submissions = Submission.objects.select_for_update(
                ).filter(
                    status=Submission.GradingStatus.received
                ).order_by('_timestamp')
                if not received_submissions:
                    time.sleep(1)
                    continue

                print('queueing submissions')
                for submission in received_submissions:
                    submission.status = Submission.GradingStatus.queued
                    submission.save()
                    submission_ids.append(submission.pk)

            for sub_id in submission_ids:
                workers.apply_async(grade_submission, [sub_id, log_dirname])

            # submission_ids = (
            #     (sub.pk, log_dirname) for sub in received_submissions)
            # workers.starmap(grade_submission, submission_ids)


def initialize_process(django_settings_module):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", django_settings_module)

    import django
    django.setup()

    # print(django.db.connection)

    def sigterm_handler(sig_num, stack):
        from django.db import connection
        connection.close()
        raise SystemExit

    signal.signal(signal.SIGTERM, sigterm_handler)


def grade_submission(submission_id, log_dirname):
    with get_worker_log_file(log_dirname) as f, \
            contextlib.redirect_stdout(f):
            # contextlib.redirect_stderr(f):
        from autograder.models import Submission
        import autograder.shared.utilities as ut

        print('grade_submission:', submission_id)
        try:
            submission = Submission.objects.get(pk=submission_id)
            submission.status = Submission.GradingStatus.being_graded
            submission.save()

            with ut.ChangeDirectory(ut.get_submission_dir(submission)):
                prepare_and_run_tests(submission)
                submission.status = Submission.GradingStatus.finished_grading
                submission.save()
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            submission.status = Submission.GradingStatus.error
            submission.invalid_reason_or_error = [str(e)]
            submission.save()
        finally:
            print(DIVIDER * 3)


def get_worker_log_file(log_dirname):
    log_filename = os.path.join(
        log_dirname,
        'worker{}.log'.format(multiprocessing.current_process().pid))
    return open(log_filename, 'a')


def prepare_and_run_tests(submission):
    from autograder.autograder_sandbox import AutograderSandbox

    import autograder.shared.utilities as ut

    group = submission.submission_group
    project_files_dir = ut.get_project_files_dir(group.project)

    sandbox_name = '{}-{}-{}'.format(
        '_'.join(sorted(group.members)).replace('@', '.'),
        submission.timestamp.strftime('%Y-%m-%d_%H.%M.%S'),
        uuid.uuid4().hex)
    print(sandbox_name)

    # HACK: this is a workaround to make it so that different docker
    # containers use users with different UIDs
    sandbox_linux_user_id = (submission.pk + 2000) % 3000
    with AutograderSandbox(name=sandbox_name,
                           linux_user_id=sandbox_linux_user_id) as sandbox:
        for test_case in group.project.autograder_test_cases.all():
            print(test_case.name)
            files_to_copy = (
                test_case.student_resource_files +
                [os.path.join(project_files_dir, filename) for
                 filename in test_case.test_resource_files])
            sandbox.copy_into_sandbox(*files_to_copy)

            result = test_case.run(
                submission=submission, autograder_sandbox=sandbox)
            print('finished_running')
            result.save()

            sandbox.clear_working_dir()


if __name__ == '__main__':
    main()
