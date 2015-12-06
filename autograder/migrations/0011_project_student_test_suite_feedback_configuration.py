# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.models.feedback_configuration
import autograder.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0010_studenttestsuitebase_points_per_buggy_implementation_exposed'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='student_test_suite_feedback_configuration',
            field=autograder.models.fields.ClassField(default=autograder.models.feedback_configuration.StudentTestSuiteFeedbackConfiguration, class_=autograder.models.feedback_configuration.StudentTestSuiteFeedbackConfiguration, editable=False),
        ),
    ]
