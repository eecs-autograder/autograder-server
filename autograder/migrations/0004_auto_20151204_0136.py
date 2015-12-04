# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0003_auto_20151204_0133'),
    ]

    operations = [
        migrations.AddField(
            model_name='studenttestsuiteresult',
            name='submission',
            field=models.ForeignKey(blank=True, null=True, default=None, to='autograder.Submission'),
        ),
        migrations.AddField(
            model_name='studenttestsuiteresult',
            name='test_suite',
            field=models.ForeignKey(related_name='results', default=None, to='autograder.StudentTestSuiteBase'),
            preserve_default=False,
        ),
    ]
