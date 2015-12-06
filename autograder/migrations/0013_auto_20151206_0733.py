# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0012_submission_student_test_suite_feedback_config_override'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studenttestsuiteresult',
            name='detailed_results',
            field=autograder.models.fields.ClassField(class_=list, editable=False, default=list, blank=True),
        ),
    ]
