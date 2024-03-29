# Generated by Django 3.2.2 on 2022-11-30 19:35

import autograder.core.fields
import autograder.core.models.ag_command.command
import autograder.core.models.mutation_test_suite.mutation_test_suite
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0098_alter_mutationtestsuite_grade_buggy_impl_command'),
    ]

    operations = [
        migrations.AddField(
            model_name='mutationtestsuite',
            name='test_name_discovery_whitespace_handling',
            field=models.CharField(blank=True, choices=[('newline', 'newline'), ('any_whitespace', 'any_whitespace')], default='any_whitespace', max_length=20),
        ),
        migrations.AlterField(
            model_name='mutationtestsuite',
            name='get_student_test_names_command',
            field=autograder.core.fields.ValidatedJSONField(default=autograder.core.models.mutation_test_suite.mutation_test_suite.new_make_default_get_student_test_names_cmd, help_text="This required command should print out a list of student\n             test case names. If test_name_discovery_whitespace_handling is set to\n             'any_whitespace', the output of this command will be parsed using\n             Python's str.split(). If set to 'newline', the output will\n             be parsed using Python's str.splitlines(), and leading and trailing\n             whitespace will be stripped from each line.", serializable_class=autograder.core.models.ag_command.command.Command),
        ),
        migrations.AlterField(
            model_name='mutationtestsuite',
            name='grade_buggy_impl_command',
            field=autograder.core.fields.ValidatedJSONField(default=autograder.core.models.mutation_test_suite.mutation_test_suite.new_make_default_grade_buggy_impl_command, help_text='This command will be run at least once for every buggy implementation.\n            A nonzero exit status indicates that the valid student tests exposed the\n            buggy impl, whereas an exit status of zero indicates that the student\n            tests did not expose the buggy impl.\n\n            This command must contain the placeholders ${buggy_impl_name}\n            and one of ${student_test_name} or ${all_valid_test_names}.\n            The placeholder ${buggy_impl_name} will be replaced with the name of\n            the buggy impl that the student test is being run against.\n            If the placeholder ${student_test_name} is present,\n            it will be replaced with the name of a single valid student test case,\n            and the command will be run once for every (buggy implementation, valid test) pair.\n            If the placeholder ${all_valid_test_names} is present,\n            it will be replaced with the individually-quoted names of all valid\n            student tests, and the command will be run once for each buggy implementation.\n\n            This latter approach can potentially reduce the runtime (e.g., by\n            reducing the number of times an interpreter is invoked).\n            Note that you may need to specify a higher time limit with this strategy--for\n            example, if each individual test takes 1 second to run and running\n            10 tests at once takes 10 seconds, the time limit will need to be\n            more than 10 seconds, otherwise buggy impls could be erroneously\n            marked as exposed due to the tests exceeding a low time limit.', serializable_class=autograder.core.models.ag_command.command.Command),
        ),
    ]
