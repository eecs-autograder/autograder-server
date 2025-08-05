import datetime
import sys

from django.core.management.base import BaseCommand
from django.db import transaction

from autograder.core.migrate_output import (
    migrate_ag_test_command_result_output,
    migrate_ag_test_suite_result_output,
    migrate_mutation_test_suite_result_output
)
import autograder.core.models as ag_models
from autograder.core.submission_feedback import update_denormalized_ag_test_results


class Command(BaseCommand):
    help = (
        "Incrementally migrate stored output to the optimized format "
        "added in version 2025.08.0"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--summarize",
            action='store_true',
            default=False,
            help='Print a summary of how many submissions have had '
                 'their output migrated, then exit.'
                 'Works with --since and --until'
        )
        parser.add_argument("--since", "-s", type=datetime.date.fromisoformat)
        parser.add_argument("--until", "-u", type=datetime.date.fromisoformat)
        parser.add_argument("--limit", "-l", type=int)

    def handle(self, *args, **options):
        since = options['since']
        if since is None:
            since = datetime.date(2000, 1, 1)

        until = options['until']
        if until is None:
            until = datetime.date.today()

        submissions_ascending = ag_models.Submission.objects.order_by('pk')
        in_date_range = submissions_ascending.filter(
            timestamp__gte=since,
            timestamp__lte=until,
        )
        not_migrated_query = in_date_range.filter(_output_migrated=False)

        if options['summarize']:
            total = in_date_range.count()
            migrated_count = total - not_migrated_query.count()
            print(f'{migrated_count}/{total} submissions between {since} and {until} '
                  'have had their output migrated')
            return

        limit = options['limit']
        if limit is None:
            limit = not_migrated_query.count()

        print(f'Migrating output for {limit} '
              f'submissions between {since} and {until}')

        errors = []

        for submission in not_migrated_query[:limit]:
            print(f'Migrating submission {submission.pk}')
            try:
                with transaction.atomic():
                    for ag_test_suite_result in submission.ag_test_suite_results.all():
                        migrate_ag_test_suite_result_output(ag_test_suite_result)

                    cmd_results = ag_models.AGTestCommandResult.objects.filter(
                        ag_test_case_result__ag_test_suite_result__submission=submission)
                    for ag_test_cmd_result in cmd_results:
                        migrate_ag_test_command_result_output(ag_test_cmd_result)

                    for mutation_suite_result in submission.mutation_test_suite_results.all():
                        migrate_mutation_test_suite_result_output(mutation_suite_result)

                    submission = update_denormalized_ag_test_results(submission.pk)

                    submission._output_migrated = True
                    submission.save()
            except Exception as e:
                errors.append((submission.pk, e))

        if errors:
            print(len(errors), 'errors occurred. Summary below:')
            for pk, error in errors:
                print('Submission ', pk)
                print(error)

            sys.exit(1)
