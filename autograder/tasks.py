import time

from celery import shared_task

from autograder.models import Course


@shared_task(bind=True, ignore_result=True)
def debug_task(self):
    print('starting task')
    for i in range(5):
        courses = Course.objects.all()
        print(courses)
        if courses:
            print('found {} courses'.format(courses.count()))
        else:
            print('no courses found')
        print('Waiting for {} seconds'.format(i))
        time.sleep(i)
    print('all done')


@shared_task(bind=True, ignore_result=True)
def grade_submission(self, submission):
    pass
