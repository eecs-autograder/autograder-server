# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0002_auto_20150807_1555'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='test_case_feedback_configuration',
            field=autograder.models.fields.FeedbackConfigurationField(default=dict, validators=[autograder.models.fields._validate_feedback_configuration, autograder.models.fields._validate_feedback_configuration, autograder.models.fields._validate_feedback_configuration]),
        ),
    ]
