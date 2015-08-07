# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='test_case_feedback_configuration',
            field=autograder.models.fields.FeedbackConfigurationField(validators=[autograder.models.fields._validate_feedback_configuration, autograder.models.fields._validate_feedback_configuration, autograder.models.fields._validate_feedback_configuration], default=dict),
        ),
    ]
