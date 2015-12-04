# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.postgres.fields
import autograder.models.fields
import autograder.models.student_test_suite.student_test_suite_result


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0002_auto_20151204_0131'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='studenttestsuiteresult',
            name='blah',
        ),
        migrations.AddField(
            model_name='studenttestsuiteresult',
            name='detailed_results',
            field=django.contrib.postgres.fields.ArrayField(blank=True, size=None, default=[], base_field=autograder.models.fields.ClassField(editable=False, class_=autograder.models.student_test_suite.student_test_suite_result.StudentTestCaseEvaluationResult)),
        ),
    ]
