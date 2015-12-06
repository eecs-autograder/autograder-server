# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('autograder', '0009_auto_20151205_1724'),
    ]

    operations = [
        migrations.AddField(
            model_name='studenttestsuitebase',
            name='points_per_buggy_implementation_exposed',
            field=models.IntegerField(validators=[django.core.validators.MinValueValidator(0)], default=0),
        ),
    ]
