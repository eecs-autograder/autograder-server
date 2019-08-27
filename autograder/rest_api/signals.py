from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from autograder.core.caching import clear_submission_results_cache
import autograder.core.models as ag_models
from autograder.grading_tasks.tasks import register_project_queues


@receiver(post_save, sender=ag_models.Project)
def on_project_created(sender, instance, created, **kwargs):
    if not created:
        return

    from autograder.celery import app
    register_project_queues.apply_async(
        kwargs={'project_pks': [instance.pk]}, queue='small_tasks',
        connection=app.connection())


@receiver(post_save, sender=ag_models.AGTestSuite)
def on_ag_test_suite_save(sender, instance: ag_models.AGTestSuite, created, **kwargs):
    if not created:
        clear_submission_results_cache(instance.project_id)


@receiver(post_delete, sender=ag_models.AGTestSuite)
def on_ag_test_suite_delete(sender, instance: ag_models.AGTestSuite, *args, **kwargs):
    clear_submission_results_cache(instance.project_id)


@receiver(post_save, sender=ag_models.AGTestCase)
def on_ag_test_case_save(sender, instance: ag_models.AGTestCase, created, **kwargs):
    if not created:
        clear_submission_results_cache(instance.ag_test_suite.project_id)


@receiver(post_delete, sender=ag_models.AGTestCase)
def on_ag_test_case_delete(sender, instance: ag_models.AGTestCase, *args, **kwargs):
    clear_submission_results_cache(instance.ag_test_suite.project_id)


@receiver(post_save, sender=ag_models.AGTestCommand)
def on_ag_test_command_save(sender, instance: ag_models.AGTestCommand, created, **kwargs):
    if not created:
        clear_submission_results_cache(instance.ag_test_case.ag_test_suite.project_id)


@receiver(post_delete, sender=ag_models.AGTestCommand)
def on_ag_test_command_delete(sender, instance: ag_models.AGTestCommand, *args, **kwargs):
    clear_submission_results_cache(instance.ag_test_case.ag_test_suite.project_id)


@receiver(post_save, sender=ag_models.StudentTestSuite)
def on_student_test_suite_save(sender, instance: ag_models.StudentTestSuite, created, **kwargs):
    if not created:
        clear_submission_results_cache(instance.project_id)


@receiver(post_delete, sender=ag_models.StudentTestSuite)
def on_student_test_suite_delete(sender, instance: ag_models.StudentTestSuite, *args, **kwargs):
    clear_submission_results_cache(instance.project_id)
