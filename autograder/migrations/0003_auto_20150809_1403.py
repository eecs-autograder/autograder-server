# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0002_auto_20150808_2145'),
    ]

    operations = [
        migrations.AlterField(
            model_name='_submittedfile',
            name='submission',
            field=models.ForeignKey(related_name='_submitted_files', to='autograder.Submission'),
        ),
        migrations.AlterUniqueTogether(
            name='_submittedfile',
            unique_together=set([]),
        ),
    ]
