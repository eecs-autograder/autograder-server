# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import autograder.shared.utilities


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0004_auto_20150707_1527'),
    ]

    operations = [
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('_timestamp', models.DateTimeField(auto_now_add=True)),
                ('submission_group', models.ForeignKey(to='autograder.SubmissionGroup')),
            ],
        ),
        migrations.AlterField(
            model_name='autogradertestcasebase',
            name='executable_name',
            field=models.CharField(max_length=255, validators=[autograder.shared.utilities.check_user_provided_filename], blank=True),
        ),
    ]
