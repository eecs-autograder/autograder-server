# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.models.student_test_suite.student_test_suite_result
import autograder.models.fields
import django.contrib.postgres.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0007_auto_20151204_2026'),
    ]

    operations = [
        migrations.AddField(
            model_name='studenttestsuitebase',
            name='compile_implementation_files',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='studenttestsuiteresult',
            name='detailed_results',
            field=django.contrib.postgres.fields.ArrayField(default=list, blank=True, base_field=autograder.models.fields.ClassField(editable=False, class_=autograder.models.student_test_suite.student_test_suite_result.StudentTestCaseEvaluationResult), size=None),
        ),
    ]
