# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.models.submission


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0003_auto_20150711_1624'),
    ]

    operations = [
        migrations.AlterField(
            model_name='_submittedfile',
            name='submitted_file',
            field=models.FileField(upload_to=autograder.models.submission._get_submission_file_upload_to_dir, validators=[autograder.models.submission._validate_filename], max_length=510),
        ),
    ]
