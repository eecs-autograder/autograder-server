import itertools

import sys
import os
import multiprocessing
import django
from django.db import transaction
from django.db.utils import OperationalError, InterfaceError

sys.path.append('.')
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "autograder.settings.production")
django.setup()

from autograder.core.models import *


def main():
    # convert_suite_res_output(AGTestSuiteResult.objects.first())
    # convert_cmd_res_output(AGTestCommandResult.objects.first())

    suite_results = [res.pk for res in AGTestSuiteResult.objects.all()]
    cmd_results = [res.pk for res in AGTestCommandResult.objects.all()]

    from django.db import connections
    connections.close_all()

    print('starting suites', file=sys.stderr)
    with multiprocessing.Pool(8) as pool:
        pool.map(convert_suite_res_output, suite_results)

    print('starting cmds', file=sys.stderr)

    with multiprocessing.Pool(8) as pool:
        pool.map(convert_cmd_res_output, cmd_results)

    print('finished')


def convert_suite_res_output(suite_res_pk: int):
    from django.db import connection

    suite_res = AGTestSuiteResult.objects.get(pk=suite_res_pk)
    # print('suite', suite_res.pk)
    suite_res.submission.save()
    while True:
        try:
            with suite_res.open_setup_stdout('w') as f:
                f.write(suite_res.setup_stdout)
            with suite_res.open_setup_stderr('w') as f:
                f.write(suite_res.setup_stderr)
            with suite_res.open_teardown_stdout('w') as f:
                f.write(suite_res.teardown_stdout)
            with suite_res.open_teardown_stderr('w') as f:
                f.write(suite_res.teardown_stderr)

            break
        except OperationalError:
            pass
        except InterfaceError:
            connection.close()


def convert_cmd_res_output(cmd_res_pk: int):
    from django.db import connection

    cmd_res = AGTestCommandResult.objects.get(pk=cmd_res_pk)
    # print('cmd', cmd_res.pk)
    while True:
        try:
            with cmd_res.open_stdout('w') as f:
                f.write(cmd_res.stdout)

            with cmd_res.open_stderr('w') as f:
                f.write(cmd_res.stderr)
            break
        except OperationalError:
            pass
        except InterfaceError:
            connection.close()

if __name__ == '__main__':
    main()
