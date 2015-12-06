# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0018_auto_20150823_0411'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submission',
            name='submission_group',
            field=models.ForeignKey(related_name='submissions', to='autograder.SubmissionGroup'),
        ),
    ]
