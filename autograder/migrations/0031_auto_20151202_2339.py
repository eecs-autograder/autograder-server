# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0030_auto_20151202_2338'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studenttestsuitebase',
            name='compiler',
            field=models.CharField(max_length=255, default='g++'),
        ),
    ]
