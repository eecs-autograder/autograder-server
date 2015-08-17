# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0010_auto_20150812_1249'),
    ]

    operations = [
        migrations.AddField(
            model_name='autogradertestcaseresultbase',
            name='submission',
            field=models.ForeignKey(to='autograder.Submission', default=None, related_name='results', blank=True),
        ),
    ]
