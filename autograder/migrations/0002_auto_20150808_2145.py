# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0001_initial'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='_submittedfile',
            unique_together=set([('submitted_file', 'submission')]),
        ),
    ]
