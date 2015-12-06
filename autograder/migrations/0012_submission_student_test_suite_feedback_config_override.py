# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.models.feedback_configuration
import autograder.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0011_project_student_test_suite_feedback_configuration'),
    ]

    operations = [
        migrations.AddField(
            model_name='submission',
            name='student_test_suite_feedback_config_override',
            field=autograder.models.fields.ClassField(default=None, editable=False, null=True, class_=autograder.models.feedback_configuration.StudentTestSuiteFeedbackConfiguration),
        ),
    ]
