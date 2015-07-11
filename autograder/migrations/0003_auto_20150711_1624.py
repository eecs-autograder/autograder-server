# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.models.submission


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0002_submission_ignore_extra_files'),
    ]

    operations = [
        migrations.CreateModel(
            name='_SubmittedFile',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('submitted_file', models.FileField(validators=[autograder.models.submission._validate_filename], upload_to=autograder.models.submission._get_submission_file_upload_to_dir)),
            ],
        ),
        migrations.RemoveField(
            model_name='submission',
            name='submitted_files',
        ),
        migrations.AddField(
            model_name='_submittedfile',
            name='submission',
            field=models.ForeignKey(to='autograder.Submission', related_name='submitted_files'),
        ),
    ]
