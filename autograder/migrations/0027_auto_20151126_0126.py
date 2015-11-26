# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0026_auto_20151126_0125'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studenttestsuitebase',
            name='project',
            field=models.ForeignKey(to='autograder.Project', related_name='student_test_suites'),
        ),
    ]
