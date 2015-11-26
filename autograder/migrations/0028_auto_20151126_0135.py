# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0027_auto_20151126_0126'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studenttestsuitebase',
            name='implementation_file_alias',
            field=models.CharField(max_length=255, blank=True),
        ),
    ]
