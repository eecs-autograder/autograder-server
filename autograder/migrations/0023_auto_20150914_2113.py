# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0022_auto_20150906_1744'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submissiongroup',
            name='project',
            field=models.ForeignKey(related_name='submission_groups', to='autograder.Project'),
        ),
    ]
