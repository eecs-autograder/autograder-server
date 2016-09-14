import datetime
import os
from kombu import Queue


BROKER_URL = os.environ.get('AG_CELERY_BROKER_URL', 'amqp://guest@localhost:5672//')

CELERYD_PREFETCH_MULTIPLIER = 1
CELERYD_CONCURRENCY = 1

CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']  # Ignore other content
CELERY_RESULT_SERIALIZER = 'json'
#CELERY_QUEUES = (
#    Queue('submissions'),
#    Queue('deferred'),
#    Queue('submission_listener')
#)

#CELERYBEAT_SCHEDULE = {
#    'queue-submissions': {
#        'task': 'autograder.celery.queue_submissions',
#        'schedule': datetime.timedelta(seconds=5),  # UPDATE AS DESIRED
#        'options': {
#            'queue': 'submission_listener'
#        }
#    },
#}
