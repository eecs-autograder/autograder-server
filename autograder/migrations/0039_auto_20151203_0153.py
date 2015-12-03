# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0038_studenttestsuitebase_compiler_flags'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studenttestsuitebase',
            name='compiler',
            field=models.CharField(max_length=255, default='g++', choices=[('g++', 'g++')]),
        ),
    ]
