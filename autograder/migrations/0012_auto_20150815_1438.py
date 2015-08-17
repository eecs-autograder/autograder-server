# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0011_autogradertestcaseresultbase_submission'),
    ]

    operations = [
        migrations.AlterField(
            model_name='autogradertestcaseresultbase',
            name='submission',
            field=models.ForeignKey(null=True, default=None, to='autograder.Submission', related_name='results', blank=True),
        ),
    ]
