# See http://docs.celeryproject.org/en/latest/configuration.html
# for full option docs.

import datetime
import os

BROKER_URL = os.environ.get('AG_CELERY_BROKER_URL', 'amqp://guest@localhost:5672//')

CELERYD_PREFETCH_MULTIPLIER = 1
# Set this using the -c flag for the worker
CELERYD_CONCURRENCY = 1

CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']  # Ignore other content
CELERY_RESULT_SERIALIZER = 'json'

CELERYD_MAX_TASKS_PER_CHILD = 1000

CELERY_RESULT_BACKEND = os.environ.get('AG_CELERY_RESULTS_BACKEND_URL',
                                       'redis://localhost:6379/0')
CELERY_RESULT_PERSISTENT = True

BROKER_POOL_LIMIT = None

CELERYBEAT_SCHEDULE = {
    'queue-submissions': {
        'task': 'autograder.grading_tasks.tasks.queueing.queue_submissions',
        'schedule': datetime.timedelta(
            seconds=int(os.environ.get('AG_SUBMISSION_LISTENER_INTERVAL', '5'))),
        'options': {
            'queue': 'periodic_tasks'
        }
    },
}

SUBMISSION_WORKER_PREFIX = 'submission_grader'
FAST_GRADER_WORKER_PREFIX = 'fast_submission_grader'
DEFERRED_WORKER_PREFIX = 'deferred'
RERUN_WORKER_PREFIX = 'rerun'

SUBMISSION_QUEUE_TMPL = 'project{}'
FAST_QUEUE_TMPL = 'fast_project{}'
DEFERRED_QUEUE_TMPL = 'deferred_project{}'
RERUN_QUEUE_TMPL = 'rerun_project{}'

# Grading workers should be configured to have a hostname of
# XX@host_machine, where XX is one of the keys in this dictionary.
# This dictionary then defines the kinds of queues those workers should
# consume from. For example, 'submission_grader' workers consume from
# both 'project' and 'fast_project' queues.
WORKER_PREFIX_TO_QUEUE_TMPLS = {
    SUBMISSION_WORKER_PREFIX: [SUBMISSION_QUEUE_TMPL, FAST_QUEUE_TMPL],
    FAST_GRADER_WORKER_PREFIX: [FAST_QUEUE_TMPL],
    DEFERRED_WORKER_PREFIX: [DEFERRED_QUEUE_TMPL],
    RERUN_WORKER_PREFIX: [RERUN_QUEUE_TMPL],
}
