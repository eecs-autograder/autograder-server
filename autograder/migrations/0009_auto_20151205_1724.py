# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0008_auto_20151204_2225'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studenttestsuiteresult',
            name='submission',
            field=models.ForeignKey(null=True, default=None, blank=True, to='autograder.Submission', related_name='suite_results'),
        ),
        migrations.AlterField(
            model_name='studenttestsuiteresult',
            name='test_suite',
            field=models.ForeignKey(to='autograder.StudentTestSuiteBase'),
        ),
    ]
