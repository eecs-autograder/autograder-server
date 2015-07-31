# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.models.project


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0002_auto_20150730_1716'),
    ]

    operations = [
        migrations.AlterField(
            model_name='_uploadedprojectfile',
            name='uploaded_file',
            field=models.FileField(max_length=510, upload_to=autograder.models.project._get_project_file_upload_to_dir, validators=[autograder.models.project._validate_filename]),
        ),
    ]
