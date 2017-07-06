# See http://docs.celeryproject.org/en/latest/configuration.html
# for full option docs.

import datetime
import os

BROKER_URL = os.environ.get('AG_CELERY_BROKER_URL', 'amqp://guest@localhost:5672//')

CELERYD_PREFETCH_MULTIPLIER = 1
CELERYD_CONCURRENCY = 1

CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']  # Ignore other content
CELERY_RESULT_SERIALIZER = 'json'

CELERYD_MAX_TASKS_PER_CHILD = 1000

CELERY_RESULT_BACKEND = os.environ.get('AG_CELERY_RESULTS_BACKEND_URL',
                                       'redis://localhost:6379/0')
CELERY_RESULT_PERSISTENT = True

# Probably want to set some high max for this?
# CELERYD_TASK_TIME_LIMIT =

# Set this using the -c flag for the worker
# CELERYD_CONCURRENCY

CELERYBEAT_SCHEDULE = {
    'queue-submissions': {
        'task': 'autograder.grading_tasks.tasks.queue_submissions',
        'schedule': datetime.timedelta(
            seconds=int(os.environ.get('AG_SUBMISSION_LISTENER_INTERVAL', '5'))),
        'options': {
            'queue': 'periodic_tasks'
        }
    },
}

SUBMISSION_WORKER_PREFIX = 'submission_grader'
